# security/auth.py
# Production authentication — RS256 JWT, Argon2id passwords,
# HttpOnly cookie delivery, refresh token rotation, brute-force lockout.

import os
import uuid
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import redis
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import HTTPException, Security, Depends, Request, Response, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from security.config import (
    ALGORITHM, ACCESS_TOKEN_EXPIRE_MIN, REFRESH_TOKEN_EXPIRE_D,
    ISSUER, AUDIENCE,
    RSA_PRIVATE_KEY_PATH, RSA_PUBLIC_KEY_PATH,
    ARGON2_TIME_COST, ARGON2_MEMORY_COST, ARGON2_PARALLELISM,
    ARGON2_HASH_LEN, ARGON2_SALT_LEN,
    LOCKOUT_THRESHOLD, LOCKOUT_DURATION_S, MAX_LOCKOUT_DURATION_S,
    API_KEY_LENGTH_BYTES, API_KEY_ROTATION_DAYS, API_KEY_PREFIX,
    COOKIE_SECURE, COOKIE_HTTPONLY, COOKIE_SAMESITE, COOKIE_DOMAIN,
    MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH,
)
import re
from security.config import PASSWORD_REGEX

# ── RSA KEY LOADING ────────────────────────────────────────────────────────────
def _load_key(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise RuntimeError(
            f"Key not found at {path}. "
            "Run: python -m security.generate_keys"
        )
    return p.read_text()

try:
    _PRIVATE_KEY = _load_key(RSA_PRIVATE_KEY_PATH)
    _PUBLIC_KEY  = _load_key(RSA_PUBLIC_KEY_PATH)
except RuntimeError as e:
    # Allow startup without keys in CI/test environments
    import warnings
    warnings.warn(f"Auth keys not loaded: {e}", RuntimeWarning)
    _PRIVATE_KEY = _PUBLIC_KEY = None

# ── ARGON2 HASHER ──────────────────────────────────────────────────────────────
_ph = PasswordHasher(
    time_cost=ARGON2_TIME_COST,
    memory_cost=ARGON2_MEMORY_COST,
    parallelism=ARGON2_PARALLELISM,
    hash_len=ARGON2_HASH_LEN,
    salt_len=ARGON2_SALT_LEN,
)

# ── REDIS CLIENT ──────────────────────────────────────────────────────────────
try:
    _redis = redis.Redis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True
    )
    _redis.ping()
    _REDIS_OK = True
except Exception:
    _redis = None
    _REDIS_OK = False

# ── SCOPES ─────────────────────────────────────────────────────────────────────
SCOPE_RANK = {"public": 0, "research": 1, "admin": 2}
VALID_SCOPES = frozenset(SCOPE_RANK.keys())

bearer = HTTPBearer(auto_error=False)


# ═══════════════════════════════════════════════════════════════════════════════
# PASSWORD HASHING
# ═══════════════════════════════════════════════════════════════════════════════

def validate_password_strength(password: str) -> None:
    """
    Enforce password policy before hashing.
    Raises ValueError with specific feedback.
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"Password must not exceed {MAX_PASSWORD_LENGTH} characters")
    if not re.match(PASSWORD_REGEX, password):
        raise ValueError(
            "Password must contain: uppercase letter, lowercase letter, "
            "digit, and special character (@$!%*?&#^()_+)"
        )


def hash_password(password: str) -> str:
    """Hash a password using Argon2id. Returns the full encoded hash string."""
    validate_password_strength(password)
    return _ph.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a password against its Argon2id hash.
    Returns False (never raises) to prevent timing oracle attacks.
    """
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    """True if the stored hash was created with older cost parameters."""
    return _ph.check_needs_rehash(hashed)


# ═══════════════════════════════════════════════════════════════════════════════
# BRUTE FORCE LOCKOUT
# ═══════════════════════════════════════════════════════════════════════════════

def _lockout_key(identifier: str) -> str:
    return f"lockout:{identifier}"

def _attempt_key(identifier: str) -> str:
    return f"attempts:{identifier}"


