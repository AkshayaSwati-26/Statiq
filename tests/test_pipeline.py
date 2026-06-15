"""
tests/test_pipeline.py
=======================
Unit + integration tests for all ingestion modules.

Run all:
    cd statiq_ingestion
    pytest tests/test_pipeline.py -v

Run fast tests only (no Docker needed):
    pytest tests/test_pipeline.py -v -k "not Redis and not MinIO and not Postgres"

Run integration tests (Docker must be running):
    pytest tests/test_pipeline.py -v -k "Redis or MinIO or Postgres"
"""

import sys, os, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

import pytest
import pandas as pd
import numpy as np


# ─────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def minimal_fwf_bytes():
    """10 synthetic FWF records, 150 chars each, latin-1 encoded."""
    lines = []
    for i in range(10):
        record = (
            "80"       # round
            "250"      # schedule
            "1"        # sample
            "55"       # ??
            "81"       # ??
            "1101013"  # id block
            "0100101"
            "1122 6 "
            f"{str(i+1).zfill(2)}"
            " " * 120  # pad to 150
        )
        lines.append(record[:150].ljust(150))
    return "\n".join(lines).encode("latin-1")


@pytest.fixture
def minimal_layout():
    """Minimal layout spec — 4 fields, official 1-indexed positions."""
    return {
        "meta": {"record_length": 150, "filename": "TEST.TXT"},
        "fields": [
            {"name": "rnd",  "full_name": "Round",   "length": 2,
             "official_start": 1,  "official_end": 2,
             "python_start": 0,  "python_end": 2,  "colspec": (0,2),  "remarks": ""},
            {"name": "sch",  "full_name": "Schedule","length": 3,
             "official_start": 3,  "official_end": 5,
             "python_start": 2,  "python_end": 5,  "colspec": (2,5),  "remarks": ""},
            {"name": "sec",  "full_name": "Sector",  "length": 1,
             "official_start": 6,  "official_end": 6,
             "python_start": 5,  "python_end": 6,  "colspec": (5,6),  "remarks": ""},
            {"name": "st",   "full_name": "State",   "length": 2,
             "official_start": 21, "official_end": 22,
             "python_start": 20, "python_end": 22, "colspec": (20,22),"remarks": ""},
        ]
    }


@pytest.fixture
def minimal_codebook():
    return {
        "sec": {"1": "Rural", "2": "Urban"},
        "st":  {"33": "Tamil Nadu", "28": "Andhra Pradesh", "01": "J&K"},
        "b3c4": {"1": "Male", "2": "Female", "3": "Transgender"},
        "b3c17":{"01": "AB-PMJAY", "19": "Not covered"},
    }


@pytest.fixture
def sample_members_df():
    """Minimal HCES members-like DataFrame for transform tests."""
    return pd.DataFrame({
        "st":    ["33", "28", "01", "33", "28"],
        "sec":   ["1",  "2",  "1",  "2",  "1"],
        "b3c4":  ["1",  "2",  "1",  "2",  "2"],
        "b3c5":  ["25", "45", "8",  "65", "30"],
        "b3c7":  ["06", "09", "04", "12", "07"],
        "b3c9":  ["1",  "2",  "2",  "1",  "2"],
        "b3c14": ["2",  "1",  "2",  "1",  "2"],
        "b3c17": ["01", "19", "19", "01", "02"],
        "mult":  [16275.0, 8200.0, 9500.0, 12000.0, 7800.0],
    })


@pytest.fixture
def sample_plfs_df():
    """Minimal PLFS person-like DataFrame."""
    return pd.DataFrame({
        "st":              ["33", "33", "33", "28", "28"],
        "sec":             ["1",  "1",  "2",  "1",  "2"],
        "b3c4":            ["1",  "2",  "1",  "2",  "1"],
        "b3c5":            ["30", "25", "60", "15", "40"],
        "usual_activity":  ["21", "91", "93", "51", "11"],
        "multiplier":      [8000.0, 9000.0, 7000.0, 6000.0, 11000.0],
    })


# ─────────────────────────────────────────────────────────────
# TEST: FWF PARSER
# ─────────────────────────────────────────────────────────────

