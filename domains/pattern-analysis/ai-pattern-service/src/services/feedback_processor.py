"""Feedback processing service. Story 40.5."""
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import PatternTrainingData

logger = logging.getLogger(__name__)

# Confidence adjustments
ACCEPT_BOOST = 0.1
REJECT_PENALTY = 0.2
CONFIDENCE_MIN = 0.1
CONFIDENCE_MAX = 0.95
REJECTION_SUPPRESSION_DAYS = 30


class FeedbackProcessor:
    """Processes user feedback to improve pattern confidence. Story 40.5."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def apply_feedback(self, pattern_id: int, action: str) -> None:
        """Apply confidence adjustment based on feedback."""
        result = await self.db.execute(
            select(PatternTrainingData).where(PatternTrainingData.id == pattern_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            return

        old_confidence = record.confidence
        if action == "accept":
            record.confidence = min(CONFIDENCE_MAX, old_confidence + ACCEPT_BOOST)
        elif action == "reject":
            record.confidence = max(CONFIDENCE_MIN, old_confidence - REJECT_PENALTY)

        await self.db.flush()
        logger.info(
            "Feedback on pattern %d: %s (confidence %.2f -> %.2f)",
            pattern_id,
            action,
            old_confidence,
            record.confidence,
        )

    async def is_suppressed(self, pattern_type: str, device_id: str) -> bool:
        """Check if a pattern is suppressed due to recent rejection."""
        cutoff = datetime.now(UTC) - timedelta(days=REJECTION_SUPPRESSION_DAYS)
        stmt = (
            select(func.count())
            .select_from(PatternTrainingData)
            .where(
                PatternTrainingData.pattern_type == pattern_type,
                PatternTrainingData.device_id == device_id,
                PatternTrainingData.user_action == "reject",
                PatternTrainingData.user_feedback_at >= cutoff,
            )
        )
        result = await self.db.execute(stmt)
        count = result.scalar() or 0
        return count > 0

    async def get_acceptance_stats(self) -> list[dict[str, Any]]:
        """Get acceptance rate per pattern type."""
        stmt = (
            select(
                PatternTrainingData.pattern_type,
                func.count().label("total"),
                func.count()
                .filter(PatternTrainingData.user_action == "accept")
                .label("accepted"),
                func.count()
                .filter(PatternTrainingData.user_action == "reject")
                .label("rejected"),
                func.count()
                .filter(PatternTrainingData.user_action == "ignore")
                .label("ignored"),
            )
            .where(PatternTrainingData.user_action.isnot(None))
            .group_by(PatternTrainingData.pattern_type)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            {
                "pattern_type": row.pattern_type,
                "total": row.total,
                "accepted": row.accepted,
                "rejected": row.rejected,
                "ignored": row.ignored,
                "acceptance_rate": row.accepted / row.total if row.total > 0 else 0.0,
            }
            for row in rows
        ]
