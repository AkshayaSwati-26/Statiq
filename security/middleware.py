# security/middleware.py
# Production security middleware stack.
# Every HTTP response gets the full OWASP recommended header set.
# HTTPS is enforced — HTTP requests are redirected.

import time
import logging
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from security.config import FORCE_HTTPS, HSTS_MAX_AGE
from security.audit import log_api_call, log_security_event
from security.rate_limiter import _get_client_ip

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds the full OWASP security header set to every response.
    These headers instruct browsers to apply additional protections.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # ── Prevent MIME type sniffing ─────────────────────────────────────────
        response.headers["X-Content-Type-Options"] = "nosniff"

        # ── Block clickjacking ────────────────────────────────────────────────
        response.headers["X-Frame-Options"] = "DENY"

        # ── XSS filter (legacy browsers) ─────────────────────────────────────
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # ── Referrer policy — don't leak URL in Referer header ────────────────
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # ── Content Security Policy ───────────────────────────────────────────
        # API only — no inline scripts/styles needed at the API layer.
        # Frontend has its own (more permissive) CSP.
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'none'; "
            "form-action 'none'"
        )

        # ── Permissions Policy — disable unneeded browser features ────────────
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )

        # ── HSTS — force HTTPS for 1 year, include subdomains ────────────────
        if FORCE_HTTPS:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={HSTS_MAX_AGE}; includeSubDomains; preload"
            )

        # ── Remove server fingerprinting headers ──────────────────────────────
        # Starlette MutableHeaders uses del, not pop()
        for _hdr in ("Server", "X-Powered-By"):
            if _hdr in response.headers:
                del response.headers[_hdr]

        # ── Cache control for API responses ───────────────────────────────────
        if request.url.path.startswith("/v1/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"]        = "no-cache"

        return response


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Redirect all HTTP requests to HTTPS.
    Skipped in development (FORCE_HTTPS=false).
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if FORCE_HTTPS:
            if request.url.scheme == "http":
                https_url = request.url.replace(scheme="https")
                return RedirectResponse(url=str(https_url), status_code=301)
        return await call_next(request)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Log every API request with timing, status, and user info.
    Runs after auth so we can capture the user ID from the token.
    """

    # Paths that don't need audit logging (health checks etc.)
    _SKIP_PATHS = frozenset({"/health", "/metrics", "/favicon.ico"})

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self._SKIP_PATHS:
            return await call_next(request)

        start    = time.perf_counter()
        ip_hash  = _get_client_ip(request)
        response = await call_next(request)
        duration = (time.perf_counter() - start) * 1000

        # Extract user from token if available (set by auth dependency)
        user_id = getattr(request.state, "user_id", "anonymous")

        log_api_call(
            user_id     = user_id,
            endpoint    = request.url.path,
            method      = request.method,
            params      = dict(request.query_params),
            status_code = response.status_code,
            duration_ms = duration,
            ip_hash     = ip_hash,
        )

        # Add timing header for debugging
        response.headers["X-Response-Time-Ms"] = str(round(duration, 2))

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Reject requests with bodies larger than MAX_BODY_BYTES.
    Prevents memory exhaustion from large malicious payloads.
    """
    MAX_BODY_BYTES = 1024 * 1024  # 1 MB

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_BODY_BYTES:
            return Response(
                content='{"detail":"Request body too large"}',
                status_code=413,
                media_type="application/json",
            )
        return await call_next(request)


class SuspiciousRequestMiddleware(BaseHTTPMiddleware):
    """
    Detect and log obviously malicious requests.
    Includes common vulnerability scanner patterns and injection probes.
    """
    _SUSPICIOUS_PATTERNS = [
        "../",         # path traversal
        "..\\",
        "<script",     # XSS probe
        "javascript:",
        "SELECT ",     # SQL injection in URL
        "UNION ",
        "' OR ",
        "DROP TABLE",
        "/etc/passwd", # LFI probe
        "cmd.exe",     # Windows shell probe
        "eval(",       # code injection probe
    ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        url_str = str(request.url).lower()
        ip_hash = _get_client_ip(request)

        for pattern in self._SUSPICIOUS_PATTERNS:
            if pattern.lower() in url_str:
                log_security_event(
                    event_type = "suspicious_request",
                    user_id    = "anonymous",
                    ip_hash    = ip_hash,
                    severity   = "medium",
                    details    = {
                        "pattern":  pattern,
                        "path":     request.url.path,
                        "method":   request.method,
                    }
                )
                return Response(
                    content='{"detail":"Bad request"}',
                    status_code=400,
                    media_type="application/json",
                )

        return await call_next(request)
