import json
from typing import Dict, Any, List
from ai.db_adapter import repository

def get_schema(survey_id: str = "default") -> Dict[str, Any]:
    """
    Returns the database schema aggregated from the metadata_registry.
    Format is strictly defined by the integration contract.
    """
    raw_metadata = repository.get_metadata_registry(survey_id)
    
    # Group columns by table
    tables_map = {}
    for row in raw_metadata:
        t_name = row["table_name"]
        if t_name not in tables_map:
            tables_map[t_name] = {
                "table_name": t_name,
                "columns": []
            }
        
        # Parse sample_values if it's a JSON string, otherwise keep as is
        sample_vals = row.get("sample_values", [])
        if isinstance(sample_vals, str):
            try:
                sample_vals = json.loads(sample_vals)
            except Exception:
                sample_vals = [sample_vals]
                
        tables_map[t_name]["columns"].append({
            "column_name": row["column_name"],
            "data_type": row["data_type"],
            "description": row["description"],
            "sample_values": sample_vals
        })
        
    return {
        "survey_id": survey_id,
        "tables": list(tables_map.values())
    }

def get_data_dictionary() -> List[Dict[str, Any]]:
    return repository.get_data_dictionary()

def get_dataset_profile() -> List[Dict[str, Any]]:
    return repository.get_dataset_profile()

def get_sensitive_columns() -> List[Dict[str, Any]]:
    return repository.get_sensitive_columns()
