# security/config.py
# Central security configuration — all tunable constants live here.
# In production, sensitive values come from Vault, not environment variables.

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── TOKEN SETTINGS ─────────────────────────────────────────────────────────────
# RS256: private key signs tokens, public key verifies them.
# Even if the API server is compromised, the private key (in Vault) stays safe.
ALGORITHM               = "RS256"
ACCESS_TOKEN_EXPIRE_MIN = 30          # short-lived access tokens
REFRESH_TOKEN_EXPIRE_D  = 7           # refresh tokens last 7 days
ISSUER                  = "mospi-api.gov.in"
AUDIENCE                = "mospi-platform"

# Key paths — in production these come from Vault, not filesystem
RSA_PRIVATE_KEY_PATH    = os.environ.get("RSA_PRIVATE_KEY_PATH",  "keys/private.pem")
RSA_PUBLIC_KEY_PATH     = os.environ.get("RSA_PUBLIC_KEY_PATH",   "keys/public.pem")

# ── PASSWORD POLICY ────────────────────────────────────────────────────────────
# Argon2id is OWASP's current recommendation over bcrypt/scrypt.
ARGON2_TIME_COST        = 3           # iterations
ARGON2_MEMORY_COST      = 65536       # 64 MB RAM per hash
ARGON2_PARALLELISM      = 4           # threads
ARGON2_HASH_LEN         = 32          # output bytes
ARGON2_SALT_LEN         = 16          # random salt bytes

MIN_PASSWORD_LENGTH     = 6
MAX_PASSWORD_LENGTH     = 128
# Passwords must contain uppercase, lowercase, digit, and special char
PASSWORD_REGEX          = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#^()_+])[A-Za-z\d@$!%*?&#^()_+]{6,128}$"

# ── RATE LIMITING ──────────────────────────────────────────────────────────────
# Three-tier limits: by IP (unauthenticated), by user+scope (authenticated),
# and a hard global ceiling per IP regardless of auth.
RATE_LIMITS = {
    # scope        → (requests, window_seconds)
    "public":      (20,   60),
    "research":    (100,  60),
    "admin":       (1000, 60),
    "unauthenticated": (5, 60),   # IP-only, no token
}
IP_HARD_CEILING         = (200, 60)   # no single IP exceeds this
LOCKOUT_THRESHOLD       = 5           # failed auth attempts before lockout
LOCKOUT_DURATION_S      = 900         # 15 minutes
MAX_LOCKOUT_DURATION_S  = 86400       # 24 hours (exponential backoff ceiling)

# ── TLS / TRANSPORT ────────────────────────────────────────────────────────────
FORCE_HTTPS             = os.environ.get("FORCE_HTTPS", "true").lower() == "true"
HSTS_MAX_AGE            = 31536000    # 1 year in seconds
TLS_MIN_VERSION         = "TLSv1.3"

# ── COOKIE SETTINGS ───────────────────────────────────────────────────────────
# Tokens stored in HttpOnly cookies, not localStorage.
# JavaScript cannot read HttpOnly cookies — XSS cannot steal tokens.
COOKIE_SECURE           = FORCE_HTTPS
COOKIE_HTTPONLY         = True
COOKIE_SAMESITE         = "strict"    # CSRF protection
COOKIE_DOMAIN           = os.environ.get("COOKIE_DOMAIN", None)

