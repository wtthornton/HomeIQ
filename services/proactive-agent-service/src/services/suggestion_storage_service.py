"""
Suggestion Storage Service for Proactive Agent Service

CRUD operations for managing proactive automation suggestions.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session_maker
from ..models import Suggestion

logger = logging.getLogger(__name__)


class DatabaseNotInitializedError(Exception):
    """Raised when database session maker is not initialized"""
    pass


def _get_session_maker():
    """
    Get the async session maker, raising a clear error if not initialized.
    
    Returns:
        The async session maker
        
    Raises:
        DatabaseNotInitializedError: If database not initialized
    """
    session_maker = get_async_session_maker()
    if session_maker is None:
        raise DatabaseNotInitializedError(
            "Database not initialized. Call init_database() before using storage service. "
            "Ensure the service is started and database initialization completed."
        )
    return session_maker


class SuggestionStorageService:
    """Service for storing and managing suggestions"""

    def __init__(self):
        """Initialize storage service"""
        # Note: Database initialization is checked at runtime when methods are called
        # The database should be initialized before creating this service
        logger.debug("SuggestionStorageService initialized")

    async def create_suggestion(
        self,
        prompt: str,
        context_type: str,
        quality_score: float = 0.0,
        context_metadata: dict[str, Any] | None = None,
        prompt_metadata: dict[str, Any] | None = None,
        db: AsyncSession | None = None,
        check_duplicates: bool = True,
        duplicate_window_hours: int = 24,
    ) -> Suggestion | None:
        """
        Create a new suggestion.

        Args:
            prompt: The prompt sent to the HA AI Agent
            context_type: Type of context (weather, sports, energy, pattern)
            quality_score: Quality score for the suggestion (0.0-1.0)
            context_metadata: Context analysis metadata
            prompt_metadata: Prompt generation metadata
            db: Optional database session (will create one if not provided)
            check_duplicates: Whether to check for duplicate prompts (default: True)
            duplicate_window_hours: Hours to look back for duplicates (default: 24)

        Returns:
            Created Suggestion object, or None if duplicate found and skipped
        """
        if db is None:
            async with _get_session_maker()() as session:
                try:
                    # Check for duplicates if enabled
                    if check_duplicates:
                        duplicate = await self._check_duplicate(
                            prompt, context_type, duplicate_window_hours, session
                        )
                        if duplicate:
                            logger.info(
                                f"Skipping duplicate suggestion (prompt: {prompt[:50]}..., "
                                f"existing_id: {duplicate.id}, created: {duplicate.created_at})"
                            )
                            return None
                    
                    suggestion = Suggestion(
                        prompt=prompt,
                        context_type=context_type,
                        status="pending",
                        quality_score=quality_score,
                        context_metadata=context_metadata or {},
                        prompt_metadata=prompt_metadata or {},
                    )

                    session.add(suggestion)
                    await session.commit()
                    await session.refresh(suggestion)

                    logger.info(f"Created suggestion {suggestion.id} (context_type={context_type})")
                    return suggestion
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Failed to create suggestion: {e}", exc_info=True)
                    raise
        else:
            try:
                # Check for duplicates if enabled
                if check_duplicates:
                    duplicate = await self._check_duplicate(
                        prompt, context_type, duplicate_window_hours, db
                    )
                    if duplicate:
                        logger.info(
                            f"Skipping duplicate suggestion (prompt: {prompt[:50]}..., "
                            f"existing_id: {duplicate.id}, created: {duplicate.created_at})"
                        )
                        return None
                
                suggestion = Suggestion(
                    prompt=prompt,
                    context_type=context_type,
                    status="pending",
                    quality_score=quality_score,
                    context_metadata=context_metadata or {},
                    prompt_metadata=prompt_metadata or {},
                )

                db.add(suggestion)
                await db.commit()
                await db.refresh(suggestion)

                logger.info(f"Created suggestion {suggestion.id} (context_type={context_type})")
                return suggestion
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to create suggestion: {e}", exc_info=True)
                raise

    async def _check_duplicate(
        self,
        prompt: str,
        context_type: str,
        window_hours: int,
        db: AsyncSession,
    ) -> Suggestion | None:
        """
        Check if a duplicate suggestion exists within the time window.
        
        Args:
            prompt: Prompt text to check
            context_type: Context type to check
            window_hours: Hours to look back for duplicates
            db: Database session
            
        Returns:
            Existing Suggestion if duplicate found, None otherwise
        """
        from datetime import timedelta
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        
        result = await db.execute(
            select(Suggestion)
            .where(Suggestion.prompt == prompt.strip())
            .where(Suggestion.context_type == context_type)
            .where(Suggestion.created_at >= cutoff_time)
            .order_by(Suggestion.created_at.desc())
            .limit(1)
        )
        
        return result.scalar_one_or_none()
    
    async def get_suggestion(self, suggestion_id: str, db: AsyncSession | None = None) -> Suggestion | None:
        """
        Get a suggestion by ID.

        Args:
            suggestion_id: Suggestion ID
            db: Optional database session

        Returns:
            Suggestion object or None if not found
        """
        if db is None:
            async with _get_session_maker()() as session:
                try:
                    result = await session.execute(select(Suggestion).where(Suggestion.id == suggestion_id))
                    return result.scalar_one_or_none()
                except Exception as e:
                    logger.error(f"Failed to get suggestion {suggestion_id}: {e}", exc_info=True)
                    return None
        else:
            try:
                result = await db.execute(select(Suggestion).where(Suggestion.id == suggestion_id))
                return result.scalar_one_or_none()
            except Exception as e:
                logger.error(f"Failed to get suggestion {suggestion_id}: {e}", exc_info=True)
                return None

    async def list_suggestions(
        self,
        status: str | None = None,
        context_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
        db: AsyncSession | None = None,
    ) -> list[Suggestion]:
        """
        List suggestions with optional filters.

        Args:
            status: Filter by status (pending, sent, approved, rejected)
            context_type: Filter by context type
            limit: Maximum number of results
            offset: Offset for pagination
            db: Optional database session

        Returns:
            List of Suggestion objects
        """
        if db is None:
            async with _get_session_maker()() as session:
                try:
                    query = select(Suggestion)

                    if status:
                        query = query.where(Suggestion.status == status)
                    if context_type:
                        query = query.where(Suggestion.context_type == context_type)

                    query = query.order_by(Suggestion.created_at.desc()).limit(limit).offset(offset)

                    result = await session.execute(query)
                    return list(result.scalars().all())
                except Exception as e:
                    logger.error(f"Failed to list suggestions: {e}", exc_info=True)
                    return []
        else:
            try:
                query = select(Suggestion)

                if status:
                    query = query.where(Suggestion.status == status)
                if context_type:
                    query = query.where(Suggestion.context_type == context_type)

                query = query.order_by(Suggestion.created_at.desc()).limit(limit).offset(offset)

                result = await db.execute(query)
                return list(result.scalars().all())
            except Exception as e:
                logger.error(f"Failed to list suggestions: {e}", exc_info=True)
                return []

    async def update_suggestion_status(
        self,
        suggestion_id: str,
        status: str,
        agent_response: dict[str, Any] | None = None,
        db: AsyncSession | None = None,
    ) -> Suggestion | None:
        """
        Update suggestion status.

        Args:
            suggestion_id: Suggestion ID
            status: New status (pending, sent, approved, rejected)
            agent_response: Optional agent response metadata
            db: Optional database session

        Returns:
            Updated Suggestion object or None if not found
        """
        if db is None:
            async with _get_session_maker()() as session:
                try:
                    # Get existing suggestion
                    result = await session.execute(select(Suggestion).where(Suggestion.id == suggestion_id))
                    suggestion = result.scalar_one_or_none()

                    if not suggestion:
                        logger.warning(f"Suggestion {suggestion_id} not found for status update")
                        return None

                    # Update status
                    suggestion.status = status
                    if agent_response:
                        suggestion.agent_response = agent_response

                    # Set sent_at timestamp if status is "sent"
                    if status == "sent" and not suggestion.sent_at:
                        suggestion.sent_at = datetime.now(timezone.utc)

                    await session.commit()
                    await session.refresh(suggestion)

                    logger.info(f"Updated suggestion {suggestion_id} status to {status}")
                    return suggestion
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Failed to update suggestion {suggestion_id}: {e}", exc_info=True)
                    return None
        else:
            try:
                # Get existing suggestion
                result = await db.execute(select(Suggestion).where(Suggestion.id == suggestion_id))
                suggestion = result.scalar_one_or_none()

                if not suggestion:
                    logger.warning(f"Suggestion {suggestion_id} not found for status update")
                    return None

                # Update status
                suggestion.status = status
                if agent_response:
                    suggestion.agent_response = agent_response

                # Set sent_at timestamp if status is "sent"
                if status == "sent" and not suggestion.sent_at:
                    suggestion.sent_at = datetime.now(timezone.utc)

                await db.commit()
                await db.refresh(suggestion)

                logger.info(f"Updated suggestion {suggestion_id} status to {status}")
                return suggestion
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to update suggestion {suggestion_id}: {e}", exc_info=True)
                return None

    async def delete_suggestion(self, suggestion_id: str, db: AsyncSession | None = None) -> bool:
        """
        Delete a suggestion.

        Args:
            suggestion_id: Suggestion ID
            db: Optional database session

        Returns:
            True if deleted, False if not found
        """
        if db is None:
            async with _get_session_maker()() as session:
                try:
                    result = await session.execute(delete(Suggestion).where(Suggestion.id == suggestion_id))
                    await session.commit()

                    deleted = result.rowcount > 0
                    if deleted:
                        logger.info(f"Deleted suggestion {suggestion_id}")
                    else:
                        logger.warning(f"Suggestion {suggestion_id} not found for deletion")

                    return deleted
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Failed to delete suggestion {suggestion_id}: {e}", exc_info=True)
                    return False
        else:
            try:
                result = await db.execute(delete(Suggestion).where(Suggestion.id == suggestion_id))
                await db.commit()

                deleted = result.rowcount > 0
                if deleted:
                    logger.info(f"Deleted suggestion {suggestion_id}")
                else:
                    logger.warning(f"Suggestion {suggestion_id} not found for deletion")

                return deleted
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to delete suggestion {suggestion_id}: {e}", exc_info=True)
                return False

    async def cleanup_old_suggestions(
        self,
        days_old: int = 90,
        status_filter: str | None = None,
        db: AsyncSession | None = None,
    ) -> int:
        """
        Clean up old suggestions (TTL-based cleanup).

        Args:
            days_old: Delete suggestions older than this many days
            status_filter: Only delete suggestions with this status (None = all statuses)
            db: Optional database session

        Returns:
            Number of suggestions deleted
        """
        if db is None:
            async with _get_session_maker()() as session:
                try:
                    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

                    query = delete(Suggestion).where(Suggestion.created_at < cutoff_date)

                    if status_filter:
                        query = query.where(Suggestion.status == status_filter)

                    result = await session.execute(query)
                    await session.commit()

                    deleted_count = result.rowcount
                    logger.info(f"Cleaned up {deleted_count} suggestions older than {days_old} days")
                    return deleted_count
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Failed to cleanup old suggestions: {e}", exc_info=True)
                    return 0
        else:
            try:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

                query = delete(Suggestion).where(Suggestion.created_at < cutoff_date)

                if status_filter:
                    query = query.where(Suggestion.status == status_filter)

                result = await db.execute(query)
                await db.commit()

                deleted_count = result.rowcount
                logger.info(f"Cleaned up {deleted_count} suggestions older than {days_old} days")
                return deleted_count
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to cleanup old suggestions: {e}", exc_info=True)
                return 0

    async def count_suggestions(
        self,
        status: str | None = None,
        context_type: str | None = None,
        db: AsyncSession | None = None,
    ) -> int:
        """
        Count suggestions with optional filters (efficient COUNT query).

        Args:
            status: Filter by status
            context_type: Filter by context type
            db: Optional database session

        Returns:
            Total count
        """
        if db is None:
            async with _get_session_maker()() as session:
                try:
                    query = select(func.count(Suggestion.id))

                    if status:
                        query = query.where(Suggestion.status == status)
                    if context_type:
                        query = query.where(Suggestion.context_type == context_type)

                    result = await session.execute(query)
                    return result.scalar_one() or 0
                except Exception as e:
                    logger.error(f"Failed to count suggestions: {e}", exc_info=True)
                    return 0
        else:
            try:
                query = select(func.count(Suggestion.id))

                if status:
                    query = query.where(Suggestion.status == status)
                if context_type:
                    query = query.where(Suggestion.context_type == context_type)

                result = await db.execute(query)
                return result.scalar_one() or 0
            except Exception as e:
                logger.error(f"Failed to count suggestions: {e}", exc_info=True)
                return 0

    async def get_suggestion_stats(self, db: AsyncSession | None = None) -> dict[str, Any]:
        """
        Get suggestion statistics using efficient SQL aggregation.

        Args:
            db: Optional database session

        Returns:
            Dictionary with statistics
        """
        if db is None:
            async with _get_session_maker()() as session:
                try:
                    # Total count
                    total_result = await session.execute(select(func.count(Suggestion.id)))
                    total_count = total_result.scalar_one() or 0

                    # Count by status (single query with GROUP BY)
                    status_query = (
                        select(Suggestion.status, func.count(Suggestion.id).label("count"))
                        .group_by(Suggestion.status)
                    )
                    status_result = await session.execute(status_query)
                    status_counts = {row[0]: row[1] for row in status_result.all()}
                    # Ensure all statuses are present
                    for status in ["pending", "sent", "approved", "rejected"]:
                        if status not in status_counts:
                            status_counts[status] = 0

                    # Count by context type (single query with GROUP BY)
                    context_query = (
                        select(Suggestion.context_type, func.count(Suggestion.id).label("count"))
                        .group_by(Suggestion.context_type)
                    )
                    context_result = await session.execute(context_query)
                    context_counts = {row[0]: row[1] for row in context_result.all()}

                    return {
                        "total": total_count,
                        "by_status": status_counts,
                        "by_context_type": context_counts,
                    }
                except Exception as e:
                    logger.error(f"Failed to get suggestion stats: {e}", exc_info=True)
                    return {"total": 0, "by_status": {}, "by_context_type": {}}
        else:
            try:
                # Total count
                total_result = await db.execute(select(func.count(Suggestion.id)))
                total_count = total_result.scalar_one() or 0

                # Count by status (single query with GROUP BY)
                status_query = (
                    select(Suggestion.status, func.count(Suggestion.id).label("count"))
                    .group_by(Suggestion.status)
                )
                status_result = await db.execute(status_query)
                status_counts = {row[0]: row[1] for row in status_result.all()}
                # Ensure all statuses are present
                for status in ["pending", "sent", "approved", "rejected"]:
                    if status not in status_counts:
                        status_counts[status] = 0

                # Count by context type (single query with GROUP BY)
                context_query = (
                    select(Suggestion.context_type, func.count(Suggestion.id).label("count"))
                    .group_by(Suggestion.context_type)
                )
                context_result = await db.execute(context_query)
                context_counts = {row[0]: row[1] for row in context_result.all()}

                return {
                    "total": total_count,
                    "by_status": status_counts,
                    "by_context_type": context_counts,
                }
            except Exception as e:
                logger.error(f"Failed to get suggestion stats: {e}", exc_info=True)
                return {"total": 0, "by_status": {}, "by_context_type": {}}
