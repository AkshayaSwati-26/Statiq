-- ================================================================
-- StatIQ — PostgreSQL 16 + TimescaleDB Schema
-- Runs automatically when the container starts for the first time.
-- ================================================================

-- Enable TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ── PLFS PERSON TABLE ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS plfs_person (
    id                BIGSERIAL PRIMARY KEY,
    -- Identification (sampling hierarchy)
    state_code        VARCHAR(2),
    state_name        VARCHAR(60),
    district_code     VARCHAR(4),
    sector            SMALLINT,
    sector_label      VARCHAR(10),
    fsu_serial        VARCHAR(6),     -- masked in API views
    hh_serial         VARCHAR(6),     -- masked in API views
    -- Demographics
    age               SMALLINT,
    age_group         VARCHAR(10),
    gender            SMALLINT,
    gender_label      VARCHAR(15),
    marital_status    SMALLINT,
    education_code    VARCHAR(3),
    education_label   VARCHAR(80),
    -- Employment
    usual_activity    VARCHAR(3),
    activity_label    VARCHAR(80),
    employment_status VARCHAR(15),
    in_labour_force   SMALLINT,       -- 1=yes 0=no
    is_employed       SMALLINT,       -- 1=yes 0=no
    working_age       SMALLINT,       -- 1=age 15-59 0=outside
    -- Survey design (for weighted estimates)
    multiplier        NUMERIC(18,4),
    census_count      NUMERIC(12,0),
    -- Meta
    survey_year       VARCHAR(10)  NOT NULL,
    round_no          SMALLINT,
    survey_id         VARCHAR(20),
    ingested_at       TIMESTAMPTZ  DEFAULT NOW()
);

-- Indexes for fast API queries
CREATE INDEX IF NOT EXISTS idx_plfs_state_year
    ON plfs_person(state_name, survey_year);
CREATE INDEX IF NOT EXISTS idx_plfs_employment
    ON plfs_person(employment_status, survey_year, state_name);
CREATE INDEX IF NOT EXISTS idx_plfs_gender_age
    ON plfs_person(gender, age_group, state_name);
CREATE INDEX IF NOT EXISTS idx_plfs_working_age
    ON plfs_person(working_age, state_name, gender);

