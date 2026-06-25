-- ================================================================
-- StatIQ — Complete PostgreSQL 16 + TimescaleDB Init Script
-- ================================================================

-- Enable TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ── PLFS PERSON TABLE ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS plfs_person (
    id                BIGSERIAL PRIMARY KEY,
    state_code        VARCHAR(2),
    state_name        VARCHAR(60),
    district_code     VARCHAR(4),
    sector            SMALLINT,
    sector_label      VARCHAR(10),
    fsu_serial        VARCHAR(6),
    hh_serial         VARCHAR(6),
    age               SMALLINT,
    age_group         VARCHAR(10),
    gender            SMALLINT,
    gender_label      VARCHAR(15),
    marital_status    SMALLINT,
    education_code    VARCHAR(3),
    education_label   VARCHAR(80),
    usual_activity    VARCHAR(3),
    activity_label    VARCHAR(80),
    employment_status VARCHAR(15),
    in_labour_force   SMALLINT,
    is_employed       SMALLINT,
    working_age       SMALLINT,
    multiplier        NUMERIC(18,4),
    census_count      NUMERIC(12,0),
    survey_year       VARCHAR(10)  NOT NULL,
    round_no          SMALLINT,
    survey_id         VARCHAR(20),
    ingested_at       TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_plfs_state_year ON plfs_person(state_name, survey_year);
CREATE INDEX IF NOT EXISTS idx_plfs_employment ON plfs_person(employment_status, survey_year, state_name);
CREATE INDEX IF NOT EXISTS idx_plfs_gender_age ON plfs_person(gender, age_group, state_name);
CREATE INDEX IF NOT EXISTS idx_plfs_working_age ON plfs_person(working_age, state_name, gender);

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
    hh_size          SMALLINT,
    religion         SMALLINT,
    religion_label   VARCHAR(30),
    social_group     SMALLINT,
    social_label     VARCHAR(40),
    hh_type          SMALLINT,
    hh_type_label    VARCHAR(50),
    umce             NUMERIC(12,2),
    ins_premium      NUMERIC(12,2),
    multiplier       NUMERIC(18,4),
    nst              NUMERIC(12,0),
    nstj             NUMERIC(10,0),
    subdvsn          SMALLINT,
    caph             SMALLINT,
    smah             SMALLINT,
    survey_year      VARCHAR(10),
    survey_id        VARCHAR(20),
    ingested_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hces_hh_state_sector ON hces_health_hh(state_name, sector_label, survey_year);
CREATE INDEX IF NOT EXISTS idx_hces_hh_social ON hces_health_hh(social_group, state_name);

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
    gender           SMALLINT,
    gender_label     VARCHAR(15),
    age              SMALLINT,
    age_group        VARCHAR(10),
    education_code   VARCHAR(3),
    education_label  VARCHAR(80),
    hospitalised     SMALLINT,
    hosp_times       SMALLINT,
    chronic_ailment  SMALLINT,
    ailment_15d      SMALLINT,
    insurance_code   VARCHAR(3),
    insurance_label  VARCHAR(120),
    vaccine_received SMALLINT,
    multiplier       NUMERIC(18,4),
    nst              NUMERIC(12,0),
    nstj             NUMERIC(10,0),
    subdvsn          SMALLINT,
    caph             SMALLINT,
    smah             SMALLINT,
    survey_year      VARCHAR(10),
    survey_id        VARCHAR(20),
    ingested_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hces_mem_state_gender ON hces_health_members(state_name, gender, age_group);
CREATE INDEX IF NOT EXISTS idx_hces_mem_hosp ON hces_health_members(hospitalised, state_name, sector_label);
CREATE INDEX IF NOT EXISTS idx_hces_mem_chronic ON hces_health_members(chronic_ailment, state_name, gender);
CREATE INDEX IF NOT EXISTS idx_hces_mem_insurance ON hces_health_members(insurance_code, state_name);

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
    total_medical     NUMERIC(12,2),
    total_expense     NUMERIC(12,2),
    reimbursed        NUMERIC(12,2),
    out_of_pocket     NUMERIC(12,2),
    finance_source    SMALLINT,
    finance_label     VARCHAR(50),
    multiplier        NUMERIC(18,4),
    raw_multiplier    NUMERIC(18,4),
    nst               NUMERIC(12,0),
    nstj              NUMERIC(10,0),
    survey_year       VARCHAR(10),
    survey_id         VARCHAR(20),
    ingested_at       TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hces_hosp_ailment ON hces_health_hosp(ailment_code, state_name, sector_label);
CREATE INDEX IF NOT EXISTS idx_hces_hosp_institution ON hces_health_hosp(institution_type, state_name);
CREATE INDEX IF NOT EXISTS idx_hces_hosp_oop ON hces_health_hosp(out_of_pocket, state_name);

-- ── TIMESCALEDB: API USAGE LOG ────────────────────────────────
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

SELECT create_hypertable(
    'api_usage_log', 'ts',
    if_not_exists         => TRUE,
    chunk_time_interval   => INTERVAL '7 days'
);

CREATE INDEX IF NOT EXISTS idx_log_api_key ON api_usage_log(api_key_hash, ts DESC);
CREATE INDEX IF NOT EXISTS idx_log_survey ON api_usage_log(survey, ts DESC);

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

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_lfpr ON mv_lfpr_by_state(state_name, sector_label, gender_label, age_group, survey_year);

-- ── MATERIALIZED VIEW: Unemployment rate ──────────────────────
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_unemployment_rate AS
SELECT
    state_code,
    sector,
    survey_year,
    ROUND(
        SUM(CASE WHEN in_labour_force = 1 AND is_employed = 0 THEN multiplier ELSE 0 END)
        / NULLIF(SUM(CASE WHEN in_labour_force = 1 THEN multiplier ELSE 0 END), 0) * 100,
        2
    ) AS unemployment_rate,
    ROUND(SUM(multiplier)) AS weighted_population
FROM plfs_person
WHERE state_code IS NOT NULL
GROUP BY state_code, sector, survey_year
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_unemployment ON mv_unemployment_rate(state_code, sector, survey_year);

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
    survey_id   TEXT NOT NULL,
    table_name  TEXT NOT NULL,
    column_name TEXT NOT NULL,
    data_type   TEXT NOT NULL,
    description TEXT,
    is_sensitive BOOLEAN DEFAULT FALSE,
    is_masked    BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_survey_meta_col UNIQUE (survey_id, table_name, column_name)
);

