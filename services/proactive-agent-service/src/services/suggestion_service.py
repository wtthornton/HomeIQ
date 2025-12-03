"""
Suggestion Service for Proactive Agent Service

CRUD operations for suggestion storage and management.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Suggestion

logger = logging.getLogger(__name__)


class SuggestionService:
    """Service for managing suggestions"""

    def __init__(self, db_session: AsyncSession):
        """
        Initialize Suggestion Service.

        Args:
            db_session: Database session
        """
        self.db = db_session
        logger.debug("Suggestion Service initialized")

    async def create_suggestion(
        self,
        prompt: str,
        context_type: str,
        quality_score: float = 0.0,
        context_metadata: dict[str, Any] | None = None,
        prompt_metadata: dict[str, Any] | None = None,
    ) -> Suggestion:
        """
        Create a new suggestion.

        Args:
            prompt: Generated prompt text
            context_type: Type of context (weather, sports, energy, historical_pattern)
            quality_score: Prompt quality score (0.0-1.0)
            context_metadata: Context analysis metadata
            prompt_metadata: Prompt generation metadata

        Returns:
            Created Suggestion object
        """
        suggestion = Suggestion(
            prompt=prompt,
            context_type=context_type,
            quality_score=quality_score,
            context_metadata=context_metadata or {},
            prompt_metadata=prompt_metadata or {},
            status="pending",
        )

        self.db.add(suggestion)
        await self.db.commit()
        await self.db.refresh(suggestion)

        logger.info(f"Created suggestion: id={suggestion.id}, context_type={context_type}")
        return suggestion

    async def get_suggestion(self, suggestion_id: str) -> Suggestion | None:
        """
        Get suggestion by ID.

        Args:
            suggestion_id: Suggestion ID

        Returns:
            Suggestion object or None if not found
        """
        result = await self.db.execute(
            select(Suggestion).where(Suggestion.id == suggestion_id)
        )
        return result.scalar_one_or_none()

    async def list_suggestions(
        self,
        status: str | None = None,
        context_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Suggestion]:
        """
        List suggestions with optional filters.

        Args:
            status: Filter by status (pending, sent, approved, rejected)
            context_type: Filter by context type
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of Suggestion objects
        """
        query = select(Suggestion)

        if status:
            query = query.where(Suggestion.status == status)
        if context_type:
            query = query.where(Suggestion.context_type == context_type)

        query = query.order_by(Suggestion.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_suggestion_status(
        self,
        suggestion_id: str,
        status: str,
        agent_response: dict[str, Any] | None = None,
    ) -> Suggestion | None:
        """
        Update suggestion status.

        Args:
            suggestion_id: Suggestion ID
            status: New status (pending, sent, approved, rejected)
            agent_response: Optional agent response metadata

        Returns:
            Updated Suggestion object or None if not found
        """
        suggestion = await self.get_suggestion(suggestion_id)
        if not suggestion:
            return None

        suggestion.status = status
        if agent_response:
            suggestion.agent_response = agent_response
        if status == "sent":
            suggestion.sent_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(suggestion)

        logger.info(f"Updated suggestion status: id={suggestion_id}, status={status}")
        return suggestion

    async def mark_sent(
        self,
        suggestion_id: str,
        agent_response: dict[str, Any] | None = None,
    ) -> Suggestion | None:
        """
        Mark suggestion as sent.

        Args:
            suggestion_id: Suggestion ID
            agent_response: Agent response metadata

        Returns:
            Updated Suggestion object or None if not found
        """
        return await self.update_suggestion_status(suggestion_id, "sent", agent_response)

    async def mark_approved(self, suggestion_id: str) -> Suggestion | None:
        """
        Mark suggestion as approved.

        Args:
            suggestion_id: Suggestion ID

        Returns:
            Updated Suggestion object or None if not found
        """
        return await self.update_suggestion_status(suggestion_id, "approved")

    async def mark_rejected(self, suggestion_id: str) -> Suggestion | None:
        """
        Mark suggestion as rejected.

        Args:
            suggestion_id: Suggestion ID

        Returns:
            Updated Suggestion object or None if not found
        """
        return await self.update_suggestion_status(suggestion_id, "rejected")

    async def cleanup_old_suggestions(self, days: int = 90) -> int:
        """
        Clean up suggestions older than specified days.

        Args:
            days: Number of days to keep (default: 90)

        Returns:
            Number of suggestions deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = await self.db.execute(
            select(Suggestion).where(Suggestion.created_at < cutoff_date)
        )
        old_suggestions = result.scalars().all()

        count = len(old_suggestions)
        for suggestion in old_suggestions:
            await self.db.delete(suggestion)

        await self.db.commit()

        if count > 0:
            logger.info(f"Cleaned up {count} suggestions older than {days} days")

        return count

    async def get_statistics(self) -> dict[str, Any]:
        """
        Get suggestion statistics.

        Returns:
            Dictionary with statistics
        """
        total = await self.db.scalar(select(func.count(Suggestion.id)))
        pending = await self.db.scalar(
            select(func.count(Suggestion.id)).where(Suggestion.status == "pending")
        )
        sent = await self.db.scalar(
            select(func.count(Suggestion.id)).where(Suggestion.status == "sent")
        )
        approved = await self.db.scalar(
            select(func.count(Suggestion.id)).where(Suggestion.status == "approved")
        )
        rejected = await self.db.scalar(
            select(func.count(Suggestion.id)).where(Suggestion.status == "rejected")
        )

        return {
            "total": total or 0,
            "pending": pending or 0,
            "sent": sent or 0,
            "approved": approved or 0,
            "rejected": rejected or 0,
        }

