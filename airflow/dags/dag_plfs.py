"""
airflow/dags/dag_plfs.py
=========================
Airflow DAG — PLFS 2024-25 (NSS Round 51) ingestion pipeline.
"""

import sys, os, time, logging
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty  import EmptyOperator
from airflow.utils.dates      import days_ago

sys.path.insert(0, '/opt/airflow/statiq_src')
from ingestion.fwf_parser import (parse_layout_excel, parse_codes_excel,
                                   read_fwf_level, apply_codebook_labels,
                                   cast_types, validate_dataframe)
from ingestion.transforms  import transform_plfs_person
from db.postgres_client    import StatIQDB
from db.minio_client       import StatIQStorage
from db.redis_client       import StatIQCache

log = logging.getLogger("statiq.dag.plfs")

DATA_DIR    = os.getenv("PLFS_DATA_DIR",    "/data/raw/plfs/")
LAYOUT_XLSX = os.getenv("PLFS_LAYOUT_XLSX", "/data/layouts/PLFS_Layout.xlsx")
CODES_XLSX  = os.getenv("PLFS_CODES_XLSX",  "/data/layouts/PLFS_Codes.xlsx")
OUT_DIR     = os.getenv("STATIQ_OUTPUT_DIR","/data/processed/")
SURVEY_YEAR = "2024-25"


def task_validate(**ctx):
    missing = []
    for f in [os.path.join(DATA_DIR,'CPERV1.TXT'), LAYOUT_XLSX, CODES_XLSX]:
        if not os.path.exists(f): missing.append(f)
        else: log.info(f"  OK: {f} ({os.path.getsize(f)/1e6:.1f}MB)")
    if missing: raise FileNotFoundError("Missing:\n" + "\n".join(missing))


def task_upload_raw(**ctx):
    store = StatIQStorage()
    for f in ['CPERV1.TXT', 'CHHV1.TXT']:
        fp = os.path.join(DATA_DIR, f)
        if os.path.exists(fp):
            store.upload_raw_file(fp, f"plfs/{SURVEY_YEAR}/{f}")
    store.upload_raw_file(LAYOUT_XLSX, f"plfs/{SURVEY_YEAR}/layout/Layout.xlsx")


def task_parse_person(**ctx):
    t0       = time.time()
    layout   = parse_layout_excel(LAYOUT_XLSX)
    codebook = parse_codes_excel(CODES_XLSX)
    lvl_key  = next((k for k in layout if 'per' in k.lower() or k=='lvl_01'), list(layout.keys())[0])
    df = read_fwf_level(os.path.join(DATA_DIR,'CPERV1.TXT'), layout[lvl_key])
    df = apply_codebook_labels(df, codebook)
    df = cast_types(df)
    df = transform_plfs_person(df, SURVEY_YEAR)
    qc = validate_dataframe(df, 'plfs_person')
    os.makedirs(OUT_DIR, exist_ok=True)
    df.to_parquet(os.path.join(OUT_DIR,'plfs_person.parquet'), index=False)
    StatIQStorage().upload_parquet(df, f"plfs/{SURVEY_YEAR}/plfs_person.parquet")
    ctx['ti'].xcom_push(key='rows', value=len(df))
    ctx['ti'].xcom_push(key='qc',   value=qc)
    log.info(f"PLFS person: {len(df):,} rows in {time.time()-t0:.1f}s")


def task_load(**ctx):
    import pandas as pd
    df = pd.read_parquet(os.path.join(OUT_DIR,'plfs_person.parquet'))
    db = StatIQDB()
    db.bulk_load(df, 'plfs_person', if_exists='replace')
    
    # Load metadata registry
    from ingestion.metadata_generator import (extract_column_metadata,
                                              generate_sample_values,
                                              generate_dataset_profile,
                                              extract_dictionary_metadata,
                                              generate_relationship_metadata,
                                              generate_suggested_queries)
    layout   = parse_layout_excel(LAYOUT_XLSX)
    codebook = parse_codes_excel(CODES_XLSX)
    lvl_key  = next((k for k in layout if 'per' in k.lower() or k=='lvl_01'), list(layout.keys())[0])
    
    cols = extract_column_metadata("plfs", "plfs_person", df, layout[lvl_key])
    samps = generate_sample_values("plfs", "plfs_person", df)
    prof = generate_dataset_profile("plfs", "plfs_person", df)
    dict_meta = extract_dictionary_metadata("plfs", codebook)
    rels_meta = generate_relationship_metadata("plfs")
    queries_meta = generate_suggested_queries("plfs")
    
    db.load_survey_metadata(
        survey_id="plfs",
        relationships=rels_meta,
        dictionary=dict_meta,
        columns=cols,
        samples=samps,
        profiles=prof,
        suggested_queries=queries_meta
    )



def task_refresh(**ctx):
    StatIQDB().refresh_views()
    StatIQCache().invalidate_survey('plfs')


def task_report(**ctx):
    ti   = ctx['ti']
    rows = ti.xcom_pull(key='rows') or 0
    report = {
        'dag_run_id': ctx['run_id'], 'survey': 'plfs',
        'survey_year': SURVEY_YEAR, 'completed_at': datetime.utcnow().isoformat(),
        'total_rows': rows, 'qc': ti.xcom_pull(key='qc') or {},
    }
    StatIQStorage().upload_json(
        report, f"plfs/{SURVEY_YEAR}/qc_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.json"
    )
    log.info(f"PLFS report saved. Total rows: {rows:,}")


default_args = {'owner':'team_nexus','depends_on_past':False,'retries':1,'retry_delay':timedelta(minutes=5)}

with DAG(
    dag_id='statiq_plfs', description='PLFS 2024-25 → PostgreSQL + MinIO',
    default_args=default_args, start_date=days_ago(1),
    schedule_interval='@monthly', catchup=False, tags=['statiq','plfs'],
) as dag:
    start = EmptyOperator(task_id='start')
    end   = EmptyOperator(task_id='end')
    t1 = PythonOperator(task_id='validate_files',   python_callable=task_validate)
    t2 = PythonOperator(task_id='upload_raw_minio', python_callable=task_upload_raw)
    t3 = PythonOperator(task_id='parse_person',     python_callable=task_parse_person)
    t4 = PythonOperator(task_id='load_postgres',    python_callable=task_load)
    t5 = PythonOperator(task_id='refresh_views',    python_callable=task_refresh)
    t6 = PythonOperator(task_id='qc_report',        python_callable=task_report)
    start >> t1 >> t2 >> t3 >> t4 >> t5 >> t6 >> end
