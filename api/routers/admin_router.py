# api/routers/admin_router.py
# ──────────────────────────────────────────────────────────────────
# All admin management endpoints. Requires scope = 'admin'.
#
#   GET  /v1/admin/overview                — live platform stats
#   GET  /v1/admin/users                   — list all users
#   POST /v1/admin/users                   — create a new user
#   PATCH /v1/admin/users/{uid}/scope      — change user scope
#   PATCH /v1/admin/users/{uid}/active     — activate / deactivate user
#   GET  /v1/admin/datasets                — list all registered datasets
#   PATCH /v1/admin/datasets/{id}/tier     — set free / premium
#   DELETE /v1/admin/datasets/{id}         — soft-delete dataset
#   GET  /v1/admin/audit-logs              — paginated audit log (filtered / sorted)
#   GET  /v1/admin/settings                — read admin_settings table
#   PATCH /v1/admin/settings               — update a setting value
#   GET  /v1/admin/sensitive-columns       — list column sensitivity flags
#   PATCH /v1/admin/sensitive-columns/{id} — toggle is_sensitive / is_masked

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import csv
import io
import json
import secrets
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import text

from security.auth import require_scope, hash_password, hash_otp, verify_token
from security.validators import SignupRequest
from api.utils.email import send_otp_email, send_rejection_email
from db.loader import engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/admin", tags=["admin"])


# ═══════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════

class CreateUserRequest(BaseModel):
    email: str         = Field(..., min_length=3, max_length=200)
    password: str      = Field(..., min_length=6, max_length=128)
    scope: str         = Field(default="public")
    admin_passcode: Optional[str] = None


class UpdateScopeRequest(BaseModel):
    scope: str = Field(..., pattern="^(public|research|admin)$")


class UpdateActiveRequest(BaseModel):
    is_active: bool


class UpdateTierRequest(BaseModel):
    access_tier: str = Field(..., pattern="^(free|premium)$")


class UpdateSettingRequest(BaseModel):
    key:   str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=1, max_length=500)


class UpdateColumnSensitivityRequest(BaseModel):
    is_sensitive: Optional[bool] = None
    is_masked:    Optional[bool] = None


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def _require_admin(token: dict = Depends(require_scope("admin"))) -> dict:
    return token


# ═══════════════════════════════════════════════════════════════════
# OVERVIEW
# ═══════════════════════════════════════════════════════════════════

