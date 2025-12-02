"""
Pattern Quality Reporting

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.9: Quality Metrics & Reporting

Generate comprehensive quality reports.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .metrics import PatternQualityMetrics
from database.models import Pattern, UserFeedback

logger = logging.getLogger(__name__)


class QualityReporter:
    """
    Generate quality reports.
    
    Provides reports for:
    - Model performance over time
    - User feedback statistics
    - Quality improvement trends
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize quality reporter.
        
        Args:
            db: Database session
        """
        self.db = db
        self.metrics = PatternQualityMetrics()
    
    async def generate_model_performance_report(
        self,
        days: int = 30
    ) -> dict[str, Any]:
        """
        Generate model performance report.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Model performance report
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get patterns with quality scores
        stmt = select(Pattern).where(
            Pattern.created_at >= cutoff_date
        )
        result = await self.db.execute(stmt)
        patterns = result.scalars().all()
        
        if not patterns:
            return {
                'period_days': days,
                'patterns_analyzed': 0,
                'metrics': {}
            }
        
        # Extract quality scores and labels (from feedback)
        quality_scores = []
        labels = []
        
        for pattern in patterns:
            # Use quality_score if available, otherwise use confidence
            quality_score = getattr(pattern, 'quality_score', None)
            if quality_score is None:
                quality_score = pattern.confidence
            
            quality_scores.append(quality_score)
            
            # Get label from feedback (1=approved, 0=rejected)
            # For now, use pattern.deprecated as negative label
            label = 0 if pattern.deprecated else 1
            labels.append(label)
        
        # Calculate metrics
        metrics = self.metrics.calculate_comprehensive_metrics(
            quality_scores,
            labels,
            threshold=0.7
        )
        
        return {
            'period_days': days,
            'patterns_analyzed': len(patterns),
            'metrics': metrics,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
    
    async def generate_feedback_statistics(
        self,
        days: int = 30
    ) -> dict[str, Any]:
        """
        Generate user feedback statistics.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Feedback statistics report
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get feedback
        stmt = select(UserFeedback).where(
            UserFeedback.created_at >= cutoff_date
        )
        result = await self.db.execute(stmt)
        feedbacks = result.scalars().all()
        
        if not feedbacks:
            return {
                'period_days': days,
                'total_feedback': 0,
                'statistics': {}
            }
        
        # Count by action
        action_counts = {}
        for feedback in feedbacks:
            action = feedback.action
            action_counts[action] = action_counts.get(action, 0) + 1
        
        # Calculate approval rate
        total = len(feedbacks)
        approvals = action_counts.get('approved', 0)
        rejections = action_counts.get('rejected', 0)
        modifications = action_counts.get('modified', 0)
        
        approval_rate = approvals / total if total > 0 else 0.0
        
        return {
            'period_days': days,
            'total_feedback': total,
            'statistics': {
                'approvals': approvals,
                'rejections': rejections,
                'modifications': modifications,
                'approval_rate': approval_rate,
                'action_distribution': action_counts
            },
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
    
    async def generate_quality_improvement_report(
        self,
        days: int = 30,
        window_days: int = 7
    ) -> dict[str, Any]:
        """
        Generate quality improvement report over time.
        
        Args:
            days: Total number of days to analyze
            window_days: Window size for trend calculation
        
        Returns:
            Quality improvement report
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get patterns grouped by time windows
        windows = []
        current_date = cutoff_date
        
        while current_date < datetime.now(timezone.utc):
            window_end = current_date + timedelta(days=window_days)
            
            stmt = select(Pattern).where(
                Pattern.created_at >= current_date,
                Pattern.created_at < window_end
            )
            result = await self.db.execute(stmt)
            patterns = result.scalars().all()
            
            if patterns:
                quality_scores = [
                    getattr(p, 'quality_score', p.confidence)
                    for p in patterns
                ]
                
                avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
                high_quality_count = sum(1 for s in quality_scores if s >= 0.7)
                
                windows.append({
                    'window_start': current_date.isoformat(),
                    'window_end': window_end.isoformat(),
                    'pattern_count': len(patterns),
                    'avg_quality': avg_quality,
                    'high_quality_count': high_quality_count,
                    'high_quality_rate': high_quality_count / len(patterns) if patterns else 0.0
                })
            
            current_date = window_end
        
        # Calculate trend
        if len(windows) >= 2:
            first_avg = windows[0]['avg_quality']
            last_avg = windows[-1]['avg_quality']
            trend = last_avg - first_avg
            trend_pct = (trend / first_avg * 100) if first_avg > 0 else 0.0
        else:
            trend = 0.0
            trend_pct = 0.0
        
        return {
            'period_days': days,
            'window_days': window_days,
            'windows': windows,
            'trend': {
                'absolute': trend,
                'percentage': trend_pct,
                'improving': trend > 0
            },
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
    
    async def generate_comprehensive_report(
        self,
        days: int = 30
    ) -> dict[str, Any]:
        """
        Generate comprehensive quality report.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Comprehensive report with all metrics
        """
        model_performance = await self.generate_model_performance_report(days)
        feedback_stats = await self.generate_feedback_statistics(days)
        quality_improvement = await self.generate_quality_improvement_report(days)
        
        return {
            'report_period_days': days,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'model_performance': model_performance,
            'feedback_statistics': feedback_stats,
            'quality_improvement': quality_improvement
        }