class TestFWFParser:

    def test_1_to_0_index_conversion(self, minimal_layout):
        """
        THE CORE RULE:
          python_start = official_start - 1
          python_end   = official_end  (unchanged)
        """
        for f in minimal_layout["fields"]:
            assert f["python_start"] == f["official_start"] - 1, (
                f"{f['name']}: python_start={f['python_start']} "
                f"should be official_start-1={f['official_start']-1}"
            )
            assert f["python_end"] == f["official_end"], (
                f"{f['name']}: python_end={f['python_end']} "
                f"should equal official_end={f['official_end']}"
            )

    def test_colspec_tuple(self, minimal_layout):
        """colspec = (python_start, python_end)."""
        for f in minimal_layout["fields"]:
            assert f["colspec"] == (f["python_start"], f["python_end"])

    def test_read_fwf_from_bytes_shape(self, minimal_fwf_bytes, minimal_layout):
        """FWF reader returns correct row and column count."""
        from ingestion.fwf_parser import read_fwf_from_bytes
        df = read_fwf_from_bytes(minimal_fwf_bytes, minimal_layout)
        assert len(df) == 10
        assert list(df.columns) == ["rnd", "sch", "sec", "st"]

    def test_read_fwf_round_column(self, minimal_fwf_bytes, minimal_layout):
        """Round column extracted correctly from position 0:2."""
        from ingestion.fwf_parser import read_fwf_from_bytes
        df = read_fwf_from_bytes(minimal_fwf_bytes, minimal_layout)
        assert df["rnd"].iloc[0] == "80"

    def test_read_fwf_nrows_limit(self, minimal_fwf_bytes, minimal_layout):
        """nrows parameter limits rows read."""
        from ingestion.fwf_parser import read_fwf_from_bytes
        df = read_fwf_from_bytes(minimal_fwf_bytes, minimal_layout, nrows=5)
        assert len(df) == 5

    def test_apply_codebook_label_hit(self, sample_members_df, minimal_codebook):
        """Known code maps to correct label."""
        from ingestion.fwf_parser import apply_codebook_labels
        df = apply_codebook_labels(sample_members_df.copy(), minimal_codebook)
        assert "sec_label" in df.columns
        assert df.loc[df["sec"] == "1", "sec_label"].iloc[0] == "Rural"
        assert df.loc[df["sec"] == "2", "sec_label"].iloc[0] == "Urban"

    def test_apply_codebook_unknown_code_is_nan(self, sample_members_df, minimal_codebook):
        """Unknown code maps to NaN — no KeyError raised."""
        from ingestion.fwf_parser import apply_codebook_labels
        df = sample_members_df.copy()
        df.loc[0, "sec"] = "9"     # invalid
        df = apply_codebook_labels(df, minimal_codebook)
        assert pd.isna(df.loc[0, "sec_label"])

    def test_apply_codebook_insurance(self, sample_members_df, minimal_codebook):
        """Insurance code 01 → AB-PMJAY, 19 → Not covered."""
        from ingestion.fwf_parser import apply_codebook_labels
        df = apply_codebook_labels(sample_members_df.copy(), minimal_codebook)
        assert df.loc[df["b3c17"] == "01", "b3c17_label"].iloc[0] == "AB-PMJAY"
        assert df.loc[df["b3c17"] == "19", "b3c17_label"].iloc[0] == "Not covered"

    def test_cast_types_numeric_fields(self, sample_members_df):
        """mult column is cast to float."""
        from ingestion.fwf_parser import cast_types
        df = sample_members_df.copy()
        df["mult"] = df["mult"].astype(str)
        df = cast_types(df)
        assert pd.api.types.is_float_dtype(df["mult"])

    def test_cast_types_string_cleaning(self):
        """String 'nan' becomes actual NaN."""
        from ingestion.fwf_parser import cast_types
        df = pd.DataFrame({"st": ["33", "nan", "  28  "], "mult": ["100", "nan", "200"]})
        df = cast_types(df)
        assert pd.isna(df.loc[1, "st"])
        assert df.loc[2, "st"] == "28"

    def test_validate_null_state(self):
        """QC report flags null state correctly."""
        from ingestion.fwf_parser import validate_dataframe
        df = pd.DataFrame({"st": [None, "33", None, "28"], "b3c4": ["1","2","1","2"]})
        qc = validate_dataframe(df, "test")
        assert qc["total_rows"] == 4
        null_issue = next((i for i in qc["issues"] if "state" in i["check"]), None)
        assert null_issue is not None
        assert null_issue["count"] == 2

    def test_validate_age_outliers(self):
        """QC report catches negative and > 120 ages."""
        from ingestion.fwf_parser import validate_dataframe
        df = pd.DataFrame({
            "st":   ["33","33","33"],
            "b3c4": ["1","2","1"],
            "b3c5": [25, -1, 150],
        })
        qc = validate_dataframe(df, "test")
        outlier = next((i for i in qc["issues"] if "outlier" in i["check"]), None)
        assert outlier is not None
        assert outlier["count"] == 2


