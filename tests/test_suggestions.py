import pytest
from ai import suggestions_service

def test_get_few_shot_examples_structure():
    examples = suggestions_service.get_few_shot_examples()
    assert isinstance(examples, list)
    
    if len(examples) > 0:
        example = examples[0]
        assert "question" in example
        assert "sql_query" in example  # Contract requires mapping to sql_query or sql
        assert "category" in example
