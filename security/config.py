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
COOKIE_DOMAIN           = os.environ.get("COOKIE_DOMAIN", "localhost")

# ── SQL SAFETY ─────────────────────────────────────────────────────────────────
# Allowlisted table names and column names for dynamic query building.
# If a name is not in these sets, the query is rejected — even if parameterized.
ALLOWED_TABLES = frozenset({
    "plfs_person", "plfs_household",
    "hces_person", "hces_household",
    "nsso_rounds",
})
ALLOWED_COLUMNS = frozenset({
    "state_code", "district_code", "sector", "age", "sex",
    "usual_activity_status", "multiplier", "survey_year",
    "nic_2008_code", "nco_2004_code", "consumption_expenditure",
    "household_size", "religion", "social_group",
})
MAX_QUERY_LIMIT         = 500         # hard cap — no query returns more than 500 rows
MAX_SQL_LENGTH          = 4096        # reject absurdly long SQL from the NL agent

# ── DATA PRIVACY ──────────────────────────────────────────────────────────────
# Minimum cell size for any aggregation result.
# If a group has fewer than MIN_CELL_SIZE respondents, suppress the result.
# This prevents re-identification of individuals from small groups.
MIN_CELL_SIZE           = 30

# Columns that must NEVER appear in API output under any scope
ALWAYS_MASKED_COLUMNS   = frozenset({
    "household_id", "person_id", "fsu_serial_no",
    "second_stage_stratum", "sample_hhd_no",
})

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
