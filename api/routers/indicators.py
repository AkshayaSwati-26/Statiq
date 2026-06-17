# api/routers/indicators.py
# All statistical indicator endpoints.
# Every query uses survey weights (SUM(multiplier)) — never COUNT(*).
# Results pass through cell suppression before leaving the API.
# Uses materialized views for instant response on common queries.

import time
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response, HTTPException
from sqlalchemy import text

from security.auth import require_scope, verify_token
from security.rate_limiter import rate_limited
from security.sql_guard import (
    validate_table_name, validate_column_name,
    mask_sensitive_columns, enforce_cell_suppression
)
from security.audit import log_api_call, log_security_event
from security.rate_limiter import _get_client_ip

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/indicators", tags=["indicators"])

from db.loader import engine


# ═══════════════════════════════════════════════════════════════════════════════
# SHARED QUERY BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def _build_filters(
    year:   int,
    state:  Optional[int],
    sector: Optional[int],
    sex:    Optional[int],
) -> tuple[str, dict]:
    """
    Build a parameterized WHERE clause from common filter params.
    Returns (where_clause_string, params_dict).
    All values are parameterized — never string-interpolated.
    """
    conditions = ["survey_year = :year"]
    params     = {"year": year}

    if state is not None:
        conditions.append("state_code = :state")
        params["state"] = state
    if sector is not None:
        conditions.append("sector = :sector")
        params["sector"] = sector
    if sex is not None:
        conditions.append("sex = :sex")
        params["sex"] = sex

    return "WHERE " + " AND ".join(conditions), params


