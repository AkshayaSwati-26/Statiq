# api/routers/auth.py
# Authentication endpoints:
#   POST /v1/auth/login        — credential verification, token issuance
#   POST /v1/auth/logout       — token revocation, cookie clearing
#   POST /v1/auth/refresh      — rotate refresh token, issue new access token
#   POST /v1/auth/api-key      — generate a scoped API key
#   DELETE /v1/auth/api-key    — revoke an API key
#   GET  /v1/auth/me           — return current token claims

import os
import time
import logging
from datetime import datetime, timezone

from fastapi import (
    APIRouter, HTTPException, Depends,
    Request, Response, Cookie
)
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy import text

from security.auth import (
    verify_password, hash_password, needs_rehash,
    create_access_token, create_refresh_token, verify_token_raw,
    revoke_token, set_auth_cookies, clear_auth_cookies,
    generate_api_key, verify_api_key,
    check_lockout, record_failed_attempt, clear_failed_attempts,
    verify_token, require_scope,
    ACCESS_TOKEN_EXPIRE_MIN, REFRESH_TOKEN_EXPIRE_D,
)
from security.audit import log_auth_event, log_security_event
from security.rate_limiter import _get_client_ip
from security.validators import TokenRequest, APIKeyCreateRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/auth", tags=["authentication"])

# ── DB engine (Member 1 delivers this — stub until Day 3) ─────────────────────
from db.loader import engine
_DB_AVAILABLE = True


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _get_user_from_db(user_id: str) -> Optional[dict]:
    """
    Fetch user record from DB.
    Returns dict with keys: user_id, password_hash, scope, is_active, api_keys
    Returns None if user not found.
    """
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT user_id, password_hash, scope, is_active "
                     "FROM users WHERE user_id = :uid LIMIT 1"),
                {"uid": user_id.lower().strip()}
            ).fetchone()
        return dict(row._mapping) if row else None
    except Exception as e:
        logger.error(f"DB error fetching user: {e}")
        return None


def _get_user_by_api_key_hash(key_hash: str) -> Optional[dict]:
    """Fetch user record by hashed API key."""
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT u.user_id, u.scope, u.is_active, ak.expires_at, ak.key_id
                    FROM users u
                    JOIN api_keys ak ON ak.user_id = u.user_id
                    WHERE ak.key_hash = :h AND ak.revoked = FALSE
                    LIMIT 1
                """),
                {"h": key_hash}
            ).fetchone()
        return dict(row._mapping) if row else None
    except Exception as e:
        logger.error(f"DB error fetching user by API key: {e}")
        return None


def _update_password_hash(user_id: str, new_hash: str) -> None:
    """Re-hash password if Argon2 cost parameters have changed."""
    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE users SET password_hash = :h WHERE user_id = :uid"),
                {"h": new_hash, "uid": user_id}
            )
    except Exception as e:
        logger.error(f"Failed to update password hash: {e}")


def _store_refresh_jti(user_id: str, jti: str) -> None:
    """Store refresh token JTI in DB for revocation tracking."""
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO refresh_tokens (jti, user_id, issued_at, expires_at)
                    VALUES (:jti, :uid, NOW(), NOW() + INTERVAL ':days days')
                    ON CONFLICT (jti) DO NOTHING
                """),
                {"jti": jti, "uid": user_id, "days": REFRESH_TOKEN_EXPIRE_D}
            )
    except Exception as e:
        logger.error(f"Failed to store refresh JTI: {e}")