# ── SQL SAFETY ─────────────────────────────────────────────────────────────────
# Allowlisted table names and column names for dynamic query building.
# If a name is not in these sets, the query is rejected — even if parameterized.
# Fixed allowlist corrected to match actual DB table & view names
ALLOWED_TABLES = frozenset({
    # Base survey tables
    "plfs_person",
    "hces_health_hh",
    "hces_health_members",
    "hces_health_hosp",
    # Privacy-safe API views (these are what NL queries use)
    "api_plfs_person",
    "api_hces_members",
    "api_hces_hosp",
    # Materialized views
    "mv_lfpr_by_state",
    "mv_unemployment_rate",
    "mv_hosp_rate",
})
ALLOWED_COLUMNS = frozenset({
    "state_name", "state_code", "district_code", "sector", "sector_label",
    "age", "age_group", "sex", "gender", "gender_label",
    "education_label", "activity_label", "employment_status",
    "in_labour_force", "is_employed", "working_age",
    "multiplier", "survey_year", "round_no",
    "usual_activity_status", "nic_2008_code", "nco_2004_code",
    "consumption_expenditure", "household_size",
    "religion_label", "social_label", "hh_type_label",
    "umce", "ins_premium",
    "hospitalised", "hosp_times", "chronic_ailment", "ailment_15d",
    "insurance_label", "vaccine_received",
    "ailment_label", "institution_label", "stay_days",
    "total_expense", "reimbursed", "out_of_pocket", "finance_label",
    # Aggregation aliases allowed in GROUP BY / SELECT
    "weighted_population", "weighted_pop", "weighted_lf", "weighted_emp",
    "weighted_hosp", "lfpr_pct", "wpr_pct", "hosp_rate_pct",
    "unemployment_rate", "sample_n",
})
MAX_QUERY_LIMIT         = 500         # hard cap — no query returns more than 500 rows
MAX_SQL_LENGTH          = 4096        # reject absurdly long SQL from the NL agent

# ── DATA PRIVACY ──────────────────────────────────────────────────────────────
# Default minimum cell size. Admin can override in the admin_settings DB table.
# get_min_cell_size() returns the live DB value (with this as fallback).
MIN_CELL_SIZE           = 30


_global_engine = None

def _get_engine():
    global _global_engine
    if _global_engine is None:
        import sqlalchemy as sa
        import os
        _global_engine = sa.create_engine(
            os.environ.get("DATABASE_URL", "postgresql+psycopg2://statiq:statiq123@localhost:5432/statiq"),
            pool_size=10,
            max_overflow=10,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 2},
        )
    return _global_engine

def get_min_cell_size() -> int:
    """
    Fetch the dynamic cell suppression threshold from DB.
    Falls back to the hardcoded default (30) if the DB is unavailable.
    """
    try:
        from sqlalchemy import text as _text
        with _get_engine().connect() as _conn:
            val = _conn.execute(_text(
                "SELECT value FROM admin_settings WHERE key = 'min_cell_size' LIMIT 1"
            )).scalar()
            if val is not None:
                return int(val)
    except Exception:
        pass
    return MIN_CELL_SIZE


# Columns that must NEVER appear in API output under any scope (static defaults)
# Dynamic additions come from survey_metadata_columns WHERE is_masked = TRUE
ALWAYS_MASKED_COLUMNS   = frozenset({
    "household_id", "person_id", "fsu_serial_no",
    "second_stage_stratum", "sample_hhd_no",
})


def get_masked_columns() -> frozenset:
    """
    Merge static ALWAYS_MASKED_COLUMNS with admin-toggled is_masked columns from DB.
    """
    extra: set = set()
    try:
        from sqlalchemy import text as _text
        with _get_engine().connect() as _conn:
            rows = _conn.execute(_text(
                "SELECT column_name FROM survey_metadata_columns WHERE is_masked = TRUE"
            )).fetchall()
            extra = {r[0] for r in rows}
    except Exception:
        pass
    return ALWAYS_MASKED_COLUMNS | extra

# ── CORS ───────────────────────────────────────────────────────────────────────
# Strict allowlist — no wildcard ever in production
ALLOWED_ORIGINS = [
    o.strip() for o in
    os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
]

# ── AUDIT ─────────────────────────────────────────────────────────────────────
AUDIT_LOG_PATH          = os.environ.get("AUDIT_LOG_PATH", "logs/audit.jsonl")
AUDIT_SIGN_KEY          = os.environ.get("AUDIT_SIGN_KEY", "")   # HMAC key for log signing
AUDIT_RETENTION_DAYS    = 2555    # 7 years (government compliance)

# ── API KEY SETTINGS ───────────────────────────────────────────────────────────
API_KEY_LENGTH_BYTES    = 32      # 256-bit keys
API_KEY_ROTATION_DAYS   = 90      # keys expire after 90 days
API_KEY_PREFIX          = "msp_" # prefix for quick identification in logs
