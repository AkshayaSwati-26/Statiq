from typing import List, Dict, Any
from ai.db_adapter import repository

def get_few_shot_examples() -> List[Dict[str, Any]]:
    """
    Returns the suggested queries which act as few-shot examples for the AI.
    Format is strictly defined by the integration contract.
    """
    return repository.get_suggested_queries()