@router.get("/overview")
async def get_overview(token: dict = Depends(verify_token)):
    """
    Live platform statistics for the admin dashboard.
    Returns real counts from the database.
    Accessible to all users for metric cards, but recent_activity is restricted to admins.
    """
    user_scope = token.get("scope", "public")
    try:
        with engine.connect() as conn:
            # Total active datasets
            ds_count = conn.execute(text(
                "SELECT COUNT(*) FROM datasets_registry WHERE is_active = TRUE"
            )).scalar() or 0

            # Total active users
            user_count = conn.execute(text(
                "SELECT COUNT(*) FROM users WHERE is_active = TRUE"
            )).scalar() or 0

            # Free vs Premium user split
            scope_counts = conn.execute(text(
                "SELECT scope, COUNT(*) as cnt FROM users WHERE is_active = TRUE GROUP BY scope"
            )).fetchall()
            scope_map = {r[0]: r[1] for r in scope_counts}

            # Total records across all active datasets
            try:
                total_rows = conn.execute(text(
                    "SELECT COALESCE(SUM(row_count), 0) FROM datasets_registry WHERE is_active = TRUE"
                )).scalar() or 0
            except Exception:
                total_rows = 0

            # Queries in last 24h (from api_usage_log)
            try:
                queries_24h = conn.execute(text(
                    "SELECT COUNT(*) FROM api_usage_log WHERE ts >= NOW() - INTERVAL '24 hours'"
                )).scalar() or 0
            except Exception:
                queries_24h = 0

            # Total queries all time
            try:
                total_queries = conn.execute(text(
                    "SELECT COUNT(*) FROM api_usage_log"
                )).scalar() or 0
            except Exception:
                total_queries = 0

            # Recent activity (last 10 audit events from auth_events_log)
            try:
                recent_rows = conn.execute(text("""
                    SELECT event_time, event_type, user_id, detail
                    FROM auth_events_log
                    ORDER BY event_time DESC
                    LIMIT 10
                """)).fetchall()
                recent_activity = [
                    {
                        "time": r[0].isoformat() if r[0] else "",
                        "action": r[1] or "",
                        "detail": r[2] or "",
                        "extra": r[3] or "",
                    }
                    for r in recent_rows
                ]
            except Exception:
                recent_activity = []

            # Suppressed cells in last 24h
            try:
                suppressed = conn.execute(text(
                    "SELECT COALESCE(SUM(suppressed_cells), 0) FROM api_usage_log WHERE ts >= NOW() - INTERVAL '24 hours'"
                )).scalar() or 0
            except Exception:
                suppressed = 0

        if user_scope != "admin":
            recent_activity = []

        return {
            "datasets":       int(ds_count),
            "total_users":    int(user_count),
            "free_users":     int(scope_map.get("public", 0)),
            "premium_users":  int(scope_map.get("research", 0)),
            "admin_users":    int(scope_map.get("admin", 0)),
            "total_rows":     int(total_rows),
            "queries_24h":    int(queries_24h),
            "total_queries":  int(total_queries),
            "suppressed_24h": int(suppressed),
            "recent_activity": recent_activity,
        }
    except Exception as e:
        logger.error(f"[Admin] Overview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# USER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

@router.get("/users")
async def list_users(
    scope:     Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    token: dict = Depends(_require_admin),
):
    """List all users. Optionally filter by scope or active status."""
    try:
        with engine.connect() as conn:
            conditions = ["1=1"]
            params = {}
            if scope:
                conditions.append("scope = :scope")
                params["scope"] = scope
            if is_active is not None:
                conditions.append("is_active = :is_active")
                params["is_active"] = is_active

            where = " AND ".join(conditions)
            rows = conn.execute(text(f"""
                SELECT user_id, email, scope, is_active, created_at, last_login_at, updated_at
                FROM users
                WHERE {where}
                ORDER BY created_at DESC
            """), params).fetchall()

        return [
            {
                "user_id":       r[0],
                "email":         r[1],
                "scope":         r[2],
                "is_active":     r[3],
                "created_at":    r[4].isoformat() if r[4] else None,
                "last_login_at": r[5].isoformat() if r[5] else None,
                "updated_at":    r[6].isoformat() if r[6] else None,
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"[Admin] List users error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users", status_code=201)
async def create_user(
    body: CreateUserRequest,
    token: dict = Depends(_require_admin),
):
    """Create a new user account. Admin-only."""
    import re, uuid

    # Validate scope
    if body.scope not in ("public", "research", "admin"):
        raise HTTPException(status_code=400, detail="Invalid scope")

    if body.scope == "admin":
        if body.admin_passcode != "MoSPIAdmin2026":
            raise HTTPException(status_code=403, detail="Invalid admin passcode")

    email = body.email.strip().lower()
    user_id = email.split("@")[0].lower()
    user_id = re.sub(r"[^a-z0-9_]", "_", user_id)[:40]

    # Check uniqueness
    try:
        with engine.connect() as conn:
            existing = conn.execute(text(
                "SELECT user_id FROM users WHERE user_id = :uid OR email = :email LIMIT 1"
            ), {"uid": user_id, "email": email}).fetchone()
            if existing:
                raise HTTPException(status_code=409, detail=f"User '{email}' already exists.")

            password_hash = hash_password(body.password)
            conn.execute(text("""
                INSERT INTO users (user_id, password_hash, scope, is_active, email, created_at, updated_at)
                VALUES (:uid, :pwd, :scope, TRUE, :email, NOW(), NOW())
            """), {"uid": user_id, "pwd": password_hash, "scope": body.scope, "email": email})
            conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin] Create user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return {"user_id": user_id, "email": email, "scope": body.scope, "created": True}


@router.patch("/users/{user_id}/scope")
async def update_user_scope(
    user_id: str,
    body: UpdateScopeRequest,
    token: dict = Depends(_require_admin),
):
    """Change a user's scope (public / research / admin)."""
    caller = token.get("sub")
    if caller == user_id and body.scope != "admin":
        raise HTTPException(status_code=400, detail="Cannot demote yourself")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                UPDATE users SET scope = :scope, updated_at = NOW()
                WHERE user_id = :uid
            """), {"scope": body.scope, "uid": user_id})
            conn.commit()
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="User not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"user_id": user_id, "scope": body.scope, "updated": True}


@router.patch("/users/{user_id}/active")
async def toggle_user_active(
    user_id: str,
    body: UpdateActiveRequest,
    token: dict = Depends(_require_admin),
):
    """Activate or deactivate a user account."""
    caller = token.get("sub")
    if caller == user_id and not body.is_active:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                UPDATE users SET is_active = :active, updated_at = NOW()
                WHERE user_id = :uid
            """), {"active": body.is_active, "uid": user_id})
            conn.commit()
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="User not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"user_id": user_id, "is_active": body.is_active, "updated": True}


