import pytest
from ai import context_builder

def test_build_context_structure():
    context = context_builder.build_context("What is the unemployment rate?")
    
    assert "schema" in context
    assert "relationships" in context
    assert "examples" in context
    assert "survey_metadata" in context
    assert "data_dictionary" in context
    assert "dataset_profile" in context
    assert "query_type" in context
    assert "timestamp" in context
    
    # Check that schema returned properly
    assert "survey_id" in context["schema"]
    assert "tables" in context["schema"]
