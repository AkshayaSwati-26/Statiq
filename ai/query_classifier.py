from typing import Dict, Any

def classify_query(question: str) -> Dict[str, Any]:
    """
    Classifies the natural language question into specific query types.
    Supported classes: aggregation, comparison, ranking, trend, distribution
    """
    question_lower = question.lower()
    
    # Simple heuristic-based classification (to be replaced with ML/LLM model later if needed)
    query_type = "distribution"
    confidence = 0.50
    
    if "top" in question_lower or "highest" in question_lower or "lowest" in question_lower or "rank" in question_lower:
        query_type = "ranking"
        confidence = 0.90
    elif "trend" in question_lower or "over time" in question_lower or "year by year" in question_lower:
        query_type = "trend"
        confidence = 0.85
    elif "compare" in question_lower or "vs" in question_lower or "difference" in question_lower:
        query_type = "comparison"
        confidence = 0.85
    elif "average" in question_lower or "sum" in question_lower or "total" in question_lower or "count" in question_lower or "rate" in question_lower:
        query_type = "aggregation"
        confidence = 0.95
        
    return {
        "query_type": query_type,
        "confidence": confidence
    }
