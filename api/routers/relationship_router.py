from fastapi import APIRouter
from ai import relationship_service

router = APIRouter(tags=["relationships"])

@router.get("/v1/relationships")
async def get_relationships():
    """Returns the table relationships registry."""
    return relationship_service.get_joins()
