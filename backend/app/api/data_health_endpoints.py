"""
Data-Source Health and Verification API Endpoints for ClearSky Intelligence.
Exposes endpoints for auditing data freshness, completeness, provenance, and live connectivity.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.core.logging import logger
from app.services.data_source_registry import (
    DataSourceMetadata,
    data_source_registry
)
from app.services.data_health_service import (
    DataHealthSummary,
    SourceVerificationResult,
    data_health_service
)

router = APIRouter(prefix="/data-health", tags=["Data Health & Verification"])


@router.get("", response_model=DataHealthSummary)
async def get_data_health_summary():
    """
    Returns a comprehensive summary of registered data sources and their current health status.
    Reflects the latest audited status without triggering heavy external calls.
    """
    return data_health_service.get_cached_status()


@router.get("/sources", response_model=List[DataSourceMetadata])
async def list_registered_sources():
    """
    Returns all registered environmental data sources, required configurations,
    supported fields, freshness thresholds, and limitations.
    """
    return data_health_service.get_registered_sources()


@router.get("/sources/{source_id}", response_model=SourceVerificationResult)
async def get_source_health_detail(source_id: str):
    """
    Returns detailed verification information for a specific data source.
    If the source has not yet been checked, returns its current status (or NOT_CHECKED).
    Raises 404 if source_id is not recognized.
    """
    meta = data_health_service.get_source_metadata(source_id)
    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source '{source_id}' is not registered."
        )

    # Return cached check if available, or run single source check
    cached = data_health_service._last_verification_cache.get(source_id)
    if cached:
        return cached

    # If never checked, execute single-source live check
    return await data_health_service.check_source(source_id)


@router.post("/check")
async def trigger_live_check(
    source_id: Optional[str] = Query(None, description="Optional specific source ID to verify. If omitted, checks all sources.")
):
    """
    Triggers an explicitly requested live operational check.
    Uses bounded concurrency and short timeouts.
    Does not crash on provider failure; records provider status accurately in response.
    """
    if source_id:
        meta = data_health_service.get_source_metadata(source_id)
        if not meta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data source '{source_id}' is not registered."
            )
        res = await data_health_service.check_source(source_id)
        return res

    summary = await data_health_service.check_all_sources()
    return summary


@router.post("/audit", response_model=DataHealthSummary)
async def trigger_stored_data_audit():
    """
    Runs an offline stored-dataset audit inspecting SQLite tables, JSON datasets,
    memory cache, and local/S3 partitions without issuing outbound network requests.
    """
    summary = await data_health_service.audit_stored_datasets()
    return summary
