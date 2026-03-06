"""
Engagement Tracker Service for Proactive Agent Service

Tracks user engagement with proactive suggestions and creates memories
based on engagement patterns (Story 31.4).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session_maker
from ..models import Suggestion, SuggestionEngagement, SuggestionEngagementEvent

logger = logging.getLogger(__name__)

try:
    from homeiq_memory import MemoryClient, MemoryType, SourceChannel
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    logger.warning("homeiq_memory not available - pattern memories will not be saved")


class DatabaseNotInitializedError(Exception):
    """Raised when database session maker is not initialized."""
    pass


def _get_session_maker():
    """Get the async session maker."""
    session_maker = get_async_session_maker()
    if session_maker is None:
        raise DatabaseNotInitializedError(
            "Database not initialized. Call init_database() before using engagement tracker."
        )
    return session_maker


class EngagementTracker:
    """
    Track user engagement with proactive suggestions.

    Creates behavioral/preference memories when engagement patterns
    cross configurable thresholds.
    """

    IGNORE_THRESHOLD = 5
    ENGAGE_THRESHOLD = 3
    TRACKING_WINDOW_DAYS = 30
    SOURCE_SERVICE = "proactive-agent-engagement"

    def __init__(self, memory_client: MemoryClient | None = None):
        """
        Initialize the engagement tracker.

        Args:
            memory_client: Optional MemoryClient for saving pattern memories.
                If not provided and homeiq_memory is available, creates one lazily.
        """
        self._memory_client = memory_client
        self._memory_initialized = False

    async def _ensure_memory_client(self) -> MemoryClient | None:
        """Lazily initialize memory client if available."""
        if not MEMORY_AVAILABLE:
            return None

        if self._memory_client is None:
            self._memory_client = MemoryClient()

        if not self._memory_initialized:
            success = await self._memory_client.initialize()
            self._memory_initialized = success
            if not success:
                logger.warning("Failed to initialize memory client")
                return None

        return self._memory_client

    async def close(self) -> None:
        """Close resources."""
        if self._memory_client and self._memory_initialized:
            await self._memory_client.close()
            self._memory_initialized = False

    async def track_engagement(
        self,
        suggestion_id: str,
        category: str,
        engagement: SuggestionEngagement,
        metadata: dict[str, Any] | None = None,
        db: AsyncSession | None = None,
    ) -> SuggestionEngagementEvent | None:
        """
        Track a single engagement event.

        Args:
            suggestion_id: ID of the suggestion being engaged with.
            category: Category of the suggestion (weather, sports, energy, pattern).
            engagement: Type of engagement (delivered, viewed, acted, ignored).
            metadata: Optional metadata about the engagement.
            db: Optional database session.

        Returns:
            Created engagement event, or None on error.
        """
        if db is None:
            async with _get_session_maker()() as session:
                return await self._track_engagement_impl(
                    suggestion_id, category, engagement, metadata, session
                )
        else:
            return await self._track_engagement_impl(
                suggestion_id, category, engagement, metadata, db
            )

    async def _track_engagement_impl(
        self,
        suggestion_id: str,
        category: str,
        engagement: SuggestionEngagement,
        metadata: dict[str, Any] | None,
        db: AsyncSession,
    ) -> SuggestionEngagementEvent | None:
        """Internal implementation of engagement tracking."""
        try:
            result = await db.execute(
                select(Suggestion).where(Suggestion.id == suggestion_id)
            )
            suggestion = result.scalar_one_or_none()
            if not suggestion:
                logger.warning(f"Suggestion {suggestion_id} not found for engagement tracking")
                return None

            event = SuggestionEngagementEvent(
                suggestion_id=suggestion_id,
                category=category,
                engagement_type=engagement.value,
                metadata_=metadata,
            )
            db.add(event)
            await db.commit()
            await db.refresh(event)

            logger.info(
                f"Tracked engagement: suggestion={suggestion_id}, "
                f"category={category}, type={engagement.value}"
            )

            await self._check_thresholds_and_create_memories(category, engagement, db)

            return event

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to track engagement: {e}", exc_info=True)
            return None

    async def _check_thresholds_and_create_memories(
        self,
        category: str,
        engagement: SuggestionEngagement,
        db: AsyncSession,
    ) -> None:
        """Check if thresholds are met and create memories if so."""
        cutoff_date = datetime.now(UTC) - timedelta(days=self.TRACKING_WINDOW_DAYS)

        if engagement == SuggestionEngagement.IGNORED:
            ignored_count = await self._count_engagements(
                category, SuggestionEngagement.IGNORED, cutoff_date, db
            )
            if ignored_count >= self.IGNORE_THRESHOLD:
                await self._save_behavioral_memory(category, ignored_count)

        elif engagement == SuggestionEngagement.ACTED:
            acted_count = await self._count_engagements(
                category, SuggestionEngagement.ACTED, cutoff_date, db
            )
            if acted_count >= self.ENGAGE_THRESHOLD:
                await self._save_preference_memory(category, acted_count)

    async def _count_engagements(
        self,
        category: str,
        engagement: SuggestionEngagement,
        since: datetime,
        db: AsyncSession,
    ) -> int:
        """Count engagements of a specific type for a category."""
        result = await db.execute(
            select(func.count(SuggestionEngagementEvent.id))
            .where(SuggestionEngagementEvent.category == category)
            .where(SuggestionEngagementEvent.engagement_type == engagement.value)
            .where(SuggestionEngagementEvent.recorded_at >= since)
        )
        return result.scalar_one() or 0

    async def _save_behavioral_memory(self, category: str, ignored_count: int) -> None:
        """Save a behavioral memory when ignore threshold is reached."""
        memory_client = await self._ensure_memory_client()
        if not memory_client:
            logger.debug("Memory client not available - skipping behavioral memory")
            return

        content = (
            f"User consistently ignores {category} suggestions "
            f"({ignored_count} ignored in {self.TRACKING_WINDOW_DAYS} days). "
            f"Consider reducing frequency or improving relevance of {category} suggestions."
        )

        try:
            await memory_client.save(
                content=content,
                memory_type=MemoryType.BEHAVIORAL,
                source_channel=SourceChannel.IMPLICIT,
                source_service=self.SOURCE_SERVICE,
                tags=["suggestion-engagement", f"category:{category}", "ignored-pattern"],
                confidence=0.7,
                metadata={
                    "category": category,
                    "pattern": "ignored",
                    "count": ignored_count,
                    "window_days": self.TRACKING_WINDOW_DAYS,
                    "threshold": self.IGNORE_THRESHOLD,
                },
            )
            logger.info(
                f"Saved behavioral memory: {category} suggestions ignored "
                f"{ignored_count} times"
            )
        except Exception as e:
            logger.error(f"Failed to save behavioral memory: {e}", exc_info=True)

    async def _save_preference_memory(self, category: str, acted_count: int) -> None:
        """Save a preference memory when engagement threshold is reached."""
        memory_client = await self._ensure_memory_client()
        if not memory_client:
            logger.debug("Memory client not available - skipping preference memory")
            return

        content = (
            f"User actively engages with {category} suggestions "
            f"({acted_count} acted upon in {self.TRACKING_WINDOW_DAYS} days). "
            f"User shows preference for {category} automation suggestions."
        )

        try:
            await memory_client.save(
                content=content,
                memory_type=MemoryType.PREFERENCE,
                source_channel=SourceChannel.IMPLICIT,
                source_service=self.SOURCE_SERVICE,
                tags=["suggestion-engagement", f"category:{category}", "preference-pattern"],
                confidence=0.8,
                metadata={
                    "category": category,
                    "pattern": "engaged",
                    "count": acted_count,
                    "window_days": self.TRACKING_WINDOW_DAYS,
                    "threshold": self.ENGAGE_THRESHOLD,
                },
            )
            logger.info(
                f"Saved preference memory: {category} suggestions acted upon "
                f"{acted_count} times"
            )
        except Exception as e:
            logger.error(f"Failed to save preference memory: {e}", exc_info=True)

    async def evaluate_patterns(
        self,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate engagement patterns across all categories.

        Returns statistics and identifies categories that need attention.

        Returns:
            Dictionary with pattern analysis results.
        """
        if db is None:
            async with _get_session_maker()() as session:
                return await self._evaluate_patterns_impl(session)
        else:
            return await self._evaluate_patterns_impl(db)

    async def _evaluate_patterns_impl(self, db: AsyncSession) -> dict[str, Any]:
        """Internal implementation of pattern evaluation."""
        cutoff_date = datetime.now(UTC) - timedelta(days=self.TRACKING_WINDOW_DAYS)

        category_query = (
            select(
                SuggestionEngagementEvent.category,
                SuggestionEngagementEvent.engagement_type,
                func.count(SuggestionEngagementEvent.id).label("count"),
            )
            .where(SuggestionEngagementEvent.recorded_at >= cutoff_date)
            .group_by(
                SuggestionEngagementEvent.category,
                SuggestionEngagementEvent.engagement_type,
            )
        )
        result = await db.execute(category_query)
        rows = result.all()

        categories: dict[str, dict[str, int]] = {}
        for category, engagement_type, count in rows:
            if category not in categories:
                categories[category] = {}
            categories[category][engagement_type] = count

        patterns = {
            "ignored_categories": [],
            "engaged_categories": [],
            "low_engagement_categories": [],
        }

        for category, stats in categories.items():
            ignored = stats.get("ignored", 0)
            acted = stats.get("acted", 0)
            viewed = stats.get("viewed", 0)
            delivered = stats.get("delivered", 0)

            if ignored >= self.IGNORE_THRESHOLD:
                patterns["ignored_categories"].append({
                    "category": category,
                    "ignored_count": ignored,
                    "threshold": self.IGNORE_THRESHOLD,
                })

            if acted >= self.ENGAGE_THRESHOLD:
                patterns["engaged_categories"].append({
                    "category": category,
                    "acted_count": acted,
                    "threshold": self.ENGAGE_THRESHOLD,
                })

            total = ignored + acted + viewed + delivered
            if total > 0:
                engagement_rate = acted / total
                if engagement_rate < 0.1 and ignored < self.IGNORE_THRESHOLD:
                    patterns["low_engagement_categories"].append({
                        "category": category,
                        "engagement_rate": round(engagement_rate, 3),
                        "total_events": total,
                    })

        return {
            "window_days": self.TRACKING_WINDOW_DAYS,
            "categories": categories,
            "patterns": patterns,
            "thresholds": {
                "ignore": self.IGNORE_THRESHOLD,
                "engage": self.ENGAGE_THRESHOLD,
            },
        }

    async def get_engagement_stats(
        self,
        suggestion_id: str | None = None,
        category: str | None = None,
        days: int | None = None,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """
        Get engagement statistics with optional filters.

        Args:
            suggestion_id: Filter by specific suggestion.
            category: Filter by category.
            days: Filter to events within N days (default: TRACKING_WINDOW_DAYS).
            db: Optional database session.

        Returns:
            Dictionary with engagement statistics.
        """
        if db is None:
            async with _get_session_maker()() as session:
                return await self._get_engagement_stats_impl(
                    suggestion_id, category, days, session
                )
        else:
            return await self._get_engagement_stats_impl(
                suggestion_id, category, days, db
            )

    async def _get_engagement_stats_impl(
        self,
        suggestion_id: str | None,
        category: str | None,
        days: int | None,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Internal implementation of engagement stats."""
        window_days = days or self.TRACKING_WINDOW_DAYS
        cutoff_date = datetime.now(UTC) - timedelta(days=window_days)

        query = (
            select(
                SuggestionEngagementEvent.engagement_type,
                func.count(SuggestionEngagementEvent.id).label("count"),
            )
            .where(SuggestionEngagementEvent.recorded_at >= cutoff_date)
            .group_by(SuggestionEngagementEvent.engagement_type)
        )

        if suggestion_id:
            query = query.where(SuggestionEngagementEvent.suggestion_id == suggestion_id)
        if category:
            query = query.where(SuggestionEngagementEvent.category == category)

        result = await db.execute(query)
        rows = result.all()

        stats = {engagement.value: 0 for engagement in SuggestionEngagement}
        for engagement_type, count in rows:
            stats[engagement_type] = count

        total = sum(stats.values())
        engagement_rate = stats["acted"] / total if total > 0 else 0.0

        return {
            "window_days": window_days,
            "suggestion_id": suggestion_id,
            "category": category,
            "by_type": stats,
            "total": total,
            "engagement_rate": round(engagement_rate, 3),
        }
