from fastapi import APIRouter
from ai import suggestions_service

router = APIRouter(tags=["suggestions"])

@router.get("/v1/suggested-queries")
async def get_suggested_queries():
    """Returns suggested queries for few-shot prompting."""
    return suggestions_service.get_few_shot_examples()
