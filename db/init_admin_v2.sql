-- ================================================================
-- StatIQ Admin V2 — Database Migration Script
-- Run once inside the statiq-postgres container:
--   docker exec -i statiq-postgres psql -U statiq -d statiq < db/init_admin_v2.sql
-- ================================================================

-- ── 1. DATASETS REGISTRY ─────────────────────────────────────────
-- Replaces hardcoded frontend free/premium checks.
-- Every uploaded dataset (via /upload) registers a row here.
CREATE TABLE IF NOT EXISTS datasets_registry (
    dataset_id      TEXT        PRIMARY KEY,          -- sanitized table name e.g. 'upload_plfs_2024_20260617'
    original_name   TEXT        NOT NULL,             -- original uploaded filename
    table_name      TEXT        NOT NULL UNIQUE,      -- PostgreSQL table name
    file_format     TEXT,                             -- CSV / XLSX / SAV / DTA / TXT / ZIP
    access_tier     TEXT        NOT NULL DEFAULT 'free'
                                CHECK (access_tier IN ('free','premium')),
    row_count       BIGINT      DEFAULT 0,
    column_count    INT         DEFAULT 0,
    file_hash       TEXT,                             -- SHA-256 of raw file bytes (for deduplication)
    uploaded_by     TEXT        REFERENCES users(user_id) ON DELETE SET NULL,
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    description     TEXT,
    tags            TEXT[]      DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_datasets_tier     ON datasets_registry(access_tier);
CREATE INDEX IF NOT EXISTS idx_datasets_active   ON datasets_registry(is_active);
CREATE INDEX IF NOT EXISTS idx_datasets_hash     ON datasets_registry(file_hash);
CREATE INDEX IF NOT EXISTS idx_datasets_uploaded ON datasets_registry(uploaded_at DESC);

-- Pre-register the built-in MoSPI datasets
INSERT INTO datasets_registry (dataset_id, original_name, table_name, file_format, access_tier, description)
VALUES
  ('api_plfs_person',   'PLFS 2024 Annual Survey',          'api_plfs_person',   'VIEW', 'free',    'Periodic Labour Force Survey — person level records with employment status'),
  ('api_hces_members',  'HCES 2023 Health Members Survey',  'api_hces_members',  'VIEW', 'premium', 'Household Consumption Expenditure Survey — health members data'),
  ('api_hces_hosp',     'HCES 2023 Hospitalisation Survey', 'api_hces_hosp',     'VIEW', 'premium', 'Household Consumption Expenditure Survey — hospitalisation episodes')
ON CONFLICT (dataset_id) DO NOTHING;


-- ── 2. ADMIN SETTINGS ────────────────────────────────────────────
-- Key-value store for runtime-configurable admin parameters.
-- Currently: min_cell_size, always_masked_columns
CREATE TABLE IF NOT EXISTS admin_settings (
    key             TEXT        PRIMARY KEY,
    value           TEXT        NOT NULL,
    description     TEXT,
    updated_by      TEXT        REFERENCES users(user_id) ON DELETE SET NULL,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO admin_settings (key, value, description) VALUES
  ('min_cell_size',        '30',   'Minimum respondent count per aggregation cell before suppression fires'),
  ('session_timeout_min',  '30',   'JWT access token lifetime in minutes'),
  ('max_query_limit',      '500',  'Maximum rows returned per query')
ON CONFLICT (key) DO NOTHING;


-- ── 3. SURVEY_METADATA_COLUMNS — add is_masked column ─────────────
-- is_sensitive: admin marks as potentially identifying (flagged in data dictionary)
-- is_masked:    column is stripped from ALL API responses for all scopes
ALTER TABLE survey_metadata_columns
    ADD COLUMN IF NOT EXISTS is_masked BOOLEAN NOT NULL DEFAULT FALSE;

-- Seed known PII columns as masked by default
UPDATE survey_metadata_columns
   SET is_sensitive = TRUE, is_masked = TRUE
 WHERE column_name IN ('household_id','person_id','fsu_serial_no','second_stage_stratum','sample_hhd_no');


-- ── 4. AUTH EVENTS LOG ───────────────────────────────────────────
-- Structured auth event log (supplementing the JSONL file).
-- Allows SQL queries from the Audit Log admin page.
CREATE TABLE IF NOT EXISTS auth_events_log (
    id              BIGSERIAL   PRIMARY KEY,
    event_time      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type      TEXT        NOT NULL,   -- login_success, login_failure, logout, upgrade_success, etc.
    user_id         TEXT,
    ip_hash         TEXT,
    detail          TEXT,
    scope           TEXT
);

CREATE INDEX IF NOT EXISTS idx_auth_events_time ON auth_events_log(event_time DESC);
CREATE INDEX IF NOT EXISTS idx_auth_events_user ON auth_events_log(user_id, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_auth_events_type ON auth_events_log(event_type, event_time DESC);


-- ── 5. ADD last_login_at trigger ────────────────────────────────
-- Ensure users.last_login_at is updated on successful login
-- (The application layer does this, but trigger adds safety net)
CREATE OR REPLACE FUNCTION update_last_login()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.event_type = 'login_success' AND NEW.user_id IS NOT NULL THEN
        UPDATE users SET last_login_at = NEW.event_time WHERE user_id = NEW.user_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS auth_events_last_login ON auth_events_log;
CREATE TRIGGER auth_events_last_login
    AFTER INSERT ON auth_events_log
    FOR EACH ROW EXECUTE FUNCTION update_last_login();


-- ── 6. GRANT permissions to API role ────────────────────────────
GRANT SELECT, INSERT, UPDATE, DELETE ON datasets_registry TO mospi_api_readonly;
GRANT SELECT, INSERT, UPDATE         ON admin_settings     TO mospi_api_readonly;
GRANT SELECT, INSERT                 ON auth_events_log    TO mospi_api_readonly;
GRANT USAGE, SELECT ON SEQUENCE auth_events_log_id_seq    TO mospi_api_readonly;

-- Done
DO $$ BEGIN
    RAISE NOTICE 'Admin V2 migration complete: datasets_registry, admin_settings, auth_events_log created.';
END $$;
