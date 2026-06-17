"""
src/db/postgres_client.py
==========================
PostgreSQL 16 + TimescaleDB client.

Responsibilities:
  - Bulk load DataFrames in 10k-row batches via SQLAlchemy
  - Create indexes after bulk load (3-5× faster than during)
  - Log every API call to TimescaleDB hypertable
  - Refresh materialized views after ingestion
  - Provide privacy-safe query execution (SELECT only, no PII)
"""

import os, io, time, hashlib, logging
from datetime import datetime
from typing import Optional
import pandas as pd
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.pool import QueuePool

log = logging.getLogger("statiq.db")

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://statiq:statiq123@localhost:5432/statiq"
)

# Columns the API layer is allowed to see (no PII)
SAFE_COLUMNS = {
    "plfs_person": [
        "state_name", "sector_label", "age_group", "gender_label",
        "education_label", "activity_label", "employment_status",
        "in_labour_force", "is_employed", "working_age",
        "multiplier", "survey_year",
    ],
    "hces_health_members": [
        "state_name", "sector_label", "gender_label", "age_group",
        "education_label", "insurance_label", "hospitalised",
        "hosp_times", "chronic_ailment", "ailment_15d", "multiplier", "survey_year",
    ],
    "hces_health_hosp": [
        "state_name", "sector_label", "ailment_label", "institution_label",
        "stay_days", "total_expense", "reimbursed", "out_of_pocket",
        "finance_label", "multiplier", "survey_year",
    ],
    "hces_health_hh": [
        "state_name", "sector_label", "hh_size", "religion_label",
        "social_label", "hh_type_label", "umce", "multiplier", "survey_year",
    ],
}

MATERIALIZED_VIEWS = ["mv_lfpr_by_state", "mv_hosp_rate"]


