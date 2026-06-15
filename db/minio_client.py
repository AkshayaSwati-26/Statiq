"""
src/storage/minio_client.py
============================
MinIO S3-compatible object storage client.

Buckets:
  statiq-raw       ← original .txt and .xlsx files from MoSPI
  statiq-parquet   ← cleaned Parquet files (read by Spark + FastAPI)
  statiq-processed ← QC reports and CSV exports

All read/write operations are in-memory (no temp files on disk).
"""

import io
import os
import logging
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from minio import Minio
from minio.error import S3Error

log = logging.getLogger("statiq.storage")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT",  "localhost:9000")
MINIO_ACCESS   = os.getenv("MINIO_ACCESS_KEY", "statiq")
MINIO_SECRET   = os.getenv("MINIO_SECRET_KEY", "statiq123")
MINIO_SECURE   = os.getenv("MINIO_SECURE",     "false").lower() == "true"

BUCKET_RAW       = "statiq-raw"
BUCKET_PARQUET   = "statiq-parquet"
BUCKET_PROCESSED = "statiq-processed"
ALL_BUCKETS      = [BUCKET_RAW, BUCKET_PARQUET, BUCKET_PROCESSED]


class StatIQStorage:

    def __init__(self):
        self.client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS,
            secret_key=MINIO_SECRET,
            secure=MINIO_SECURE,
        )
        self._ensure_buckets()

    def _ensure_buckets(self):
        for bucket in ALL_BUCKETS:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                log.info(f"[MinIO] Created bucket: {bucket}")

    # ── Raw file upload ───────────────────────────────────────

    def upload_raw_file(self, local_path: str, object_name: str) -> str:
        """Upload a raw MoSPI .txt or .xlsx file to statiq-raw."""
        size = os.path.getsize(local_path)
        log.info(f"[MinIO] Uploading raw: {os.path.basename(local_path)} "
                 f"({size/1e6:.1f}MB) → {BUCKET_RAW}/{object_name}")
        self.client.fput_object(BUCKET_RAW, object_name, local_path)
        return f"minio://{BUCKET_RAW}/{object_name}"

    def download_raw_file(self, object_name: str, local_path: str):
        """Download a raw file from MinIO to local disk."""
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        self.client.fget_object(BUCKET_RAW, object_name, local_path)
        log.info(f"[MinIO] Downloaded: {object_name} → {local_path}")

    # ── Parquet upload/download ───────────────────────────────

    def upload_parquet(
        self,
        df: pd.DataFrame,
        object_name: str,
        compression: str = "snappy",
    ) -> str:
        """
        Convert DataFrame to Parquet and upload to statiq-parquet.
        In-memory: no temp file written to disk.
        row_group_size=100_000 optimises Spark parallel reads.
        """
        table  = pa.Table.from_pandas(df, preserve_index=False)
        buffer = io.BytesIO()
        pq.write_table(table, buffer, compression=compression, row_group_size=100_000)
        buffer.seek(0)
        size = buffer.getbuffer().nbytes

        self.client.put_object(
            BUCKET_PARQUET, object_name, buffer,
            length=size, content_type="application/octet-stream",
        )
        log.info(f"[MinIO] Parquet uploaded: {object_name} ({size/1e6:.1f}MB) "
                 f"← {len(df):,} rows")
        return f"minio://{BUCKET_PARQUET}/{object_name}"

    def read_parquet(self, object_name: str) -> pd.DataFrame:
        """Download a Parquet file from MinIO into a pandas DataFrame."""
        try:
            response = self.client.get_object(BUCKET_PARQUET, object_name)
            buffer   = io.BytesIO(response.read())
            df       = pd.read_parquet(buffer)
            log.info(f"[MinIO] Parquet read: {object_name} → {len(df):,} rows")
            return df
        except S3Error as e:
            log.error(f"[MinIO] Read failed: {e}")
            raise

    def get_spark_path(self, object_name: str) -> str:
        """Return s3a:// path for Spark to read Parquet directly."""
        return f"s3a://{BUCKET_PARQUET}/{object_name}"

    def list_parquet(self, prefix: str = "") -> list:
        """List all Parquet files in statiq-parquet bucket."""
        objects = self.client.list_objects(BUCKET_PARQUET, prefix=prefix, recursive=True)
        return [obj.object_name for obj in objects]

    # ── QC / JSON upload ─────────────────────────────────────

    def upload_json(self, data: dict, object_name: str) -> str:
        """Upload a JSON report (QC, manifest) to statiq-processed."""
        import json
        content = json.dumps(data, indent=2, default=str).encode("utf-8")
        buffer  = io.BytesIO(content)
        self.client.put_object(
            BUCKET_PROCESSED, object_name, buffer,
            length=len(content), content_type="application/json",
        )
        return f"minio://{BUCKET_PROCESSED}/{object_name}"

    def upload_csv(self, df: pd.DataFrame, object_name: str) -> str:
        """Upload a DataFrame as CSV to statiq-processed."""
        buffer = io.BytesIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        size = buffer.getbuffer().nbytes
        self.client.put_object(
            BUCKET_PROCESSED, object_name, buffer,
            length=size, content_type="text/csv",
        )
        log.info(f"[MinIO] CSV uploaded: {object_name} ({size/1024:.1f}KB)")
        return f"minio://{BUCKET_PROCESSED}/{object_name}"

    def health(self) -> dict:
        try:
            buckets = self.client.list_buckets()
            return {"status": "ok", "buckets": [b.name for b in buckets]}
        except Exception as e:
            return {"status": "error", "message": str(e)}
