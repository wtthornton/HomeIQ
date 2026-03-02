"""
Suggestion Service

Epic 39, Story 39.10: Automation Service Foundation
Epic 7, Story 1: Pattern Detection Integration (Story 39.13)
Core service for generating and managing automation suggestions.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.data_api_client import DataAPIClient
from ..clients.openai_client import OpenAIClient
from ..clients.pattern_service_client import PatternServiceClient
from ..database.models import Suggestion

logger = logging.getLogger(__name__)


class SuggestionService:
    """
    Service for generating and managing automation suggestions.

    Features:
    - Generate suggestions from detected patterns (Story 39.13)
    - Fall back to raw events when pattern service unavailable
    - List and filter suggestions
    - Store suggestions in database
    - Track usage statistics
    """

    def __init__(
        self,
        db: AsyncSession,
        data_api_client: DataAPIClient,
        openai_client: OpenAIClient,
        pattern_client: PatternServiceClient | None = None,
    ):
        """
        Initialize suggestion service.

        Args:
            db: Database session
            data_api_client: Client for fetching data from Data API
            openai_client: Client for generating suggestions via OpenAI
            pattern_client: Optional client for fetching detected patterns
        """
        self.db = db
        self.data_api_client = data_api_client
        self.openai_client = openai_client
        self.pattern_client = pattern_client or PatternServiceClient()

    async def generate_suggestions(
        self, pattern_ids: list[str] | None = None, days: int = 30, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Generate automation suggestions from detected patterns.

        Args:
            pattern_ids: Optional list of pattern IDs to generate suggestions for
            days: Number of days of data to analyze
            limit: Maximum number of suggestions to generate

        Returns:
            List of suggestion dictionaries
        """
        try:
            # Validate OpenAI client
            if not self.openai_client or not self.openai_client.client:
                error_msg = "OpenAI API key not configured. Cannot generate suggestions."
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Fetch events from Data API
            logger.info(f"Fetching events for suggestion generation (days={days}, limit=10000)")
            try:
                events = await self.data_api_client.fetch_events(days=days, limit=10000)
            except Exception as e:
                error_msg = f"Failed to fetch events from Data API: {e}. Check Data API service and websocket-ingestion."
                logger.error(error_msg)
                raise ValueError(error_msg) from e

            logger.info(f"Received {len(events) if events else 0} events from Data API")

            if not events:
                warning_msg = f"No events found for suggestion generation (days={days}, limit={limit}). Suggestions require events from Home Assistant. Check Data API and websocket-ingestion service."
                logger.warning(warning_msg)
                return []

            # Validate event count for suggestion generation
            if len(events) < 100:
                logger.warning(
                    f"Only {len(events)} events available. Need at least 100 events to generate suggestions (have {len(events)}, need 100). Check websocket-ingestion service to ensure events are being written to InfluxDB."
                )
                return []

            # Story 39.13: Fetch detected patterns from ai-pattern-service
            patterns: list[dict[str, Any]] = []
            try:
                patterns = await self.pattern_client.fetch_patterns(
                    min_confidence=0.5, limit=limit,
                )
                if patterns:
                    logger.info(f"Using {len(patterns)} detected patterns for suggestion generation")
            except Exception as e:
                logger.warning(f"AI FALLBACK: Pattern service unavailable ({e}), using raw events")

            suggestions = []

            if patterns:
                # Pattern-enriched path: generate suggestions from detected patterns
                actual_limit = min(limit, len(patterns))
                logger.info(f"Generating {actual_limit} suggestions from {len(patterns)} patterns")

                for i in range(actual_limit):
                    try:
                        pattern = patterns[i]
                        description = await self.openai_client.generate_suggestion_description(
                            pattern_data={
                                "pattern": pattern,
                                "pattern_type": pattern.get("pattern_type", "unknown"),
                                "confidence": pattern.get("confidence", 0.0),
                                "metadata": pattern.get("metadata", {}),
                                "device_id": pattern.get("device_id"),
                            }
                        )
                        suggestion = {
                            "title": f"Automation Suggestion {i + 1}",
                            "description": description,
                            "status": "draft",
                        }
                        suggestions.append(suggestion)
                        logger.debug(f"Generated pattern-based suggestion {i + 1}/{actual_limit}")
                    except Exception as e:
                        logger.error(f"Failed to generate suggestion {i + 1} from pattern: {e}")
                        continue
            else:
                # Fallback path: generate suggestions from raw events
                max_suggestions = len(events) // 100
                actual_limit = min(limit, max_suggestions)
                logger.info(
                    f"Fallback: generating up to {actual_limit} suggestions from {len(events)} events"
                )

                if actual_limit == 0:
                    logger.warning(
                        f"Insufficient events for suggestion generation: {len(events)} events "
                        f"available, need at least 100"
                    )
                    return []

                for i in range(actual_limit):
                    try:
                        event_batch = events[i * 100 : (i + 1) * 100]
                        description = await self.openai_client.generate_suggestion_description(
                            pattern_data={"events": event_batch}
                        )
                        suggestion = {
                            "title": f"Automation Suggestion {i + 1}",
                            "description": description,
                            "status": "draft",
                        }
                        suggestions.append(suggestion)
                        logger.debug(f"Generated event-based suggestion {i + 1}/{actual_limit}")
                    except Exception as e:
                        logger.error(f"Failed to generate suggestion {i + 1}: {e}")
                        continue

            # Store suggestions in database
            stored_suggestions = []
            for suggestion_data in suggestions:
                try:
                    suggestion = Suggestion(
                        title=suggestion_data["title"],
                        description=suggestion_data["description"],
                        status=suggestion_data["status"],
                        # Note: pattern_data is stored in automation_json field if needed
                    )
                    self.db.add(suggestion)
                    await self.db.flush()
                    await self.db.refresh(suggestion)

                    stored_suggestions.append(
                        {
                            "id": suggestion.id,
                            "title": suggestion.title,
                            "description": suggestion.description,
                            "status": suggestion.status,
                            "created_at": suggestion.created_at.isoformat()
                            if suggestion.created_at
                            else None,
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to store suggestion: {e}")
                    continue

            await self.db.commit()

            logger.info(f"Generated {len(stored_suggestions)} suggestions")
            return stored_suggestions

        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")
            await self.db.rollback()
            raise

    async def list_suggestions(
        self, limit: int = 50, offset: int = 0, status: str | None = None
    ) -> dict[str, Any]:
        """
        List automation suggestions with filtering and pagination.

        Args:
            limit: Maximum number of suggestions to return
            offset: Number of suggestions to skip
            status: Optional filter by status (pending, approved, rejected, deployed)

        Returns:
            Dictionary with suggestions list and pagination info
        """
        try:
            # Build query
            query = select(Suggestion)

            if status:
                query = query.where(Suggestion.status == status)

            # Get total count (efficient SQL COUNT)
            count_query = select(func.count()).select_from(Suggestion)
            if status:
                count_query = count_query.where(Suggestion.status == status)

            total_result = await self.db.execute(count_query)
            total = total_result.scalar() or 0

            # Apply pagination
            query = query.order_by(Suggestion.created_at.desc())
            query = query.limit(limit).offset(offset)

            # Execute query
            result = await self.db.execute(query)
            suggestions = result.scalars().all()

            # Convert to dictionaries
            suggestions_list = []
            for suggestion in suggestions:
                suggestions_list.append(
                    {
                        "id": suggestion.id,
                        "title": suggestion.title,
                        "description": suggestion.description,
                        "status": suggestion.status,
                        "confidence": (
                            suggestion.confidence_score
                            if suggestion.confidence_score is not None
                            else 0.5
                        ),  # Default to 0.5 if null
                        "created_at": suggestion.created_at.isoformat()
                        if suggestion.created_at
                        else None,
                        "updated_at": suggestion.updated_at.isoformat()
                        if suggestion.updated_at
                        else None,
                    }
                )

            return {
                "suggestions": suggestions_list,
                "total": total,
                "limit": limit,
                "offset": offset,
            }

        except Exception as e:
            logger.error(f"Failed to list suggestions: {e}")
            raise

    async def get_suggestion(self, suggestion_id: int) -> dict[str, Any] | None:
        """
        Get a specific suggestion by ID.

        Args:
            suggestion_id: Suggestion ID

        Returns:
            Suggestion dictionary or None if not found
        """
        try:
            query = select(Suggestion).where(Suggestion.id == suggestion_id)
            result = await self.db.execute(query)
            suggestion = result.scalar_one_or_none()

            if not suggestion:
                return None

            return {
                "id": suggestion.id,
                "title": suggestion.title,
                "description": suggestion.description,
                "status": suggestion.status,
                "confidence": (
                    suggestion.confidence_score if suggestion.confidence_score is not None else 0.5
                ),  # Default to 0.5 if null
                "automation_yaml": suggestion.automation_yaml,
                "created_at": suggestion.created_at.isoformat() if suggestion.created_at else None,
                "updated_at": suggestion.updated_at.isoformat() if suggestion.updated_at else None,
                "deployed_at": suggestion.deployed_at.isoformat()
                if suggestion.deployed_at
                else None,
            }

        except Exception as e:
            logger.error(f"Failed to get suggestion {suggestion_id}: {e}")
            raise

    async def update_suggestion_status(self, suggestion_id: int, status: str) -> bool:
        """
        Update suggestion status.

        Args:
            suggestion_id: Suggestion ID
            status: New status (pending, approved, rejected, deployed)

        Returns:
            True if successful
        """
        try:
            query = select(Suggestion).where(Suggestion.id == suggestion_id)
            result = await self.db.execute(query)
            suggestion = result.scalar_one_or_none()

            if not suggestion:
                return False

            suggestion.status = status
            suggestion.updated_at = datetime.now(timezone.utc)

            await self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to update suggestion status: {e}")
            await self.db.rollback()
            raise

    async def get_usage_stats(self) -> dict[str, Any]:
        """
        Get suggestion usage statistics using SQL aggregation (C5 fix).

        Returns:
            Dictionary with usage statistics
        """
        try:
            # Get total count
            total_query = select(func.count()).select_from(Suggestion)
            total_result = await self.db.execute(total_query)
            total = total_result.scalar() or 0

            # Get counts by status using GROUP BY (C5: avoids loading all rows)
            status_query = select(Suggestion.status, func.count()).group_by(Suggestion.status)
            status_result = await self.db.execute(status_query)
            by_status = {(status or "unknown"): count for status, count in status_result.all()}

            stats = {
                "total": total,
                "by_status": by_status,
                "openai_usage": self.openai_client.get_usage_stats() if self.openai_client else {},
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
            raise