# ─────────────────────────────────────────────────────────────
# TEST: TRANSFORMS
# ─────────────────────────────────────────────────────────────

class TestTransforms:

    def test_hces_members_state_name(self, sample_members_df):
        """State code 33 → Tamil Nadu."""
        from ingestion.transforms import transform_hces_members
        df = transform_hces_members(sample_members_df.copy(), "2024-25", "test")
        assert "state_name" in df.columns
        assert df.loc[df["st"] == "33", "state_name"].iloc[0] == "Tamil Nadu"

    def test_hces_members_sector_label(self, sample_members_df):
        """Sector 1 → Rural, 2 → Urban."""
        from ingestion.transforms import transform_hces_members
        df = transform_hces_members(sample_members_df.copy(), "2024-25", "test")
        assert df.loc[df["sec"] == "1", "sector_label"].iloc[0] == "Rural"
        assert df.loc[df["sec"] == "2", "sector_label"].iloc[0] == "Urban"

    def test_hces_members_gender_label(self, sample_members_df):
        """b3c4 code 1 → Male, 2 → Female."""
        from ingestion.transforms import transform_hces_members
        df = transform_hces_members(sample_members_df.copy(), "2024-25", "test")
        assert df.loc[df["b3c4"] == "1", "gender_label"].iloc[0] == "Male"
        assert df.loc[df["b3c4"] == "2", "gender_label"].iloc[0] == "Female"

    def test_hces_members_age_group(self, sample_members_df):
        """Age 25 → 25-34, age 45 → 45-59, age 8 → 5-14, age 65 → 60+."""
        from ingestion.transforms import transform_hces_members
        df = transform_hces_members(sample_members_df.copy(), "2024-25", "test")
        assert "age_group" in df.columns
        age_map = dict(zip(df["b3c5"], df["age_group"]))
        assert age_map["25"] == "25-34"
        assert age_map["45"] == "45-59"
        assert age_map["8"]  == "5-14"
        assert age_map["65"] == "60+"

    def test_hces_members_survey_year(self, sample_members_df):
        """survey_year added to every row."""
        from ingestion.transforms import transform_hces_members
        df = transform_hces_members(sample_members_df.copy(), "2024-25", "test")
        assert (df["survey_year"] == "2024-25").all()

    def test_hces_members_insurance_label(self, sample_members_df):
        """b3c17 code 01 → AB-PMJAY, 19 → Not covered."""
        from ingestion.transforms import transform_hces_members
        df = transform_hces_members(sample_members_df.copy(), "2024-25", "test")
        assert df.loc[df["b3c17"] == "01", "insurance_label"].iloc[0] == "AB-PMJAY"
        assert df.loc[df["b3c17"] == "19", "insurance_label"].iloc[0] == "Not covered"

    def test_hces_hosp_out_of_pocket(self):
        """out_of_pocket = b7i15 - b7i16."""
        from ingestion.transforms import transform_hces_hosp
        df = pd.DataFrame({
            "st": ["33"], "sec": ["1"],
            "b6i5": ["35"], "b6i7": ["3"], "b7i17": ["1"],
            "b7i15": [50000.0], "b7i16": [10000.0], "mult": [5000.0],
        })
        out = transform_hces_hosp(df, "2024-25", "test")
        assert out["out_of_pocket"].iloc[0] == 40000.0

    def test_hces_hosp_zero_reimbursement(self):
        """out_of_pocket = total when reimbursement is 0."""
        from ingestion.transforms import transform_hces_hosp
        df = pd.DataFrame({
            "st": ["28"], "sec": ["2"],
            "b6i5": ["17"], "b6i7": ["3"], "b7i17": ["2"],
            "b7i15": [75000.0], "b7i16": [0.0], "mult": [8000.0],
        })
        out = transform_hces_hosp(df, "2024-25", "test")
        assert out["out_of_pocket"].iloc[0] == 75000.0

    def test_plfs_employment_status(self, sample_plfs_df):
        """Activity 21 → Employed, 91 → NLF, 51 → Unemployed."""
        from ingestion.transforms import transform_plfs_person
        df = transform_plfs_person(sample_plfs_df.copy(), "2024-25")
        es = dict(zip(df["usual_activity"], df["employment_status"]))
        assert es["21"] == "Employed"
        assert es["91"] == "NLF"
        assert es["51"] == "Unemployed"

    def test_plfs_in_labour_force_flag(self, sample_plfs_df):
        """in_labour_force = 1 for Employed/Unemployed, 0 for NLF."""
        from ingestion.transforms import transform_plfs_person
        df = transform_plfs_person(sample_plfs_df.copy(), "2024-25")
        employed   = df[df["employment_status"] == "Employed"]["in_labour_force"]
        unemployed = df[df["employment_status"] == "Unemployed"]["in_labour_force"]
        nlf        = df[df["employment_status"] == "NLF"]["in_labour_force"]
        assert (employed == 1).all()
        assert (unemployed == 1).all()
        assert (nlf == 0).all()

    def test_plfs_working_age_flag(self, sample_plfs_df):
        """working_age = 1 for ages 15–59 only."""
        from ingestion.transforms import transform_plfs_person
        df = transform_plfs_person(sample_plfs_df.copy(), "2024-25")
        wa = dict(zip(df["b3c5"].astype(int), df["working_age"]))
        assert wa[30] == 1
        assert wa[25] == 1
        assert wa[60] == 0    # 60 is outside 15-59
        assert wa[15] == 1
        assert wa[40] == 1

    def test_compute_age_group_boundaries(self):
        """Age group boundaries are correct at every edge."""
        from ingestion.transforms import compute_age_group
        ages   = pd.Series([0, 4, 5, 14, 15, 24, 25, 34, 35, 44, 45, 59, 60, 99])
        groups = compute_age_group(ages)
        expected = ['0-4','0-4','5-14','5-14','15-24','15-24',
                    '25-34','25-34','35-44','35-44','45-59','45-59','60+','60+']
        assert groups.tolist() == expected

    def test_compute_weighted_lfpr(self, sample_plfs_df):
        """LFPR computed using multiplier weights, not raw counts."""
        from ingestion.transforms import transform_plfs_person, compute_weighted_lfpr
        df  = transform_plfs_person(sample_plfs_df.copy(), "2024-25")
        agg = compute_weighted_lfpr(df, group_cols=["state_name", "survey_year"])
        assert "lfpr_pct" in agg.columns
        assert (agg["lfpr_pct"] >= 0).all()
        assert (agg["lfpr_pct"] <= 100).all()


