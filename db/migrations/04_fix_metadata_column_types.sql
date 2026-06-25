-- Migration 04: Fix survey_metadata_columns column types and metadata_registry view
-- Issue: VARCHAR(20/60/30) constraints were too narrow for real dataset names & column names,
--        causing StringDataRightTruncation errors on insert.
--        metadata_registry view was missing the survey_id column, breaking NL-query adapter.
-- Safe to re-run (idempotent via CASCADE + OR REPLACE).

BEGIN;

-- Step 1: Drop views that depend on survey_metadata_columns columns being altered
DROP VIEW IF EXISTS metadata_registry CASCADE;
DROP VIEW IF EXISTS data_dictionary CASCADE;
DROP VIEW IF EXISTS sensitive_column_registry CASCADE;

-- Step 2: Widen all narrow VARCHAR columns to TEXT
ALTER TABLE survey_metadata_columns
    ALTER COLUMN survey_id   TYPE TEXT,
    ALTER COLUMN table_name  TYPE TEXT,
    ALTER COLUMN column_name TYPE TEXT,
    ALTER COLUMN data_type   TYPE TEXT;

-- Step 3: Add missing is_masked column (if it doesn't already exist)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'survey_metadata_columns'
          AND column_name = 'is_masked'
    ) THEN
        ALTER TABLE survey_metadata_columns
            ADD COLUMN is_masked BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END $$;

-- Step 4: Also widen survey_metadata_samples if narrow
ALTER TABLE survey_metadata_samples
    ALTER COLUMN survey_id   TYPE TEXT,
    ALTER COLUMN table_name  TYPE TEXT,
    ALTER COLUMN column_name TYPE TEXT;

-- Step 5: Widen survey_metadata_profiles if narrow
ALTER TABLE survey_metadata_profiles
    ALTER COLUMN survey_id  TYPE TEXT,
    ALTER COLUMN table_name TYPE TEXT;

-- Step 6: Widen survey_metadata_suggested_queries if narrow
ALTER TABLE survey_metadata_suggested_queries
    ALTER COLUMN survey_id TYPE TEXT;

-- Step 7: Add unique constraint to prevent duplicate inserts
ALTER TABLE survey_metadata_columns
    DROP CONSTRAINT IF EXISTS uq_survey_meta_col;
ALTER TABLE survey_metadata_columns
    ADD CONSTRAINT uq_survey_meta_col UNIQUE (survey_id, table_name, column_name);

-- Step 8: Recreate metadata_registry WITH survey_id (fixes NL-query adapter)
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
        ON  c.survey_id   = s.survey_id
        AND c.table_name  = s.table_name
        AND c.column_name = s.column_name;

-- Step 9: Recreate data_dictionary view
CREATE OR REPLACE VIEW data_dictionary AS
    SELECT table_name, column_name, description AS definition
    FROM survey_metadata_columns;

-- Step 10: Recreate sensitive_column_registry view
CREATE OR REPLACE VIEW sensitive_column_registry AS
    SELECT
        table_name,
        column_name,
        CASE WHEN is_sensitive THEN 'high' ELSE 'low' END AS sensitivity_level
    FROM survey_metadata_columns;

COMMIT;
