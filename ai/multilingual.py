import os
import requests
import logging

logger = logging.getLogger(__name__)

def translate_to_english(text: str, source_language: str) -> str:
    """
    Translate user query from a source Indian language (e.g. hi, ta, te) to English.
    Integrates with Bhashini translation API. Falls back to original text if translation fails.
    """
    if not source_language or source_language == "en":
        return text
        
    bhashini_api_key = os.environ.get("BHASHINI_API_KEY")
    bhashini_url = os.environ.get("BHASHINI_URL", "https://meity-auth.ulca-bhashini.gov.in/ulca/apis/v0/model/compute")
    
    if not bhashini_api_key:
        logger.warning("BHASHINI_API_KEY not set. Translation skipped, returning original text.")
        return text
        
    payload = {
        "pipelineTasks": [
            {
                "taskType": "translation",
                "config": {
                    "language": {
                        "sourceLanguage": source_language,
                        "targetLanguage": "en"
                    }
                }
            }
        ],
        "inputData": {
            "input": [
                {
                    "source": text
                }
            ]
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": bhashini_api_key
    }
    
    try:
        response = requests.post(bhashini_url, json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            res_data = response.json()
            translated_text = res_data["pipelineResponse"][0]["output"][0]["target"]
            return translated_text
        else:
            logger.error(f"Bhashini API error: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Failed to translate query via Bhashini: {e}")
        
    return text
