import os
import requests
import json
import logging
from typing import Dict, Any
from ai.context_builder import build_context

logger = logging.getLogger(__name__)

def generate_sql(question: str) -> Dict[str, Any]:
    """
    Generate SQL query and explanation from a natural language question.
    Queries Gemma 3 4B running on Ollama, using context from context_builder.
    """
    # Build context containing schema, relationships, few-shot examples, etc.
    context = build_context(question)
    
    # Get Ollama host from environment (defaulting to the service name in docker-compose)
    ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    
    # Construct prompt
    prompt = f"""You are a natural language to SQL translation system for the MoSPI Survey Intelligence Platform.
The platform database contains survey microdata from PLFS (Periodic Labour Force Survey) and HCES (Household Consumer Expenditure Survey).

Your task is to translate the user's natural language question into a single valid SQL SELECT query and provide a brief explanation.

### Database Schema Context:
{json.dumps(context.get('schema', {}), indent=2)}

### Table Relationships (Joins):
{json.dumps(context.get('relationships', []), indent=2)}

### Data Dictionary & Code Definitions:
{json.dumps(context.get('data_dictionary', []), indent=2)}

### Few-Shot Examples (Use these as reference patterns):
"""
    for ex in context.get('examples', []):
        prompt += f"\nQuestion: {ex['question']}\nSQL: {ex['sql_query']}\nCategory: {ex['category']}\n"
        
    prompt += f"""
### User Question:
"{question}"

### Instructions:
1. ONLY return a valid JSON object. Do not include markdown formatting except the JSON block.
2. The JSON object MUST have exactly two keys:
   - "sql": A string containing the valid SQL query. Query ONLY the privacy-safe views (api_plfs_person, api_hces_members, api_hces_hosp). DO NOT query raw tables.
   - "explanation": A string explaining what the query does and how it filters/aggregates the data.
3. Ensure the SQL query only uses SELECT statements. Do not perform any modifying operations (INSERT, UPDATE, DELETE).
4. If a query refers to a code value (e.g. sector or usual activity status), consult the Data Dictionary to use the correct code integer.

Return your response in this JSON format:
{{
  "sql": "SELECT ...",
  "explanation": "..."
}}
"""

    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gemma:3b",
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    
    # Fallback SQL and explanation in case Ollama is not running or fails
    fallback_sql = (
        "SELECT state_name, sector_label, "
        "ROUND(SUM(CASE WHEN in_labour_force = 1 THEN multiplier ELSE 0 END) / NULLIF(SUM(multiplier), 0)*100, 2) AS lfpr_pct "
        "FROM api_plfs_person "
        "GROUP BY state_name, sector_label LIMIT 100"
    )
    fallback_explanation = "Fallback query: Returns Labour Force Participation Rate (LFPR) by state and sector (rural/urban)."
    
    # Cache hit check: matches query exactly against the suggested query cache registry to optimize performance
    for ex in context.get('examples', []):
        if question.lower().strip() == ex['question'].lower().strip():
            return {
                "sql": ex['sql_query'],
                "explanation": f"Retrieved query matching suggested example: {ex['question']}"
            }

    try:
        response = requests.post(f"{ollama_host}/api/generate", headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            result_json = response.json()
            response_text = result_json.get("response", "").strip()
            
            try:
                data = json.loads(response_text)
                if "sql" in data and "explanation" in data:
                    return {
                        "sql": data["sql"],
                        "explanation": data["explanation"]
                    }
            except json.JSONDecodeError:
                logger.warning(f"Ollama response was not valid JSON: {response_text}")
                
        else:
            logger.error(f"Ollama API returned status code {response.status_code}")
            
    except Exception as e:
        logger.warning(f"Failed to connect to Ollama at {ollama_host}: {e}. Returning fallback stub.")
        
    return {
        "sql": fallback_sql,
        "explanation": fallback_explanation
    }
