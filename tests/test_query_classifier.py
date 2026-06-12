import pytest
from ai import query_classifier

def test_classify_query_ranking():
    result = query_classifier.classify_query("Top 5 states with highest unemployment")
    assert result["query_type"] == "ranking"
    assert "confidence" in result

def test_classify_query_aggregation():
    result = query_classifier.classify_query("What is the average household size?")
    assert result["query_type"] == "aggregation"
    assert "confidence" in result

def test_classify_query_structure():
    result = query_classifier.classify_query("Hello")
    assert "query_type" in result
    assert "confidence" in result
    assert isinstance(result["confidence"], float)
