from typing import List, Dict, Any
from ai.db_adapter import repository

def get_joins() -> List[Dict[str, Any]]:
    """
    Returns the table relationship registry defined by the Database Layer.
    Format is strictly defined by the integration contract.
    """
    return repository.get_relationship_registry()
