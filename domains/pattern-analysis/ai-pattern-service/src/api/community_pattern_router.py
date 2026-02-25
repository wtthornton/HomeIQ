"""
Community Pattern Router - API endpoints for community-shared patterns

Epic 39: Pattern Service API endpoints
Phase 3.2: Create community pattern endpoints
Phase 3.3: Full database-backed implementation

Provides REST API for community pattern sharing:
- Users can submit patterns to the community
- Users can browse community patterns
- Patterns can be rated and reviewed by the community

2025 Enhancement: Community pattern sharing enables knowledge transfer
between users and improves pattern discovery.
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.community_patterns import (
    create_community_pattern,
    create_pattern_rating,
    get_community_pattern_by_id,
)
from ..crud.community_patterns import (
    get_pattern_ratings as crud_get_pattern_ratings,
)
from ..crud.community_patterns import (
    list_community_patterns as crud_list_community_patterns,
)
from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/community/patterns", tags=["community-patterns"])


class CommunityPatternSubmission(BaseModel):
    """Model for submitting a pattern to the community."""
    pattern_type: str = Field(..., description="Type of pattern (e.g., 'time_of_day', 'co_occurrence')")
    device_id: str | None = Field(None, description="Device ID if pattern is device-specific")
    pattern_metadata: dict[str, Any] = Field(..., description="Pattern metadata and configuration")
    description: str = Field(..., min_length=10, max_length=500, description="Human-readable description")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    author: str | None = Field(None, description="Author name (optional)")


class CommunityPatternRating(BaseModel):
    """Model for rating a community pattern."""
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    comment: str | None = Field(None, max_length=500, description="Optional comment")
    user_id: str | None = Field(None, description="Optional user identifier")


def _serialize_pattern(pattern: Any) -> dict[str, Any]:
    """Serialize a CommunityPattern ORM instance to a dict for JSON response."""
    return {
        "id": pattern.id,
        "pattern_type": pattern.pattern_type,
        "device_id": pattern.device_id,
        "pattern_metadata": pattern.pattern_metadata,
        "description": pattern.description,
        "tags": pattern.tags or [],
        "author": pattern.author,
        "status": pattern.status,
        "rating_avg": pattern.rating_avg,
        "rating_count": pattern.rating_count,
        "download_count": pattern.download_count,
        "created_at": pattern.created_at.isoformat() if pattern.created_at else None,
        "updated_at": pattern.updated_at.isoformat() if pattern.updated_at else None,
    }


def _serialize_rating(rating: Any) -> dict[str, Any]:
    """Serialize a PatternRating ORM instance to a dict for JSON response."""
    return {
        "id": rating.id,
        "pattern_id": rating.pattern_id,
        "user_id": rating.user_id,
        "rating": rating.rating,
        "comment": rating.comment,
        "created_at": rating.created_at.isoformat() if rating.created_at else None,
    }


@router.get("/list")
async def list_community_patterns(
    pattern_type: str | None = Query(default=None, description="Filter by pattern type"),
    min_rating: float = Query(default=0.0, ge=0.0, le=5.0, description="Minimum average rating"),
    tags: str | None = Query(default=None, description="Comma-separated tags to filter by"),
    skip: int = Query(default=0, ge=0, description="Number of patterns to skip"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum patterns to return"),
    order_by: str = Query(default="rating", description="Order by: rating, popularity, recent"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    List community patterns with optional filters.

    Returns community-shared patterns that users can discover and use.
    Only patterns with status 'approved' are returned.

    Args:
        pattern_type: Optional filter by pattern type
        min_rating: Minimum average rating threshold
        tags: Comma-separated tags to filter by
        skip: Number of patterns to skip (pagination offset)
        limit: Maximum number of patterns to return
        order_by: Sort order (rating, popularity, recent)
        db: Database session dependency

    Returns:
        dict: Response with community patterns list, count, and filters

    Raises:
        HTTPException: If database query fails (500 status)
    """
    try:
        # Parse tags filter
        tag_list: list[str] = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

        patterns, total_count = await crud_list_community_patterns(
            db,
            pattern_type=pattern_type,
            min_rating=min_rating,
            tags=tag_list if tag_list else None,
            limit=limit,
            offset=skip,
            order_by=order_by,
        )

        return {
            "success": True,
            "data": {
                "patterns": [_serialize_pattern(p) for p in patterns],
                "count": len(patterns),
                "total": total_count,
                "skip": skip,
                "limit": limit,
                "filters": {
                    "pattern_type": pattern_type,
                    "min_rating": min_rating,
                    "tags": tag_list,
                    "order_by": order_by,
                },
            },
            "message": f"Retrieved {len(patterns)} community patterns",
        }

    except Exception as e:
        logger.error("Failed to list community patterns: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list community patterns: {e}",
        ) from e


