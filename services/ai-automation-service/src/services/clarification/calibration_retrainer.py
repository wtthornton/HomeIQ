"""
Calibration Model Retraining

Periodic retraining of clarification confidence calibration models.
Can be run as a scheduled job (weekly/monthly) or on-demand.

2025 Best Practices:
- Full type hints (PEP 484/526)
- Async/await for database operations
- SQLAlchemy 2.0+ async patterns
"""

import logging
from typing import Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from .confidence_calibrator import ClarificationConfidenceCalibrator
from ...database.crud import get_clarification_confidence_feedback

logger = logging.getLogger(__name__)


async def retrain_calibration_model(
    db: AsyncSession,
    calibrator: Optional[ClarificationConfidenceCalibrator] = None,
    min_samples: int = 10,
    days_back: int = 30
) -> bool:
    """
    Retrain clarification confidence calibration model from database feedback.
    
    Args:
        db: Database session
        calibrator: Optional calibrator instance (creates new one if not provided)
        min_samples: Minimum number of samples required for training
        days_back: Number of days to look back for feedback data
        
    Returns:
        True if retraining was successful, False otherwise
    """
    try:
        if calibrator is None:
            calibrator = ClarificationConfidenceCalibrator()
            # Try to load existing model
            calibrator.load()
        
        # Get feedback from database
        feedback_records = await get_clarification_confidence_feedback(db, limit=10000)
        
        if len(feedback_records) < min_samples:
            logger.warning(
                f"Insufficient feedback data for retraining: "
                f"{len(feedback_records)} < {min_samples} samples"
            )
            return False
        
        # Add all feedback to calibrator
        for record in feedback_records:
            calibrator.add_feedback(
                raw_confidence=record.raw_confidence,
                actually_proceeded=record.proceeded,
                suggestion_approved=record.suggestion_approved,
                ambiguity_count=record.ambiguity_count,
                critical_ambiguity_count=record.critical_ambiguity_count,
                rounds=record.rounds,
                answer_count=record.answer_count,
                save_immediately=False  # Don't save after each addition
            )
        
        # Train and save
        calibrator.train(min_samples=min_samples)
        calibrator.save()
        
        stats = calibrator.get_stats()
        logger.info(
            f"✅ Calibration model retrained successfully: "
            f"{stats['training_samples']} samples, "
            f"{stats['positive_feedback']} positive, "
            f"{stats['negative_feedback']} negative"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to retrain calibration model: {e}", exc_info=True)
        return False


async def should_retrain_calibration(
    db: AsyncSession,
    last_retrain_date: Optional[datetime] = None,
    retrain_interval_days: int = 7,
    min_new_samples: int = 50
) -> bool:
    """
    Check if calibration model should be retrained.
    
    Args:
        db: Database session
        last_retrain_date: Date of last retraining (None if never retrained)
        retrain_interval_days: Minimum days between retraining
        min_new_samples: Minimum new samples since last retrain
        
    Returns:
        True if retraining is recommended
    """
    try:
        # Check time-based retraining
        if last_retrain_date is None:
            return True  # Never retrained, should retrain
        
        # Use timezone-aware datetime (2025 best practice)
        days_since_retrain = (datetime.now(timezone.utc) - last_retrain_date).days
        if days_since_retrain >= retrain_interval_days:
            return True
        
        # Check sample-based retraining
        # Use timezone-aware datetime (2025 best practice)
        cutoff_date = last_retrain_date if last_retrain_date else datetime.now(timezone.utc) - timedelta(days=30)
        feedback_records = await get_clarification_confidence_feedback(db, limit=10000)
        
        new_samples = sum(
            1 for record in feedback_records
            if record.created_at >= cutoff_date
        )
        
        if new_samples >= min_new_samples:
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Failed to check retrain condition: {e}", exc_info=True)
        return False