-- ── HCES HEALTH HOUSEHOLD TABLE ──────────────────────────────
CREATE TABLE IF NOT EXISTS hces_health_hh (
    id               BIGSERIAL PRIMARY KEY,
    state_code       VARCHAR(2),
    state_name       VARCHAR(60),
    sector           SMALLINT,
    sector_label     VARCHAR(10),
    hh_serial        VARCHAR(6),
    fsu_serial       VARCHAR(6),
    sss              SMALLINT,
    -- Household characteristics
    hh_size          SMALLINT,
    religion         SMALLINT,
    religion_label   VARCHAR(30),
    social_group     SMALLINT,
    social_label     VARCHAR(40),
    hh_type          SMALLINT,
    hh_type_label    VARCHAR(50),
    -- Expenditure
    umce             NUMERIC(12,2),   -- Usual Monthly Consumer Expenditure (Rs)
    ins_premium      NUMERIC(12,2),   -- Insurance premium paid (Rs)
    -- Survey design
    multiplier       NUMERIC(18,4),
    nst              NUMERIC(12,0),
    nstj             NUMERIC(10,0),
    subdvsn          SMALLINT,
    caph             SMALLINT,
    smah             SMALLINT,
    -- Meta
    survey_year      VARCHAR(10),
    survey_id        VARCHAR(20),
    ingested_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hces_hh_state_sector
    ON hces_health_hh(state_name, sector_label, survey_year);
CREATE INDEX IF NOT EXISTS idx_hces_hh_social
    ON hces_health_hh(social_group, state_name);

-- ── HCES HEALTH MEMBERS TABLE ─────────────────────────────────
CREATE TABLE IF NOT EXISTS hces_health_members (
    id               BIGSERIAL PRIMARY KEY,
    state_code       VARCHAR(2),
    state_name       VARCHAR(60),
    sector           SMALLINT,
    sector_label     VARCHAR(10),
    hh_serial        VARCHAR(6),
    fsu_serial       VARCHAR(6),
    sss              SMALLINT,
    member_serial    VARCHAR(3),
    -- Demographics
    gender           SMALLINT,
    gender_label     VARCHAR(15),
    age              SMALLINT,
    age_group        VARCHAR(10),
    education_code   VARCHAR(3),
    education_label  VARCHAR(80),
    -- Health indicators
    hospitalised     SMALLINT,        -- 1=Yes 2=No
    hosp_times       SMALLINT,
    chronic_ailment  SMALLINT,        -- 1=Yes 2=No
    ailment_15d      SMALLINT,
    insurance_code   VARCHAR(3),
    insurance_label  VARCHAR(120),
    vaccine_received SMALLINT,
    -- Survey design
    multiplier       NUMERIC(18,4),
    nst              NUMERIC(12,0),
    nstj             NUMERIC(10,0),
    subdvsn          SMALLINT,
    caph             SMALLINT,
    smah             SMALLINT,
    -- Meta
    survey_year      VARCHAR(10),
    survey_id        VARCHAR(20),
    ingested_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hces_mem_state_gender
    ON hces_health_members(state_name, gender, age_group);
CREATE INDEX IF NOT EXISTS idx_hces_mem_hosp
    ON hces_health_members(hospitalised, state_name, sector_label);
CREATE INDEX IF NOT EXISTS idx_hces_mem_chronic
    ON hces_health_members(chronic_ailment, state_name, gender);
CREATE INDEX IF NOT EXISTS idx_hces_mem_insurance
    ON hces_health_members(insurance_code, state_name);

-- ── HCES HOSPITALISATION TABLE ────────────────────────────────
CREATE TABLE IF NOT EXISTS hces_health_hosp (
    id                BIGSERIAL PRIMARY KEY,
    state_code        VARCHAR(2),
    state_name        VARCHAR(60),
    sector            SMALLINT,
    sector_label      VARCHAR(10),
    hh_serial         VARCHAR(6),
    sss               SMALLINT,
    case_serial       SMALLINT,
    member_serial     VARCHAR(3),
    age_years         SMALLINT,
    ailment_code      VARCHAR(3),
    ailment_label     VARCHAR(200),
    institution_type  SMALLINT,
    institution_label VARCHAR(60),
    stay_days         SMALLINT,
    -- Expenditure (Rs)
    total_medical     NUMERIC(12,2),
    total_expense     NUMERIC(12,2),
    reimbursed        NUMERIC(12,2),
    out_of_pocket     NUMERIC(12,2),   -- total_expense - reimbursed
    finance_source    SMALLINT,
    finance_label     VARCHAR(50),
    -- Survey design
    multiplier        NUMERIC(18,4),
    nst               NUMERIC(12,0),
    nstj              NUMERIC(10,0),
    -- Meta
    survey_year       VARCHAR(10),
    survey_id         VARCHAR(20),
    ingested_at       TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hces_hosp_ailment
    ON hces_health_hosp(ailment_code, state_name, sector_label);
CREATE INDEX IF NOT EXISTS idx_hces_hosp_institution
    ON hces_health_hosp(institution_type, state_name);
CREATE INDEX IF NOT EXISTS idx_hces_hosp_oop
    ON hces_health_hosp(out_of_pocket, state_name);

-- ── API KEYS TABLE ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS api_keys (
    id              SERIAL PRIMARY KEY,
    key_hash        VARCHAR(64)  UNIQUE NOT NULL,
    tier            VARCHAR(20)  DEFAULT 'free',
    created_at      TIMESTAMPTZ  DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,
    is_active       BOOLEAN      DEFAULT TRUE,
    org_name        VARCHAR(100),
    email_hash      VARCHAR(64),
    monthly_quota   INTEGER      DEFAULT 1000,
    calls_this_month INTEGER     DEFAULT 0,
    epsilon_budget  NUMERIC(8,4) DEFAULT 10.0
);

-- ── TIMESCALEDB: API USAGE LOG (hypertable) ───────────────────
-- Every API call is logged here for usage metering + audit
CREATE TABLE IF NOT EXISTS api_usage_log (
    ts               TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    api_key_hash     VARCHAR(64),
    endpoint         VARCHAR(100),
    survey           VARCHAR(20),
    query_hash       VARCHAR(64),
    rows_returned    INTEGER,
    response_ms      INTEGER,
    cache_hit        BOOLEAN,
    privacy_tier     VARCHAR(20),
    epsilon_used     NUMERIC(6,4),
    suppressed_cells INTEGER,
    user_ip_hash     VARCHAR(64),
    status_code      SMALLINT
);

-- Convert to TimescaleDB hypertable (auto-partitions by 7-day chunks)
SELECT create_hypertable(
    'api_usage_log', 'ts',
    if_not_exists         => TRUE,
    chunk_time_interval   => INTERVAL '7 days'
);

CREATE INDEX IF NOT EXISTS idx_log_api_key
    ON api_usage_log(api_key_hash, ts DESC);
CREATE INDEX IF NOT EXISTS idx_log_survey
    ON api_usage_log(survey, ts DESC);

-- ── MATERIALIZED VIEW: LFPR by state ─────────────────────────
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_lfpr_by_state AS
SELECT
    state_name,
    sector_label,
    gender_label,
    age_group,
    survey_year,
    COUNT(*)                                                         AS sample_n,
    SUM(multiplier)                                                  AS weighted_pop,
    SUM(CASE WHEN in_labour_force = 1 THEN multiplier ELSE 0 END)   AS weighted_lf,
    SUM(CASE WHEN is_employed = 1     THEN multiplier ELSE 0 END)   AS weighted_emp,
    ROUND(
        SUM(CASE WHEN in_labour_force = 1 THEN multiplier ELSE 0 END)
        / NULLIF(SUM(multiplier), 0) * 100, 2
    ) AS lfpr_pct,
    ROUND(
        SUM(CASE WHEN is_employed = 1 THEN multiplier ELSE 0 END)
        / NULLIF(SUM(multiplier), 0) * 100, 2
    ) AS wpr_pct
FROM plfs_person
WHERE working_age = 1 AND state_name IS NOT NULL
GROUP BY state_name, sector_label, gender_label, age_group, survey_year
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_lfpr
    ON mv_lfpr_by_state(state_name, sector_label, gender_label, age_group, survey_year);

-- ── MATERIALIZED VIEW: Hospitalisation rate ───────────────────
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_hosp_rate AS
SELECT
    state_name,
    sector_label,
    gender_label,
    age_group,
    survey_year,
    COUNT(*)                                                             AS sample_n,
    SUM(multiplier)                                                      AS weighted_pop,
    SUM(CASE WHEN hospitalised = 1 THEN multiplier ELSE 0 END)          AS weighted_hosp,
    ROUND(
        SUM(CASE WHEN hospitalised = 1 THEN multiplier ELSE 0 END)
        / NULLIF(SUM(multiplier), 0) * 100, 2
    ) AS hosp_rate_pct
FROM hces_health_members
WHERE state_name IS NOT NULL
GROUP BY state_name, sector_label, gender_label, age_group, survey_year
WITH NO DATA;

-- ── PRIVACY-SAFE API VIEWS ────────────────────────────────────
-- These are what the FastAPI layer (Member 2) queries.
-- PII fields (fsu_serial, hh_serial) are excluded.

CREATE OR REPLACE VIEW api_plfs_person AS
SELECT
    state_name, sector_label, age, age_group, gender_label,
    education_label, activity_label, employment_status,
    in_labour_force, is_employed, working_age,
    multiplier, survey_year
FROM plfs_person;

CREATE OR REPLACE VIEW api_hces_members AS
SELECT
    state_name, sector_label, gender_label, age, age_group,
    education_label, insurance_label, hospitalised, hosp_times,
    chronic_ailment, ailment_15d, vaccine_received,
    multiplier, survey_year
FROM hces_health_members;

CREATE OR REPLACE VIEW api_hces_hosp AS
SELECT
    state_name, sector_label, age_years, ailment_label,
    institution_label, stay_days, total_expense,
    reimbursed, out_of_pocket, finance_label,
    multiplier, survey_year
FROM hces_health_hosp;

COMMENT ON TABLE api_usage_log IS 'TimescaleDB hypertable — 7-day partitions';
COMMENT ON VIEW  api_plfs_person IS 'Privacy-safe PLFS view — no PII columns';
COMMENT ON VIEW  api_hces_members IS 'Privacy-safe HCES members view — no PII columns';

-- ── METADATA REGISTRY TABLES ──────────────────────────────────
CREATE TABLE IF NOT EXISTS survey_metadata_relationships (
    id SERIAL PRIMARY KEY,
    survey_id VARCHAR(20) NOT NULL,
    parent_table VARCHAR(60) NOT NULL,
    child_table VARCHAR(60) NOT NULL,
    join_keys TEXT[] NOT NULL,
    relationship_type VARCHAR(20) DEFAULT 'one-to-many',
    description TEXT
);

CREATE TABLE IF NOT EXISTS survey_metadata_dictionary (
    id SERIAL PRIMARY KEY,
    survey_id VARCHAR(20) NOT NULL,
    variable_name VARCHAR(60) NOT NULL,
    code VARCHAR(20) NOT NULL,
    code_description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS survey_metadata_columns (
    id SERIAL PRIMARY KEY,
    survey_id VARCHAR(20) NOT NULL,
    table_name VARCHAR(60) NOT NULL,
    column_name VARCHAR(60) NOT NULL,
    data_type VARCHAR(30) NOT NULL,
    description TEXT,
    is_sensitive BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS survey_metadata_samples (
    id SERIAL PRIMARY KEY,
    survey_id VARCHAR(20) NOT NULL,
    table_name VARCHAR(60) NOT NULL,
    column_name VARCHAR(60) NOT NULL,
    sample_values JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS survey_metadata_profiles (
    id SERIAL PRIMARY KEY,
    survey_id VARCHAR(20) NOT NULL,
    table_name VARCHAR(60) NOT NULL,
    row_count BIGINT NOT NULL,
    column_count INT NOT NULL,
    missing_values BIGINT NOT NULL,
    profile_data JSONB NOT NULL,
    profiled_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS survey_metadata_suggested_queries (
    id SERIAL PRIMARY KEY,
    survey_id VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    sql_query TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_meta_rel_survey ON survey_metadata_relationships(survey_id);
CREATE INDEX IF NOT EXISTS idx_meta_dict_var ON survey_metadata_dictionary(survey_id, variable_name);
CREATE INDEX IF NOT EXISTS idx_meta_cols_tbl ON survey_metadata_columns(survey_id, table_name);
CREATE INDEX IF NOT EXISTS idx_meta_samples_col ON survey_metadata_samples(survey_id, table_name, column_name);
CREATE INDEX IF NOT EXISTS idx_meta_prof_tbl ON survey_metadata_profiles(survey_id, table_name);
CREATE INDEX IF NOT EXISTS idx_meta_queries_survey ON survey_metadata_suggested_queries(survey_id);

