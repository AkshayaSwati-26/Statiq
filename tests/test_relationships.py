import pytest
from ai import relationship_service

def test_get_joins_structure():
    joins = relationship_service.get_joins()
    assert isinstance(joins, list)
    
    if len(joins) > 0:
        join = joins[0]
        assert "parent_table" in join
        assert "child_table" in join
        assert "join_key" in join
        assert "relationship_type" in join
