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
from security.rate_limiter import rate_limited_research, rate_limited_admin
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
    sql:    str   = Field(..., min_length=1, max_length=4096)
    params: dict  = Field(default_factory=dict)
    reason: str   = Field(..., min_length=10, max_length=500,
                          description="Reason for direct SQL access (audit trail)")


# ═══════════════════════════════════════════════════════════════════════════════
# NL-TO-SQL ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/nl")
async def nl_query(
    body:    NLQueryRequest,
    request: Request,
    token:   dict = Depends(rate_limited_research),
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

    return {
        "question":         body.question,
        "language":         body.language,
        "translated":       translated,
        "english_question": english_question if translated else None,
        "sql":              safe_sql,
        "explanation":      explain,
        "count":            len(rows),
        "note":             "Cells with < 30 respondents are suppressed",
        "data":             rows,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DIRECT SQL ENDPOINT — ADMIN ONLY
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/sql")
async def direct_sql(
    body:    DirectSQLRequest,
    request: Request,
    token:   dict = Depends(rate_limited_admin),
):
    """
    Execute a direct SQL SELECT statement.
    Admin scope only.
    Every call is audit-logged with the reason provided.
    All SQL still passes through the safety validator.
    """
    start   = time.perf_counter()
    ip_hash = _get_client_ip(request)
    user_id = token.get("sub", "anonymous")
    scope   = token.get("scope", "public")

    # Double-check admin scope (rate_limited_admin handles it but belt-and-braces)
    if scope != "admin":
        log_security_event(
            event_type = "unauthorized_direct_sql",
            user_id    = user_id,
            ip_hash    = ip_hash,
            severity   = "high",
            details    = {"scope": scope, "attempted_sql": body.sql[:200]}
        )
        raise HTTPException(status_code=403, detail="Admin scope required for direct SQL")

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
