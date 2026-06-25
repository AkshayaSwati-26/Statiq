# security/sql_guard.py
# Production SQL safety layer.
# All SQL — whether user-supplied, NL-agent-generated, or built dynamically —
# passes through this module before execution.
#
# Defense in depth:
#   1. Allowlist validation (table names, column names)
#   2. Dangerous keyword blocking
#   3. Query length limits
#   4. Read-only connection enforcement
#   5. Cell suppression (privacy — groups smaller than MIN_CELL_SIZE)
#   6. Column masking (ALWAYS_MASKED_COLUMNS never returned)

import re
import logging
from typing import Any

from sqlalchemy import text, event
from sqlalchemy.engine import Engine
from fastapi import HTTPException

from security.config import (
    ALLOWED_TABLES,
    ALLOWED_COLUMNS,
    MAX_QUERY_LIMIT,
    MAX_SQL_LENGTH,
    MIN_CELL_SIZE,
    ALWAYS_MASKED_COLUMNS,
    get_min_cell_size,
    get_masked_columns,
)

logger = logging.getLogger(__name__)

# ── DANGEROUS SQL PATTERNS ─────────────────────────────────────────────────────
# These patterns are never allowed in any query, even from admin users.
# Regex is case-insensitive and handles whitespace variations.
_DANGEROUS_PATTERNS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bTRUNCATE\b",
    r"\bCREATE\b",
    r"\bALTER\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bEXECUTE\b",
    r"\bEXEC\b",
    r"\bxp_cmdshell\b",
    r"\bINTO\s+OUTFILE\b",
    r"\bLOAD_FILE\b",
    r"--",                    # SQL comment — used in injection
    r"/\*.*\*/",              # block comment
    r";\s*\w",                # statement chaining
    r"\bUNION\b.*\bSELECT\b", # UNION-based injection
    r"\bINFORMATION_SCHEMA\b",
    r"\bpg_catalog\b",
    r"\bpg_tables\b",
    r"\bpg_user\b",
    r"\bpg_shadow\b",
    r"\bpg_hba\b",
    r"\bsys\.\w",             # SQL Server sys tables
]
_DANGEROUS_RE = re.compile(
    "|".join(_DANGEROUS_PATTERNS),
    re.IGNORECASE | re.DOTALL
)


# ═══════════════════════════════════════════════════════════════════════════════
# SQL VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def validate_sql(sql: str) -> str:
    """
    Validate a SQL string before execution.
    Returns the cleaned SQL or raises HTTPException 400.

    Called for:
    - NL-agent generated SQL (from Claude)
    - Any dynamic query built in the API layer
    """
    if not sql or not sql.strip():
        raise HTTPException(status_code=400, detail="Empty SQL query")

    sql = sql.strip()

    # 1. Length check
    if len(sql) > MAX_SQL_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Query too long. Maximum {MAX_SQL_LENGTH} characters."
        )

    # 2. Must be a SELECT statement
    if not sql.upper().lstrip().startswith("SELECT"):
        raise HTTPException(
            status_code=400,
            detail="Only SELECT statements are permitted"
        )

    # 3. Dangerous pattern check
    match = _DANGEROUS_RE.search(sql)
    if match:
        logger.warning(f"Dangerous SQL pattern detected: {match.group()!r}")
        raise HTTPException(
            status_code=400,
            detail="Query contains disallowed SQL patterns"
        )

    # 4. Enforce LIMIT
    if "LIMIT" not in sql.upper():
        sql = f"{sql.rstrip(';')} LIMIT {MAX_QUERY_LIMIT}"
    else:
        # Check the existing LIMIT isn't absurd
        limit_match = re.search(r"LIMIT\s+(\d+)", sql, re.IGNORECASE)
        if limit_match:
            declared_limit = int(limit_match.group(1))
            if declared_limit > MAX_QUERY_LIMIT:
                sql = re.sub(
                    r"LIMIT\s+\d+",
                    f"LIMIT {MAX_QUERY_LIMIT}",
                    sql,
                    flags=re.IGNORECASE
                )

    return sql


