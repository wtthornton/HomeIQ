"""
Community Pattern Router

Endpoints for accessing and matching community-proven automation patterns.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.data_api_client import DataAPIClient
from src.database import get_db
from src.suggestion_generation.community_learner import CommunityPatternLearner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/community-patterns", tags=["Community Patterns"])

# Initialize clients
data_api_client = DataAPIClient(base_url="http://data-api:8006")
community_learner = CommunityPatternLearner()


@router.get("/match")
async def match_community_patterns(
    limit: int = Query(default=10, ge=1, le=50, description="Maximum patterns to return"),
    category: str | None = Query(default=None, description="Filter by category"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Match community patterns to user's devices.

    Returns community-proven automation patterns that can be applied
    to the user's Home Assistant setup.
    """
    try:
        # Fetch user's devices and entities
        devices = await data_api_client.fetch_devices()
        entities = await data_api_client.fetch_entities()

        # Match patterns
        matched = community_learner.match_patterns_to_user(
            user_devices=devices or [],
            user_entities=entities or [],
            user_context=None,
        )

        # Filter by category if specified
        if category:
            matched = [p for p in matched if p.get("category") == category]

        # Limit results
        matched = matched[:limit]

        return {
            "success": True,
            "data": {
                "patterns": matched,
                "count": len(matched),
            },
            "message": f"Matched {len(matched)} community patterns",
        }

    except Exception as e:
        logger.error(f"Failed to match community patterns: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to match community patterns: {e!s}",
        )


@router.get("/list")
async def list_community_patterns(
    category: str | None = Query(default=None, description="Filter by category"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum patterns to return"),
) -> dict[str, Any]:
    """
    List available community patterns.

    Returns all community patterns, optionally filtered by category.
    """
    try:
        patterns = community_learner.patterns_db

        # Filter by category if specified
        if category:
            patterns = [p for p in patterns if p.get("category") == category]

        # Limit results
        patterns = patterns[:limit]

        return {
            "success": True,
            "data": {
                "patterns": patterns,
                "count": len(patterns),
            },
        }

    except Exception as e:
        logger.error(f"Failed to list community patterns: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list community patterns: {e!s}",
        )


@router.get("/top")
async def get_top_patterns(
    limit: int = Query(default=10, ge=1, le=50, description="Number of top patterns"),
) -> dict[str, Any]:
    """
    Get top N most popular community patterns.
    """
    try:
        top_patterns = community_learner.get_top_patterns(limit=limit)

        return {
            "success": True,
            "data": {
                "patterns": top_patterns,
                "count": len(top_patterns),
            },
        }

    except Exception as e:
        logger.error(f"Failed to get top patterns: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get top patterns: {e!s}",
        )













