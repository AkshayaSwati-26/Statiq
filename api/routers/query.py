# api/routers/query.py
# Query endpoints:
#   POST /v1/query/nl      — natural language → SQL → results (research scope)
#   POST /v1/query/sql     — direct parameterized SQL (admin scope only)
#   GET  /v1/query/history — last 20 queries for the current user

import time
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy import text

from security.auth import require_scope, verify_token
from security.rate_limiter import rate_limited, rate_limited_research, rate_limited_admin
from security.sql_guard import (
    validate_sql, mask_sensitive_columns,
    enforce_cell_suppression
)
from security.audit import log_api_call, log_security_event
from security.rate_limiter import _get_client_ip
from security.validators import NLQueryRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/query", tags=["query"])

from db.loader import engine

# ── Pydantic request model for direct SQL ─────────────────────────────────────
from pydantic import BaseModel, Field

class DirectSQLRequest(BaseModel):
    sql:        str  = Field(..., min_length=1, max_length=4096)
    session_id: str  = Field(default="", description="Dataset session ID for table scoping")
    params:     dict = Field(default_factory=dict)
    reason:     str  = Field(default="User SQL query", min_length=1, max_length=500,
                             description="Reason for direct SQL access (audit trail)")

class BuilderRequest(BaseModel):
    session_id: Optional[str] = None
    filters: dict



