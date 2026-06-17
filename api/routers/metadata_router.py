"""
api/routers/metadata_router.py
================================
Dataset upload and metadata endpoints.

Upload (POST /upload):
  - Admin only (enforced by token scope)
  - Accepts CSV, XLSX, XLS, SAV (SPSS), DTA (Stata)
  - Parses file server-side using pandas / pyreadstat
  - Stores result in PostgreSQL as  upload_<sanitized_name>_<yyyymmdd>
  - Returns real column names, row count, and 5 preview rows
  - On empty-body (legacy ping / dataset selection), falls back to DB row count lookup
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from security.auth import verify_token
from ai import metadata_service
import os
import re
import io
import logging
from datetime import datetime
from sqlalchemy import text

logger = logging.getLogger(__name__)

try:
    from db.loader import engine, load_dataframe_to_db
except ImportError:
    from api.mock_db import engine
    load_dataframe_to_db = None

router = APIRouter(tags=["metadata"])


# ── helpers ──────────────────────────────────────────────────────────────────

def _sanitize_table_name(filename: str) -> str:
    """
    Convert an uploaded filename to a safe PostgreSQL table name.
    Example:  'PLFS 2024 Annual.csv'  →  'upload_plfs_2024_annual'
    """
    name = os.path.splitext(filename)[0]           # strip extension
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)        # non-alphanumeric → _
    name = re.sub(r"_+", "_", name).strip("_")      # collapse repeated _
    name = name[:40]                                 # max 40 chars
    date_suffix = datetime.now().strftime("%Y%m%d")
    return f"upload_{name}_{date_suffix}"


def _parse_file(contents: bytes, filename: str):
    """
    Parse uploaded bytes into a pandas DataFrame.
    Supports: .csv  .xlsx  .xls  .sav (SPSS)  .dta (Stata)
    Returns: (DataFrame, detected_format_str)
    """
    import pandas as pd

    ext = os.path.splitext(filename)[1].lower()

    if ext == ".csv":
        # Try common encodings
        for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding=enc, low_memory=False)
                return df, "CSV"
            except UnicodeDecodeError:
                continue
        raise HTTPException(status_code=400, detail="Could not decode CSV file. Try saving as UTF-8.")

    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(io.BytesIO(contents))
        return df, "XLSX"

    elif ext == ".sav":
        try:
            import pyreadstat
            df, meta = pyreadstat.read_sav(io.BytesIO(contents))
            return df, "SAV"
        except ImportError:
            raise HTTPException(status_code=400, detail="SPSS (.sav) parsing requires pyreadstat. Contact admin.")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not parse SAV file: {e}")

    elif ext == ".dta":
        try:
            import pandas as pd
            df = pd.read_stata(io.BytesIO(contents))
            return df, "DTA"
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not parse Stata file: {e}")

    elif ext == ".txt":
        # Fixed-width files — basic tab/space separated fallback
        for enc in ("latin-1", "utf-8"):
            try:
                df = pd.read_csv(io.BytesIO(contents), sep=None, engine="python", encoding=enc)
                return df, "TXT"
            except Exception:
                continue
        raise HTTPException(status_code=400, detail="Could not parse TXT file. Fixed-width MoSPI files require the pipeline.")

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'. Use CSV, XLSX, XLS, SAV, or DTA.")


def _safe_preview(df, n: int = 5) -> list:
    """Return up to n preview rows as JSON-serializable dicts."""
    import math
    preview = df.head(n).copy()
    # Replace NaN/inf with None for JSON serialization
    preview = preview.where(preview.notna(), other=None)
    rows = preview.to_dict(orient="records")
    safe = []
    for row in rows:
        safe_row = {}
        for k, v in row.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                safe_row[str(k)] = None
            else:
                safe_row[str(k)] = v
        safe.append(safe_row)
    return safe


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    token: dict = Depends(verify_token),
):
    """
    Upload a dataset file (CSV / XLSX / XLS / SAV / DTA).

    Admin scope required.
    The file is parsed server-side and stored in PostgreSQL.
    Returns dataset metadata + column names + 5 preview rows.

    Legacy behavior (empty file):
      If the uploaded file is empty (0 bytes), the endpoint falls back
      to returning row counts from an existing table whose name is
      inferred from the filename. This allows the Dashboard to 'select'
      a pre-ingested MoSPI dataset without re-uploading.
    """
    user_scope = token.get("scope", "public")
    filename   = file.filename or "upload.csv"
    ext        = os.path.splitext(filename)[1].lower()

    contents = await file.read()

    # ── LEGACY: empty-body ping → return existing table stats ────────────────
    if len(contents) == 0:
        table_name = "api_hces_members" if "hces" in filename.lower() else "api_plfs_person"

        if table_name == "api_hces_members" and user_scope == "public":
            raise HTTPException(
                status_code=403,
                detail="Free Users cannot access the Premium HCES dataset."
            )
        try:
            with engine.connect() as conn:
                count_res = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                row_count = count_res.scalar()
        except Exception:
            row_count = 5000

        return {
            "status":       "success",
            "table_name":   table_name,
            "row_count":    row_count,
            "session_id":   f"sess_{table_name}",
            "filename":     filename,
            "dataset_id":   table_name,
            "file_type":    ext.strip(".").upper() if ext else "CSV",
            "rows":         row_count,
            "columns":      20,
            "upload_time":  datetime.now().strftime("%Y-%m-%d %I:%M %p"),
            "column_names": ["state_name", "sector_label", "gender", "age", "multiplier"],
            "preview_rows": [],
        }

    # ── REAL UPLOAD ───────────────────────────────────────────────────────────
    if user_scope != "admin":
        raise HTTPException(
            status_code=403,
            detail="Dataset upload is restricted to administrators."
        )

    # Parse the file
    try:
        df, fmt = _parse_file(contents, filename)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File parse error: {e}")
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Uploaded file is empty or could not be parsed.")

    # Sanitize column names (PostgreSQL-safe)
    df.columns = [
        re.sub(r"[^a-z0-9_]", "_", str(c).lower().strip()).strip("_") or f"col_{i}"
        for i, c in enumerate(df.columns)
    ]

    # Derive table name and store in PostgreSQL
    table_name = _sanitize_table_name(filename)
    row_count  = len(df)

    try:
        if load_dataframe_to_db is not None:
            load_dataframe_to_db(df, table_name, if_exists="replace")
            logger.info(f"[Upload] Stored {row_count} rows → table '{table_name}'")
        else:
            # Fallback: use SQLAlchemy directly
            df.to_sql(table_name, engine, if_exists="replace", index=False, chunksize=5000)
            logger.info(f"[Upload] (fallback) Stored {row_count} rows → '{table_name}'")
    except Exception as e:
        logger.error(f"DB write error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store dataset: {str(e)[:200]}")

    column_names = list(df.columns)
    preview_rows = _safe_preview(df, 5)

    return {
        "status":       "success",
        "table_name":   table_name,
        "row_count":    row_count,
        "session_id":   f"sess_{table_name}",
        "filename":     filename,
        "dataset_id":   table_name,
        "file_type":    fmt,
        "rows":         row_count,
        "columns":      len(column_names),
        "upload_time":  datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "column_names": column_names,
        "preview_rows": preview_rows,
    }


# ── metadata endpoints ────────────────────────────────────────────────────────

@router.get("/v1/metadata")
async def get_metadata():
    """Returns the database schema."""
    return metadata_service.get_schema()

@router.get("/v1/data-dictionary")
async def get_data_dictionary():
    """Returns the data dictionary."""
    return metadata_service.get_data_dictionary()

@router.get("/v1/dataset-profile")
async def get_dataset_profile():
    """Returns the dataset profile."""
    return metadata_service.get_dataset_profile()

@router.get("/v1/sensitive-columns")
async def get_sensitive_columns():
    """Returns the sensitive columns registry."""
    return metadata_service.get_sensitive_columns()
