# api/main.py
# Production FastAPI application.
# Security middleware is loaded in order — outermost wraps everything.

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from dotenv import load_dotenv

from security.config import ALLOWED_ORIGINS, FORCE_HTTPS
from security.middleware import (
    SecurityHeadersMiddleware,
    HTTPSRedirectMiddleware,
    AuditMiddleware,
    RequestSizeLimitMiddleware,
    SuspiciousRequestMiddleware,
)

load_dotenv()
logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s %(levelname)s %(name)s — %(message)s"
)
logger = logging.getLogger(__name__)


# ── LIFESPAN (startup / shutdown) ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MoSPI API starting — verifying security configuration")

    # Verify RSA keys exist before accepting traffic
    from pathlib import Path
    from security.config import RSA_PRIVATE_KEY_PATH, RSA_PUBLIC_KEY_PATH
    if not Path(RSA_PRIVATE_KEY_PATH).exists():
        raise RuntimeError(
            "RSA private key not found. Run: python -m security.generate_keys"
        )
    logger.info("RSA keys verified")

    # Warn if running with weak JWT secret
    jwt_secret = os.environ.get("JWT_SECRET", "")
    if len(jwt_secret) < 32 or jwt_secret == "dev-secret-change-in-production":
        logger.warning("Weak or default JWT secret detected")

    logger.info("MoSPI API ready")
    yield
    logger.info("MoSPI API shutting down")


# ── APP INIT ───────────────────────────────────────────────────────────────────
app = FastAPI(
    title       = "MoSPI Survey Intelligence API",
    description = (
        "Unified gateway for PLFS, HCES, and NSSO survey microdata. "
        "Provides weighted statistical indicators, natural language queries, "
        "and developer APIs for evidence-based policy analysis."
    ),
    version     = "1.0.0",
    docs_url    = "/docs"   if not FORCE_HTTPS else None,  # disable Swagger in prod
    redoc_url   = "/redoc"  if not FORCE_HTTPS else None,
    openapi_url = "/openapi.json" if not FORCE_HTTPS else None,
    lifespan    = lifespan,
)


# ═══════════════════════════════════════════════════════════════════════════════
# MIDDLEWARE STACK
# Order matters: outermost middleware runs first on request, last on response.
# ═══════════════════════════════════════════════════════════════════════════════

# 1. Trusted hosts — reject requests to unknown Host headers (prevents host injection)
ALLOWED_HOSTS = [
    h.strip() for h in
    os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

# 2. HTTPS redirect — HTTP → HTTPS in production
app.add_middleware(HTTPSRedirectMiddleware)

# 3. Security headers — OWASP header set on all responses
app.add_middleware(SecurityHeadersMiddleware)

# 4. Suspicious request detection — log and reject obvious attacks
app.add_middleware(SuspiciousRequestMiddleware)

# 5. Request size limit — 1 MB max body
app.add_middleware(RequestSizeLimitMiddleware)

# 6. Audit logging — every request logged with timing
app.add_middleware(AuditMiddleware)

# 7. CORS — strict allowlist, no wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ALLOWED_ORIGINS,
    allow_credentials = True,
    allow_methods     = ["GET", "POST"],   # only what we actually use
    allow_headers     = ["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers    = ["X-RateLimit-Limit", "X-RateLimit-Remaining",
                         "X-RateLimit-Reset", "X-Response-Time-Ms"],
)


# ── ROUTERS ────────────────────────────────────────────────────────────────────
try:
    from api.routers import auth, indicators, query, metadata_router, relationship_router, suggestions_router
    app.include_router(auth.router)
    app.include_router(indicators.router)
    app.include_router(query.router)
    app.include_router(metadata_router.router)
    app.include_router(relationship_router.router)
    app.include_router(suggestions_router.router)
except ImportError as e:
    logger.warning(f"Some routers not yet implemented: {e}")


# ── SYSTEM ENDPOINTS ───────────────────────────────────────────────────────────
@app.get("/health", tags=["system"], include_in_schema=False)
def health():
    """
    Shallow health check — returns 200 if the process is alive.
    Does NOT check DB or Redis (use /health/deep for that).
    """
    return {"status": "ok", "version": "1.0.0"}


@app.get("/health/deep", tags=["system"], include_in_schema=False)
def health_deep():
    """Deep health check — verifies DB and Redis connectivity."""
    from security.rate_limiter import _REDIS_OK
    results = {"api": "ok", "redis": "ok" if _REDIS_OK else "degraded"}
    try:
        from db.loader import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        results["database"] = "ok"
    except Exception as e:
        results["database"] = f"error: {e}"

    overall = "ok" if all(v == "ok" for v in results.values()) else "degraded"
    return {"status": overall, "checks": results}
