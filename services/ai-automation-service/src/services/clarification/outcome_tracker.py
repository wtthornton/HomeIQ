"""
Clarification Outcome Tracker

Tracks clarification session outcomes for learning and improvement.
Builds predictive models to estimate expected success rates based on confidence and rounds.

2025 Best Practices:
- Full type hints (PEP 484/526)
- Async/await for all database operations
- SQLAlchemy 2.0+ async patterns
- Proper error handling with type information
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ClarificationOutcomeTracker:
    """
    Tracks clarification outcomes and provides expected success rate predictions.
    
    Learns from historical data to predict: P(success | confidence, rounds)
    
    Uses 2025 best practices: async/await, type hints, SQLAlchemy 2.0+ patterns.
    """

    def __init__(self, db: AsyncSession | None = None) -> None:
        """
        Initialize outcome tracker.
        
        Args:
            db: Optional database session for querying outcomes
        """
        self.db: AsyncSession | None = db

    async def track_outcome(
        self,
        db: AsyncSession,
        session_id: str,
        final_confidence: float,
        proceeded: bool,
        suggestion_approved: bool | None = None,
        rounds: int = 0,
        suggestion_id: int | None = None
    ) -> None:
        """
        Track clarification outcome.
        
        Uses async database operations (2025 best practice: SQLAlchemy 2.0+ async patterns).
        
        Args:
            db: Database session (async)
            session_id: Clarification session ID
            final_confidence: Final confidence when proceeding
            proceeded: Whether user proceeded after clarification
            suggestion_approved: Whether suggestion was approved (None if unknown)
            rounds: Number of clarification rounds
            suggestion_id: Optional suggestion ID if linked
        """
        try:
            from ...database.crud import store_clarification_outcome

            await store_clarification_outcome(
                db=db,
                session_id=session_id,
                final_confidence=final_confidence,
                proceeded=proceeded,
                suggestion_approved=suggestion_approved,
                rounds=rounds,
                suggestion_id=suggestion_id
            )

            logger.debug(
                f"Tracked clarification outcome: session_id={session_id}, "
                f"confidence={final_confidence:.2f}, proceeded={proceeded}, "
                f"approved={suggestion_approved}, rounds={rounds}"
            )
        except Exception as e:
            logger.error(f"Failed to track clarification outcome: {e}", exc_info=True)
            # Non-blocking: continue even if tracking fails

    async def get_expected_success_rate(
        self,
        db: AsyncSession,
        confidence: float,
        rounds: int = 0,
        min_samples: int = 10
    ) -> float | None:
        """
        Get expected success rate for given confidence and rounds.
        
        Calculates: P(success | confidence, rounds) from historical data.
        
        Args:
            db: Database session
            confidence: Confidence score
            rounds: Number of clarification rounds
            min_samples: Minimum number of samples required for prediction
            
        Returns:
            Expected success rate (0.0-1.0) or None if insufficient data
        """
        try:
            from ...database.models import ClarificationOutcome

            # Query outcomes within confidence range (±0.1) and similar rounds
            confidence_lower = max(0.0, confidence - 0.1)
            confidence_upper = min(1.0, confidence + 0.1)
            rounds_lower = max(0, rounds - 1)
            rounds_upper = rounds + 1

            query = select(ClarificationOutcome).where(
                ClarificationOutcome.final_confidence >= confidence_lower,
                ClarificationOutcome.final_confidence <= confidence_upper,
                ClarificationOutcome.rounds >= rounds_lower,
                ClarificationOutcome.rounds <= rounds_upper,
                ClarificationOutcome.proceeded == True  # Only count proceeded sessions
            )

            result = await db.execute(query)
            outcomes = list(result.scalars().all())

            if len(outcomes) < min_samples:
                logger.debug(
                    f"Insufficient data for success rate prediction: "
                    f"{len(outcomes)} < {min_samples} samples"
                )
                return None

            # Calculate success rate (proceeded AND approved)
            successful = sum(
                1 for outcome in outcomes
                if outcome.suggestion_approved is True
            )
            total = len(outcomes)

            success_rate = successful / total if total > 0 else None

            logger.debug(
                f"Expected success rate: {success_rate:.2%} "
                f"(confidence={confidence:.2f}, rounds={rounds}, samples={total})"
            )

            return success_rate

        except Exception as e:
            logger.error(f"Failed to get expected success rate: {e}", exc_info=True)
            return None

    async def get_outcome_statistics(
        self,
        db: AsyncSession,
        days: int = 30
    ) -> dict[str, Any]:
        """
        Get outcome statistics for analysis.
        
        Args:
            db: Database session
            days: Number of days to look back
            
        Returns:
            Dictionary with statistics
        """
        try:
            from ...database.models import ClarificationOutcome

            # Use timezone-aware datetime (2025 best practice)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            query = select(ClarificationOutcome).where(
                ClarificationOutcome.created_at >= cutoff_date
            )

            result = await db.execute(query)
            outcomes = list(result.scalars().all())

            if not outcomes:
                return {
                    'total': 0,
                    'proceeded': 0,
                    'approved': 0,
                    'rejected': 0,
                    'unknown': 0,
                    'avg_confidence': 0.0,
                    'avg_rounds': 0.0
                }

            proceeded_count = sum(1 for o in outcomes if o.proceeded)
            approved_count = sum(1 for o in outcomes if o.suggestion_approved is True)
            rejected_count = sum(1 for o in outcomes if o.suggestion_approved is False)
            unknown_count = sum(1 for o in outcomes if o.suggestion_approved is None)

            avg_confidence = sum(o.final_confidence for o in outcomes) / len(outcomes)
            avg_rounds = sum(o.rounds for o in outcomes) / len(outcomes)

            return {
                'total': len(outcomes),
                'proceeded': proceeded_count,
                'approved': approved_count,
                'rejected': rejected_count,
                'unknown': unknown_count,
                'avg_confidence': avg_confidence,
                'avg_rounds': avg_rounds,
                'approval_rate': approved_count / proceeded_count if proceeded_count > 0 else 0.0
            }

        except Exception as e:
            logger.error(f"Failed to get outcome statistics: {e}", exc_info=True)
            return {}