class StatIQDB:

    def __init__(self, db_url: str = DB_URL):
        self.engine = sa.create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=5,
            pool_pre_ping=True,
            connect_args={
                "options": "-c statement_timeout=60000",
                "application_name": "statiq_ingestion",
            },
        )
        with self.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        log.info("[DB] PostgreSQL connected.")
        self.create_metadata_tables()

    def create_metadata_tables(self):
        """Ensure metadata registry tables exist."""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS survey_metadata_relationships (
                id SERIAL PRIMARY KEY,
                survey_id VARCHAR(20) NOT NULL,
                parent_table VARCHAR(60) NOT NULL,
                child_table VARCHAR(60) NOT NULL,
                join_keys TEXT[] NOT NULL,
                relationship_type VARCHAR(20) DEFAULT 'one-to-many',
                description TEXT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS survey_metadata_dictionary (
                id SERIAL PRIMARY KEY,
                survey_id VARCHAR(20) NOT NULL,
                variable_name VARCHAR(60) NOT NULL,
                code VARCHAR(20) NOT NULL,
                code_description TEXT NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS survey_metadata_columns (
                id SERIAL PRIMARY KEY,
                survey_id VARCHAR(20) NOT NULL,
                table_name VARCHAR(60) NOT NULL,
                column_name VARCHAR(60) NOT NULL,
                data_type VARCHAR(30) NOT NULL,
                description TEXT,
                is_sensitive BOOLEAN DEFAULT FALSE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS survey_metadata_samples (
                id SERIAL PRIMARY KEY,
                survey_id VARCHAR(20) NOT NULL,
                table_name VARCHAR(60) NOT NULL,
                column_name VARCHAR(60) NOT NULL,
                sample_values JSONB NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS survey_metadata_profiles (
                id SERIAL PRIMARY KEY,
                survey_id VARCHAR(20) NOT NULL,
                table_name VARCHAR(60) NOT NULL,
                row_count BIGINT NOT NULL,
                column_count INT NOT NULL,
                missing_values BIGINT NOT NULL,
                profile_data JSONB NOT NULL,
                profiled_at TIMESTAMPTZ DEFAULT NOW()
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS survey_metadata_suggested_queries (
                id SERIAL PRIMARY KEY,
                survey_id VARCHAR(20) NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                sql_query TEXT NOT NULL
            );
            """
        ]
        with self.engine.connect() as conn:
            for q in queries:
                conn.execute(text(q))
            conn.commit()
        log.info("[DB] Metadata registry tables checked/created.")

    def load_survey_metadata(
        self,
        survey_id: str,
        relationships: list = None,
        dictionary: list = None,
        columns: list = None,
        samples: list = None,
        profiles: list = None,
        suggested_queries: list = None,
    ):
        """
        Truncate existing metadata for the given survey_id and load new values.
        Each input parameter is a list of dictionaries corresponding to the tables.
        """
        t0 = time.time()
        log.info(f"[DB] Loading registry metadata for survey: {survey_id}")

        # Inject survey_id into each record to satisfy SQLAlchemy execute parameter binding
        if relationships:
            for r in relationships:
                r["survey_id"] = survey_id
        if dictionary:
            for d in dictionary:
                d["survey_id"] = survey_id
        if columns:
            for c in columns:
                c["survey_id"] = survey_id
        if samples:
            for s in samples:
                s["survey_id"] = survey_id
        if profiles:
            for p in profiles:
                p["survey_id"] = survey_id
        if suggested_queries:
            for q in suggested_queries:
                q["survey_id"] = survey_id

        with self.engine.connect() as conn:
            # Delete existing metadata for this survey to keep it idempotent
            conn.execute(text("DELETE FROM survey_metadata_relationships WHERE survey_id = :s"), {"s": survey_id})
            conn.execute(text("DELETE FROM survey_metadata_dictionary WHERE survey_id = :s"), {"s": survey_id})
            conn.execute(text("DELETE FROM survey_metadata_columns WHERE survey_id = :s"), {"s": survey_id})
            conn.execute(text("DELETE FROM survey_metadata_samples WHERE survey_id = :s"), {"s": survey_id})
            conn.execute(text("DELETE FROM survey_metadata_profiles WHERE survey_id = :s"), {"s": survey_id})
            conn.execute(text("DELETE FROM survey_metadata_suggested_queries WHERE survey_id = :s"), {"s": survey_id})
            conn.commit()

            # Insert new data
            if relationships:
                conn.execute(text("""
                    INSERT INTO survey_metadata_relationships (survey_id, parent_table, child_table, join_keys, relationship_type, description)
                    VALUES (:survey_id, :parent_table, :child_table, :join_keys, :relationship_type, :description)
                """), relationships)

            if dictionary:
                conn.execute(text("""
                    INSERT INTO survey_metadata_dictionary (survey_id, variable_name, code, code_description)
                    VALUES (:survey_id, :variable_name, :code, :code_description)
                """), dictionary)

            if columns:
                conn.execute(text("""
                    INSERT INTO survey_metadata_columns (survey_id, table_name, column_name, data_type, description, is_sensitive)
                    VALUES (:survey_id, :table_name, :column_name, :data_type, :description, :is_sensitive)
                """), columns)

            if samples:
                import json
                for s in samples:
                    if not isinstance(s["sample_values"], str):
                        s["sample_values"] = json.dumps(s["sample_values"])
                conn.execute(text("""
                    INSERT INTO survey_metadata_samples (survey_id, table_name, column_name, sample_values)
                    VALUES (:survey_id, :table_name, :column_name, CAST(:sample_values AS jsonb))
                """), samples)

            if profiles:
                import json
                for p in profiles:
                    if not isinstance(p["profile_data"], str):
                        p["profile_data"] = json.dumps(p["profile_data"])
                conn.execute(text("""
                    INSERT INTO survey_metadata_profiles (survey_id, table_name, row_count, column_count, missing_values, profile_data)
                    VALUES (:survey_id, :table_name, :row_count, :column_count, :missing_values, CAST(:profile_data AS jsonb))
                """), profiles)

            if suggested_queries:
                conn.execute(text("""
                    INSERT INTO survey_metadata_suggested_queries (survey_id, title, description, sql_query)
                    VALUES (:survey_id, :title, :description, :sql_query)
                """), suggested_queries)

            conn.commit()

        log.info(f"[DB] Ingested metadata registry for {survey_id} in {time.time()-t0:.2f}s")


    # ── Bulk load ─────────────────────────────────────────────

    def bulk_load(
        self,
        df: pd.DataFrame,
        table_name: str,
        if_exists: str = "append",   # "replace" on first run, "append" for updates
        chunksize: int = 10_000,
    ) -> int:
        """
        Stream DataFrame into PostgreSQL.
        Uses psycopg2 COPY for large datasets (>50K rows) — 10-50× faster than INSERT.
        Falls back to to_sql for smaller datasets or test tables.
        """
        t0 = time.time()
        log.info(f"[DB] Loading {len(df):,} rows → {table_name} (mode={if_exists})")

        # Column mapping to match init.sql schema
        COLUMN_MAPPING = {
            'st':           'state_code',
            'sec':          'sector',
            'fsu':          'fsu_serial',
            'hhd':          'hh_serial',
            'mult':         'multiplier',
            'hhsz':         'hh_size',
            'b5i2':         'religion',
            'b5i3':         'social_group',
            'b5i4':         'hh_type',
            'b5i6':         'ins_premium',
            'b3c1':         'member_serial',
            'b3c4':         'gender',
            'b3c5':         'age',
            'b3c7':         'education_code',
            'b3c14':        'hospitalised',
            'b3c10':        'chronic_ailment',
            'b3c11':        'ailment_15d',
            'b3c17':        'insurance_code',
            'b3c16':        'vaccine_received',
            'b6i5':         'ailment_code',
            'b6i7':         'institution_type',
            'b6i12':        'stay_days',
            'b7i12':        'total_medical',
            'b7i15':        'total_expense',
            'b7i16':        'reimbursed',
            'b7i17':        'finance_source',
            'district':     'district_code',
            'round':        'round_no',
        }

        df_to_load = df.copy()
        # Rename columns that exist in the dataframe, but avoid duplicate target names
        rename_dict = {}
        for k, v in COLUMN_MAPPING.items():
            if k in df_to_load.columns and v not in df_to_load.columns:
                rename_dict[k] = v
        if rename_dict:
            df_to_load = df_to_load.rename(columns=rename_dict)

        with self.engine.connect() as conn:
            table_exists = conn.execute(text(
                "SELECT EXISTS (SELECT FROM pg_tables WHERE tablename = :t)"
            ), {"t": table_name}).scalar()
            
            if table_exists:
                if if_exists == "replace":
                    log.info(f"[DB] Table {table_name} exists. Truncating instead of dropping to preserve views.")
                    conn.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
                    conn.commit()
                    if_exists = "append"
                
                # Fetch matching columns from database schema
                result = conn.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = :t"
                ), {"t": table_name})
                db_columns = [row[0] for row in result]
                load_columns = [c for c in df_to_load.columns if c in db_columns]
                df_to_load = df_to_load[load_columns]
                log.info(f"[DB] Filtered to {len(load_columns)} matching columns for table {table_name}")
            else:
                log.info(f"[DB] Table {table_name} does not exist. Creating empty structure first.")
                df_to_load.head(0).to_sql(table_name, self.engine, if_exists="replace", index=False)

        # Always use COPY for maximum speed (psycopg2 COPY is 10-100x faster than to_sql)
        self._copy_load(df_to_load, table_name)

        elapsed = time.time() - t0
        log.info(f"[DB] {len(df):,} rows loaded in {elapsed:.1f}s "
                 f"({len(df)/max(elapsed,0.001):.0f} rows/s)")
        return len(df)

    def _copy_load(self, df: pd.DataFrame, table_name: str):
        """
        Use psycopg2 COPY FROM STDIN with CSV format — PostgreSQL's fastest bulk load path.
        Streams data through StringIO without writing temp files.
        Automatically casts float columns to integers when the DB expects smallint/int/bigint.
        """
        df = df.copy()

        # Query DB column types to fix float→int casting issues
        # (pandas stores int columns with NaN as float, e.g. 1.0 instead of 1)
        with self.engine.connect() as conn:
            result = conn.execute(text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = :t"
            ), {"t": table_name})
            int_cols = {row[0] for row in result if row[1] in ('smallint', 'integer', 'bigint')}

        for col in df.columns:
            if col in int_cols:
                # Force numeric coercion then convert to nullable Int64
                # Int64 (capital I) handles NaN natively — no float overflow
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
                except (ValueError, TypeError):
                    pass  # leave as-is if conversion fails

        columns = list(df.columns)
        col_list = ", ".join(f'"{c}"' for c in columns)
        copy_sql = f"COPY {table_name} ({col_list}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL '')"

        # Stream DataFrame to CSV in memory
        buffer = io.StringIO()
        df.to_csv(buffer, index=False, header=True)
        buffer.seek(0)

        # Use raw psycopg2 connection for COPY
        raw_conn = self.engine.raw_connection()
        try:
            cur = raw_conn.cursor()
            cur.copy_expert(copy_sql, buffer)
            raw_conn.commit()
            log.info(f"[DB] COPY loaded {len(df):,} rows into {table_name}")
        except Exception as e:
            raw_conn.rollback()
            log.error(f"[DB] COPY failed: {e}")
            raise
        finally:
            raw_conn.close()

    def bulk_load_with_indexes(
        self,
        df: pd.DataFrame,
        table_name: str,
        index_sqls: list,
        if_exists: str = "replace",
    ) -> int:
        """Load data then create indexes. Creating after bulk load is 3-5× faster."""
        n = self.bulk_load(df, table_name, if_exists=if_exists)
        with self.engine.connect() as conn:
            for sql in index_sqls:
                try:
                    conn.execute(text(sql))
                    log.debug(f"[DB] Index created: {sql[:60]}...")
                except Exception as e:
                    log.warning(f"[DB] Index skipped (may exist): {e}")
            conn.commit()
        return n

    # ── Safe query execution ──────────────────────────────────

    def execute_safe_query(
        self, sql: str, table_name: str, params: dict = None
    ) -> pd.DataFrame:
        """
        Execute a SELECT query and strip PII columns from the result.
        Only SELECT statements are allowed (enforced before DB hit).
        """
        if not sql.strip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT queries allowed.")
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params=params)
        safe = SAFE_COLUMNS.get(table_name, [])
        if safe:
            df = df[[c for c in safe if c in df.columns]]
        return df

    # ── TimescaleDB: API usage logging ────────────────────────

    def log_api_call(
        self,
        api_key_hash: str,
        endpoint: str,
        survey: str,
        sql: str,
        rows_returned: int,
        response_ms: int,
        cache_hit: bool = False,
        privacy_tier: str = "free",
        epsilon_used: float = 0.0,
        suppressed_cells: int = 0,
        user_ip_hash: str = "",
        status_code: int = 200,
    ):
        """
        Write one row to the TimescaleDB api_usage_log hypertable.
        SQL and keys are stored as SHA-256 hashes — never plaintext (DPDP compliant).
        Non-blocking: exceptions are swallowed so logging never breaks the API.
        """
        query_hash = hashlib.sha256(sql.encode()).hexdigest()
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO api_usage_log (
                        ts, api_key_hash, endpoint, survey, query_hash,
                        rows_returned, response_ms, cache_hit, privacy_tier,
                        epsilon_used, suppressed_cells, user_ip_hash, status_code
                    ) VALUES (
                        :ts, :ak, :ep, :sv, :qh,
                        :rr, :rm, :ch, :pt,
                        :eu, :sc, :ui, :st
                    )
                """), {
                    "ts": datetime.utcnow(), "ak": api_key_hash[:64],
                    "ep": endpoint[:100],    "sv": survey[:20],
                    "qh": query_hash,        "rr": rows_returned,
                    "rm": response_ms,       "ch": cache_hit,
                    "pt": privacy_tier[:20], "eu": epsilon_used,
                    "sc": suppressed_cells,  "ui": user_ip_hash[:64],
                    "st": status_code,
                })
                conn.commit()
        except Exception as e:
            log.warning(f"[DB] Usage log failed (non-critical): {e}")

    def get_usage_stats(self, api_key_hash: str, days: int = 30) -> list:
        """Usage stats using TimescaleDB time_bucket aggregation."""
        sql = """
            SELECT
                time_bucket('1 day', ts) AS day,
                COUNT(*)                 AS calls,
                SUM(rows_returned)       AS total_rows,
                AVG(response_ms)::INT    AS avg_latency_ms,
                SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) AS cache_hits
            FROM api_usage_log
            WHERE api_key_hash = :kh
              AND ts >= NOW() - INTERVAL '30 days'
            GROUP BY 1 ORDER BY 1 DESC
        """
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params={"kh": api_key_hash})
        return df.to_dict(orient="records")

    # ── Materialized views ────────────────────────────────────

    def refresh_views(self):
        """
        Refresh pre-computed indicator views after each ingestion.
        CONCURRENTLY means the view remains readable during refresh.
        """
        for view in MATERIALIZED_VIEWS:
            t0 = time.time()
            with self.engine.connect() as conn:
                try:
                    conn.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}"))
                    conn.commit()
                    log.info(f"[DB] Refreshed {view} CONCURRENTLY in {time.time()-t0:.1f}s")
                except Exception as e:
                    try:
                        conn.execute(text("ROLLBACK"))
                        conn.execute(text(f"REFRESH MATERIALIZED VIEW {view}"))
                        conn.commit()
                        log.info(f"[DB] Refreshed {view} (non-concurrently) in {time.time()-t0:.1f}s")
                    except Exception as e2:
                        log.warning(f"[DB] View refresh failed {view}: {e2}")

    def health(self) -> dict:
        with self.engine.connect() as conn:
            row = conn.execute(text(
                "SELECT version(), pg_database_size('statiq')/1024/1024 AS db_mb"
            )).fetchone()
        return {"status": "ok", "pg_version": str(row[0])[:30], "db_size_mb": row[1]}
