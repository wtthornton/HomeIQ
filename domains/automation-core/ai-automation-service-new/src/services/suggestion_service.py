"""
Suggestion Service

Epic 39, Story 39.10: Automation Service Foundation
Epic 7, Story 1: Pattern Detection Integration (Story 39.13)
Epic 33, Story 33.3: Memory-Aware Suggestion Filtering
Core service for generating and managing automation suggestions.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.data_api_client import DataAPIClient
from ..clients.openai_client import OpenAIClient
from ..clients.pattern_service_client import PatternServiceClient
from ..database.models import Suggestion

if TYPE_CHECKING:
    from homeiq_memory import MemorySearch, MemorySearchResult

try:
    from homeiq_memory import MemorySearch, MemorySearchResult, MemoryType

    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    MemorySearch = None  # type: ignore[misc,assignment]
    MemorySearchResult = None  # type: ignore[misc,assignment]
    MemoryType = None  # type: ignore[misc,assignment]

logger = logging.getLogger(__name__)


class SuggestionService:
    """
    Service for generating and managing automation suggestions.

    Features:
    - Generate suggestions from detected patterns (Story 39.13)
    - Fall back to raw events when pattern service unavailable
    - Memory-aware filtering and ranking (Story 33.3)
    - List and filter suggestions
    - Store suggestions in database
    - Track usage statistics
    """

    PREFERENCE_BOOST_MAX = 0.3
    OUTCOME_SUCCESS_BOOST = 1.15
    OUTCOME_FAILURE_PENALTY = 0.7

    def __init__(
        self,
        db: AsyncSession,
        data_api_client: DataAPIClient,
        openai_client: OpenAIClient,
        pattern_client: PatternServiceClient | None = None,
        memory_search: MemorySearch | None = None,
    ):
        """
        Initialize suggestion service.

        Args:
            db: Database session
            data_api_client: Client for fetching data from Data API
            openai_client: Client for generating suggestions via OpenAI
            pattern_client: Optional client for fetching detected patterns
            memory_search: Optional MemorySearch for memory-aware filtering (Story 33.3)
        """
        self.db = db
        self.data_api_client = data_api_client
        self.openai_client = openai_client
        self.pattern_client = pattern_client or PatternServiceClient()
        self.memory_search = memory_search

    async def generate_suggestions(
        self, _pattern_ids: list[str] | None = None, days: int = 30, limit: int = 10
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
            self._validate_openai_client()

            events = await self._fetch_events_for_generation(days)
            if not events:
                return []

            patterns = await self._fetch_patterns_safely(limit)
            suggestions = await self._generate_candidates(patterns, events, limit)

            if self.memory_search and MEMORY_AVAILABLE:
                suggestions = await self._apply_memory_filtering(suggestions)

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

    def _validate_openai_client(self) -> None:
        """Validate OpenAI client is configured."""
        if not self.openai_client or not self.openai_client.client:
            error_msg = "OpenAI API key not configured. Cannot generate suggestions."
            logger.error(error_msg)
            raise ValueError(error_msg)

    async def _fetch_events_for_generation(self, days: int) -> list[dict[str, Any]]:
        """Fetch and validate events from Data API."""
        logger.info(f"Fetching events for suggestion generation (days={days}, limit=10000)")
        try:
            events = await self.data_api_client.fetch_events(days=days, limit=10000)
        except Exception as e:
            error_msg = f"Failed to fetch events from Data API: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e

        event_count = len(events) if events else 0
        logger.info(f"Received {event_count} events from Data API")

        if not events:
            logger.warning(f"No events found for suggestion generation (days={days})")
            return []

        if event_count < 100:
            logger.warning(f"Only {event_count} events available, need at least 100")
            return []

        return events

    async def _fetch_patterns_safely(self, limit: int) -> list[dict[str, Any]]:
        """Fetch patterns from pattern service, returning empty list on failure."""
        try:
            patterns = await self.pattern_client.fetch_patterns(
                min_confidence=0.5, limit=limit
            )
            if patterns:
                logger.info(f"Using {len(patterns)} detected patterns")
            return patterns or []
        except Exception as e:
            logger.warning(f"AI FALLBACK: Pattern service unavailable ({e}), using raw events")
            return []

    async def _generate_candidates(
        self,
        patterns: list[dict[str, Any]],
        events: list[dict[str, Any]],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Generate suggestion candidates from patterns or events."""
        if patterns:
            return await self._generate_from_patterns(patterns, limit)
        return await self._generate_from_events(events, limit)

    async def _generate_from_patterns(
        self, patterns: list[dict[str, Any]], limit: int
    ) -> list[dict[str, Any]]:
        """Generate suggestions from detected patterns."""
        suggestions = []
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
                suggestions.append({
                    "title": f"Automation Suggestion {i + 1}",
                    "description": description,
                    "status": "draft",
                    "confidence_score": pattern.get("confidence", 0.5),
                    "entity_ids": self._extract_entity_ids_from_pattern(pattern),
                })
                logger.debug(f"Generated pattern-based suggestion {i + 1}/{actual_limit}")
            except Exception as e:
                logger.error(f"Failed to generate suggestion {i + 1} from pattern: {e}")
                continue

        return suggestions

    async def _generate_from_events(
        self, events: list[dict[str, Any]], limit: int
    ) -> list[dict[str, Any]]:
        """Generate suggestions from raw events (fallback path)."""
        suggestions = []
        max_suggestions = len(events) // 100
        actual_limit = min(limit, max_suggestions)

        if actual_limit == 0:
            logger.warning(f"Insufficient events: {len(events)} available, need at least 100")
            return []

        logger.info(f"Fallback: generating {actual_limit} suggestions from {len(events)} events")

        for i in range(actual_limit):
            try:
                event_batch = events[i * 100 : (i + 1) * 100]
                description = await self.openai_client.generate_suggestion_description(
                    pattern_data={"events": event_batch}
                )
                suggestions.append({
                    "title": f"Automation Suggestion {i + 1}",
                    "description": description,
                    "status": "draft",
                    "confidence_score": 0.5,
                    "entity_ids": self._extract_entity_ids_from_events(event_batch),
                })
                logger.debug(f"Generated event-based suggestion {i + 1}/{actual_limit}")
            except Exception as e:
                logger.error(f"Failed to generate suggestion {i + 1}: {e}")
                continue

        return suggestions

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
            suggestion.updated_at = datetime.now(UTC)

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

    def _extract_entity_ids_from_pattern(self, pattern: dict[str, Any]) -> list[str]:
        """Extract entity IDs from a pattern dictionary."""
        entity_ids: set[str] = set()
        if device_id := pattern.get("device_id"):
            entity_ids.add(device_id)
        if eid := pattern.get("entity_id"):
            if isinstance(eid, list):
                entity_ids.update(eid)
            else:
                entity_ids.add(eid)
        if metadata := pattern.get("metadata"):
            if eid := metadata.get("entity_id"):
                if isinstance(eid, list):
                    entity_ids.update(eid)
                else:
                    entity_ids.add(eid)
        return list(entity_ids)

    def _extract_entity_ids_from_events(self, events: list[dict[str, Any]]) -> list[str]:
        """Extract unique entity IDs from a list of events."""
        entity_ids: set[str] = set()
        for event in events:
            if eid := event.get("entity_id"):
                entity_ids.add(eid)
        return list(entity_ids)

    async def _apply_memory_filtering(
        self, suggestions: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Apply memory-aware filtering and ranking to suggestions (Story 33.3).

        Filters out suggestions matching boundary memories, boosts suggestions
        matching user preferences, and factors in past automation outcomes.
        """
        if not self.memory_search or not MEMORY_AVAILABLE:
            return suggestions

        entity_list = self._collect_entity_ids(suggestions)

        boundaries = await self._fetch_boundaries(entity_list)
        boundary_entities, boundary_keywords = self._extract_boundary_constraints(boundaries)

        filtered = [
            s for s in suggestions
            if not self._matches_boundary(s, boundary_entities, boundary_keywords)
        ]

        removed_count = len(suggestions) - len(filtered)
        if removed_count > 0:
            logger.info(f"Memory filter: removed {removed_count} suggestions matching boundaries")

        preferences = await self._fetch_preferences()
        self._apply_preference_boosts(filtered, preferences)

        outcomes = await self._fetch_outcomes(entity_list)
        self._apply_outcome_factors(filtered, outcomes)

        filtered.sort(key=lambda s: s.get("confidence_score", 0.5), reverse=True)
        return filtered

    def _collect_entity_ids(self, suggestions: list[dict[str, Any]]) -> list[str] | None:
        """Collect all unique entity IDs from suggestions."""
        all_ids: set[str] = set()
        for s in suggestions:
            if eids := s.get("entity_ids"):
                all_ids.update(eids)
        return list(all_ids) if all_ids else None

    async def _fetch_boundaries(
        self, entity_list: list[str] | None
    ) -> list[MemorySearchResult]:
        """Fetch boundary memories for filtering."""
        try:
            return await self.memory_search.search(
                query="automation boundary constraint",
                memory_types=[MemoryType.BOUNDARY],
                entity_ids=entity_list,
                limit=20,
                min_confidence=0.4,
            )
        except Exception as e:
            logger.warning(f"Failed to fetch boundary memories: {e}")
            return []

    def _extract_boundary_constraints(
        self, boundaries: list[MemorySearchResult]
    ) -> tuple[set[str], set[str]]:
        """Extract entity IDs and keywords from boundary memories."""
        entities: set[str] = set()
        keywords: set[str] = set()
        for result in boundaries:
            if result.memory.entity_ids:
                entities.update(result.memory.entity_ids)
            for word in result.memory.content.lower().split():
                if len(word) > 3:
                    keywords.add(word)
        return entities, keywords

    async def _fetch_preferences(self) -> list[MemorySearchResult]:
        """Fetch preference memories for boosting."""
        try:
            return await self.memory_search.search(
                query="automation preference like prefer",
                memory_types=[MemoryType.PREFERENCE],
                limit=10,
                min_confidence=0.3,
            )
        except Exception as e:
            logger.warning(f"Failed to fetch preference memories: {e}")
            return []

    def _apply_preference_boosts(
        self, suggestions: list[dict[str, Any]], preferences: list[MemorySearchResult]
    ) -> None:
        """Apply preference-based confidence boosts to suggestions."""
        for suggestion in suggestions:
            boost = self._calculate_preference_boost(suggestion, preferences)
            if boost > 0:
                current = suggestion.get("confidence_score", 0.5)
                suggestion["confidence_score"] = min(1.0, current * (1 + boost))

    async def _fetch_outcomes(
        self, entity_list: list[str] | None
    ) -> list[MemorySearchResult]:
        """Fetch outcome memories for factor calculation."""
        try:
            return await self.memory_search.search(
                query="automation outcome result",
                memory_types=[MemoryType.OUTCOME],
                entity_ids=entity_list,
                limit=10,
                min_confidence=0.3,
            )
        except Exception as e:
            logger.warning(f"Failed to fetch outcome memories: {e}")
            return []

    def _apply_outcome_factors(
        self, suggestions: list[dict[str, Any]], outcomes: list[MemorySearchResult]
    ) -> None:
        """Apply outcome-based confidence factors to suggestions."""
        for suggestion in suggestions:
            factor = self._calculate_outcome_factor(suggestion, outcomes)
            current = suggestion.get("confidence_score", 0.5)
            suggestion["confidence_score"] = min(1.0, max(0.1, current * factor))

    def _matches_boundary(
        self,
        suggestion: dict[str, Any],
        boundary_entities: set[str],
        boundary_keywords: set[str],
    ) -> bool:
        """Check if a suggestion matches any boundary constraints."""
        suggestion_entities = set(suggestion.get("entity_ids", []))
        if suggestion_entities & boundary_entities:
            return True

        description = (suggestion.get("description") or "").lower()
        title = (suggestion.get("title") or "").lower()
        combined_text = f"{title} {description}"

        matching_keywords = sum(1 for kw in boundary_keywords if kw in combined_text)
        if matching_keywords >= 2:
            return True

        return False

    def _calculate_preference_boost(
        self, suggestion: dict[str, Any], preferences: list[MemorySearchResult]
    ) -> float:
        """Calculate confidence boost based on matching preferences."""
        if not preferences:
            return 0.0

        suggestion_entities = set(suggestion.get("entity_ids", []))
        description = (suggestion.get("description") or "").lower()

        total_boost = 0.0
        for result in preferences:
            memory = result.memory
            entity_match = False
            if memory.entity_ids and suggestion_entities:
                if set(memory.entity_ids) & suggestion_entities:
                    entity_match = True

            content_lower = memory.content.lower()
            keyword_match = any(
                word in description
                for word in content_lower.split()
                if len(word) > 4
            )

            if entity_match or keyword_match:
                contribution = result.relevance_score * memory.confidence * 0.1
                total_boost += contribution

        return min(total_boost, self.PREFERENCE_BOOST_MAX)

    def _calculate_outcome_factor(
        self, suggestion: dict[str, Any], outcomes: list[MemorySearchResult]
    ) -> float:
        """Calculate confidence factor based on past automation outcomes."""
        if not outcomes:
            return 1.0

        suggestion_entities = set(suggestion.get("entity_ids", []))
        description = (suggestion.get("description") or "").lower()

        success_signals = 0.0
        failure_signals = 0.0

        for result in outcomes:
            if not self._outcome_matches_suggestion(result, suggestion_entities, description):
                continue

            success, failure = self._classify_outcome(result)
            success_signals += success
            failure_signals += failure

        return self._outcome_factor_from_signals(success_signals, failure_signals)

    def _outcome_matches_suggestion(
        self,
        result: MemorySearchResult,
        suggestion_entities: set[str],
        description: str,
    ) -> bool:
        """Check if an outcome memory is relevant to a suggestion."""
        memory = result.memory
        if memory.entity_ids and suggestion_entities:
            if set(memory.entity_ids) & suggestion_entities:
                return True

        content_lower = memory.content.lower()
        return any(
            word in description
            for word in content_lower.split()
            if len(word) > 4
        )

    def _classify_outcome(self, result: MemorySearchResult) -> tuple[float, float]:
        """Classify outcome as success or failure, returning weighted signals."""
        memory = result.memory
        metadata = memory.metadata_ or {}
        action = metadata.get("action", "")
        content_lower = memory.content.lower()

        success_keywords = ("approved", "success", "worked", "helpful")
        failure_keywords = ("rejected", "failed", "problem", "issue")

        is_success = any(kw in action or kw in content_lower for kw in success_keywords)
        is_failure = any(kw in action or kw in content_lower for kw in failure_keywords)

        success = memory.confidence if is_success else 0.0
        failure = memory.confidence if is_failure else 0.0
        return success, failure

    def _outcome_factor_from_signals(
        self, success_signals: float, failure_signals: float
    ) -> float:
        """Convert success/failure signals to a confidence factor."""
        if success_signals > failure_signals:
            return self.OUTCOME_SUCCESS_BOOST
        if failure_signals > success_signals:
            return self.OUTCOME_FAILURE_PENALTY
        return 1.0