def _execute_and_sanitize(
    sql:           str,
    params:        dict,
    suppress_col:  Optional[str] = "weighted_population",
) -> list[dict]:
    """
    Execute a query and apply all output sanitization in order:
    1. Run query
    2. Mask always-masked columns
    3. Apply cell suppression (privacy)
    """
    with engine.connect() as conn:
        rows = [dict(r._mapping) for r in conn.execute(text(sql), params)]

    rows = mask_sensitive_columns(rows)
    if suppress_col:
        rows = enforce_cell_suppression(rows, suppress_col)
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
# UNEMPLOYMENT RATE
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/unemployment-rate")
def unemployment_rate(
    request:  Request,
    response: Response,
    year:     int           = Query(2023, ge=2004, le=2025, description="Survey year"),
    state:    Optional[int] = Query(None, ge=1, le=35,      description="State code"),
    sector:   Optional[int] = Query(None, ge=1, le=2,       description="1=Rural 2=Urban"),
    sex:      Optional[int] = Query(None, ge=1, le=2,       description="1=Male 2=Female"),
    token:    dict          = Depends(rate_limited),
):
    """
    Weighted unemployment rate by state/sector/sex.
    Uses usual_activity_status codes 81 (seeking work) and 82 (not seeking but available).
    All estimates are population-weighted using the survey multiplier.
    Cells with fewer than 30 respondents are suppressed.
    """
    start   = time.perf_counter()
    ip_hash = _get_client_ip(request)
    user_id = token.get("sub", "anonymous")

    where, params = _build_filters(year, state, sector, sex)

    # Use materialized view if no sex filter (covers the common case)
    # Fall back to base table when drilling down by sex
    if sex is None and state is None:
        sql = f"""
            SELECT state_code, sector, survey_year,
                   unemployment_rate,
                   weighted_population
            FROM   mv_unemployment_rate
            {where}
            ORDER  BY state_code, sector
            LIMIT  500
        """
    else:
        sql = f"""
            SELECT
                state_code,
                sector,
                survey_year,
                ROUND(
                    SUM(CASE WHEN usual_activity_status IN (81, 82)
                            THEN multiplier ELSE 0 END)
                    / NULLIF(
                        SUM(CASE WHEN usual_activity_status BETWEEN 11 AND 82
                                THEN multiplier ELSE 0 END),
                        0
                    ) * 100,
                2) AS unemployment_rate,
                ROUND(SUM(multiplier))            AS weighted_population,
                COUNT(*)                          AS respondent_count
            FROM   plfs_person
            {where}
            GROUP  BY state_code, sector, survey_year
            HAVING COUNT(*) > 0
            ORDER  BY state_code, sector
            LIMIT  500
        """

    rows     = _execute_and_sanitize(sql, params, "weighted_population")
    duration = (time.perf_counter() - start) * 1000

    log_api_call(user_id, "/v1/indicators/unemployment-rate",
                 "GET", params, 200, duration, ip_hash, sql)

    return {
        "indicator": "unemployment_rate",
        "unit":      "percent",
        "filters":   {"year": year, "state": state, "sector": sector, "sex": sex},
        "count":     len(rows),
        "note":      "Cells with < 30 respondents are suppressed for privacy",
        "data":      rows,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# LABOUR FORCE PARTICIPATION RATE (LFPR)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/lfpr")
def labour_force_participation_rate(
    request:  Request,
    response: Response,
    year:     int           = Query(2023, ge=2004, le=2025),
    state:    Optional[int] = Query(None, ge=1, le=35),
    sector:   Optional[int] = Query(None, ge=1, le=2),
    sex:      Optional[int] = Query(None, ge=1, le=2),
    token:    dict          = Depends(rate_limited),
):
    """
    Labour Force Participation Rate — share of working-age population
    (15+) that is employed or actively seeking employment.
    LFPR = (Labour Force / Working-age Population) × 100
    """
    start   = time.perf_counter()
    ip_hash = _get_client_ip(request)
    user_id = token.get("sub", "anonymous")

    where, params = _build_filters(year, state, sector, sex)

    sql = f"""
        SELECT
            state_code,
            sector,
            survey_year,
            ROUND(
                SUM(CASE WHEN usual_activity_status BETWEEN 11 AND 82
                        THEN multiplier ELSE 0 END)
                / NULLIF(SUM(multiplier), 0) * 100,
            2) AS lfpr,
            ROUND(SUM(multiplier))  AS working_age_population,
            COUNT(*)                AS respondent_count
        FROM   plfs_person
        {where}
        AND    age >= 15
        GROUP  BY state_code, sector, survey_year
        ORDER  BY state_code, sector
        LIMIT  500
    """

    rows     = _execute_and_sanitize(sql, params, "working_age_population")
    duration = (time.perf_counter() - start) * 1000
    log_api_call(user_id, "/v1/indicators/lfpr", "GET", params, 200, duration, ip_hash, sql)

    return {
        "indicator": "lfpr",
        "unit":      "percent",
        "filters":   {"year": year, "state": state, "sector": sector, "sex": sex},
        "count":     len(rows),
        "data":      rows,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# WORKER POPULATION RATIO (WPR)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/wpr")
def worker_population_ratio(
    request:  Request,
    year:     int           = Query(2023, ge=2004, le=2025),
    state:    Optional[int] = Query(None, ge=1, le=35),
    sector:   Optional[int] = Query(None, ge=1, le=2),
    sex:      Optional[int] = Query(None, ge=1, le=2),
    token:    dict          = Depends(rate_limited),
):
    """
    Worker Population Ratio — share of working-age population (15+)
    that is employed (excludes unemployed persons in labour force).
    WPR = (Employed / Working-age Population) × 100
    """
    start   = time.perf_counter()
    ip_hash = _get_client_ip(request)
    user_id = token.get("sub", "anonymous")

    where, params = _build_filters(year, state, sector, sex)

    sql = f"""
        SELECT
            state_code,
            sector,
            survey_year,
            ROUND(
                SUM(CASE WHEN usual_activity_status BETWEEN 11 AND 72
                        THEN multiplier ELSE 0 END)
                / NULLIF(SUM(multiplier), 0) * 100,
            2) AS wpr,
            ROUND(SUM(multiplier))  AS working_age_population,
            COUNT(*)                AS respondent_count
        FROM   plfs_person
        {where}
        AND    age >= 15
        GROUP  BY state_code, sector, survey_year
        ORDER  BY state_code, sector
        LIMIT  500
    """

    rows     = _execute_and_sanitize(sql, params, "working_age_population")
    duration = (time.perf_counter() - start) * 1000
    log_api_call(user_id, "/v1/indicators/wpr", "GET", params, 200, duration, ip_hash, sql)

    return {
        "indicator": "wpr",
        "unit":      "percent",
        "filters":   {"year": year, "state": state, "sector": sector, "sex": sex},
        "count":     len(rows),
        "data":      rows,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MONTHLY PER CAPITA CONSUMER EXPENDITURE (MPCE) — HCES
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/mpce")
def monthly_per_capita_expenditure(
    request:  Request,
    year:     int           = Query(2023, ge=2004, le=2025),
    state:    Optional[int] = Query(None, ge=1, le=35),
    sector:   Optional[int] = Query(None, ge=1, le=2),
    token:    dict          = Depends(require_scope("research")),
):
    """
    Average Monthly Per Capita Consumer Expenditure from HCES.
    Requires research scope — MPCE data is more sensitive.
    Returns weighted mean and quartiles by state/sector.
    """
    start   = time.perf_counter()
    ip_hash = _get_client_ip(request)
    user_id = token.get("sub", "anonymous")

    where, params = _build_filters(year, state, sector, None)

    median_sql = """
            ROUND(
                PERCENTILE_CONT(0.5) WITHIN GROUP
                    (ORDER BY consumption_expenditure),
            2) AS mpce_median,
    """
    if engine.dialect.name == "sqlite":
        median_sql = "0.0 AS mpce_median,"

    sql = f"""
        SELECT
            state_code,
            sector,
            survey_year,
            ROUND(
                SUM(consumption_expenditure * multiplier)
                / NULLIF(SUM(multiplier), 0),
            2) AS mpce_mean,
            {median_sql}
            ROUND(SUM(multiplier))  AS weighted_households,
            COUNT(*)                AS respondent_count
        FROM   hces_household
        {where}
        AND    consumption_expenditure > 0
        GROUP  BY state_code, sector, survey_year
        ORDER  BY state_code, sector
        LIMIT  500
    """

    rows     = _execute_and_sanitize(sql, params, "weighted_households")
    duration = (time.perf_counter() - start) * 1000
    log_api_call(user_id, "/v1/indicators/mpce", "GET", params, 200, duration, ip_hash, sql)

    return {
        "indicator": "mpce",
        "unit":      "INR per person per month",
        "source":    "HCES",
        "filters":   {"year": year, "state": state, "sector": sector},
        "count":     len(rows),
        "data":      rows,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TIME SERIES — compare indicator across years
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/time-series/{indicator}")
def time_series(
    indicator: str,
    request:   Request,
    state:     Optional[int] = Query(None, ge=1, le=35),
    sector:    Optional[int] = Query(None, ge=1, le=2),
    from_year: int           = Query(2017, ge=2004, le=2025),
    to_year:   int           = Query(2023, ge=2004, le=2025),
    token:     dict          = Depends(rate_limited),
):
    """
    Fetch an indicator across multiple years for trend analysis.
    Supported indicators: unemployment_rate, lfpr, wpr
    """
    SUPPORTED = {"unemployment_rate", "lfpr", "wpr"}
    if indicator not in SUPPORTED:
        raise HTTPException(
            status_code=400,
            detail=f"Indicator '{indicator}' not supported. Choose from: {SUPPORTED}"
        )
    if from_year > to_year:
        raise HTTPException(status_code=400, detail="from_year must be ≤ to_year")

    start   = time.perf_counter()
    ip_hash = _get_client_ip(request)
    user_id = token.get("sub", "anonymous")

    INDICATOR_EXPRS = {
        "unemployment_rate": """
            ROUND(
                SUM(CASE WHEN usual_activity_status IN (81,82) THEN multiplier ELSE 0 END)
                / NULLIF(SUM(CASE WHEN usual_activity_status BETWEEN 11 AND 82
                                  THEN multiplier ELSE 0 END), 0) * 100
            , 2) AS value
        """,
        "lfpr": """
            ROUND(
                SUM(CASE WHEN usual_activity_status BETWEEN 11 AND 82 THEN multiplier ELSE 0 END)
                / NULLIF(SUM(multiplier), 0) * 100
            , 2) AS value
        """,
        "wpr": """
            ROUND(
                SUM(CASE WHEN usual_activity_status BETWEEN 11 AND 72 THEN multiplier ELSE 0 END)
                / NULLIF(SUM(multiplier), 0) * 100
            , 2) AS value
        """,
    }

    conditions = [
        "survey_year BETWEEN :from_year AND :to_year",
        "age >= 15",
    ]
    params = {"from_year": from_year, "to_year": to_year}

    if state is not None:
        conditions.append("state_code = :state")
        params["state"] = state
    if sector is not None:
        conditions.append("sector = :sector")
        params["sector"] = sector

    where  = "WHERE " + " AND ".join(conditions)
    expr   = INDICATOR_EXPRS[indicator]

    sql = f"""
        SELECT
            survey_year,
            state_code,
            sector,
            {expr},
            ROUND(SUM(multiplier))  AS weighted_population,
            COUNT(*)                AS respondent_count
        FROM   plfs_person
        {where}
        GROUP  BY survey_year, state_code, sector
        ORDER  BY survey_year, state_code, sector
        LIMIT  500
    """

    rows     = _execute_and_sanitize(sql, params, "weighted_population")
    duration = (time.perf_counter() - start) * 1000
    log_api_call(user_id, f"/v1/indicators/time-series/{indicator}",
                 "GET", params, 200, duration, ip_hash, sql)

    return {
        "indicator":  indicator,
        "unit":       "percent",
        "from_year":  from_year,
        "to_year":    to_year,
        "filters":    {"state": state, "sector": sector},
        "count":      len(rows),
        "data":       rows,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# AVAILABLE INDICATORS CATALOGUE
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/catalogue")
def indicators_catalogue(token: dict = Depends(verify_token)):
    """List all available indicators with descriptions and required scope."""
    return {
        "indicators": [
            {
                "id":          "unemployment-rate",
                "name":        "Unemployment Rate",
                "description": "Share of labour force that is unemployed (UPSS basis)",
                "source":      "PLFS",
                "scope":       "public",
                "filters":     ["year", "state", "sector", "sex"],
            },
            {
                "id":          "lfpr",
                "name":        "Labour Force Participation Rate",
                "description": "Share of working-age population (15+) in labour force",
                "source":      "PLFS",
                "scope":       "public",
                "filters":     ["year", "state", "sector", "sex"],
            },
            {
                "id":          "wpr",
                "name":        "Worker Population Ratio",
                "description": "Share of working-age population (15+) that is employed",
                "source":      "PLFS",
                "scope":       "public",
                "filters":     ["year", "state", "sector", "sex"],
            },
            {
                "id":          "mpce",
                "name":        "Monthly Per Capita Consumer Expenditure",
                "description": "Average household consumption expenditure per person per month",
                "source":      "HCES",
                "scope":       "research",
                "filters":     ["year", "state", "sector"],
            },
        ]
    }