def _revoke_refresh_jti(jti: str) -> None:
    """Mark a refresh token JTI as revoked in DB."""
    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE refresh_tokens SET revoked = TRUE WHERE jti = :jti"),
                {"jti": jti}
            )
    except Exception as e:
        logger.error(f"Failed to revoke refresh JTI: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class LoginResponse(BaseModel):
    message:    str
    scope:      str
    expires_in: int        # seconds
    token_type: str = "Bearer"

class MeResponse(BaseModel):
    user_id:    str
    scope:      str
    issued_at:  Optional[str]
    expires_at: Optional[str]

class APIKeyResponse(BaseModel):
    api_key:     str
    key_id:      str
    scope:       str
    expires_at:  str
    warning:     str = "Store this key securely. It will not be shown again."

class LogoutResponse(BaseModel):
    message: str


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/login", response_model=LoginResponse)
async def login(
    body:     TokenRequest,
    request:  Request,
    response: Response,
):
    """
    Authenticate with user_id + password.
    Issues access token (30 min) and refresh token (7 days) as HttpOnly cookies.
    Implements brute-force lockout — 5 failures triggers 15-min lockout.
    """
    ip_hash = _get_client_ip(request)
    user_id = body.user_id.lower().strip()

    # 1. Check lockout before doing anything
    check_lockout(user_id)
    check_lockout(ip_hash)

    # 2. Fetch user — use constant-time path even if user doesn't exist
    #    to prevent user enumeration via timing differences
    user = _get_user_from_db(user_id)

    # 3. Verify password — always run even if user is None (dummy hash)
    DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$dummysaltdummy1$dummyhashvalue000000000000000000"
    password_hash = user["password_hash"] if user else DUMMY_HASH
    password_valid = verify_password(body.password, password_hash)

    # 4. Reject if user doesn't exist, password wrong, or account inactive
    if not user or not password_valid or not user.get("is_active", False):
        count = record_failed_attempt(user_id)
        record_failed_attempt(ip_hash)
        log_auth_event("login_failure", user_id, ip_hash,
                       f"attempt {count}/{5}")
        # Same error message regardless of reason — prevents user enumeration
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    # 5. Clear failed attempts on success
    clear_failed_attempts(user_id)
    clear_failed_attempts(ip_hash)

    # 6. Re-hash password if Argon2 cost parameters changed
    if needs_rehash(user["password_hash"]):
        _update_password_hash(user_id, hash_password(body.password))

    # 7. Issue tokens
    scope         = user["scope"]
    access_token  = create_access_token(user_id, scope)
    refresh_token, refresh_jti = create_refresh_token(user_id, scope)

    # 8. Store refresh JTI for revocation
    _store_refresh_jti(user_id, refresh_jti)

    # 9. Set HttpOnly cookies
    set_auth_cookies(response, access_token, refresh_token)

    log_auth_event("login_success", user_id, ip_hash)

    return LoginResponse(
        message    = "Login successful",
        scope      = scope,
        expires_in = ACCESS_TOKEN_EXPIRE_MIN * 60,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request:       Request,
    response:      Response,
    token:         dict = Depends(verify_token),
    refresh_token: Optional[str] = Cookie(default=None),
):
    """
    Revoke the current access and refresh tokens.
    Clears HttpOnly cookies.
    Both tokens are blocklisted in Redis so they can't be reused.
    """
    ip_hash = _get_client_ip(request)
    user_id = token.get("sub", "unknown")

    # Revoke access token JTI
    access_jti = token.get("jti")
    if access_jti:
        remaining = token.get("exp", 0) - int(time.time())
        revoke_token(access_jti, max(remaining, 0))

    # Revoke refresh token JTI
    if refresh_token:
        try:
            refresh_payload = verify_token_raw(refresh_token)
            refresh_jti = refresh_payload.get("jti")
            if refresh_jti:
                revoke_token(refresh_jti, REFRESH_TOKEN_EXPIRE_D * 86400)
                _revoke_refresh_jti(refresh_jti)
        except Exception:
            pass  # Expired refresh tokens are fine on logout

    clear_auth_cookies(response)
    log_auth_event("logout", user_id, ip_hash)

    return LogoutResponse(message="Logged out successfully")


@router.post("/refresh")
async def refresh_token_endpoint(
    request:       Request,
    response:      Response,
    refresh_token: Optional[str] = Cookie(default=None),
):
    """
    Rotate refresh token — issue new access token + new refresh token.
    Old refresh token is revoked (one-time use).
    Implements refresh token rotation: stolen tokens can't be reused.
    """
    ip_hash = _get_client_ip(request)

    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    # Verify the refresh token
    try:
        payload = verify_token_raw(refresh_token)
    except HTTPException:
        log_auth_event("refresh_failure", "unknown", ip_hash, "invalid token")
        raise

    # Must be a refresh token specifically
    if payload.get("token_type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")

    user_id = payload.get("sub")
    scope   = payload.get("scope", "public")
    old_jti = payload.get("jti")

    # Revoke old refresh token immediately (rotation)
    if old_jti:
        revoke_token(old_jti, REFRESH_TOKEN_EXPIRE_D * 86400)
        _revoke_refresh_jti(old_jti)

    # Verify user still exists and is active
    user = _get_user_from_db(user_id)
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=401, detail="User no longer active")

    # Issue new token pair
    new_access  = create_access_token(user_id, scope)
    new_refresh, new_jti = create_refresh_token(user_id, scope)
    _store_refresh_jti(user_id, new_jti)

    set_auth_cookies(response, new_access, new_refresh)
    log_auth_event("token_refresh", user_id, ip_hash)

    return {
        "message":    "Tokens refreshed",
        "scope":      scope,
        "expires_in": ACCESS_TOKEN_EXPIRE_MIN * 60,
    }


