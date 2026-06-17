# tests/unit/test_sql_guard.py
# Unit tests for the SQL safety layer.
# Every injection technique in the OWASP top-10 must be caught here.
# Run: pytest tests/unit/test_sql_guard.py -v

import pytest
from fastapi import HTTPException

import os
os.environ["FORCE_HTTPS"] = "false"


# ═══════════════════════════════════════════════════════════════════════════════
# SQL VALIDATION — ALLOWED QUERIES
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidSQLAccepted:

    def test_simple_select_passes(self):
        from security.sql_guard import validate_sql
        sql = "SELECT state_code, COUNT(*) FROM plfs_person GROUP BY state_code"
        result = validate_sql(sql)
        assert "SELECT" in result.upper()

    def test_select_with_where_passes(self):
        from security.sql_guard import validate_sql
        sql = "SELECT * FROM plfs_person WHERE survey_year = 2023 LIMIT 100"
        result = validate_sql(sql)
        assert result is not None

    def test_limit_added_if_missing(self):
        from security.sql_guard import validate_sql
        from security.config import MAX_QUERY_LIMIT
        sql = "SELECT state_code FROM plfs_person"
        result = validate_sql(sql)
        assert f"LIMIT {MAX_QUERY_LIMIT}" in result.upper() or "LIMIT" in result.upper()

    def test_existing_limit_capped(self):
        from security.sql_guard import validate_sql
        from security.config import MAX_QUERY_LIMIT
        sql = f"SELECT state_code FROM plfs_person LIMIT {MAX_QUERY_LIMIT + 10000}"
        result = validate_sql(sql)
        assert str(MAX_QUERY_LIMIT + 10000) not in result

    def test_lowercase_select_passes(self):
        from security.sql_guard import validate_sql
        result = validate_sql("select state_code from plfs_person limit 10")
        assert result is not None


# ═══════════════════════════════════════════════════════════════════════════════
# SQL VALIDATION — BLOCKED QUERIES
# ═══════════════════════════════════════════════════════════════════════════════

class TestDangerousSQLBlocked:

    def _assert_blocked(self, sql: str):
        from security.sql_guard import validate_sql
        with pytest.raises(HTTPException) as exc:
            validate_sql(sql)
        assert exc.value.status_code == 400

    def test_drop_table_blocked(self):
        self._assert_blocked("DROP TABLE plfs_person")

    def test_delete_blocked(self):
        self._assert_blocked("DELETE FROM plfs_person WHERE 1=1")

    def test_insert_blocked(self):
        self._assert_blocked("INSERT INTO plfs_person VALUES (1,2,3)")

    def test_update_blocked(self):
        self._assert_blocked("UPDATE plfs_person SET state_code=1")

    def test_truncate_blocked(self):
        self._assert_blocked("TRUNCATE TABLE plfs_person")

    def test_union_injection_blocked(self):
        self._assert_blocked(
            "SELECT state_code FROM plfs_person UNION SELECT password FROM users"
        )

    def test_sql_comment_injection_blocked(self):
        self._assert_blocked(
            "SELECT * FROM plfs_person WHERE state_code=1 -- OR 1=1"
        )

    def test_statement_chaining_blocked(self):
        self._assert_blocked(
            "SELECT * FROM plfs_person; DROP TABLE users"
        )

    def test_information_schema_blocked(self):
        self._assert_blocked(
            "SELECT table_name FROM INFORMATION_SCHEMA.TABLES"
        )

    def test_pg_catalog_blocked(self):
        self._assert_blocked("SELECT * FROM pg_catalog.pg_tables")

    def test_empty_sql_blocked(self):
        self._assert_blocked("")

    def test_non_select_blocked(self):
        self._assert_blocked("EXEC xp_cmdshell('ls -la')")

    def test_load_file_blocked(self):
        self._assert_blocked("SELECT LOAD_FILE('/etc/passwd')")

    def test_sql_too_long_blocked(self):
        from security.sql_guard import validate_sql
        from security.config import MAX_SQL_LENGTH
        long_sql = "SELECT " + "state_code, " * 1000 + "1 FROM plfs_person"
        with pytest.raises(HTTPException) as exc:
            validate_sql(long_sql)
        assert exc.value.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# ALLOWLIST VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestAllowlists:

    def test_valid_table_passes(self):
        from security.sql_guard import validate_table_name
        assert validate_table_name("plfs_person") == "plfs_person"

    def test_invalid_table_blocked(self):
        from security.sql_guard import validate_table_name
        with pytest.raises(HTTPException) as exc:
            validate_table_name("users")
        assert exc.value.status_code == 400

    def test_sql_injection_in_table_blocked(self):
        from security.sql_guard import validate_table_name
        with pytest.raises(HTTPException):
            validate_table_name("plfs_person; DROP TABLE users --")

    def test_valid_column_passes(self):
        from security.sql_guard import validate_column_name
        assert validate_column_name("state_code") == "state_code"

    def test_invalid_column_blocked(self):
        from security.sql_guard import validate_column_name
        with pytest.raises(HTTPException):
            validate_column_name("password_hash")

    def test_all_allowed_tables_pass(self):
        from security.sql_guard import validate_table_name
        from security.config import ALLOWED_TABLES
        for table in ALLOWED_TABLES:
            assert validate_table_name(table) == table

    def test_all_allowed_columns_pass(self):
        from security.sql_guard import validate_column_name
        from security.config import ALLOWED_COLUMNS
        for col in ALLOWED_COLUMNS:
            assert validate_column_name(col) == col


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT SANITIZATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestOutputSanitization:

    def test_masked_columns_removed(self):
        from security.sql_guard import mask_sensitive_columns
        from security.config import ALWAYS_MASKED_COLUMNS
        rows = [{"state_code": 1, "household_id": "HH123", "multiplier": 500}]
        result = mask_sensitive_columns(rows)
        assert "household_id" not in result[0]
        assert "state_code" in result[0]

    def test_empty_rows_pass_through(self):
        from security.sql_guard import mask_sensitive_columns
        assert mask_sensitive_columns([]) == []

    def test_cell_suppression_small_group(self):
        from security.sql_guard import enforce_cell_suppression
        from security.config import MIN_CELL_SIZE
        rows = [{
            "state_code": 1,
            "unemployment_rate": 12.5,
            "weighted_population": MIN_CELL_SIZE - 1,  # below threshold
        }]
        result = enforce_cell_suppression(rows, "weighted_population")
        assert result[0]["_suppressed"] is True
        assert result[0]["unemployment_rate"] is None

    def test_cell_suppression_large_group_passes(self):
        from security.sql_guard import enforce_cell_suppression
        from security.config import MIN_CELL_SIZE
        rows = [{
            "state_code": 1,
            "unemployment_rate": 12.5,
            "weighted_population": MIN_CELL_SIZE * 10,
        }]
        result = enforce_cell_suppression(rows, "weighted_population")
        assert "_suppressed" not in result[0]
        assert result[0]["unemployment_rate"] == 12.5

    def test_fsu_serial_no_masked(self):
        from security.sql_guard import mask_sensitive_columns
        rows = [{"state_code": 5, "fsu_serial_no": "FSU001", "age": 35}]
        result = mask_sensitive_columns(rows)
        assert "fsu_serial_no" not in result[0]
        assert "age" in result[0]
