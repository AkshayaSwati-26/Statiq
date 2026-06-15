"""
scripts/run_pipeline.py
========================
Run the complete ingestion pipeline without Airflow.
Use this for local testing or when Airflow is not available.

Usage:
  python scripts/run_pipeline.py --survey hces --nrows 1000   # test
  python scripts/run_pipeline.py --survey hces                 # full
  python scripts/run_pipeline.py --survey plfs                 # PLFS
  python scripts/run_pipeline.py --survey all                  # both
"""

import sys, os, argparse, logging, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("statiq.run")

from ingestion.fwf_parser import (parse_layout_excel, parse_codes_excel,
                                   read_fwf_level, apply_codebook_labels,
                                   cast_types, validate_dataframe)
from ingestion.transforms import (transform_hces_hh, transform_hces_members,
                                   transform_hces_hosp, transform_hces_outpatient,
                                   transform_plfs_person)
from db.postgres_client   import StatIQDB
from db.minio_client      import StatIQStorage
from db.redis_client      import StatIQCache

HCES_LEVELS = {
    'lvl_01': {'file': 'h80_lvl_01.txt', 'table': 'hces_health_hh',         'transform': transform_hces_hh},
    'lvl_02': {'file': 'h80_lvl_02.txt', 'table': 'hces_health_members',     'transform': transform_hces_members},
    'lvl_04': {'file': 'h80_lvl_04.txt', 'table': 'hces_health_hosp',        'transform': transform_hces_hosp},
    'lvl_05': {'file': 'h80_lvl_05.txt', 'table': 'hces_health_outpatient',  'transform': transform_hces_outpatient},
}


def run_hces(args):
    DATA_DIR    = os.getenv("HCES_DATA_DIR",    "data/raw/hces/")
    LAYOUT_XLSX = os.getenv("HCES_LAYOUT_XLSX", "data/layouts/Datalayout_250_80R.xlsx")
    CODES_XLSX  = os.getenv("HCES_CODES_XLSX",  "data/layouts/CODEs_for_Blocks_of_Sch__25_0.xlsx")
    OUT_DIR     = os.getenv("STATIQ_OUTPUT_DIR","data/processed/")
    SURVEY_YEAR = "2024-25"
    SURVEY_ID   = "hces_health_80"

    log.info("=" * 60)
    log.info("  HCES Health Ingestion")
    log.info(f"  Data dir:    {DATA_DIR}")
    log.info(f"  Layout:      {LAYOUT_XLSX}")
    log.info(f"  nrows limit: {args.nrows or 'ALL'}")
    log.info("=" * 60)

    layout   = parse_layout_excel(LAYOUT_XLSX)
    codebook = parse_codes_excel(CODES_XLSX)

    db    = StatIQDB()    if not args.no_db    else None
    store = StatIQStorage() if not args.no_minio else None

    os.makedirs(OUT_DIR, exist_ok=True)
    total = 0
    all_cols = []
    all_samples = []
    all_profiles = []

    for lvl_key, cfg in HCES_LEVELS.items():
        fp   = os.path.join(DATA_DIR, cfg['file'])
        if not os.path.exists(fp):
            log.warning(f"  File not found: {fp} — skipping")
            continue

        spec = layout.get(lvl_key)
        if not spec:
            log.warning(f"  Layout missing for {lvl_key} — skipping")
            continue

        t0 = time.time()
        log.info(f"\n[{lvl_key}] Parsing {cfg['file']}...")

        df = read_fwf_level(fp, spec, nrows=args.nrows)
        df = apply_codebook_labels(df, codebook)
        df = cast_types(df)
        df = cfg['transform'](df, SURVEY_YEAR, SURVEY_ID)
        qc = validate_dataframe(df, f"hces/{lvl_key}")

        parquet_out = os.path.join(OUT_DIR, f"{SURVEY_ID}_{cfg['table']}.parquet")
        df.to_parquet(parquet_out, index=False)
        log.info(f"  Saved: {parquet_out} ({os.path.getsize(parquet_out)/1e6:.1f}MB)")

        if store:
            store.upload_parquet(df, f"hces_health/{SURVEY_YEAR}/{cfg['table']}.parquet")
        if db:
            db.bulk_load(df, cfg['table'], if_exists='replace')
            from ingestion.metadata_generator import (extract_column_metadata,
                                                      generate_sample_values,
                                                      generate_dataset_profile)
            cols = extract_column_metadata("hces_health", cfg['table'], df, spec)
            samps = generate_sample_values("hces_health", cfg['table'], df)
            prof = generate_dataset_profile("hces_health", cfg['table'], df)
            all_cols.extend(cols)
            all_samples.extend(samps)
            all_profiles.extend(prof)

        total += len(df)
        log.info(f"  [{lvl_key}] {len(df):,} rows in {time.time()-t0:.1f}s")

    if db:
        from ingestion.metadata_generator import (extract_dictionary_metadata,
                                                  generate_relationship_metadata,
                                                  generate_suggested_queries)
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
        db.refresh_views()
        StatIQCache().invalidate_survey('hces_health')

    log.info(f"\nHCES complete: {total:,} total rows")