@router.get("/me", response_model=MeResponse)
async def get_me(token: dict = Depends(verify_token)):
    """Return claims from the current token — no DB call needed."""
    exp = token.get("exp")
    iat = token.get("iat")
    return MeResponse(
        user_id    = token.get("sub", ""),
        scope      = token.get("scope", "public"),
        issued_at  = datetime.fromtimestamp(iat, tz=timezone.utc).isoformat() if iat else None,
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc).isoformat() if exp else None,
    )


@router.post("/api-key", response_model=APIKeyResponse)
async def create_api_key_endpoint(
    body:    APIKeyCreateRequest,
    request: Request,
    token:   dict = Depends(require_scope("research")),
):
    """
    Generate a scoped API key for programmatic access.
    Key is shown ONCE — only the SHA3-256 hash is stored in DB.
    Keys expire after 90 days and must be rotated.
    Minimum scope: research.
    """
    import uuid
    from datetime import timedelta
    from security.config import API_KEY_ROTATION_DAYS

    ip_hash  = _get_client_ip(request)
    user_id  = token.get("sub")
    raw_key, key_hash = generate_api_key()
    key_id   = str(uuid.uuid4())
    expires  = datetime.now(timezone.utc) + timedelta(days=API_KEY_ROTATION_DAYS)

    # Store hash in DB
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO api_keys
                        (key_id, user_id, key_hash, scope, description, expires_at, revoked)
                    VALUES
                        (:kid, :uid, :hash, :scope, :desc, :exp, FALSE)
                """),
                {
                    "kid":   key_id,
                    "uid":   user_id,
                    "hash":  key_hash,
                    "scope": body.scope,
                    "desc":  body.description,
                    "exp":   expires,
                }
            )
    except Exception as e:
        logger.error(f"Failed to store API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to create API key")

    log_auth_event("api_key_created", user_id, ip_hash, f"key_id={key_id}")

    return APIKeyResponse(
        api_key    = raw_key,
        key_id     = key_id,
        scope      = body.scope,
        expires_at = expires.isoformat(),
    )


@router.delete("/api-key/{key_id}")
async def revoke_api_key(
    key_id:  str,
    request: Request,
    token:   dict = Depends(require_scope("research")),
):
    """Revoke an API key by its key_id. Owner or admin only."""
    user_id = token.get("sub")
    scope   = token.get("scope")
    ip_hash = _get_client_ip(request)

    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    UPDATE api_keys SET revoked = TRUE
                    WHERE key_id = :kid
                    AND (user_id = :uid OR :scope = 'admin')
                """),
                {"kid": key_id, "uid": user_id, "scope": scope}
            )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="API key not found or not yours")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to revoke API key")

    log_auth_event("api_key_revoked", user_id, ip_hash, f"key_id={key_id}")
    return {"message": "API key revoked", "key_id": key_id}