# ─────────────────────────────────────────────────────────────
# TEST: REDIS CACHE
# ─────────────────────────────────────────────────────────────

class TestRedisCache:

    @pytest.fixture(autouse=True)
    def skip_no_redis(self):
        try:
            import redis
            redis.Redis(host="localhost", port=6379).ping()
        except Exception:
            pytest.skip("Redis not running — start with: docker-compose up -d redis")

    def test_nl_sql_miss_then_hit(self):
        from db.redis_client import StatIQCache
        c = StatIQCache()
        q, s = "female LFPR Tamil Nadu", "plfs"
        c.r.delete(f"nlsql:{c._hash(q, s)}")
        assert c.get_nl_sql(q, s) is None          # MISS
        c.set_nl_sql(q, s, "SELECT state_name FROM plfs_person WHERE gender='2'")
        result = c.get_nl_sql(q, s)
        assert result is not None                   # HIT
        assert "plfs_person" in result

    def test_result_cache_roundtrip(self):
        from db.redis_client import StatIQCache
        c = StatIQCache()
        sql  = "SELECT state_name, COUNT(*) FROM plfs_person GROUP BY 1"
        tier = "free"
        data = {"rows": [{"state_name": "Tamil Nadu", "count": 4820}]}
        c.set_query_result(sql, tier, data, ttl=60)
        out = c.get_query_result(sql, tier)
        assert out is not None
        assert out["rows"][0]["state_name"] == "Tamil Nadu"

    def test_rate_limit_under_limit(self):
        from db.redis_client import StatIQCache
        c = StatIQCache()
        key = "test_under_limit"
        c.r.delete(f"rate:{key}")
        allowed, remaining = c.check_rate_limit(key, limit_per_minute=10)
        assert allowed is True
        assert remaining == 9

    def test_rate_limit_over_limit(self):
        import time
        from db.redis_client import StatIQCache
        c = StatIQCache()
        key = "test_over_limit"
        c.r.delete(f"rate:{key}")
        for _ in range(5):
            c.check_rate_limit(key, limit_per_minute=3)
            time.sleep(0.02)
        allowed, remaining = c.check_rate_limit(key, limit_per_minute=3)
        assert allowed is False
        assert remaining == 0

    def test_monthly_counter(self):
        from db.redis_client import StatIQCache
        import datetime
        c   = StatIQCache()
        key = "test_monthly_xyz"
        now = datetime.datetime.utcnow()
        c.r.delete(f"quota:{key}:{now.year}:{now.month:02d}")
        n1 = c.increment_monthly_calls(key)
        n2 = c.increment_monthly_calls(key)
        assert n2 == n1 + 1

    def test_invalidate_survey(self):
        from db.redis_client import StatIQCache
        c = StatIQCache()
        c.set_query_result("SELECT * FROM plfs_person", "free",
                           {"rows": []}, ttl=300)
        c.invalidate_survey("plfs")
        result = c.get_query_result("SELECT * FROM plfs_person", "free")
        assert result is None


