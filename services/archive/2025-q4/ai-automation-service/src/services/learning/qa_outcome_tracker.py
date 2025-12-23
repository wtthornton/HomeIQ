"""
Q&A Outcome Tracker

Tracks Q&A session outcomes and automation success for learning.
Links clarification sessions to automation outcomes to enable learning
from successful and failed automation creation attempts.

2025 Best Practices:
- Full type hints (PEP 484/526)
- Async/await for all database operations
- SQLAlchemy 2.0+ async patterns
- Proper error handling with type information
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class QAOutcomeTracker:
    """
    Tracks Q&A session outcomes and automation success.
    
    Records outcomes of clarification sessions including:
    - Whether automation was created
    - Automation success (days active, user satisfaction)
    - Questions count and confidence achieved
    
    Uses 2025 best practices: async/await, type hints, SQLAlchemy 2.0+ patterns.
    """

    async def track_qa_outcome(
        self,
        db: AsyncSession,
        session_id: str,
        questions_count: int,
        confidence_achieved: float,
        outcome_type: str,
        automation_id: str | None = None,
        days_active: int | None = None,
        user_satisfaction: float | None = None
    ) -> int | None:
        """
        Track Q&A session outcome.
        
        Args:
            db: Database session (async)
            session_id: Clarification session ID
            questions_count: Number of questions asked
            confidence_achieved: Final confidence score
            outcome_type: 'automation_created', 'abandoned', 'rejected'
            automation_id: Optional automation ID if created
            days_active: Optional days automation was active
            user_satisfaction: Optional user satisfaction score (0.0-1.0)
            
        Returns:
            Created QAOutcome ID or None if failed
        """
        try:
            from ...database.models import QAOutcome

            outcome = QAOutcome(
                session_id=session_id,
                automation_id=automation_id,
                questions_count=questions_count,
                confidence_achieved=confidence_achieved,
                outcome_type=outcome_type,
                days_active=days_active,
                user_satisfaction=user_satisfaction,
                created_at=datetime.now(timezone.utc)
            )

            db.add(outcome)
            await db.commit()
            await db.refresh(outcome)

            logger.info(
                f"Tracked Q&A outcome: session_id={session_id}, "
                f"outcome_type='{outcome_type}', automation_id={automation_id}, "
                f"confidence={confidence_achieved:.2f}"
            )

            return outcome.id

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to track Q&A outcome: {e}", exc_info=True)
            return None

    async def update_automation_outcome(
        self,
        db: AsyncSession,
        session_id: str,
        automation_id: str | None = None,
        days_active: int | None = None,
        user_satisfaction: float | None = None,
        outcome_type: str | None = None
    ) -> bool:
        """
        Update automation outcome for existing Q&A session.
        
        Called when automation is deleted, modified, or user provides feedback.
        
        Args:
            db: Database session
            session_id: Clarification session ID
            automation_id: Automation ID (if not already set)
            days_active: Days automation was active
            user_satisfaction: User satisfaction score
            outcome_type: Updated outcome type
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            from ...database.models import QAOutcome

            # Find existing outcome by session_id
            query = select(QAOutcome).where(
                QAOutcome.session_id == session_id
            ).order_by(QAOutcome.created_at.desc()).limit(1)

            result = await db.execute(query)
            outcome = result.scalar_one_or_none()

            if not outcome:
                logger.warning(f"No Q&A outcome found for session_id={session_id}")
                return False

            # Update fields
            if automation_id is not None:
                outcome.automation_id = automation_id
            if days_active is not None:
                outcome.days_active = days_active
            if user_satisfaction is not None:
                outcome.user_satisfaction = user_satisfaction
            if outcome_type is not None:
                outcome.outcome_type = outcome_type

            outcome.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(outcome)

            logger.info(
                f"Updated Q&A outcome: session_id={session_id}, "
                f"days_active={days_active}, satisfaction={user_satisfaction}"
            )

            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to update automation outcome: {e}", exc_info=True)
            return False

    async def get_outcome_statistics(
        self,
        db: AsyncSession,
        user_id: str | None = None,
        days: int = 30
    ) -> dict[str, Any]:
        """
        Get Q&A outcome statistics for analysis.
        
        Args:
            db: Database session
            user_id: Optional user ID to filter
            days: Number of days to look back
            
        Returns:
            Dictionary with statistics
        """
        try:
            from ...database.models import QAOutcome, ClarificationSessionDB
            from datetime import timedelta

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Build query
            query = select(QAOutcome).join(
                ClarificationSessionDB,
                QAOutcome.session_id == ClarificationSessionDB.session_id
            ).where(
                QAOutcome.created_at >= cutoff_date
            )

            if user_id:
                query = query.where(ClarificationSessionDB.user_id == user_id)

            result = await db.execute(query)
            outcomes = list(result.scalars().all())

            if not outcomes:
                return {
                    'total': 0,
                    'automation_created': 0,
                    'abandoned': 0,
                    'rejected': 0,
                    'avg_confidence': 0.0,
                    'avg_questions': 0.0,
                    'avg_days_active': 0.0,
                    'success_rate': 0.0
                }

            automation_created = sum(1 for o in outcomes if o.outcome_type == 'automation_created')
            abandoned = sum(1 for o in outcomes if o.outcome_type == 'abandoned')
            rejected = sum(1 for o in outcomes if o.outcome_type == 'rejected')

            avg_confidence = sum(o.confidence_achieved for o in outcomes) / len(outcomes)
            avg_questions = sum(o.questions_count for o in outcomes) / len(outcomes)

            # Calculate success rate (automations that stayed active 30+ days)
            successful_automations = [
                o for o in outcomes
                if o.outcome_type == 'automation_created' and o.days_active is not None and o.days_active >= 30
            ]
            success_rate = len(successful_automations) / automation_created if automation_created > 0 else 0.0

            avg_days_active = sum(
                o.days_active for o in outcomes
                if o.days_active is not None
            ) / max(1, len([o for o in outcomes if o.days_active is not None]))

            return {
                'total': len(outcomes),
                'automation_created': automation_created,
                'abandoned': abandoned,
                'rejected': rejected,
                'avg_confidence': avg_confidence,
                'avg_questions': avg_questions,
                'avg_days_active': avg_days_active,
                'success_rate': success_rate
            }

        except Exception as e:
            logger.error(f"Failed to get outcome statistics: {e}", exc_info=True)
            return {}

    async def get_successful_sessions(
        self,
        db: AsyncSession,
        min_days_active: int = 30,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get successful Q&A sessions for learning.
        
        Returns sessions that led to automations that stayed active for specified days.
        
        Args:
            db: Database session
            min_days_active: Minimum days active to consider successful
            limit: Maximum number of sessions to return
            
        Returns:
            List of successful session data
        """
        try:
            from ...database.models import QAOutcome, ClarificationSessionDB

            query = select(QAOutcome, ClarificationSessionDB).join(
                ClarificationSessionDB,
                QAOutcome.session_id == ClarificationSessionDB.session_id
            ).where(
                QAOutcome.outcome_type == 'automation_created',
                QAOutcome.days_active >= min_days_active
            ).order_by(
                QAOutcome.created_at.desc()
            ).limit(limit)

            result = await db.execute(query)
            rows = result.all()

            successful_sessions = []
            for outcome, session in rows:
                successful_sessions.append({
                    'session_id': outcome.session_id,
                    'automation_id': outcome.automation_id,
                    'questions_count': outcome.questions_count,
                    'confidence_achieved': outcome.confidence_achieved,
                    'days_active': outcome.days_active,
                    'user_satisfaction': outcome.user_satisfaction,
                    'original_query': session.original_query,
                    'questions': session.questions,
                    'answers': session.answers,
                    'created_at': outcome.created_at.isoformat()
                })

            logger.debug(f"Found {len(successful_sessions)} successful sessions")
            return successful_sessions

        except Exception as e:
            logger.error(f"Failed to get successful sessions: {e}", exc_info=True)
            return []