CREATE TABLE IF NOT EXISTS survey_metadata_samples (
    id SERIAL PRIMARY KEY,
    survey_id    TEXT NOT NULL,
    table_name   TEXT NOT NULL,
    column_name  TEXT NOT NULL,
    sample_values JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS survey_metadata_profiles (
    id SERIAL PRIMARY KEY,
    survey_id    TEXT NOT NULL,
    table_name   TEXT NOT NULL,
    row_count    BIGINT NOT NULL,
    column_count INT NOT NULL,
    missing_values BIGINT NOT NULL,
    profile_data JSONB NOT NULL,
    profiled_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS survey_metadata_suggested_queries (
    id SERIAL PRIMARY KEY,
    survey_id   TEXT NOT NULL,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    sql_query   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_meta_rel_survey ON survey_metadata_relationships(survey_id);
CREATE INDEX IF NOT EXISTS idx_meta_dict_var ON survey_metadata_dictionary(survey_id, variable_name);
CREATE INDEX IF NOT EXISTS idx_meta_cols_tbl ON survey_metadata_columns(survey_id, table_name);
CREATE INDEX IF NOT EXISTS idx_meta_samples_col ON survey_metadata_samples(survey_id, table_name, column_name);
CREATE INDEX IF NOT EXISTS idx_meta_prof_tbl ON survey_metadata_profiles(survey_id, table_name);
CREATE INDEX IF NOT EXISTS idx_meta_queries_survey ON survey_metadata_suggested_queries(survey_id);

-- ── INTEGRATION VIEWS FOR OTHER LAYERS ────────────────────────
CREATE OR REPLACE VIEW metadata_registry AS
SELECT 
    c.survey_id,
    c.table_name, 
    c.column_name, 
    c.data_type, 
    c.description, 
    s.sample_values::TEXT AS sample_values
FROM survey_metadata_columns c
LEFT JOIN survey_metadata_samples s 
    ON c.survey_id = s.survey_id 
    AND c.table_name = s.table_name 
    AND c.column_name = s.column_name;

CREATE OR REPLACE VIEW relationship_registry AS
SELECT 
    parent_table, 
    child_table, 
    join_keys[1] AS join_key,
    relationship_type
FROM survey_metadata_relationships;

CREATE OR REPLACE VIEW suggested_query_registry AS
SELECT 
    title AS question, 
    sql_query, 
    COALESCE(description, 'general') AS category
FROM survey_metadata_suggested_queries;

CREATE OR REPLACE VIEW data_dictionary AS
SELECT 
    table_name, 
    column_name, 
    description AS definition
FROM survey_metadata_columns;

CREATE OR REPLACE VIEW dataset_profile AS
SELECT 
    'row_count' AS profile_key, 
    row_count::TEXT AS profile_value
FROM survey_metadata_profiles
UNION ALL
SELECT 
    'column_count' AS profile_key, 
    column_count::TEXT AS profile_value
FROM survey_metadata_profiles
UNION ALL
SELECT 
    'missing_values' AS profile_key, 
    missing_values::TEXT AS profile_value
FROM survey_metadata_profiles;

CREATE OR REPLACE VIEW sensitive_column_registry AS
SELECT 
    table_name, 
    column_name, 
    CASE WHEN is_sensitive THEN 'high' ELSE 'low' END AS sensitivity_level
FROM survey_metadata_columns;


-- ── AUTH TABLES & SEED DATA ──────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    user_id         TEXT        PRIMARY KEY,
    password_hash   TEXT        NOT NULL,
    scope           TEXT        NOT NULL DEFAULT 'public' CHECK (scope IN ('public','research','admin')),
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    email           TEXT        UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_users_email    ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_active   ON users (is_active);

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS users_updated_at ON users;
CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TABLE IF NOT EXISTS api_keys (
    key_id      TEXT        PRIMARY KEY,
    user_id     TEXT        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    key_hash    TEXT        NOT NULL UNIQUE,
    scope       TEXT        NOT NULL DEFAULT 'public' CHECK (scope IN ('public','research')),
    description TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked     BOOLEAN     NOT NULL DEFAULT FALSE,
    last_used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user    ON api_keys (user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash    ON api_keys (key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_active  ON api_keys (revoked, expires_at);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    jti         TEXT        PRIMARY KEY,
    user_id     TEXT        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    issued_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked     BOOLEAN     NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user    ON refresh_tokens (user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_active  ON refresh_tokens (revoked, expires_at);

-- Read-only API Role configuration
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'mospi_api_readonly') THEN
        CREATE ROLE mospi_api_readonly LOGIN PASSWORD 'change-in-production';
    END IF;
END
$$;

GRANT SELECT ON plfs_person     TO mospi_api_readonly;
GRANT SELECT ON hces_health_hh  TO mospi_api_readonly;
GRANT SELECT ON hces_health_members TO mospi_api_readonly;
GRANT SELECT ON hces_health_hosp TO mospi_api_readonly;

GRANT SELECT, INSERT, UPDATE ON users          TO mospi_api_readonly;
GRANT SELECT, INSERT, UPDATE ON api_keys       TO mospi_api_readonly;
GRANT SELECT, INSERT, UPDATE ON refresh_tokens TO mospi_api_readonly;

-- Seed Default Users
INSERT INTO users (user_id, password_hash, scope, is_active, email)
VALUES
    ('admin', '$argon2id$v=19$m=65536,t=3,p=4$EVd0yt4N1F1yV2gcG5GvHw$46mXnV854w+ys+mv/VehCWUFLWuzXoc6MQHkGePx/dU', 'admin', TRUE, 'admin@mospi.gov.in'),
    ('analyst', '$argon2id$v=19$m=65536,t=3,p=4$EVd0yt4N1F1yV2gcG5GvHw$46mXnV854w+ys+mv/VehCWUFLWuzXoc6MQHkGePx/dU', 'research', TRUE, 'analyst@mospi.gov.in'),
    ('student', '$argon2id$v=19$m=65536,t=3,p=4$EVd0yt4N1F1yV2gcG5GvHw$46mXnV854w+ys+mv/VehCWUFLWuzXoc6MQHkGePx/dU', 'public', TRUE, 'student@univ.edu.in')
ON CONFLICT (user_id) DO NOTHING;
