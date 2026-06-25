import os
import requests
import json
import logging
from typing import List, Dict, Any

from sqlalchemy import text
from db.loader import engine

logger = logging.getLogger(__name__)

def generate_dataset_description(dataset_id: str, table_name: str, columns: List[Dict[str, Any]], row_count: int) -> str:
    """
    Generate a detailed entity and relationship description for an uploaded dataset using Ollama.
    """
    ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    
    col_str = "\n".join([
        f"- {c.get('column_name', 'Unknown')} ({c.get('data_type', 'unknown')}): {c.get('description', '')}" 
        for c in columns[:50]  # Limit to 50 columns to avoid token overflow
    ])
    
    prompt = f"""You are a data architect for the MoSPI Survey Intelligence Platform. 
A new dataset has just been uploaded. Your task is to analyze the columns and generate a clear, concise Entity & Schema Description for the dataset.

### Dataset Details
Table Name: {table_name}
Rows: {row_count}

### Columns:
{col_str}

### Instructions:
1. Describe the core Entity (what does a single row represent? A household? A person? A hospital case?).
2. Briefly describe the key dimensions and metrics available in this dataset.
3. Keep the description professional, informative, and around 3 to 4 sentences.
4. Do NOT use markdown formatting like bolding or headers. Output raw text only.
"""

    headers = {"Content-Type": "application/json"}
    payload = {
        "model": "gemma3:4b",
        "prompt": prompt,
        "stream": False
    }
    
    fallback_desc = f"This dataset contains {row_count} records. It includes fields such as {', '.join([c.get('column_name') for c in columns[:5]])} and {len(columns)} total columns."
    
    try:
        response = requests.post(f"{ollama_host}/api/generate", headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            result_json = response.json()
            response_text = result_json.get("response", "").strip()
            if response_text:
                return response_text
    except Exception as e:
        logger.warning(f"Failed to generate AI description for {dataset_id}: {e}")
        
    return fallback_desc

def async_generate_and_store_description(dataset_id: str, table_name: str, row_count: int):
    """
    Background task to generate and store the description.
    """
    try:
        with engine.connect() as conn:
            # Fetch columns for the dataset
            rows = conn.execute(text(
                "SELECT column_name, data_type, description FROM survey_metadata_columns WHERE table_name = :tname"
            ), {"tname": table_name}).fetchall()
            
            columns = [
                {"column_name": r[0], "data_type": r[1], "description": r[2]}
                for r in rows
            ]
            
        if not columns:
            return
            
        desc = generate_dataset_description(dataset_id, table_name, columns, row_count)
        
        with engine.connect() as conn:
            conn.execute(text(
                "UPDATE datasets_registry SET description = :desc WHERE dataset_id = :did"
            ), {"desc": desc, "did": dataset_id})
            conn.commit()
            
    except Exception as e:
        logger.error(f"Error in background description generation: {e}")
