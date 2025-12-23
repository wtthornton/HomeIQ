"""
Metrics Collector

Aggregates and tracks success metrics for Q&A learning features:
- Effectiveness rate: How often Q&A sessions lead to successful automations
- Hit rate: How often user preferences are applied
- Accuracy: How accurate are predictions and question quality

Created: January 2025
Story: Q&A Learning Enhancement Plan
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .qa_outcome_tracker import QAOutcomeTracker
from .question_quality_tracker import QuestionQualityTracker
from .user_preference_learner import UserPreferenceLearner

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects and aggregates success metrics for Q&A learning features.
    
    Tracks:
    - Effectiveness rate: % of Q&A sessions that lead to successful automations
    - Hit rate: % of times preferences are applied vs. skipped
    - Accuracy: Question quality metrics and prediction accuracy
    """

    def __init__(self):
        """Initialize metrics collector with service dependencies."""
        self.outcome_tracker = QAOutcomeTracker()
        self.quality_tracker = QuestionQualityTracker()
        self.preference_learner = UserPreferenceLearner()

    async def get_effectiveness_rate(
        self,
        db: AsyncSession,
        user_id: str | None = None,
        days: int = 30
    ) -> dict[str, Any]:
        """
        Calculate effectiveness rate: % of Q&A sessions leading to successful automations.
        
        Args:
            db: Database session
            user_id: Optional user ID filter
            days: Number of days to look back
            
        Returns:
            Dictionary with effectiveness metrics
        """
        try:
            from ...database.models import QAOutcome, ClarificationSessionDB

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Build query for Q&A outcomes
            query = select(QAOutcome).where(
                QAOutcome.created_at >= cutoff_date
            )

            # Join with clarification sessions if user_id filter
            if user_id:
                query = query.join(
                    ClarificationSessionDB,
                    QAOutcome.session_id == ClarificationSessionDB.session_id
                ).where(
                    ClarificationSessionDB.user_id == user_id
                )

            result = await db.execute(query)
            outcomes = list(result.scalars().all())

            if not outcomes:
                return {
                    'effectiveness_rate': 0.0,
                    'total_sessions': 0,
                    'successful_automations': 0,
                    'abandoned_sessions': 0,
                    'rejected_sessions': 0,
                    'avg_confidence': 0.0,
                    'avg_questions': 0.0,
                    'days': days
                }

            total_sessions = len(outcomes)
            successful = sum(1 for o in outcomes if o.outcome_type == 'automation_created')
            abandoned = sum(1 for o in outcomes if o.outcome_type == 'abandoned')
            rejected = sum(1 for o in outcomes if o.outcome_type == 'rejected')

            effectiveness_rate = (successful / total_sessions) * 100.0 if total_sessions > 0 else 0.0
            avg_confidence = sum(o.confidence_achieved for o in outcomes) / total_sessions
            avg_questions = sum(o.questions_count for o in outcomes) / total_sessions

            return {
                'effectiveness_rate': round(effectiveness_rate, 2),
                'total_sessions': total_sessions,
                'successful_automations': successful,
                'abandoned_sessions': abandoned,
                'rejected_sessions': rejected,
                'avg_confidence': round(avg_confidence, 3),
                'avg_questions': round(avg_questions, 2),
                'days': days
            }

        except Exception as e:
            logger.error(f"Failed to calculate effectiveness rate: {e}", exc_info=True)
            return {
                'effectiveness_rate': 0.0,
                'error': str(e)
            }

    async def get_preference_hit_rate(
        self,
        db: AsyncSession,
        user_id: str | None = None,
        days: int = 30
    ) -> dict[str, Any]:
        """
        Calculate preference hit rate: % of times preferences are applied.
        
        Args:
            db: Database session
            user_id: Optional user ID filter
            days: Number of days to look back
            
        Returns:
            Dictionary with hit rate metrics
        """
        try:
            from ...database.models import UserPreference, ClarificationSessionDB

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Get preferences for user
            if user_id:
                preferences = await self.preference_learner.get_user_preferences(
                    db=db,
                    user_id=user_id,
                    min_consistency=0.9
                )
            else:
                # Get all preferences
                query = select(UserPreference).where(
                    UserPreference.last_used >= cutoff_date
                )
                result = await db.execute(query)
                prefs = result.scalars().all()
                preferences = [
                    {
                        'id': p.id,
                        'user_id': p.user_id,
                        'question_category': p.question_category,
                        'usage_count': p.usage_count,
                        'last_used': p.last_used.isoformat() if p.last_used else None
                    }
                    for p in prefs
                ]

            if not preferences:
                return {
                    'hit_rate': 0.0,
                    'total_preferences': 0,
                    'total_applications': 0,
                    'avg_consistency': 0.0,
                    'days': days
                }

            total_preferences = len(preferences)
            total_applications = sum(p.get('usage_count', 0) for p in preferences)

            # Calculate average consistency
            if user_id:
                query = select(func.avg(UserPreference.consistency_score)).where(
                    UserPreference.user_id == user_id
                )
            else:
                query = select(func.avg(UserPreference.consistency_score))

            result = await db.execute(query)
            avg_consistency = result.scalar() or 0.0

            # Hit rate is based on usage count (higher usage = more hits)
            # Normalize by number of opportunities (sessions with matching questions)
            hit_rate = min(100.0, (total_applications / max(1, total_preferences * 10)) * 100.0)

            return {
                'hit_rate': round(hit_rate, 2),
                'total_preferences': total_preferences,
                'total_applications': total_applications,
                'avg_consistency': round(avg_consistency, 3),
                'days': days
            }

        except Exception as e:
            logger.error(f"Failed to calculate preference hit rate: {e}", exc_info=True)
            return {
                'hit_rate': 0.0,
                'error': str(e)
            }

    async def get_question_accuracy(
        self,
        db: AsyncSession,
        days: int = 30
    ) -> dict[str, Any]:
        """
        Calculate question accuracy: Success rate and quality metrics.
        
        Args:
            db: Database session
            days: Number of days to look back
            
        Returns:
            Dictionary with accuracy metrics
        """
        try:
            from ...database.models import QuestionQualityMetric

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            query = select(QuestionQualityMetric).where(
                QuestionQualityMetric.updated_at >= cutoff_date
            )
            result = await db.execute(query)
            metrics = list(result.scalars().all())

            if not metrics:
                return {
                    'accuracy': 0.0,
                    'total_questions': 0,
                    'avg_success_rate': 0.0,
                    'avg_confidence_impact': 0.0,
                    'total_asked': 0,
                    'total_successful': 0,
                    'confusion_rate': 0.0,
                    'unnecessary_rate': 0.0,
                    'days': days
                }

            total_questions = len(metrics)
            total_asked = sum(m.times_asked for m in metrics)
            total_successful = sum(m.times_led_to_success for m in metrics)
            total_confusing = sum(m.confusion_count for m in metrics)
            total_unnecessary = sum(m.unnecessary_count for m in metrics)

            # Calculate accuracy as overall success rate
            accuracy = (total_successful / total_asked * 100.0) if total_asked > 0 else 0.0

            # Average success rate per question
            avg_success_rate = sum(m.success_rate or 0.0 for m in metrics) / total_questions

            # Average confidence impact
            confidence_impacts = [m.avg_confidence_impact for m in metrics if m.avg_confidence_impact is not None]
            avg_confidence_impact = sum(confidence_impacts) / len(confidence_impacts) if confidence_impacts else 0.0

            # Confusion and unnecessary rates
            confusion_rate = (total_confusing / total_asked * 100.0) if total_asked > 0 else 0.0
            unnecessary_rate = (total_unnecessary / total_asked * 100.0) if total_asked > 0 else 0.0

            return {
                'accuracy': round(accuracy, 2),
                'total_questions': total_questions,
                'avg_success_rate': round(avg_success_rate, 3),
                'avg_confidence_impact': round(avg_confidence_impact, 3),
                'total_asked': total_asked,
                'total_successful': total_successful,
                'confusion_rate': round(confusion_rate, 2),
                'unnecessary_rate': round(unnecessary_rate, 2),
                'days': days
            }

        except Exception as e:
            logger.error(f"Failed to calculate question accuracy: {e}", exc_info=True)
            return {
                'accuracy': 0.0,
                'error': str(e)
            }

    async def get_comprehensive_metrics(
        self,
        db: AsyncSession,
        user_id: str | None = None,
        days: int = 30
    ) -> dict[str, Any]:
        """
        Get comprehensive metrics combining all learning features.
        
        Args:
            db: Database session
            user_id: Optional user ID filter
            days: Number of days to look back
            
        Returns:
            Dictionary with all metrics
        """
        try:
            effectiveness = await self.get_effectiveness_rate(db, user_id, days)
            hit_rate = await self.get_preference_hit_rate(db, user_id, days)
            accuracy = await self.get_question_accuracy(db, days)

            # Calculate overall learning score (weighted average)
            effectiveness_weight = 0.5
            hit_rate_weight = 0.2
            accuracy_weight = 0.3

            overall_score = (
                (effectiveness.get('effectiveness_rate', 0.0) * effectiveness_weight) +
                (hit_rate.get('hit_rate', 0.0) * hit_rate_weight) +
                (accuracy.get('accuracy', 0.0) * accuracy_weight)
            )

            return {
                'overall_score': round(overall_score, 2),
                'effectiveness': effectiveness,
                'hit_rate': hit_rate,
                'accuracy': accuracy,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'user_id': user_id,
                'days': days
            }

        except Exception as e:
            logger.error(f"Failed to get comprehensive metrics: {e}", exc_info=True)
            return {
                'overall_score': 0.0,
                'error': str(e)
            }

    async def get_trend_metrics(
        self,
        db: AsyncSession,
        user_id: str | None = None,
        days: int = 30,
        interval_days: int = 7
    ) -> dict[str, Any]:
        """
        Get trend metrics over time intervals.
        
        Args:
            db: Database session
            user_id: Optional user ID filter
            days: Total days to look back
            interval_days: Size of each interval
            
        Returns:
            Dictionary with trend data
        """
        try:
            intervals = []
            current_date = datetime.now(timezone.utc)

            for i in range(0, days, interval_days):
                interval_start = current_date - timedelta(days=i + interval_days)
                interval_end = current_date - timedelta(days=i)

                # Get metrics for this interval
                interval_effectiveness = await self.get_effectiveness_rate(
                    db, user_id, interval_days
                )
                interval_accuracy = await self.get_question_accuracy(db, interval_days)

                intervals.append({
                    'start': interval_start.isoformat(),
                    'end': interval_end.isoformat(),
                    'effectiveness_rate': interval_effectiveness.get('effectiveness_rate', 0.0),
                    'accuracy': interval_accuracy.get('accuracy', 0.0),
                    'total_sessions': interval_effectiveness.get('total_sessions', 0)
                })

            return {
                'intervals': intervals,
                'interval_days': interval_days,
                'total_days': days,
                'user_id': user_id
            }

        except Exception as e:
            logger.error(f"Failed to get trend metrics: {e}", exc_info=True)
            return {
                'intervals': [],
                'error': str(e)
            }