# ═══════════════════════════════════════════════════════════════════════════════
# NL-TO-SQL ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/nl")
async def nl_query(
    body:    NLQueryRequest,
    request: Request,
    token:   dict = Depends(rate_limited),
):
    """
    Natural language → SQL → results.
    Accepts plain English (or 10 Indian languages via Bhashini).
    Minimum scope: research.

    Pipeline:
      1. Translate to English if needed (Bhashini)
      2. Claude API converts question to SQL
      3. SQL passes safety validation
      4. Execute against read-only DB connection
      5. Sanitize and suppress output
    """
    start   = time.perf_counter()
    ip_hash = _get_client_ip(request)
    user_id = token.get("sub", "anonymous")
    scope   = token.get("scope", "free")

    if scope == "free":
        raise HTTPException(status_code=403, detail="Upgrade to Premium to use the Natural Language Builder.")

    # ── Step 1: Translate if not English (Member 3 delivers ai/multilingual.py)
    english_question = body.question
    translated       = False

    if body.language != "en":
        from ai.multilingual import translate_to_english
        english_question = translate_to_english(body.question, body.language)
        translated       = True

    # ── Step 2: NL → SQL via Claude
    from ai.nl_agent import generate_sql
    nl_result = generate_sql(english_question)
    raw_sql   = nl_result["sql"]
    explain   = nl_result["explanation"]

    # ── Step 3: SQL safety validation ────────────────────────────────────────
    try:
        safe_sql = validate_sql(raw_sql)
    except HTTPException as e:
        log_security_event(
            event_type = "invalid_nl_sql",
            user_id    = user_id,
            ip_hash    = ip_hash,
            severity   = "medium",
            details    = {
                "question": body.question[:200],
                "raw_sql":  raw_sql[:500],
                "reason":   e.detail,
            }
        )
        raise

    # ── Step 4: Execute ───────────────────────────────────────────────────────
    try:
        with engine.connect() as conn:
            rows = [dict(r._mapping) for r in conn.execute(text(safe_sql))]
    except Exception as e:
        logger.error(f"Query execution failed: {e} | sql={safe_sql[:200]}")
        raise HTTPException(
            status_code=500,
            detail="Query execution failed. The generated SQL may reference "
                   "unavailable tables or columns. Try rephrasing your question."
        )

    # ── Step 5: Sanitize output ───────────────────────────────────────────────
    rows = mask_sensitive_columns(rows)
    rows = enforce_cell_suppression(rows)

    duration = (time.perf_counter() - start) * 1000
    log_api_call(user_id, "/v1/query/nl", "POST",
                 {"question": body.question[:100], "language": body.language},
                 200, duration, ip_hash, safe_sql)

    has_suppression = any(row.get("_suppressed", False) for row in rows)

    return {
        "question":         body.question,
        "language":         body.language,
        "translated":       translated,
        "english_question": english_question if translated else None,
        "sql":              safe_sql,
        "explanation":      explain,
        "count":            len(rows),
        "note":             "Cells with < 30 respondents are suppressed",
        "privacy_safe":     not has_suppression,
        "privacy_message":  "Some aggregation cells were suppressed due to low respondent count (below threshold)." if has_suppression else None,
        "data":             rows,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# BUILDER ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/builder")
async def builder_query(
    body:    BuilderRequest,
    request: Request,
    token:   dict = Depends(rate_limited),
):
    """
    Visual query builder → NL → SQL → results.
    Accepts drag-and-drop zones and translates them into a query.
    """
    start   = time.perf_counter()
    ip_hash = _get_client_ip(request)
    user_id = token.get("sub", "anonymous")
    scope   = token.get("scope", "free")

    if scope == "free":
        raise HTTPException(status_code=403, detail="Upgrade to Premium to use the Visual Query Builder.")

    zones = body.filters
    
    rows = [f.get("label", "") for f in zones.get("rows", [])]
    cols = [f.get("label", "") for f in zones.get("columns", [])]
    fils = [f.get("label", "") for f in zones.get("filters", [])]
    # Deterministic fast-path for Visual Query Builder
    metrics = cols if cols else fils if fils else ["records"]
    metric = metrics[0].lower() if metrics else "records"
    question = f"Show {', '.join(metrics)}"
    if rows:
        question += f" grouped by {', '.join(rows)}"
    
    group_by_cols = []
    select_cols = []
    
    # Map generic UI labels to DB columns
    for r in rows:
        rl = r.lower()
        if "state" in rl:
            group_by_cols.append("state_name")
            select_cols.append("state_name")
        elif "sector" in rl:
            group_by_cols.append("sector_label")
            select_cols.append("sector_label")
        elif "gender" in rl or "sex" in rl:
            group_by_cols.append("gender_label")
            select_cols.append("gender_label")
        elif "education" in rl:
            group_by_cols.append("education_label")
            select_cols.append("education_label")
            
    if not select_cols:
        group_by_cols = ["state_name"]
        select_cols = ["state_name"]
        
    group_by_clause = ", ".join(group_by_cols)
    select_clause = ", ".join(select_cols)

    if "employment" in metric or "unemployment" in metric:
        raw_sql = f"SELECT {select_clause}, ROUND(SUM(CASE WHEN usual_activity IN ('81', '82') THEN multiplier ELSE 0 END) / NULLIF(SUM(CASE WHEN usual_activity IN ('11', '12', '21', '31', '41', '51', '81', '82') THEN multiplier ELSE 0 END), 0) * 100, 2) AS unemployment_rate FROM plfs_person GROUP BY {group_by_clause} LIMIT 100"
        explain = "Calculated Unemployment Rate by dividing unemployed persons by total labour force."
    elif "lfpr" in metric or "participation" in metric or "labour force" in metric:
        raw_sql = f"SELECT {select_clause}, ROUND(SUM(CASE WHEN in_labour_force = 1 THEN multiplier ELSE 0 END) / NULLIF(SUM(multiplier), 0) * 100, 2) AS lfpr_pct FROM plfs_person WHERE working_age = 1 GROUP BY {group_by_clause} LIMIT 100"
        explain = "Calculated Labour Force Participation Rate."
    elif "consumption" in metric or "umce" in metric:
        raw_sql = f"SELECT {select_clause}, ROUND(SUM(umce * multiplier) / NULLIF(SUM(multiplier), 0), 2) AS avg_umce FROM hces_health_hh GROUP BY {group_by_clause} LIMIT 100"
        explain = "Calculated Average Usual Monthly Consumer Expenditure (UMCE)."
    elif "hospital" in metric:
        raw_sql = f"SELECT {select_clause}, ROUND(SUM(CASE WHEN hospitalised = 1 THEN multiplier ELSE 0 END) / NULLIF(SUM(multiplier), 0) * 100, 2) AS hospitalisation_rate FROM hces_health_members GROUP BY {group_by_clause} LIMIT 100"
        explain = "Calculated Hospitalisation Rate."
    else:
        raw_sql = f"SELECT {select_clause}, COUNT(*) as records FROM plfs_person GROUP BY {group_by_clause} LIMIT 100"
        explain = "Counted generic records."

    try:
        safe_sql = validate_sql(raw_sql)
    except HTTPException as e:
        log_security_event("invalid_builder_sql", user_id, ip_hash, "medium", {"sql": raw_sql[:500]})
        raise HTTPException(status_code=400, detail="Generated SQL failed validation")

    try:
        with engine.connect() as conn:
            data_rows = [dict(r._mapping) for r in conn.execute(text(safe_sql))]
    except Exception as e:
        logger.error(f"Builder query execution failed: {e}")
        raise HTTPException(status_code=500, detail="Query failed. Please adjust your filters.")

    data_rows = mask_sensitive_columns(data_rows)
    data_rows = enforce_cell_suppression(data_rows)
    duration = (time.perf_counter() - start) * 1000
    
    log_api_call(user_id, "/v1/query/builder", "POST",
                 {"question": question},
                 200, duration, ip_hash, safe_sql)

    has_suppression = any(row.get("_suppressed", False) for row in data_rows)

    return {
        "question":         question,
        "sql":              safe_sql,
        "explanation":      explain,
        "count":            len(data_rows),
        "privacy_safe":     not has_suppression,
        "privacy_message":  "Some aggregation cells were suppressed due to low respondent count (below threshold)." if has_suppression else None,
        "data":             data_rows,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DIRECT SQL ENDPOINT — RESEARCH + ADMIN (SELECT only, safety-validated)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/sql")
async def direct_sql(
    body:    DirectSQLRequest,
    request: Request,
    token:   dict = Depends(rate_limited_research),
):
    """
    Execute a direct SQL SELECT statement against the active session dataset.
    Research scope and above — all SQL passes through the safety validator.
    Only SELECT statements are permitted; DML/DDL is blocked at validation.
    Every call is audit-logged.
    """
    start   = time.perf_counter()
    ip_hash = _get_client_ip(request)
    user_id = token.get("sub", "anonymous")
    scope   = token.get("scope", "public")

    # Block public (free) tier
    if scope == "public":
        log_security_event(
            event_type = "unauthorized_direct_sql",
            user_id    = user_id,
            ip_hash    = ip_hash,
            severity   = "medium",
            details    = {"scope": scope, "attempted_sql": body.sql[:200]}
        )
        raise HTTPException(status_code=403, detail="Direct SQL requires Research or Admin tier")

    # Validate SQL
    safe_sql = validate_sql(body.sql)

    # Execute with user-supplied params (parameterized — safe)
    try:
        with engine.connect() as conn:
            rows = [dict(r._mapping) for r in conn.execute(text(safe_sql), body.params)]
    except Exception as e:
        logger.error(f"Direct SQL failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)[:200]}")

    rows     = mask_sensitive_columns(rows)
    duration = (time.perf_counter() - start) * 1000

    log_api_call(
        user_id    = user_id,
        endpoint   = "/v1/query/sql",
        method     = "POST",
        params     = {"reason": body.reason, "sql_preview": safe_sql[:100]},
        status_code = 200,
        duration_ms = duration,
        ip_hash    = ip_hash,
        sql        = safe_sql,
    )

    return {
        "sql":     safe_sql,
        "reason":  body.reason,
        "count":   len(rows),
        "data":    rows,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# QUERY HISTORY
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/history")
async def query_history(
    request: Request,
    limit:   int  = 20,
    token:   dict = Depends(verify_token),
):
    """
    Return the last N queries made by the current user.
    Read from the audit log — no separate query history table needed.
    """
    import json
    from pathlib import Path
    from security.config import AUDIT_LOG_PATH

    user_id = token.get("sub", "anonymous")
    log_path = Path(AUDIT_LOG_PATH)

    if not log_path.exists():
        return {"user": user_id, "count": 0, "history": []}

    entries = []
    with open(log_path, "r") as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                if record.get("user") == user_id and record.get("event") == "api_call":
                    entries.append({
                        "ts":       record["ts"],
                        "endpoint": record["endpoint"],
                        "params":   record.get("params", {}),
                        "status":   record.get("status"),
                        "duration_ms": record.get("duration_ms"),
                    })
            except Exception:
                continue

    # Return most recent first
    history = sorted(entries, key=lambda x: x["ts"], reverse=True)[:limit]

    return {
        "user":    user_id,
        "count":   len(history),
        "history": history,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TABLE COLUMNS — schema browser for SQL tab
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/columns")
async def get_table_columns(
    table:   str,
    request: Request,
    token:   dict = Depends(verify_token),
):
    """
    Return column names and data types for a given table or view.
    Used by the frontend SQL tab to display a schema browser.
    Validates the table name against an allowlist to prevent injection.
    """
    # Allowlist: only alphanumeric + underscores, no schema prefix injection
    import re
    if not re.match(r'^[a-z][a-z0-9_]{0,100}$', table):
        raise HTTPException(status_code=400, detail="Invalid table name")

    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = :tname
                  AND table_schema = 'public'
                ORDER BY ordinal_position
            """), {"tname": table}).fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schema lookup failed: {str(e)[:200]}")

    if not rows:
        raise HTTPException(status_code=404, detail=f"Table '{table}' not found")

    return {
        "table":   table,
        "columns": [{"name": r[0], "type": r[1]} for r in rows],
        "count":   len(rows),
    }