# ─────────────────────────────────────────────────────────────
# TEST: MINIO STORAGE
# ─────────────────────────────────────────────────────────────

class TestMinIOStorage:

    @pytest.fixture(autouse=True)
    def skip_no_minio(self):
        try:
            from minio import Minio
            Minio("localhost:9000", access_key="statiq",
                  secret_key="statiq123", secure=False).list_buckets()
        except Exception:
            pytest.skip("MinIO not running — start with: docker-compose up -d minio")

    def test_buckets_exist(self):
        from db.minio_client import StatIQStorage, ALL_BUCKETS
        s = StatIQStorage()
        for b in ALL_BUCKETS:
            assert s.client.bucket_exists(b), f"Bucket missing: {b}"

    def test_parquet_upload_download_roundtrip(self):
        from db.minio_client import StatIQStorage
        s  = StatIQStorage()
        df = pd.DataFrame({"state": ["TN", "KA", "MH"], "lfpr_pct": [42.1, 38.5, 44.3]})
        s.upload_parquet(df, "test/roundtrip_test.parquet")
        out = s.read_parquet("test/roundtrip_test.parquet")
        assert len(out) == 3
        assert list(out.columns) == ["state", "lfpr_pct"]
        assert out["lfpr_pct"].iloc[0] == pytest.approx(42.1)

    def test_spark_path_format(self):
        from db.minio_client import StatIQStorage, BUCKET_PARQUET
        s    = StatIQStorage()
        path = s.get_spark_path("plfs/plfs_person.parquet")
        assert path.startswith("s3a://")
        assert BUCKET_PARQUET in path
        assert "plfs_person.parquet" in path

    def test_json_upload(self):
        from db.minio_client import StatIQStorage
        s    = StatIQStorage()
        data = {"survey": "plfs", "rows": 1148634, "status": "ok"}
        url  = s.upload_json(data, "test/test_manifest.json")
        assert "statiq-processed" in url


