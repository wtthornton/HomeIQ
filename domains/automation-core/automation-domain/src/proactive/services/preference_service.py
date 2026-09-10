"""
Memory Brain Integration — Preference Recall (Epic 68, Story 68.2).

Queries user preference history from Memory Brain and action_preference_history
table before generating suggestions. Injects preference context into the LLM
reasoning prompt.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select

try:
    from homeiq_memory import MemorySearch, MemoryType

    _MEMORY_AVAILABLE = True
except ImportError:
    MemorySearch = None  # type: ignore[assignment,misc]
    MemoryType = None  # type: ignore[assignment,misc]
    _MEMORY_AVAILABLE = False

from ..models.autonomous_action import ActionPreferenceHistory

logger = logging.getLogger(__name__)


class PreferenceService:
    """Queries user preference history for confidence scoring and prompt injection."""

    def __init__(self, memory_search: Any = None):
        self.memory_search = memory_search

    async def get_acceptance_rate(
        self,
        action_type: str,
        entity_domain: str,
        context_type: str,
        time_slot: str,
    ) -> float | None:
        """Get historical acceptance rate for a similar action.

        Returns None if no history available (new action type).
        """
        from ..database import db

        try:
            async with db.get_db() as session:
                stmt = select(ActionPreferenceHistory).where(
                    ActionPreferenceHistory.action_type == action_type,
                    ActionPreferenceHistory.entity_domain == entity_domain,
                    ActionPreferenceHistory.context_type == context_type,
                    ActionPreferenceHistory.time_slot == time_slot,
                )
                result = await session.execute(stmt)
                history = result.scalar_one_or_none()
                if history:
                    return history.acceptance_rate
        except Exception as e:
            logger.debug("Failed to query preference history: %s", e)
        return None

    async def get_preference_summary(self) -> str | None:
        """Build a preference summary string for LLM prompt injection.

        Combines:
        1. Memory Brain behavioral/boundary memories
        2. Top acceptance/rejection patterns from history table
        """
        parts: list[str] = []

        # Memory Brain preferences
        if self.memory_search and _MEMORY_AVAILABLE:
            try:
                memory_prefs = await self._query_memory_preferences()
                if memory_prefs:
                    parts.append(memory_prefs)
            except Exception as e:
                logger.debug("Memory preference query failed: %s", e)

        # Database preference patterns
        try:
            db_prefs = await self._query_db_preferences()
            if db_prefs:
                parts.append(db_prefs)
        except Exception as e:
            logger.debug("DB preference query failed: %s", e)

        return "\n".join(parts) if parts else None

    async def _query_memory_preferences(self) -> str | None:
        """Query Memory Brain for user preferences."""
        if not self.memory_search or not _MEMORY_AVAILABLE:
            return None

        try:
            results = await self.memory_search.search(
                query="user preference proactive automation",
                memory_types=[MemoryType.BEHAVIORAL, MemoryType.BOUNDARY],
                limit=5,
                min_confidence=0.3,
            )
            if not results:
                return None

            lines = ["User preferences from memory:"]
            for mem in results:
                lines.append(f"- {mem.content[:200]}")
            return "\n".join(lines)
        except Exception as e:
            logger.debug("Memory search failed: %s", e)
            return None

    async def _query_db_preferences(self) -> str | None:
        """Query preference history table for top patterns."""
        from ..database import db

        try:
            async with db.get_db() as session:
                # Get top accepted patterns
                stmt = (
                    select(ActionPreferenceHistory)
                    .where(ActionPreferenceHistory.acceptance_count > 0)
                    .order_by(ActionPreferenceHistory.acceptance_rate.desc())
                    .limit(5)
                )
                result = await session.execute(stmt)
                top_accepted = result.scalars().all()

                # Get top rejected patterns
                stmt_rej = (
                    select(ActionPreferenceHistory)
                    .where(ActionPreferenceHistory.rejection_count > 2)
                    .order_by(ActionPreferenceHistory.acceptance_rate.asc())
                    .limit(3)
                )
                result_rej = await session.execute(stmt_rej)
                top_rejected = result_rej.scalars().all()

                if not top_accepted and not top_rejected:
                    return None

                lines = ["Historical action preferences:"]
                for pref in top_accepted:
                    lines.append(
                        f"- User accepts {pref.action_type} on {pref.entity_domain} "
                        f"during {pref.time_slot} ({pref.acceptance_rate:.0%} acceptance)"
                    )
                for pref in top_rejected:
                    lines.append(
                        f"- User rejects {pref.action_type} on {pref.entity_domain} "
                        f"during {pref.time_slot} ({pref.acceptance_rate:.0%} acceptance)"
                    )
                return "\n".join(lines)
        except Exception as e:
            logger.debug("DB preference query failed: %s", e)
            return None
