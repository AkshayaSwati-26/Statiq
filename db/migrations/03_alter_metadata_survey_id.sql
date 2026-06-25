-- db/migrations/03_alter_metadata_survey_id.sql
-- Expand varchar limits on metadata tables to support longer dynamic table/column names.

-- 1. Drop views that depend on the metadata tables
DROP VIEW IF EXISTS metadata_registry CASCADE;
DROP VIEW IF EXISTS relationship_registry CASCADE;
DROP VIEW IF EXISTS suggested_query_registry CASCADE;
DROP VIEW IF EXISTS data_dictionary CASCADE;
DROP VIEW IF EXISTS dataset_profile CASCADE;
DROP VIEW IF EXISTS sensitive_column_registry CASCADE;

-- 2. Alter table columns
-- survey_metadata_relationships
ALTER TABLE survey_metadata_relationships ALTER COLUMN survey_id TYPE VARCHAR(100);
ALTER TABLE survey_metadata_relationships ALTER COLUMN parent_table TYPE VARCHAR(100);
ALTER TABLE survey_metadata_relationships ALTER COLUMN child_table TYPE VARCHAR(100);

-- survey_metadata_dictionary
ALTER TABLE survey_metadata_dictionary ALTER COLUMN survey_id TYPE VARCHAR(100);

-- survey_metadata_columns
ALTER TABLE survey_metadata_columns ALTER COLUMN survey_id TYPE VARCHAR(100);
ALTER TABLE survey_metadata_columns ALTER COLUMN table_name TYPE VARCHAR(100);
ALTER TABLE survey_metadata_columns ALTER COLUMN column_name TYPE VARCHAR(100);

-- survey_metadata_samples
ALTER TABLE survey_metadata_samples ALTER COLUMN survey_id TYPE VARCHAR(100);
ALTER TABLE survey_metadata_samples ALTER COLUMN table_name TYPE VARCHAR(100);
ALTER TABLE survey_metadata_samples ALTER COLUMN column_name TYPE VARCHAR(100);

-- survey_metadata_profiles
ALTER TABLE survey_metadata_profiles ALTER COLUMN survey_id TYPE VARCHAR(100);
ALTER TABLE survey_metadata_profiles ALTER COLUMN table_name TYPE VARCHAR(100);

-- survey_metadata_suggested_queries
ALTER TABLE survey_metadata_suggested_queries ALTER COLUMN survey_id TYPE VARCHAR(100);

-- 3. Recreate the views
CREATE OR REPLACE VIEW metadata_registry AS
SELECT 
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
