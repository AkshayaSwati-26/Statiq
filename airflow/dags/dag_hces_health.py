"""
airflow/dags/dag_hces_health.py
================================
Airflow DAG — HCES Health (NSS Round 80) full ingestion pipeline.

Task chain (7 tasks):
  start
    → task_validate        (check files exist)
    → task_upload_raw      (upload .txt to MinIO)
    → task_parse_lvl01 ─┐
    → task_parse_lvl02 ─┤ (parallel)
    → task_parse_lvl04 ─┤
    → task_parse_lvl05 ─┘
    → task_load_postgres   (bulk load all 4 tables)
    → task_refresh_views   (refresh materialized views + clear Redis)
    → task_qc_report       (save QC JSON to MinIO)
  end

Trigger:  http://localhost:8080  → admin/admin → statiq_hces_health
CLI:      docker exec statiq-airflow-web airflow dags trigger statiq_hces_health
"""

import sys, os, time, logging
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty  import EmptyOperator
from airflow.utils.dates      import days_ago

sys.path.insert(0, '/opt/airflow/statiq_src')

from ingestion.fwf_parser  import (parse_layout_excel, parse_codes_excel,
                                    read_fwf_level, apply_codebook_labels,
                                    cast_types, validate_dataframe)
from ingestion.transforms  import (transform_hces_hh, transform_hces_members,
                                    transform_hces_hosp, transform_hces_outpatient)
from db.postgres_client    import StatIQDB
from db.minio_client       import StatIQStorage
from db.redis_client       import StatIQCache

log = logging.getLogger("statiq.dag.hces")

# ── Config ─────────────────────────────────────────────────────
DATA_DIR    = os.getenv("HCES_DATA_DIR",    "/data/raw/hces/")
LAYOUT_XLSX = os.getenv("HCES_LAYOUT_XLSX", "/data/layouts/Datalayout_250_80R.xlsx")
CODES_XLSX  = os.getenv("HCES_CODES_XLSX",  "/data/layouts/CODEs_for_Blocks_of_Sch__25_0.xlsx")
OUT_DIR     = os.getenv("STATIQ_OUTPUT_DIR","/data/processed/")
SURVEY_YEAR = "2024-25"
SURVEY_ID   = "hces_health_80"

LEVELS = {
    'lvl_01': {'file': 'h80_lvl_01.txt', 'table': 'hces_health_hh',
               'transform': transform_hces_hh},
    'lvl_02': {'file': 'h80_lvl_02.txt', 'table': 'hces_health_members',
               'transform': transform_hces_members},
    'lvl_04': {'file': 'h80_lvl_04.txt', 'table': 'hces_health_hosp',
               'transform': transform_hces_hosp},
    'lvl_05': {'file': 'h80_lvl_05.txt', 'table': 'hces_health_outpatient',
               'transform': transform_hces_outpatient},
}

# ── Tasks ──────────────────────────────────────────────────────

def task_validate(**ctx):
    log.info("[Task 1] Validating source files...")
    missing = []
    for cfg in LEVELS.values():
        fp = os.path.join(DATA_DIR, cfg['file'])
        if not os.path.exists(fp):
            missing.append(fp)
        else:
            log.info(f"  OK: {cfg['file']} ({os.path.getsize(fp)/1e6:.1f}MB)")
    for f in [LAYOUT_XLSX, CODES_XLSX]:
        if not os.path.exists(f): missing.append(f)
    if missing:
        raise FileNotFoundError("Missing files:\n" + "\n".join(missing))
    log.info("[Task 1] All files present.")


def task_upload_raw(**ctx):
    log.info("[Task 2] Uploading raw files to MinIO...")
    store = StatIQStorage()
    for cfg in LEVELS.values():
        fp = os.path.join(DATA_DIR, cfg['file'])
        if os.path.exists(fp):
            store.upload_raw_file(fp, f"hces_health/{SURVEY_YEAR}/{cfg['file']}")
    store.upload_raw_file(LAYOUT_XLSX, f"hces_health/{SURVEY_YEAR}/layout/Datalayout.xlsx")
    store.upload_raw_file(CODES_XLSX,  f"hces_health/{SURVEY_YEAR}/layout/CODEs.xlsx")
    log.info("[Task 2] Done.")


def _make_parse_task(lvl_key):
    def parse(**ctx):
        cfg  = LEVELS[lvl_key]
        t0   = time.time()
        log.info(f"[Task 3/{lvl_key}] Parsing {cfg['file']}...")

        layout   = parse_layout_excel(LAYOUT_XLSX)
        codebook = parse_codes_excel(CODES_XLSX)
        spec     = layout.get(lvl_key)
        if not spec:
            raise ValueError(f"Level {lvl_key} not found in layout.")

        df = read_fwf_level(os.path.join(DATA_DIR, cfg['file']), spec)
        df = apply_codebook_labels(df, codebook)
        df = cast_types(df)
        df = cfg['transform'](df, SURVEY_YEAR, SURVEY_ID)

        qc = validate_dataframe(df, f"hces/{lvl_key}")

        os.makedirs(OUT_DIR, exist_ok=True)
        parquet_path = os.path.join(OUT_DIR, f"{SURVEY_ID}_{cfg['table']}.parquet")
        df.to_parquet(parquet_path, index=False)

        store = StatIQStorage()
        store.upload_parquet(df, f"hces_health/{SURVEY_YEAR}/{cfg['table']}.parquet")

        ctx['ti'].xcom_push(key=f'rows_{lvl_key}', value=len(df))
        ctx['ti'].xcom_push(key=f'qc_{lvl_key}',   value=qc)
        log.info(f"[Task 3/{lvl_key}] Done: {len(df):,} rows in {time.time()-t0:.1f}s")

    parse.__name__ = f"parse_{lvl_key}"
    return parse


