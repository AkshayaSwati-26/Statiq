from fastapi import APIRouter
from ai import metadata_service

router = APIRouter(tags=["metadata"])

@router.get("/v1/metadata")
async def get_metadata():
    """Returns the database schema."""
    return metadata_service.get_schema()

@router.get("/v1/data-dictionary")
async def get_data_dictionary():
    """Returns the data dictionary."""
    return metadata_service.get_data_dictionary()

@router.get("/v1/dataset-profile")
async def get_dataset_profile():
    """Returns the dataset profile."""
    return metadata_service.get_dataset_profile()

@router.get("/v1/sensitive-columns")
async def get_sensitive_columns():
    """Returns the sensitive columns registry."""
    return metadata_service.get_sensitive_columns()