@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_community_pattern(
    pattern: CommunityPatternSubmission,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Submit a pattern to the community.

    Allows users to share their discovered patterns with the community.
    Patterns start with 'pending' status and must be reviewed before
    being made public.

    Args:
        pattern: Pattern submission data
        db: Database session dependency

    Returns:
        dict: Confirmation of pattern submission with generated ID

    Raises:
        HTTPException: If submission fails (500 status)
    """
    try:
        pattern_id = str(uuid.uuid4())

        community_pattern = await create_community_pattern(
            db,
            pattern_id=pattern_id,
            pattern_type=pattern.pattern_type,
            pattern_metadata=pattern.pattern_metadata,
            description=pattern.description,
            tags=pattern.tags,
            device_id=pattern.device_id,
            author=pattern.author,
        )

        return {
            "success": True,
            "data": {
                "pattern_id": community_pattern.id,
                "status": community_pattern.status,
                "message": "Pattern submitted successfully. It will be reviewed before being made public.",
            },
            "message": "Pattern submitted to community",
        }

    except Exception as e:
        logger.error("Failed to submit community pattern: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit pattern: {e}",
        ) from e


@router.get("/{pattern_id}")
async def get_community_pattern(
    pattern_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get detailed community pattern by ID.

    Args:
        pattern_id: Unique community pattern identifier
        db: Database session dependency

    Returns:
        dict: Community pattern details

    Raises:
        HTTPException: If pattern not found (404) or query fails (500)
    """
    try:
        pattern = await get_community_pattern_by_id(db, pattern_id)

        if not pattern:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Community pattern not found: {pattern_id}",
            )

        return {
            "success": True,
            "data": _serialize_pattern(pattern),
            "message": f"Retrieved community pattern {pattern_id}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get community pattern %s: %s", pattern_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get community pattern: {e}",
        ) from e


@router.post("/{pattern_id}/rate", status_code=status.HTTP_201_CREATED)
async def rate_community_pattern(
    pattern_id: str,
    rating: CommunityPatternRating,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Rate a community pattern.

    Allows users to rate and comment on community patterns.
    Ratings help surface the best patterns. The pattern's average
    rating and count are updated atomically.

    Args:
        pattern_id: Unique community pattern identifier
        rating: Rating data (1-5 stars, optional comment)
        db: Database session dependency

    Returns:
        dict: Confirmation of rating submission with updated averages

    Raises:
        HTTPException: If pattern not found (404) or storage fails (500)
    """
    try:
        # Verify the pattern exists before accepting a rating
        pattern = await get_community_pattern_by_id(db, pattern_id)
        if not pattern:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Community pattern not found: {pattern_id}",
            )

        rating_id = str(uuid.uuid4())

        pattern_rating = await create_pattern_rating(
            db,
            rating_id=rating_id,
            pattern_id=pattern_id,
            rating=rating.rating,
            comment=rating.comment,
            user_id=rating.user_id,
        )

        # Re-fetch pattern to get updated aggregates
        updated_pattern = await get_community_pattern_by_id(db, pattern_id)

        return {
            "success": True,
            "data": {
                "rating_id": pattern_rating.id,
                "pattern_id": pattern_id,
                "rating": pattern_rating.rating,
                "comment_received": pattern_rating.comment is not None,
                "updated_average": updated_pattern.rating_avg if updated_pattern else 0.0,
                "total_ratings": updated_pattern.rating_count if updated_pattern else 0,
            },
            "message": "Rating submitted successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to rate community pattern %s: %s", pattern_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit rating: {e}",
        ) from e


@router.get("/{pattern_id}/ratings")
async def get_pattern_ratings(
    pattern_id: str,
    skip: int = Query(default=0, ge=0, description="Number of ratings to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum ratings to return"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get ratings and comments for a community pattern.

    Args:
        pattern_id: Unique community pattern identifier
        skip: Number of ratings to skip (pagination offset)
        limit: Maximum ratings to return
        db: Database session dependency

    Returns:
        dict: List of ratings with aggregate statistics

    Raises:
        HTTPException: If pattern not found (404) or query fails (500)
    """
    try:
        # Verify the pattern exists
        pattern = await get_community_pattern_by_id(db, pattern_id)
        if not pattern:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Community pattern not found: {pattern_id}",
            )

        ratings, total_count = await crud_get_pattern_ratings(
            db,
            pattern_id=pattern_id,
            limit=limit,
            offset=skip,
        )

        return {
            "success": True,
            "data": {
                "pattern_id": pattern_id,
                "ratings": [_serialize_rating(r) for r in ratings],
                "count": len(ratings),
                "total": total_count,
                "skip": skip,
                "limit": limit,
                "average_rating": pattern.rating_avg,
                "total_ratings": pattern.rating_count,
            },
            "message": f"Retrieved {len(ratings)} ratings for pattern {pattern_id}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get ratings for pattern %s: %s", pattern_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ratings: {e}",
        ) from e
