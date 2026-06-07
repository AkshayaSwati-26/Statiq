# security/audit.py
# Tamper-evident audit logging.
#
# Every API call generates a signed audit record.
# Records are HMAC-signed: even if someone edits the log file,
# the signature check will fail during compliance review.
#
# Compliant with:
#   - IT Act 2000 (India) — Section 43A data protection
#   - NIC security guidelines for government APIs
#   - 7-year retention requirement

import os
import json
import hmac
import hashlib
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from security.config import AUDIT_LOG_PATH, AUDIT_SIGN_KEY, AUDIT_RETENTION_DAYS

logger = logging.getLogger(__name__)

# Thread-safe file writing
_lock = threading.Lock()

# Signing key — in production, load from Vault
_SIGN_KEY = (AUDIT_SIGN_KEY or os.environ.get("AUDIT_SIGN_KEY", "dev-sign-key")).encode()

# ── ENSURE LOG DIR EXISTS ──────────────────────────────────────────────────────
Path(AUDIT_LOG_PATH).parent.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT RECORD STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════

def _sign(record: dict) -> str:
    """
    HMAC-SHA256 signature over the canonical JSON of the record.
    Canonical = sorted keys, no whitespace.
    """
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return hmac.new(
        _SIGN_KEY,
        canonical.encode(),
        hashlib.sha256
    ).hexdigest()


def _write(record: dict) -> None:
    """Thread-safe append to the audit log file."""
    line = json.dumps(record, separators=(",", ":")) + "\n"
    with _lock:
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)


def log_api_call(
    user_id:      str,
    endpoint:     str,
    method:       str,
    params:       dict,
    status_code:  int,
    duration_ms:  float,
    ip_hash:      str,
    sql:          Optional[str] = None,
    error:        Optional[str] = None,
) -> None:
    """
    Write one audit record per API call.
    - Never logs raw PII (IPs are pre-hashed by caller)
    - SQL is hashed, not stored verbatim (prevents log injection)
    - Each record is HMAC-signed for tamper detection
    """
    record = {
        "ts":          datetime.now(timezone.utc).isoformat(),
        "event":       "api_call",
        "user":        user_id,
        "endpoint":    endpoint,
        "method":      method,
        "params":      _sanitize_params(params),
        "status":      status_code,
        "duration_ms": round(duration_ms, 2),
        "ip_hash":     ip_hash,
        "sql_hash":    hashlib.sha256(sql.encode()).hexdigest() if sql else None,
        "error":       error,
    }
    record["sig"] = _sign({k: v for k, v in record.items() if k != "sig"})

    try:
        _write(record)
    except Exception as e:
        # Audit failure must not crash the API — log to system logger instead
        logger.error(f"AUDIT WRITE FAILED: {e} | record: {record}")


def log_auth_event(
    event_type: str,   # login_success, login_failure, logout, token_refresh, lockout
    user_id:    str,
    ip_hash:    str,
    details:    Optional[str] = None,
) -> None:
    """Log authentication events separately for SIEM correlation."""
    record = {
        "ts":      datetime.now(timezone.utc).isoformat(),
        "event":   f"auth:{event_type}",
        "user":    user_id,
        "ip_hash": ip_hash,
        "details": details,
    }
    record["sig"] = _sign({k: v for k, v in record.items() if k != "sig"})

    try:
        _write(record)
    except Exception as e:
        logger.error(f"AUDIT WRITE FAILED (auth): {e}")


def log_security_event(
    event_type: str,   # sql_injection_attempt, rate_limit_exceeded, forbidden_column
    user_id:    str,
    ip_hash:    str,
    severity:   str,   # low, medium, high, critical
    details:    dict,
) -> None:
    """Log security-relevant events for SIEM and incident response."""
    record = {
        "ts":       datetime.now(timezone.utc).isoformat(),
        "event":    f"security:{event_type}",
        "severity": severity,
        "user":     user_id,
        "ip_hash":  ip_hash,
        "details":  details,
    }
    record["sig"] = _sign({k: v for k, v in record.items() if k != "sig"})

    # High/critical events also go to stderr immediately
    if severity in ("high", "critical"):
        logger.critical(f"SECURITY EVENT [{severity.upper()}]: {event_type} | user={user_id}")

    try:
        _write(record)
    except Exception as e:
        logger.error(f"AUDIT WRITE FAILED (security): {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# LOG VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

def verify_audit_log(log_path: str = AUDIT_LOG_PATH) -> dict:
    """
    Verify the integrity of the audit log.
    Returns a summary: total records, valid, tampered, unreadable.
    Run this as a scheduled job or during compliance audits.
    """
    total = valid = tampered = unreadable = 0

    with open(log_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                record = json.loads(line)
                stored_sig = record.pop("sig", None)
                expected_sig = _sign(record)
                if stored_sig and hmac.compare_digest(stored_sig, expected_sig):
                    valid += 1
                else:
                    tampered += 1
                    logger.warning(f"TAMPERED record at line {line_num}")
            except Exception:
                unreadable += 1
                logger.warning(f"UNREADABLE record at line {line_num}")

    return {
        "total":     total,
        "valid":     valid,
        "tampered":  tampered,
        "unreadable": unreadable,
        "integrity": tampered == 0 and unreadable == 0,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _sanitize_params(params: dict) -> dict:
    """
    Remove or mask any parameter values that look like PII or secrets.
    Keeps keys (useful for debugging) but masks suspicious values.
    """
    SENSITIVE_KEYS = {"password", "token", "api_key", "secret", "otp"}
    return {
        k: "***" if k.lower() in SENSITIVE_KEYS else v
        for k, v in (params or {}).items()
    }
