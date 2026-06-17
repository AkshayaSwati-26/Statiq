import datetime
from typing import Dict, Any

from ai.metadata_service import get_schema, get_data_dictionary, get_dataset_profile
from ai.relationship_service import get_joins
from ai.suggestions_service import get_few_shot_examples
from ai.query_classifier import classify_query

def build_context(question: str) -> Dict[str, Any]:
    """
    Builds the complete context object for the NL-to-SQL AI module.
    Aggregates data from all specific services into a single JSON block.
    """
    schema = get_schema()
    relationships = get_joins()
    examples = get_few_shot_examples()
    survey_metadata = {} # Extracted from schema or other source if needed
    data_dictionary = get_data_dictionary()
    dataset_profile = get_dataset_profile()
    query_type = classify_query(question)
    
    return {
        "schema": schema,
        "relationships": relationships,
        "examples": examples,
        "survey_metadata": survey_metadata,
        "data_dictionary": data_dictionary,
        "dataset_profile": dataset_profile,
        "query_type": query_type,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }
