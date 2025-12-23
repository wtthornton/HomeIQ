"""
Question Quality Tracker

Tracks effectiveness of individual questions to improve question generation.
Measures success rate, confusion rate, and confidence impact.

2025 Best Practices:
- Full type hints (PEP 484/526)
- Async/await for all database operations
- SQLAlchemy 2.0+ async patterns
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class QuestionQualityTracker:
    """
    Tracks question effectiveness metrics.
    
    Measures:
    - Success rate (questions that lead to approved automations)
    - Confusion rate (user marked as confusing)
    - Necessity rate (user skipped or marked unnecessary)
    - Confidence impact (average confidence increase after answer)
    """

    async def track_question_quality(
        self,
        db: AsyncSession,
        question_id: str,
        question_text: str,
        question_category: str | None = None,
        outcome: str | None = None,  # 'success', 'confusion', 'unnecessary'
        confidence_impact: float | None = None
    ) -> bool:
        """
        Track question quality metrics.
        
        Args:
            db: Database session
            question_id: Unique question identifier
            question_text: Question text
            question_category: Optional category
            outcome: Optional outcome ('success', 'confusion', 'unnecessary')
            confidence_impact: Optional confidence increase after answer
            
        Returns:
            True if tracked successfully, False otherwise
        """
        try:
            from ...database.models import QuestionQualityMetric, SystemSettings

            # Check if learning is enabled
            settings_result = await db.execute(select(SystemSettings).limit(1))
            settings = settings_result.scalar_one_or_none()
            if settings and not getattr(settings, 'enable_qa_learning', True):
                logger.debug("Q&A learning disabled in settings")
                return False

            # Find or create metric
            query = select(QuestionQualityMetric).where(
                QuestionQualityMetric.question_id == question_id
            )

            result = await db.execute(query)
            metric = result.scalar_one_or_none()

            if metric:
                # Update existing metric
                metric.times_asked += 1
                metric.updated_at = datetime.now(timezone.utc)

                if outcome == 'success':
                    metric.times_led_to_success += 1
                elif outcome == 'confusion':
                    metric.confusion_count += 1
                elif outcome == 'unnecessary':
                    metric.unnecessary_count += 1

                if confidence_impact is not None:
                    # Update average confidence impact
                    if metric.avg_confidence_impact is None:
                        metric.avg_confidence_impact = confidence_impact
                    else:
                        # Weighted average
                        total_impacts = metric.times_asked - 1
                        metric.avg_confidence_impact = (
                            (metric.avg_confidence_impact * total_impacts + confidence_impact) /
                            metric.times_asked
                        )

                # Recalculate success rate
                if metric.times_asked > 0:
                    metric.success_rate = metric.times_led_to_success / metric.times_asked

                await db.commit()
                await db.refresh(metric)

                logger.debug(
                    f"Updated question quality: question_id={question_id}, "
                    f"success_rate={metric.success_rate:.2f}, times_asked={metric.times_asked}"
                )
            else:
                # Create new metric
                success_rate = 1.0 if outcome == 'success' else 0.0

                metric = QuestionQualityMetric(
                    question_id=question_id,
                    question_text=question_text,
                    question_category=question_category,
                    times_asked=1,
                    times_led_to_success=1 if outcome == 'success' else 0,
                    confusion_count=1 if outcome == 'confusion' else 0,
                    unnecessary_count=1 if outcome == 'unnecessary' else 0,
                    avg_confidence_impact=confidence_impact,
                    success_rate=success_rate,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )

                db.add(metric)
                await db.commit()
                await db.refresh(metric)

                logger.debug(f"Created question quality metric: question_id={question_id}")

            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to track question quality: {e}", exc_info=True)
            return False

    async def update_question_quality(
        self,
        db: AsyncSession,
        question_id: str,
        outcome: str,  # 'success', 'confusion', 'unnecessary'
        confidence_impact: float | None = None
    ) -> bool:
        """
        Update question quality from outcome.
        
        Args:
            db: Database session
            question_id: Question identifier
            outcome: Outcome type
            confidence_impact: Optional confidence impact
            
        Returns:
            True if updated successfully, False otherwise
        """
        return await self.track_question_quality(
            db=db,
            question_id=question_id,
            question_text="",  # Not needed for update
            outcome=outcome,
            confidence_impact=confidence_impact
        )

    async def get_question_quality(
        self,
        db: AsyncSession,
        question_id: str
    ) -> dict[str, Any] | None:
        """
        Get quality metrics for a question.
        
        Args:
            db: Database session
            question_id: Question identifier
            
        Returns:
            Quality metrics dictionary or None if not found
        """
        try:
            from ...database.models import QuestionQualityMetric

            query = select(QuestionQualityMetric).where(
                QuestionQualityMetric.question_id == question_id
            )

            result = await db.execute(query)
            metric = result.scalar_one_or_none()

            if not metric:
                return None

            return {
                'question_id': metric.question_id,
                'question_text': metric.question_text,
                'question_category': metric.question_category,
                'times_asked': metric.times_asked,
                'times_led_to_success': metric.times_led_to_success,
                'confusion_count': metric.confusion_count,
                'unnecessary_count': metric.unnecessary_count,
                'avg_confidence_impact': metric.avg_confidence_impact,
                'success_rate': metric.success_rate,
                'created_at': metric.created_at.isoformat() if metric.created_at else None,
                'updated_at': metric.updated_at.isoformat() if metric.updated_at else None
            }

        except Exception as e:
            logger.error(f"Failed to get question quality: {e}", exc_info=True)
            return None

    async def get_high_quality_questions(
        self,
        db: AsyncSession,
        min_success_rate: float = 0.8,
        min_times_asked: int = 5,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get high-quality questions for learning.
        
        Returns questions with high success rates for use in improving
        question generation.
        
        Args:
            db: Database session
            min_success_rate: Minimum success rate (0.0-1.0)
            min_times_asked: Minimum times asked
            limit: Maximum number to return
            
        Returns:
            List of high-quality question metrics
        """
        try:
            from ...database.models import QuestionQualityMetric

            query = select(QuestionQualityMetric).where(
                QuestionQualityMetric.success_rate >= min_success_rate,
                QuestionQualityMetric.times_asked >= min_times_asked
            ).order_by(
                QuestionQualityMetric.success_rate.desc(),
                QuestionQualityMetric.times_asked.desc()
            ).limit(limit)

            result = await db.execute(query)
            metrics = list(result.scalars().all())

            return [
                {
                    'question_id': m.question_id,
                    'question_text': m.question_text,
                    'question_category': m.question_category,
                    'success_rate': m.success_rate,
                    'times_asked': m.times_asked,
                    'avg_confidence_impact': m.avg_confidence_impact
                }
                for m in metrics
            ]

        except Exception as e:
            logger.error(f"Failed to get high-quality questions: {e}", exc_info=True)
            return []

    async def get_question_quality_statistics(
        self,
        db: AsyncSession
    ) -> dict[str, Any]:
        """
        Get overall question quality statistics.
        
        Args:
            db: Database session
            
        Returns:
            Statistics dictionary
        """
        try:
            from ...database.models import QuestionQualityMetric
            from sqlalchemy import func

            # Get all metrics
            query = select(QuestionQualityMetric)
            result = await db.execute(query)
            metrics = list(result.scalars().all())

            if not metrics:
                return {
                    'total_questions': 0,
                    'avg_success_rate': 0.0,
                    'avg_times_asked': 0.0,
                    'total_asked': 0,
                    'total_successful': 0,
                    'total_confusing': 0,
                    'total_unnecessary': 0
                }

            total_questions = len(metrics)
            avg_success_rate = sum(m.success_rate or 0.0 for m in metrics) / total_questions
            avg_times_asked = sum(m.times_asked for m in metrics) / total_questions
            total_asked = sum(m.times_asked for m in metrics)
            total_successful = sum(m.times_led_to_success for m in metrics)
            total_confusing = sum(m.confusion_count for m in metrics)
            total_unnecessary = sum(m.unnecessary_count for m in metrics)

            return {
                'total_questions': total_questions,
                'avg_success_rate': avg_success_rate,
                'avg_times_asked': avg_times_asked,
                'total_asked': total_asked,
                'total_successful': total_successful,
                'total_confusing': total_confusing,
                'total_unnecessary': total_unnecessary,
                'overall_success_rate': total_successful / total_asked if total_asked > 0 else 0.0
            }

        except Exception as e:
            logger.error(f"Failed to get question quality statistics: {e}", exc_info=True)
            return {}