def task_load_postgres(**ctx):
    log.info("[Task 4] Bulk loading to PostgreSQL...")
    db = StatIQDB()
    
    from ingestion.metadata_generator import (extract_column_metadata,
                                              generate_sample_values,
                                              generate_dataset_profile,
                                              extract_dictionary_metadata,
                                              generate_relationship_metadata,
                                              generate_suggested_queries)
    layout   = parse_layout_excel(LAYOUT_XLSX)
    codebook = parse_codes_excel(CODES_XLSX)
    
    all_cols = []
    all_samples = []
    all_profiles = []
    
    for lvl, cfg in LEVELS.items():
        path = os.path.join(OUT_DIR, f"{SURVEY_ID}_{cfg['table']}.parquet")
        if not os.path.exists(path):
            log.warning(f"  Parquet missing for {lvl}: {path}")
            continue
        import pandas as pd
        df = pd.read_parquet(path)
        db.bulk_load(df, cfg['table'], if_exists='replace')
        
        spec = layout.get(lvl)
        if spec:
            cols = extract_column_metadata("hces_health", cfg['table'], df, spec)
            samps = generate_sample_values("hces_health", cfg['table'], df)
            prof = generate_dataset_profile("hces_health", cfg['table'], df)
            all_cols.extend(cols)
            all_samples.extend(samps)
            all_profiles.extend(prof)

    dict_meta = extract_dictionary_metadata("hces_health", codebook)
    rels_meta = generate_relationship_metadata("hces_health")
    queries_meta = generate_suggested_queries("hces_health")
    
    db.load_survey_metadata(
        survey_id="hces_health",
        relationships=rels_meta,
        dictionary=dict_meta,
        columns=all_cols,
        samples=all_samples,
        profiles=all_profiles,
        suggested_queries=queries_meta
    )
    log.info("[Task 4] Done.")



def task_refresh_views(**ctx):
    log.info("[Task 5] Refreshing materialized views...")
    StatIQDB().refresh_views()
    StatIQCache().invalidate_survey('hces_health')
    log.info("[Task 5] Done.")


def task_qc_report(**ctx):
    ti     = ctx['ti']
    total  = 0
    levels = {}
    for lvl in LEVELS:
        rows = ti.xcom_pull(key=f'rows_{lvl}') or 0
        qc   = ti.xcom_pull(key=f'qc_{lvl}')   or {}
        levels[lvl] = {'rows': rows, 'qc': qc}
        total += rows

    report = {
        'dag_run_id': ctx['run_id'], 'survey_id': SURVEY_ID,
        'survey_year': SURVEY_YEAR, 'completed_at': datetime.utcnow().isoformat(),
        'total_rows': total, 'levels': levels,
    }
    StatIQStorage().upload_json(
        report,
        f"hces_health/{SURVEY_YEAR}/qc_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.json"
    )
    log.info(f"[Task 6] QC report saved. Total rows: {total:,}")


# ── DAG definition ─────────────────────────────────────────────
default_args = {
    'owner': 'team_nexus', 'depends_on_past': False,
    'retries': 1, 'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='statiq_hces_health',
    description='HCES Health NSS 80 → PostgreSQL + MinIO',
    default_args=default_args,
    start_date=days_ago(1),
    schedule_interval='@monthly',
    catchup=False,
    tags=['statiq', 'hces', 'ingestion'],
) as dag:

    start = EmptyOperator(task_id='start')
    end   = EmptyOperator(task_id='end')

    t_validate   = PythonOperator(task_id='validate_files',   python_callable=task_validate)
    t_upload_raw = PythonOperator(task_id='upload_raw_minio', python_callable=task_upload_raw)

    parse_tasks  = {
        lvl: PythonOperator(task_id=f'parse_{lvl}', python_callable=_make_parse_task(lvl))
        for lvl in LEVELS
    }

    t_load   = PythonOperator(task_id='load_postgres',     python_callable=task_load_postgres)
    t_views  = PythonOperator(task_id='refresh_views',     python_callable=task_refresh_views)
    t_report = PythonOperator(task_id='qc_report',         python_callable=task_qc_report)

    # Dependency chain
    start >> t_validate >> t_upload_raw
    for pt in parse_tasks.values():
        t_upload_raw >> pt >> t_load
    t_load >> t_views >> t_report >> end
