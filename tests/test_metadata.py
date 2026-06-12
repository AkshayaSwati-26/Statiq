import pytest
from ai import metadata_service

def test_get_schema_structure():
    schema = metadata_service.get_schema()
    assert "survey_id" in schema
    assert "tables" in schema
    assert isinstance(schema["tables"], list)
    
    if len(schema["tables"]) > 0:
        table = schema["tables"][0]
        assert "table_name" in table
        assert "columns" in table
        assert isinstance(table["columns"], list)
        
        if len(table["columns"]) > 0:
            column = table["columns"][0]
            assert "column_name" in column
            assert "data_type" in column
            assert "description" in column
            assert "sample_values" in column

def test_get_data_dictionary():
    dd = metadata_service.get_data_dictionary()
    assert isinstance(dd, list)
    if len(dd) > 0:
        item = dd[0]
        assert "table_name" in item
        assert "column_name" in item
        assert "definition" in item

def test_get_dataset_profile():
    profile = metadata_service.get_dataset_profile()
    assert isinstance(profile, list)
    if len(profile) > 0:
        item = profile[0]
        assert "profile_key" in item
        assert "profile_value" in item

def test_get_sensitive_columns():
    sensitive = metadata_service.get_sensitive_columns()
    assert isinstance(sensitive, list)
    if len(sensitive) > 0:
        item = sensitive[0]
        assert "table_name" in item
        assert "column_name" in item
        assert "sensitivity_level" in item