# ═══════════════════════════════════════════════════════════════════
# DATASET MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

@router.get("/datasets")
async def list_datasets(
    tier:      Optional[str]  = Query(None, pattern="^(free|premium)$"),
    is_active: Optional[bool] = Query(None),
    search:    Optional[str]  = Query(None),
    token: dict = Depends(_require_admin),
):
    """List all registered datasets."""
    try:
        with engine.connect() as conn:
            conditions = ["1=1"]
            params = {}
            if tier:
                conditions.append("access_tier = :tier")
                params["tier"] = tier
            if is_active is not None:
                conditions.append("is_active = :is_active")
                params["is_active"] = is_active
            if search:
                conditions.append("(original_name ILIKE :search OR dataset_id ILIKE :search)")
                params["search"] = f"%{search}%"

            where = " AND ".join(conditions)
            rows = conn.execute(text(f"""
                SELECT dataset_id, original_name, table_name, file_format,
                       access_tier, row_count, column_count, file_hash,
                       uploaded_by, uploaded_at, is_active, description, tags
                FROM datasets_registry
                WHERE {where}
                ORDER BY uploaded_at DESC
            """), params).fetchall()

        return [
            {
                "dataset_id":   r[0],
                "original_name": r[1],
                "table_name":   r[2],
                "file_format":  r[3],
                "access_tier":  r[4],
                "row_count":    r[5],
                "column_count": r[6],
                "file_hash":    r[7],
                "uploaded_by":  r[8],
                "uploaded_at":  r[9].isoformat() if r[9] else None,
                "is_active":    r[10],
                "description":  r[11],
                "tags":         r[12] or [],
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"[Admin] List datasets error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/datasets/{dataset_id}/tier")
async def update_dataset_tier(
    dataset_id: str,
    body: UpdateTierRequest,
    token: dict = Depends(_require_admin),
):
    """Update a dataset's access tier (free / premium)."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                UPDATE datasets_registry SET access_tier = :tier
                WHERE dataset_id = :did
            """), {"tier": body.access_tier, "did": dataset_id})
            conn.commit()
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Dataset not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"dataset_id": dataset_id, "access_tier": body.access_tier}


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    token: dict = Depends(_require_admin),
):
    """Soft-delete a dataset (sets is_active = FALSE)."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                UPDATE datasets_registry SET is_active = FALSE
                WHERE dataset_id = :did
            """), {"did": dataset_id})
            conn.commit()
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Dataset not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"dataset_id": dataset_id, "deleted": True}


# ═══════════════════════════════════════════════════════════════════
# AUDIT LOGS
# ═══════════════════════════════════════════════════════════════════

