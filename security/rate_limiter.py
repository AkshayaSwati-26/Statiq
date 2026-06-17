# security/rate_limiter.py
# Production rate limiting:
# - Three layers: IP ceiling → per-user/scope → per-endpoint
# - Sliding window algorithm (Redis sorted sets)
# - Writes rate limit headers to every response
# - Handles Redis unavailability gracefully (fail open with warning)

import time
import hashlib
import logging
from typing import Optional

import redis
from fastapi import Request, HTTPException, Depends
from fastapi.responses import Response

from security.config import RATE_LIMITS, IP_HARD_CEILING
from security.auth import verify_token, SCOPE_RANK

logger = logging.getLogger(__name__)

# ── REDIS ──────────────────────────────────────────────────────────────────────
try:
    import os
    _redis = redis.Redis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    _redis.ping()
    _REDIS_OK = True
except Exception as e:
    _redis = None
    _REDIS_OK = False
    logger.warning(f"Redis unavailable for rate limiting: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# CORE SLIDING WINDOW
# ═══════════════════════════════════════════════════════════════════════════════

def _sliding_window_check(
    key:     str,
    limit:   int,
    window:  int,
) -> tuple[int, int, int]:
    """
    Sliding window rate check using Redis sorted sets.
    Returns (current_count, limit, remaining).
    Raises 429 if limit exceeded.

    The sorted set stores each request timestamp as both the member and score.
    zremrangebyscore removes old entries outside the window.
    zcard counts what remains — that's the request count in the window.
    """
    if not _REDIS_OK:
        # Fail open in dev — log a warning but don't block requests
        logger.warning("Rate limiting disabled — Redis not available")
        return 0, limit, limit

    now          = time.time()
    window_start = now - window

    pipe = _redis.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)      # remove expired entries
    pipe.zadd(key, {f"{now}:{id(pipe)}": now})       # add this request (unique member)
    pipe.zcard(key)                                   # count requests in window
    pipe.expire(key, window * 2)                      # TTL cleanup
    results = pipe.execute()

    count     = results[2]
    remaining = max(0, limit - count)

    if count > limit:
        retry_after = int(window - (now - window_start))
        raise HTTPException(
            status_code=429,
            detail={
                "error":       "rate_limit_exceeded",
                "limit":       limit,
                "window_s":    window,
                "retry_after": retry_after,
            },
            headers={
                "Retry-After":          str(retry_after),
                "X-RateLimit-Limit":    str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset":    str(int(now + retry_after)),
            }
        )

    return count, limit, remaining


# ═══════════════════════════════════════════════════════════════════════════════
# IP FINGERPRINTING (for unauthenticated or suspicious requests)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_client_ip(request: Request) -> str:
    """
    Extract real client IP, handling reverse proxy headers.
    Prefer X-Forwarded-For (set by Nginx/load balancer) over direct IP.
    Hashed before use as a Redis key to avoid storing raw IPs.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first (leftmost) IP — the actual client
        ip = forwarded_for.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"

    # Hash IP so we're not storing PII in Redis
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def _get_user_agent_fingerprint(request: Request) -> str:
    """Rough fingerprint combining IP + User-Agent for anomaly detection."""
    ip = _get_client_ip(request)
    ua = request.headers.get("User-Agent", "")
    raw = f"{ip}:{ua}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ═══════════════════════════════════════════════════════════════════════════════
# DEPENDENCY: rate_limited
# Use this on every endpoint: Depends(rate_limited)
# ═══════════════════════════════════════════════════════════════════════════════

class RateLimiter:
    """
    Layered rate limiter as a FastAPI dependency.

    Layer 1: Hard IP ceiling — blocks scrapers and DDoS regardless of auth
    Layer 2: Per-user + scope limit — enforces tiered API access
    Layer 3: Adds X-RateLimit-* headers to response
    """

    def __init__(self, scope_override: Optional[str] = None):
        self.scope_override = scope_override

    async def __call__(
        self,
        request:  Request,
        response: Response,
        token:    Optional[dict] = Depends(verify_token),
    ) -> dict:

        ip_hash = _get_client_ip(request)

        # ── Layer 1: IP hard ceiling ───────────────────────────────────────────
        ip_limit, ip_window = IP_HARD_CEILING
        try:
            count, limit, remaining = _sliding_window_check(
                key=f"ip:{ip_hash}",
                limit=ip_limit,
                window=ip_window,
            )
        except HTTPException:
            raise HTTPException(
                status_code=429,
                detail="IP rate limit exceeded. Contact support if this is in error."
            )

        # ── Layer 2: Scope enforcement ─────────────────────────────────────────
        # If this limiter requires a minimum scope, enforce it here (403 if insufficient)
        token_scope = token.get("scope", "public")
        if self.scope_override and SCOPE_RANK.get(token_scope, 0) < SCOPE_RANK.get(self.scope_override, 0):
            raise HTTPException(
                status_code=403,
                detail=f"Scope '{self.scope_override}' required. Your token scope: '{token_scope}'"
            )

        # ── Layer 3: Per-user + scope rate limit ───────────────────────────────
        scope      = self.scope_override or token_scope
        user_id    = token.get("sub", f"anon:{ip_hash}")
        req_limit, req_window = RATE_LIMITS.get(scope, RATE_LIMITS["public"])

        count, limit, remaining = _sliding_window_check(
            key=f"user:{scope}:{user_id}",
            limit=req_limit,
            window=req_window,
        )

        # ── Layer 4: Write headers ────────────────────────────────────────────
        response.headers["X-RateLimit-Limit"]     = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"]     = str(int(time.time() + req_window))
        response.headers["X-RateLimit-Scope"]     = scope

        return token


# Singleton dependency instances for each scope requirement
rate_limited          = RateLimiter()
rate_limited_research = RateLimiter(scope_override="research")
rate_limited_admin    = RateLimiter(scope_override="admin")
