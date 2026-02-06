"""
Cleanup router for data-retention service.
"""

import logging

from fastapi import APIRouter, HTTPException, Query, Request

from ..models import CleanupResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cleanup", tags=["cleanup"])


@router.post("", response_model=CleanupResponse)
async def run_cleanup(
    request: Request,
    policy_name: str = Query(None, description="Optional policy name to run cleanup for")
):
    """
    Run data cleanup operation.

    Executes cleanup based on retention policies. Optionally filters by policy name.
    """
    try:
        service = request.app.state.service
        results = await service.run_cleanup(policy_name)
        return {"results": results}
    except Exception as e:
        logger.error(f"Cleanup operation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "Internal server error"})

