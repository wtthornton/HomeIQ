"""
Community Pattern CRUD Operations for Pattern Service

Phase 3.3: Community pattern sharing - database access layer.
Provides async CRUD operations for community patterns and ratings.
"""

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import CommunityPattern, PatternRating

logger = logging.getLogger(__name__)


async def create_community_pattern(
    db: AsyncSession,
    pattern_id: str,
    pattern_type: str,
    pattern_metadata: dict[str, Any],
    description: str,
    tags: list[str] | None = None,
    device_id: str | None = None,
    author: str | None = None,
) -> CommunityPattern:
    """
    Create a new community pattern record.

    Args:
        db: Database session
        pattern_id: Pre-generated UUID for the pattern
        pattern_type: Type of pattern (e.g., 'time_of_day', 'co_occurrence')
        pattern_metadata: Pattern metadata and configuration
        description: Human-readable description
        tags: Optional list of tags for categorization
        device_id: Optional device ID if pattern is device-specific
        author: Optional author name

    Returns:
        The created CommunityPattern instance
    """
    pattern = CommunityPattern(
        id=pattern_id,
        pattern_type=pattern_type,
        device_id=device_id,
        pattern_metadata=pattern_metadata,
        description=description,
        tags=tags or [],
        author=author,
        status="pending",
    )
    db.add(pattern)
    await db.flush()
    logger.info("Created community pattern %s (type=%s, author=%s)", pattern_id, pattern_type, author or "anonymous")
    return pattern


async def get_community_pattern_by_id(
    db: AsyncSession,
    pattern_id: str,
) -> CommunityPattern | None:
    """
    Retrieve a single community pattern by ID.

    Args:
        db: Database session
        pattern_id: Unique community pattern identifier

    Returns:
        CommunityPattern instance or None if not found
    """
    query = select(CommunityPattern).where(CommunityPattern.id == pattern_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def list_community_patterns(
    db: AsyncSession,
    pattern_type: str | None = None,
    min_rating: float = 0.0,
    tags: list[str] | None = None,
    limit: int = 50,
    offset: int = 0,
    order_by: str = "rating",
) -> tuple[list[CommunityPattern], int]:
    """
    List community patterns with optional filters, pagination, and sorting.

    Only returns patterns with status 'approved' for public listing.

    Args:
        db: Database session
        pattern_type: Optional filter by pattern type
        min_rating: Minimum average rating threshold
        tags: Optional list of tags to filter by (any match)
        limit: Maximum number of patterns to return
        offset: Number of patterns to skip (for pagination)
        order_by: Sort order ('rating', 'popularity', 'recent')

    Returns:
        Tuple of (list of CommunityPattern instances, total count)
    """
    # Base query - only approved patterns are publicly listed
    base_conditions = [CommunityPattern.status == "approved"]

    if pattern_type:
        base_conditions.append(CommunityPattern.pattern_type == pattern_type)

    if min_rating > 0.0:
        base_conditions.append(CommunityPattern.rating_avg >= min_rating)

    # Count query (before pagination)
    count_query = select(func.count(CommunityPattern.id)).where(*base_conditions)
    count_result = await db.execute(count_query)
    total_count = count_result.scalar() or 0

    # Main query
    query = select(CommunityPattern).where(*base_conditions)

    # Apply tag filtering if provided
    if tags:
        for tag in tags:
            query = query.where(CommunityPattern.tags.cast(str).contains(tag))

    # Sorting
    if order_by == "popularity":
        query = query.order_by(CommunityPattern.download_count.desc())
    elif order_by == "recent":
        query = query.order_by(CommunityPattern.created_at.desc())
    else:
        # Default: rating descending, then download_count as tiebreaker
        query = query.order_by(CommunityPattern.rating_avg.desc(), CommunityPattern.download_count.desc())

    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    patterns = list(result.scalars().all())
    return patterns, total_count


async def create_pattern_rating(
    db: AsyncSession,
    rating_id: str,
    pattern_id: str,
    rating: int,
    comment: str | None = None,
    user_id: str | None = None,
) -> PatternRating:
    """
    Create a rating for a community pattern and update aggregates atomically.

    Uses a single flush to ensure the rating insert and aggregate update
    happen in the same transaction.

    Args:
        db: Database session
        rating_id: Pre-generated UUID for the rating
        pattern_id: ID of the pattern being rated
        rating: Rating value (1-5)
        comment: Optional review comment
        user_id: Optional user identifier

    Returns:
        The created PatternRating instance
    """
    # Insert the rating record
    pattern_rating = PatternRating(
        id=rating_id,
        pattern_id=pattern_id,
        rating=rating,
        comment=comment,
        user_id=user_id,
    )
    db.add(pattern_rating)
    await db.flush()

    # Update aggregate rating on the community pattern atomically
    # Recompute from all ratings to avoid floating-point drift
    avg_query = select(func.avg(PatternRating.rating)).where(PatternRating.pattern_id == pattern_id)
    count_query = select(func.count(PatternRating.id)).where(PatternRating.pattern_id == pattern_id)

    avg_result = await db.execute(avg_query)
    count_result = await db.execute(count_query)

    new_avg = avg_result.scalar() or 0.0
    new_count = count_result.scalar() or 0

    # Update the pattern record
    pattern_query = select(CommunityPattern).where(CommunityPattern.id == pattern_id)
    pattern_result = await db.execute(pattern_query)
    pattern = pattern_result.scalar_one_or_none()
    if pattern:
        pattern.rating_avg = round(float(new_avg), 2)
        pattern.rating_count = new_count

    logger.info(
        "Created rating for pattern %s: rating=%d, new_avg=%.2f, count=%d",
        pattern_id, rating, new_avg, new_count,
    )
    return pattern_rating


async def get_pattern_ratings(
    db: AsyncSession,
    pattern_id: str,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[PatternRating], int]:
    """
    Retrieve ratings for a community pattern with pagination.

    Args:
        db: Database session
        pattern_id: ID of the pattern
        limit: Maximum number of ratings to return
        offset: Number of ratings to skip (for pagination)

    Returns:
        Tuple of (list of PatternRating instances, total count)
    """
    # Count query
    count_query = select(func.count(PatternRating.id)).where(PatternRating.pattern_id == pattern_id)
    count_result = await db.execute(count_query)
    total_count = count_result.scalar() or 0

    # Main query - most recent first
    query = (
        select(PatternRating)
        .where(PatternRating.pattern_id == pattern_id)
        .order_by(PatternRating.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    ratings = list(result.scalars().all())

    return ratings, total_count