@router.get("/audit-logs")
async def get_audit_logs(
    page:       int           = Query(1, ge=1),
    page_size:  int           = Query(50, ge=1, le=500),
    user_id:    Optional[str] = Query(None),
    endpoint:   Optional[str] = Query(None),
    status_code: Optional[str] = Query(None),
    date_from:  Optional[str] = Query(None, description="ISO date: YYYY-MM-DD"),
    date_to:    Optional[str] = Query(None, description="ISO date: YYYY-MM-DD"),
    sort_by:    str           = Query("ts", pattern="^(ts|user|endpoint|status_code|response_ms)$"),
    sort_dir:   str           = Query("desc", pattern="^(asc|desc)$"),
    token: dict = Depends(_require_admin),
):
    """
    Paginated audit log combining api_usage_log and auth_events_log.
    Full filtering and sorting support.
    """
    try:
        with engine.connect() as conn:
            # Build API usage log query
            api_conditions = ["1=1"]
            params: dict = {"offset": (page - 1) * page_size, "limit": page_size}

            if user_id:
                # Issue 8: Search by username (exact/partial/case-insensitive) instead of hash key
                api_conditions.append("(api_usage_log.api_key_hash ILIKE :user_filter OR EXISTS (SELECT 1 FROM users u WHERE u.user_id = api_usage_log.api_key_hash AND u.email ILIKE :user_filter))")
                params["user_filter"] = f"%{user_id}%"
            if endpoint:
                api_conditions.append("endpoint ILIKE :endpoint")
                params["endpoint"] = f"%{endpoint}%"
            if status_code:
                if isinstance(status_code, str) and status_code.upper().endswith("XX"):
                    base = int(status_code[0]) * 100
                    api_conditions.append("status_code >= :sc_min AND status_code <= :sc_max")
                    params["sc_min"] = base
                    params["sc_max"] = base + 99
                else:
                    api_conditions.append("status_code = :status_code")
                    params["status_code"] = int(status_code)
            if date_from:
                api_conditions.append("ts >= :date_from")
                params["date_from"] = date_from
            if date_to:
                api_conditions.append("ts <= :date_to::date + INTERVAL '1 day'")
                params["date_to"] = date_to

            api_where = " AND ".join(api_conditions)

            # Map sort_by to column
            sort_col_map = {
                "ts": "ts", "user": "api_key_hash",
                "endpoint": "endpoint", "status_code": "status_code",
                "response_ms": "response_ms"
            }
            sort_col = sort_col_map.get(sort_by, "ts")
            direction = "DESC" if sort_dir == "desc" else "ASC"

            # Count total
            count_sql = f"""
                SELECT COUNT(*) FROM api_usage_log
                WHERE {api_where}
            """
            # Remove pagination params for count
            count_params = {k: v for k, v in params.items() if k not in ("offset", "limit")}
            total = conn.execute(text(count_sql), count_params).scalar() or 0

            # Fetch rows
            rows = conn.execute(text(f"""
                SELECT ts, api_key_hash, endpoint, survey, query_hash,
                       rows_returned, response_ms, cache_hit, privacy_tier,
                       suppressed_cells, user_ip_hash, status_code
                FROM api_usage_log
                WHERE {api_where}
                ORDER BY {sort_col} {direction}
                LIMIT :limit OFFSET :offset
            """), params).fetchall()

        return {
            "total":     int(total),
            "page":      page,
            "page_size": page_size,
            "pages":     max(1, -(-int(total) // page_size)),
            "rows": [
                {
                    "ts":              r[0].isoformat() if r[0] else None,
                    "api_key_hash":    r[1],
                    "endpoint":        r[2],
                    "survey":          r[3],
                    "query_hash":      r[4],
                    "rows_returned":   r[5],
                    "response_ms":     r[6],
                    "cache_hit":       r[7],
                    "privacy_tier":    r[8],
                    "suppressed_cells": r[9],
                    "user_ip_hash":    r[10],
                    "status_code":     r[11],
                }
                for r in rows
            ],
        }
    except Exception as e:
        logger.error(f"[Admin] Audit log error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# ADMIN SETTINGS
# ═══════════════════════════════════════════════════════════════════

@router.get("/settings")
async def get_settings(token: dict = Depends(_require_admin)):
    """Read all admin settings."""
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT key, value, description, updated_by, updated_at FROM admin_settings ORDER BY key"
            )).fetchall()
        return [
            {
                "key":         r[0],
                "value":       r[1],
                "description": r[2],
                "updated_by":  r[3],
                "updated_at":  r[4].isoformat() if r[4] else None,
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/settings")
async def update_setting(
    body: UpdateSettingRequest,
    token: dict = Depends(_require_admin),
):
    """Update an admin setting value."""
    caller = token.get("sub", "admin")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                UPDATE admin_settings
                   SET value = :value, updated_by = :caller, updated_at = NOW()
                 WHERE key = :key
            """), {"key": body.key, "value": body.value, "caller": caller})
            conn.commit()
            if result.rowcount == 0:
                # Insert if it doesn't exist
                conn.execute(text("""
                    INSERT INTO admin_settings (key, value, updated_by, updated_at)
                    VALUES (:key, :value, :caller, NOW())
                """), {"key": body.key, "value": body.value, "caller": caller})
                conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"key": body.key, "value": body.value, "updated": True}


# ═══════════════════════════════════════════════════════════════════
# COLUMN SENSITIVITY
# ═══════════════════════════════════════════════════════════════════

@router.get("/sensitive-columns")
async def list_sensitive_columns(
    survey_id:    Optional[str]  = Query(None),
    is_sensitive: Optional[bool] = Query(None),
    is_masked:    Optional[bool] = Query(None),
    token: dict = Depends(_require_admin),
):
    """List all columns with their sensitivity / masking flags."""
    try:
        # Auto-populate survey_metadata_columns if empty for active datasets.
        # Use a separate transaction per dataset so one failure never rolls back others.
        with engine.connect() as scan_conn:
            datasets = scan_conn.execute(text(
                "SELECT dataset_id, table_name FROM datasets_registry WHERE is_active = TRUE"
            )).fetchall()

        for ds in datasets:
            ds_id, t_name = ds[0], ds[1]
            try:
                with engine.begin() as conn:
                    exists = conn.execute(text(
                        "SELECT EXISTS(SELECT 1 FROM survey_metadata_columns WHERE survey_id = :sid)"
                    ), {"sid": ds_id}).scalar()
                    if not exists:
                        columns_info = conn.execute(text("""
                            SELECT column_name, data_type
                            FROM information_schema.columns
                            WHERE table_name = :tname AND table_schema = 'public'
                        """), {"tname": t_name}).fetchall()

                        for col in columns_info:
                            col_name, dtype = col[0], col[1]
                            is_sens = col_name.lower() in (
                                'fsu_serial', 'hh_serial', 'fsu', 'hhd',
                                'user_ip_hash', 'api_key_hash'
                            )
                            conn.execute(text("""
                                INSERT INTO survey_metadata_columns
                                    (survey_id, table_name, column_name, data_type,
                                     description, is_sensitive, is_masked)
                                VALUES (:sid, :tname, :col, :dtype, :desc, :is_sens, FALSE)
                                ON CONFLICT (survey_id, table_name, column_name) DO NOTHING
                            """), {
                                "sid":     ds_id,
                                "tname":   t_name,
                                "col":     col_name,
                                "dtype":   dtype,
                                "desc":    f"Column {col_name} from dataset",
                                "is_sens": is_sens,
                            })
            except Exception as ds_err:
                logger.warning(f"Skipping auto-populate for dataset {ds_id}: {ds_err}")

        with engine.connect() as conn:
            conditions = ["1=1"]
            params = {}
            if survey_id:
                conditions.append("survey_id = :survey_id")
                params["survey_id"] = survey_id
            if is_sensitive is not None:
                conditions.append("is_sensitive = :is_sensitive")
                params["is_sensitive"] = is_sensitive
            if is_masked is not None:
                conditions.append("is_masked = :is_masked")
                params["is_masked"] = is_masked

            where = " AND ".join(conditions)
            rows = conn.execute(text(f"""
                SELECT id, survey_id, table_name, column_name, data_type,
                       description, is_sensitive, is_masked
                FROM survey_metadata_columns
                WHERE {where}
                ORDER BY table_name, column_name
            """), params).fetchall()

        return [
            {
                "id":           r[0],
                "survey_id":    r[1],
                "table_name":   r[2],
                "column_name":  r[3],
                "data_type":    r[4],
                "description":  r[5],
                "is_sensitive": r[6],
                "is_masked":    r[7],
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"Error listing sensitive columns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/sensitive-columns/{col_id}")
async def update_column_sensitivity(
    col_id: int,
    body: UpdateColumnSensitivityRequest,
    token: dict = Depends(_require_admin),
):
    """Toggle is_sensitive and/or is_masked flags on a column."""
    if body.is_sensitive is None and body.is_masked is None:
        raise HTTPException(status_code=400, detail="Provide at least one field to update")
    try:
        updates = []
        params: dict = {"id": col_id}
        if body.is_sensitive is not None:
            updates.append("is_sensitive = :is_sensitive")
            params["is_sensitive"] = body.is_sensitive
        if body.is_masked is not None:
            updates.append("is_masked = :is_masked")
            params["is_masked"] = body.is_masked

        with engine.connect() as conn:
            result = conn.execute(text(
                f"UPDATE survey_metadata_columns SET {', '.join(updates)} WHERE id = :id"
            ), params)
            conn.commit()
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Column not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"id": col_id, "updated": True, **{k: v for k, v in body.dict().items() if v is not None}}


# ═══════════════════════════════════════════════════════════════════
# USER REGISTRATIONS
# ═══════════════════════════════════════════════════════════════════

@router.get("/users/export")
async def export_users(token: dict = Depends(_require_admin)):
    """Export all active accounts to CSV."""
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT email, user_id, scope, created_at, last_login_at FROM users"
            )).fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Email", "User ID", "Scope", "Created At", "Last Login At"])
        for row in rows:
            writer.writerow([
                row[0],
                row[1],
                row[2],
                row[3].isoformat() if row[3] else "",
                row[4].isoformat() if row[4] else ""
            ])

        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=statiq_users.csv"}
        )
    except Exception as e:
        logger.error(f"Failed to export users: {e}")
        raise HTTPException(status_code=500, detail="Failed to export users")
