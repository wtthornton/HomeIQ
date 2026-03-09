"""Training data collection and export service. Story 40.1."""
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import PatternTrainingData

logger = logging.getLogger(__name__)

MIN_TRAINING_DAYS = 7
RETENTION_DAYS = 90


class TrainingDataService:
    """Collects and serves training data for ML pattern detectors."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_detection_run(
        self,
        patterns: list[dict[str, Any]],
        events_summary: dict[str, Any],
        run_id: str | None = None,
    ) -> int:
        """Record patterns from a detection run as training data."""
        run_id = run_id or str(uuid.uuid4())
        count = 0
        for pattern in patterns:
            record = PatternTrainingData(
                run_id=run_id,
                pattern_type=pattern.get("pattern_type", "unknown"),
                device_id=pattern.get("device_id"),
                raw_events_summary=events_summary,
                detected_pattern=pattern,
                confidence=pattern.get("confidence", 0.0),
            )
            self.db.add(record)
            count += 1
        await self.db.flush()
        logger.info("Recorded %d training samples for run %s", count, run_id)
        return count

    async def record_feedback(
        self, pattern_id: int, action: str
    ) -> bool:
        """Record user feedback on a pattern."""
        result = await self.db.execute(
            select(PatternTrainingData).where(PatternTrainingData.id == pattern_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            return False
        record.user_action = action
        record.user_feedback_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def get_training_data(
        self,
        pattern_type: str,
        min_confidence: float = 0.0,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        """Get training data for a specific pattern type."""
        stmt = (
            select(PatternTrainingData)
            .where(
                PatternTrainingData.pattern_type == pattern_type,
                PatternTrainingData.confidence >= min_confidence,
            )
            .order_by(PatternTrainingData.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "id": r.id,
                "run_id": r.run_id,
                "pattern_type": r.pattern_type,
                "device_id": r.device_id,
                "detected_pattern": r.detected_pattern,
                "user_action": r.user_action,
                "confidence": r.confidence,
                "ml_model_version": r.ml_model_version,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]

    async def has_sufficient_data(self, pattern_type: str) -> bool:
        """Check if we have enough training data (>= MIN_TRAINING_DAYS of runs)."""
        cutoff = datetime.now(UTC) - timedelta(days=MIN_TRAINING_DAYS)
        stmt = select(func.count()).select_from(PatternTrainingData).where(
            PatternTrainingData.pattern_type == pattern_type,
            PatternTrainingData.created_at >= cutoff,
        )
        result = await self.db.execute(stmt)
        count = result.scalar() or 0
        return count >= MIN_TRAINING_DAYS  # At least 1 record per day

    async def cleanup_old_data(self) -> int:
        """Remove training data older than RETENTION_DAYS."""
        cutoff = datetime.now(UTC) - timedelta(days=RETENTION_DAYS)
        stmt = delete(PatternTrainingData).where(
            PatternTrainingData.created_at < cutoff
        )
        result = await self.db.execute(stmt)
        deleted = result.rowcount
        if deleted:
            logger.info(
                "Cleaned up %d training records older than %d days",
                deleted, RETENTION_DAYS,
            )
        return deleted

    async def export_for_training(
        self, pattern_type: str
    ) -> list[dict[str, Any]]:
        """Export training data with feedback labels for offline model training."""
        stmt = (
            select(PatternTrainingData)
            .where(
                PatternTrainingData.pattern_type == pattern_type,
                PatternTrainingData.user_action.isnot(None),
            )
            .order_by(PatternTrainingData.created_at)
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "detected_pattern": r.detected_pattern,
                "user_action": r.user_action,
                "confidence": r.confidence,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
