# api/mock_db.py
# SQLite in-memory database with realistic mock PLFS data.
# Used ONLY during development when db/loader.py is not yet available.
# DELETE this file once Member 1 delivers the real DB layer.
# The real engine swap is one line per router:
#   from db.loader import engine

import logging
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from security.auth import hash_password

logger = logging.getLogger(__name__)

np.random.seed(42)
N = 5000  # enough rows to give realistic indicator distributions

# ── GENERATE MOCK PLFS PERSON DATA ────────────────────────────────────────────
# activity_status distribution approximates real PLFS proportions:
# 11-72 = employed (~65%), 81-82 = unemployed (~8%), rest = outside labour force
activity_weights = [0.30, 0.20, 0.15, 0.05, 0.05, 0.05, 0.05, 0.07, 0.05, 0.03]
activity_codes   = [11, 12, 21, 31, 41, 51, 61, 71, 81, 82]

mock_plfs = pd.DataFrame({
    "survey_year":            np.random.choice([2021, 2022, 2023], N),
    "state_code":             np.random.randint(1, 29, N),
    "district_code":          np.random.randint(1, 10, N),
    "sector":                 np.random.choice([1, 2], N, p=[0.65, 0.35]),
    "age":                    np.random.randint(5, 80, N),
    "sex":                    np.random.choice([1, 2], N, p=[0.51, 0.49]),
    "usual_activity_status":  np.random.choice(activity_codes, N, p=activity_weights),
    "multiplier":             np.random.uniform(500, 5000, N),
    "nco_2004_code":          np.random.randint(100, 999, N).astype(str),
    "nic_2008_code":          np.random.randint(10, 99, N).astype(str),
})

# ── GENERATE MOCK HCES HOUSEHOLD DATA ─────────────────────────────────────────
N_HH = 2000
mock_hces = pd.DataFrame({
    "survey_year":             np.random.choice([2022, 2023], N_HH),
    "state_code":              np.random.randint(1, 29, N_HH),
    "sector":                  np.random.choice([1, 2], N_HH, p=[0.65, 0.35]),
    "household_size":          np.random.randint(1, 10, N_HH),
    "consumption_expenditure": np.random.lognormal(mean=7.5, sigma=0.5, size=N_HH),
    "multiplier":              np.random.uniform(200, 3000, N_HH),
    "social_group":            np.random.choice([1, 2, 3, 4], N_HH),
    "religion":                np.random.choice([1, 2, 3, 4, 5], N_HH),
})

# ── MOCK USERS TABLE ──────────────────────────────────────────────────────────
# Pre-hashed passwords using Argon2id
mock_users = pd.DataFrame({
    "user_id":       ["admin", "researcher1", "public1"],
    "password_hash": [
        hash_password("AdminPassword123!"),
        hash_password("ResearchPassword123!"),
        hash_password("PublicPassword123!"),
    ],
    "scope":         ["admin", "research", "public"],
    "is_active":     [True, True, True],
})

# ── BUILD IN-MEMORY SQLITE ────────────────────────────────────────────────────
# StaticPool reuses the SAME underlying connection for every engine.connect()
# so tables created during init are visible to all subsequent queries.
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

with engine.begin() as conn:
    mock_plfs.to_sql("plfs_person",    conn, index=False, if_exists="replace")
    mock_hces.to_sql("hces_household", conn, index=False, if_exists="replace")
    mock_users.to_sql("users",         conn, index=False, if_exists="replace")

    # Minimal api_keys and refresh_tokens tables
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS api_keys (
            key_id TEXT PRIMARY KEY,
            user_id TEXT, key_hash TEXT,
            scope TEXT, description TEXT,
            expires_at TEXT, revoked INTEGER DEFAULT 0
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            jti TEXT PRIMARY KEY,
            user_id TEXT, issued_at TEXT,
            expires_at TEXT, revoked INTEGER DEFAULT 0
        )
    """))

    # Materialized view equivalent for SQLite
    conn.execute(text("""
        CREATE VIEW IF NOT EXISTS mv_unemployment_rate AS
        SELECT
            state_code, sector, survey_year,
            ROUND(
                SUM(CASE WHEN usual_activity_status IN (81,82) THEN multiplier ELSE 0 END)
                / MAX(1.0, SUM(CASE WHEN usual_activity_status <= 82
                               THEN multiplier ELSE 0 END)) * 100,
            2) AS unemployment_rate,
            ROUND(SUM(multiplier)) AS weighted_population
        FROM plfs_person
        GROUP BY state_code, sector, survey_year
    """))

logger.info(
    f"Mock DB ready — "
    f"{len(mock_plfs):,} PLFS rows, "
    f"{len(mock_hces):,} HCES rows, "
    f"{len(mock_users)} users (SQLite in-memory)"
)