def validate_table_name(table: str) -> str:
    """
    Allowlist check for table names used in dynamic queries.
    Prevents any table name injection.
    """
    if table not in ALLOWED_TABLES:
        raise HTTPException(
            status_code=400,
            detail=f"Table '{table}' is not accessible. "
                   f"Available: {sorted(ALLOWED_TABLES)}"
        )
    return table


def validate_column_name(column: str) -> str:
    """
    Allowlist check for column names used in dynamic queries.
    """
    if column not in ALLOWED_COLUMNS:
        raise HTTPException(
            status_code=400,
            detail=f"Column '{column}' is not accessible. "
                   f"Available: {sorted(ALLOWED_COLUMNS)}"
        )
    return column


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT SANITIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def mask_sensitive_columns(rows: list[dict]) -> list[dict]:
    """
    Mask sensitive columns from every row before returning to client.
    Merges static ALWAYS_MASKED_COLUMNS with admin-toggled is_masked columns from DB.
    These columns (household_id, fsu_serial_no etc.) can re-identify individuals.
    """
    if not rows:
        return rows
    masked = get_masked_columns()
    
    import re
    def _mask_val(val):
        if val is None: return None
        s = str(val)
        if '@' in s:
            parts = s.split('@', 1)
            if len(parts[0]) > 2:
                return parts[0][:2] + "***@" + parts[1]
            return "***@" + parts[1]
        elif re.match(r'^\+?\d{8,15}$', s):
            if len(s) > 4:
                return '*' * (len(s)-4) + s[-4:]
            return '***'
        else:
            words = s.split(' ')
            return ' '.join([w[0] + '*' * (len(w)-1) if len(w) > 1 else w for w in words])

    return [
        {k: (_mask_val(v) if k in masked else v) for k, v in row.items()}
        for row in rows
    ]


def enforce_cell_suppression(
    rows:        list[dict],
    count_col:   str = "weighted_population",
) -> list[dict]:
    """
    Statistical disclosure control.
    Suppress any aggregation cell where the underlying respondent count
    is below MIN_CELL_SIZE — prevents re-identification of individuals
    in small geographic/demographic groups.

    MIN_CELL_SIZE is read dynamically from admin_settings DB (default 30).
    Returns rows with suppressed cells replaced by None and a flag.
    """
    cell_threshold = get_min_cell_size()
    suppressed = []
    for row in rows:
        pop = row.get(count_col)
        if pop is not None and float(pop) < cell_threshold:
            # Replace all numeric values with None but keep group keys
            new_row = {}
            for k, v in row.items():
                if isinstance(v, (int, float)) and k != count_col:
                    new_row[k] = None
                else:
                    new_row[k] = v
            new_row["_suppressed"] = True
            new_row["_suppression_reason"] = (
                f"Cell suppressed: respondent count below {cell_threshold}"
            )
            suppressed.append(new_row)
        else:
            suppressed.append(row)
    return suppressed


# ═══════════════════════════════════════════════════════════════════════════════
# READ-ONLY CONNECTION ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def make_readonly_engine(engine: Engine) -> Engine:
    """
    Attach a SQLAlchemy event listener that rolls back any write operation
    before it can commit. Double safety net on top of SQL validation.
    Use a dedicated PostgreSQL read-only role (see db/roles.sql) as first line.
    """
    @event.listens_for(engine, "before_execute")
    def _intercept(conn, clauseelement, multiparams, params, execution_options):
        sql_str = str(clauseelement).upper().strip()
        if not sql_str.startswith("SELECT") and not sql_str.startswith("WITH"):
            logger.critical(
                f"WRITE OPERATION BLOCKED on read-only engine: {sql_str[:100]}"
            )
            raise HTTPException(
                status_code=403,
                detail="Write operations are not permitted on this connection"
            )

    return engine