def run_plfs(args):
    DATA_DIR    = os.getenv("PLFS_DATA_DIR",    "data/raw/plfs/")
    LAYOUT_XLSX = os.getenv("PLFS_LAYOUT_XLSX", "data/layouts/PLFS_Layout.xlsx")
    CODES_XLSX  = os.getenv("PLFS_CODES_XLSX",  "data/layouts/PLFS_Codes.xlsx")
    OUT_DIR     = os.getenv("STATIQ_OUTPUT_DIR","data/processed/")
    SURVEY_YEAR = "2024-25"

    log.info("=" * 60)
    log.info("  PLFS Ingestion")
    log.info("=" * 60)

    layout   = parse_layout_excel(LAYOUT_XLSX)
    codebook = parse_codes_excel(CODES_XLSX)

    lvl_key = next((k for k in layout if 'per' in k.lower() or k == 'lvl_02'), list(layout.keys())[0])
    fp      = os.path.join(DATA_DIR, 'CPERV1.TXT')

    if not os.path.exists(fp):
        log.error(f"PLFS file not found: {fp}")
        return

    t0 = time.time()
    df = read_fwf_level(fp, layout[lvl_key], nrows=args.nrows)
    df = apply_codebook_labels(df, codebook)
    df = cast_types(df)
    df = transform_plfs_person(df, SURVEY_YEAR)
    validate_dataframe(df, 'plfs_person')

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, 'plfs_person.parquet')
    df.to_parquet(out, index=False)

    if not args.no_minio:
        StatIQStorage().upload_parquet(df, f"plfs/{SURVEY_YEAR}/plfs_person.parquet")
    if not args.no_db:
        db = StatIQDB()
        db.bulk_load(df, 'plfs_person', if_exists='replace')
        
        from ingestion.metadata_generator import (extract_column_metadata,
                                                  generate_sample_values,
                                                  generate_dataset_profile,
                                                  extract_dictionary_metadata,
                                                  generate_relationship_metadata,
                                                  generate_suggested_queries)
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
        db.refresh_views()
        StatIQCache().invalidate_survey('plfs')

    log.info(f"PLFS complete: {len(df):,} rows in {time.time()-t0:.1f}s")


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='StatIQ pipeline runner')
    p.add_argument('--survey',   required=True, choices=['hces','plfs','all'])
    p.add_argument('--nrows',    type=int, default=None, help='Row limit for testing')
    p.add_argument('--no-db',    action='store_true',    help='Skip PostgreSQL load')
    p.add_argument('--no-minio', action='store_true',    help='Skip MinIO upload')
    args = p.parse_args()

    if args.survey in ('hces', 'all'): run_hces(args)
    if args.survey in ('plfs', 'all'): run_plfs(args)