# ─────────────────────────────────────────────────────────────
# TEST: POSTGRESQL
# ─────────────────────────────────────────────────────────────

class TestPostgres:

    @pytest.fixture(autouse=True)
    def skip_no_postgres(self):
        try:
            from db.postgres_client import StatIQDB
            StatIQDB()
        except Exception:
            pytest.skip("PostgreSQL not running — start with: docker-compose up -d postgres")

    def test_bulk_load_and_count(self):
        from db.postgres_client import StatIQDB
        from sqlalchemy import text
        db = StatIQDB()
        df = pd.DataFrame({
            "state_name":  ["Tamil Nadu", "Karnataka"],
            "survey_year": ["2024-25",    "2024-25"],
            "gender_label":["Male",       "Female"],
            "multiplier":  [8000.0,        9000.0],
        })
        db.bulk_load(df, "__test_bulk__", if_exists="replace")
        with db.engine.connect() as conn:
            n = conn.execute(text("SELECT COUNT(*) FROM __test_bulk__")).scalar()
            conn.execute(text("DROP TABLE IF EXISTS __test_bulk__"))
            conn.commit()
        assert n == 2

    def test_safe_columns_no_pii(self):
        """PII columns must NOT appear in SAFE_COLUMNS."""
        from db.postgres_client import SAFE_COLUMNS
        for table, cols in SAFE_COLUMNS.items():
            assert "fsu_serial"  not in cols, f"{table} exposes fsu_serial"
            assert "hh_serial"   not in cols, f"{table} exposes hh_serial"
            assert "state_name"  in cols,     f"{table} missing state_name"
            assert "survey_year" in cols,     f"{table} missing survey_year"

    def test_api_usage_log_insert(self):
        from db.postgres_client import StatIQDB
        from sqlalchemy import text
        db = StatIQDB()
        db.log_api_call(
            api_key_hash="testhash123", endpoint="/api/v1/query/nl",
            survey="plfs", sql="SELECT state_name FROM plfs_person",
            rows_returned=500, response_ms=220, cache_hit=False,
            privacy_tier="free",
        )
        with db.engine.connect() as conn:
            n = conn.execute(text(
                "SELECT COUNT(*) FROM api_usage_log WHERE api_key_hash='testhash123'"
            )).scalar()
        assert n >= 1

    def test_health_check(self):
        from db.postgres_client import StatIQDB
        h = StatIQDB().health()
        assert h["status"] == "ok"
        assert "pg_version" in h


# ─────────────────────────────────────────────────────────────
# INTEGRATION: full pipeline on synthetic data
# ─────────────────────────────────────────────────────────────

class TestEndToEnd:

    def test_parse_transform_save_parquet(self, tmp_path, minimal_fwf_bytes,
                                          minimal_layout, minimal_codebook,
                                          sample_members_df):
        """Full mini pipeline: bytes → parse → label → cast → transform → parquet."""
        from ingestion.fwf_parser import (read_fwf_from_bytes,
                                           apply_codebook_labels, cast_types)
        from ingestion.transforms import transform_hces_members

        # Parse
        df = read_fwf_from_bytes(minimal_fwf_bytes, minimal_layout)
        assert len(df) == 10

        # Labels
        df = apply_codebook_labels(df, minimal_codebook)
        assert "sec_label" in df.columns

        # Provide required cols for transform
        df["b3c4"]  = "2"
        df["b3c5"]  = "35"
        df["b3c7"]  = "09"
        df["b3c17"] = "19"
        df["mult"]  = 10000.0

        # Transform
        df = cast_types(df)
        df = transform_hces_members(df, "2024-25", "test")

        assert "state_name"   in df.columns
        assert "sector_label" in df.columns
        assert "gender_label" in df.columns
        assert "age_group"    in df.columns
        assert (df["survey_year"] == "2024-25").all()

        # Save parquet
        out = tmp_path / "test_output.parquet"
        df.to_parquet(out, index=False)
        loaded = pd.read_parquet(out)
        assert len(loaded) == len(df)
        assert "state_name" in loaded.columns