def record_failed_attempt(identifier: str) -> int:
    """
    Record a failed auth attempt.
    Returns the current attempt count.
    Uses exponential backoff for repeat offenders.
    """
    if not _REDIS_OK:
        return 0

    attempt_key = _attempt_key(identifier)
    count = _redis.incr(attempt_key)

    # Escalating lockout duration
    if count >= LOCKOUT_THRESHOLD:
        # Each threshold breach doubles the lockout, up to MAX_LOCKOUT_DURATION_S
        multiplier = 2 ** (count // LOCKOUT_THRESHOLD - 1)
        duration   = min(LOCKOUT_DURATION_S * multiplier, MAX_LOCKOUT_DURATION_S)
        _redis.setex(_lockout_key(identifier), int(duration), "locked")
        _redis.expire(attempt_key, int(duration))

    return count


def check_lockout(identifier: str) -> None:
    """Raises 429 if the identifier (user ID or IP) is locked out."""
    if not _REDIS_OK:
        return
    if _redis.exists(_lockout_key(identifier)):
        ttl = _redis.ttl(_lockout_key(identifier))
        raise HTTPException(
            status_code=429,
            detail=f"Account temporarily locked due to repeated failures. "
                   f"Try again in {ttl} seconds.",
            headers={"Retry-After": str(ttl)}
        )


def clear_failed_attempts(identifier: str) -> None:
    """Clear lockout on successful auth."""
    if not _REDIS_OK:
        return
    _redis.delete(_lockout_key(identifier))
    _redis.delete(_attempt_key(identifier))


# ═══════════════════════════════════════════════════════════════════════════════
# JWT TOKENS — RS256
# ═══════════════════════════════════════════════════════════════════════════════

def create_access_token(
    user_id:    str,
    scope:      str,
    extra_claims: dict = None,
) -> str:
    """
    Issue a short-lived RS256 access token.
    Private key signs → anyone with public key can verify.
    """
    if not _PRIVATE_KEY:
        raise RuntimeError("RSA private key not loaded")
    if scope not in VALID_SCOPES:
        raise ValueError(f"Invalid scope '{scope}'. Valid: {VALID_SCOPES}")

    now = datetime.now(timezone.utc)
    payload = {
        "sub":   user_id,
        "scope": scope,
        "iss":   ISSUER,
        "aud":   AUDIENCE,
        "iat":   now,
        "exp":   now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MIN),
        "jti":   str(uuid.uuid4()),   # unique token ID for revocation
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, _PRIVATE_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str, scope: str) -> tuple[str, str]:
    """
    Issue a long-lived refresh token.
    Returns (raw_token, jti) — store jti in DB to enable revocation.
    """
    if not _PRIVATE_KEY:
        raise RuntimeError("RSA private key not loaded")

    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    payload = {
        "sub":       user_id,
        "scope":     scope,
        "iss":       ISSUER,
        "aud":       AUDIENCE,
        "iat":       now,
        "exp":       now + timedelta(days=REFRESH_TOKEN_EXPIRE_D),
        "jti":       jti,
        "token_type": "refresh",
    }
    token = jwt.encode(payload, _PRIVATE_KEY, algorithm=ALGORITHM)
    return token, jti


def verify_token_raw(token: str) -> dict:
    """
    Verify and decode a JWT. Returns payload dict.
    Validates signature, expiry, issuer, and audience.
    """
    if not _PUBLIC_KEY:
        raise RuntimeError("RSA public key not loaded")
    try:
        payload = jwt.decode(
            token,
            _PUBLIC_KEY,
            algorithms=[ALGORITHM],
            audience=AUDIENCE,
            issuer=ISSUER,
        )
        # Reject revoked tokens (jti in Redis blocklist)
        jti = payload.get("jti")
        if jti and _REDIS_OK and _redis.exists(f"revoked_jti:{jti}"):
            raise HTTPException(status_code=401, detail="Token has been revoked")
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


def revoke_token(jti: str, expires_in_seconds: int) -> None:
    """
    Add a token's jti to the Redis blocklist.
    Used on logout and when a refresh token is rotated.
    """
    if _REDIS_OK and jti:
        _redis.setex(f"revoked_jti:{jti}", expires_in_seconds, "revoked")


# ── FASTAPI DEPENDENCIES ───────────────────────────────────────────────────────

async def verify_token(
    request: Request,
    # Try Authorization header first
    creds: Optional[HTTPAuthorizationCredentials] = Security(bearer),
    # Then try HttpOnly cookie (production path)
    access_token: Optional[str] = Cookie(default=None),
) -> dict:
    """
    Extract and verify token from:
    1. Authorization: Bearer header (developer/API access)
    2. HttpOnly cookie named 'access_token' (browser/dashboard access)
    Cookie path is preferred — never touches JavaScript.
    """
    token = None

    if creds and creds.credentials:
        token = creds.credentials
    elif access_token:
        token = access_token

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return verify_token_raw(token)


def require_scope(required: str):
    """
    Dependency factory: Depends(require_scope("research"))
    Rejects tokens with insufficient scope.
    """
    async def _checker(token: dict = Depends(verify_token)) -> dict:
        user_scope = token.get("scope", "public")
        if SCOPE_RANK.get(user_scope, 0) < SCOPE_RANK.get(required, 0):
            raise HTTPException(
                status_code=403,
                detail=f"Scope '{required}' required. Your token scope: '{user_scope}'"
            )
        return token
    return _checker


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """
    Set both tokens as HttpOnly secure cookies.
    JavaScript running on the page cannot read these.
    """
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MIN * 60,
        secure=COOKIE_SECURE,
        httponly=COOKIE_HTTPONLY,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=REFRESH_TOKEN_EXPIRE_D * 86400,
        secure=COOKIE_SECURE,
        httponly=COOKIE_HTTPONLY,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        path="/v1/auth/refresh",  # scoped path — only sent to refresh endpoint
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear both auth cookies on logout."""
    for name in ("access_token", "refresh_token"):
        response.delete_cookie(
            key=name,
            secure=COOKIE_SECURE,
            httponly=COOKIE_HTTPONLY,
            samesite=COOKIE_SAMESITE,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# API KEYS
# ═══════════════════════════════════════════════════════════════════════════════

def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key.
    Returns (raw_key_for_user, hashed_key_for_db).
    Format: msp_<base64url_256bits>
    NEVER store the raw key — only the hash goes in the DB.
    """
    raw_bytes = secrets.token_bytes(API_KEY_LENGTH_BYTES)
    raw_key   = API_KEY_PREFIX + secrets.token_urlsafe(API_KEY_LENGTH_BYTES)
    hashed    = hashlib.sha3_256(raw_key.encode()).hexdigest()  # SHA3-256
    return raw_key, hashed


def verify_api_key(raw: str, stored_hash: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    computed = hashlib.sha3_256(raw.encode()).hexdigest()
    return hmac.compare_digest(computed, stored_hash)
