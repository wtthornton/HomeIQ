"""
Blueprint Analytics Service

Tracks blueprint and automation metrics to measure progress toward target goals:
- Automation Adoption Rate: 30%
- Automation Success Rate: 85%
- Pattern Quality: 90%
- User Satisfaction: 4.0+
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class DeploymentMetric:
    """Represents a single deployment event."""
    
    blueprint_id: str | None
    synergy_id: str | None
    automation_id: str
    deployed_at: datetime
    deployed_by: str = "system"
    source: str = "synergy"  # synergy, blueprint, manual
    
    # Outcome tracking (updated after deployment)
    success: bool | None = None
    error_message: str | None = None
    execution_count: int = 0
    failure_count: int = 0
    last_executed_at: datetime | None = None
    
    # User feedback
    user_rating: float | None = None
    user_feedback: str | None = None
    rated_at: datetime | None = None


@dataclass
class AnalyticsSummary:
    """Summary of analytics metrics for a time period."""
    
    period_start: datetime
    period_end: datetime
    
    # Adoption metrics
    total_synergies: int = 0
    synergies_deployed: int = 0
    adoption_rate: float = 0.0  # Target: 30%
    
    # Success metrics
    total_executions: int = 0
    successful_executions: int = 0
    success_rate: float = 0.0  # Target: 85%
    
    # Pattern quality
    patterns_used: int = 0
    patterns_successful: int = 0
    pattern_quality: float = 0.0  # Target: 90%
    
    # User satisfaction
    total_ratings: int = 0
    average_rating: float = 0.0  # Target: 4.0+
    
    # Blueprint-specific
    blueprint_deployments: int = 0
    yaml_fallback_deployments: int = 0
    blueprint_utilization_rate: float = 0.0


class BlueprintAnalytics:
    """
    Central analytics service for tracking blueprint and automation metrics.
    
    Implements the metrics tracking required by RECOMMENDATIONS_FEASIBILITY_ANALYSIS.md
    to achieve Month 3-6 targets.
    """
    
    def __init__(self, retention_days: int = 90):
        """
        Initialize analytics service.
        
        Args:
            retention_days: Number of days to retain detailed metrics
        """
        self.retention_days = retention_days
        self._deployments: list[DeploymentMetric] = []
        self._synergy_counts: dict[str, int] = defaultdict(int)  # synergy_id -> view count
        self._pattern_outcomes: dict[str, list[bool]] = defaultdict(list)  # pattern_id -> [success]
        
        logger.info(f"BlueprintAnalytics initialized with {retention_days} day retention")
    
    def record_deployment(
        self,
        automation_id: str,
        blueprint_id: str | None = None,
        synergy_id: str | None = None,
        source: str = "synergy",
        deployed_by: str = "system",
    ) -> DeploymentMetric:
        """
        Record a new automation deployment.
        
        Args:
            automation_id: Home Assistant automation entity ID
            blueprint_id: Optional blueprint ID if deployed from blueprint
            synergy_id: Optional synergy ID that triggered deployment
            source: Deployment source (synergy, blueprint, manual)
            deployed_by: User or system that triggered deployment
            
        Returns:
            DeploymentMetric for the deployment
        """
        metric = DeploymentMetric(
            blueprint_id=blueprint_id,
            synergy_id=synergy_id,
            automation_id=automation_id,
            deployed_at=datetime.utcnow(),
            deployed_by=deployed_by,
            source=source,
        )
        self._deployments.append(metric)
        
        # Update synergy deployment count
        if synergy_id:
            self._synergy_counts[synergy_id] += 1
        
        logger.info(
            f"Recorded deployment: automation={automation_id}, "
            f"blueprint={blueprint_id}, synergy={synergy_id}, source={source}"
        )
        return metric
    
    def record_execution(
        self,
        automation_id: str,
        success: bool,
        error_message: str | None = None,
    ) -> None:
        """
        Record an automation execution result.
        
        Args:
            automation_id: Home Assistant automation entity ID
            success: Whether execution was successful
            error_message: Error message if failed
        """
        # Find deployment metric for this automation
        metric = self._find_deployment(automation_id)
        if metric:
            metric.execution_count += 1
            if not success:
                metric.failure_count += 1
            metric.success = success
            metric.error_message = error_message
            metric.last_executed_at = datetime.utcnow()
            
            logger.debug(
                f"Recorded execution: automation={automation_id}, "
                f"success={success}, executions={metric.execution_count}"
            )
    
    def record_rating(
        self,
        automation_id: str,
        rating: float,
        feedback: str | None = None,
    ) -> None:
        """
        Record user rating for a deployment.
        
        Args:
            automation_id: Home Assistant automation entity ID
            rating: User rating (1-5 scale)
            feedback: Optional text feedback
        """
        metric = self._find_deployment(automation_id)
        if metric:
            metric.user_rating = rating
            metric.user_feedback = feedback
            metric.rated_at = datetime.utcnow()
            
            logger.info(
                f"Recorded rating: automation={automation_id}, rating={rating}"
            )
    
    def record_pattern_outcome(
        self,
        pattern_id: str,
        success: bool,
    ) -> None:
        """
        Record whether a pattern led to a successful automation.
        
        Args:
            pattern_id: Pattern identifier
            success: Whether automation from pattern was successful
        """
        self._pattern_outcomes[pattern_id].append(success)
    
    def get_summary(
        self,
        days: int = 30,
        total_synergies: int | None = None,
    ) -> AnalyticsSummary:
        """
        Get analytics summary for the specified period.
        
        Args:
            days: Number of days to analyze
            total_synergies: Total synergies generated (for adoption rate)
            
        Returns:
            AnalyticsSummary with calculated metrics
        """
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=days)
        
        # Filter deployments within period
        period_deployments = [
            d for d in self._deployments
            if d.deployed_at >= period_start
        ]
        
        # Calculate adoption rate
        synergies_deployed = len([d for d in period_deployments if d.synergy_id])
        adoption_rate = (
            synergies_deployed / total_synergies * 100
            if total_synergies and total_synergies > 0
            else 0.0
        )
        
        # Calculate success rate
        deployments_with_executions = [d for d in period_deployments if d.execution_count > 0]
        total_executions = sum(d.execution_count for d in deployments_with_executions)
        total_failures = sum(d.failure_count for d in deployments_with_executions)
        success_rate = (
            (total_executions - total_failures) / total_executions * 100
            if total_executions > 0
            else 0.0
        )
        
        # Calculate pattern quality
        all_outcomes = []
        for outcomes in self._pattern_outcomes.values():
            all_outcomes.extend(outcomes)
        pattern_quality = (
            sum(all_outcomes) / len(all_outcomes) * 100
            if all_outcomes
            else 0.0
        )
        
        # Calculate user satisfaction
        rated_deployments = [d for d in period_deployments if d.user_rating is not None]
        average_rating = (
            sum(d.user_rating for d in rated_deployments) / len(rated_deployments)
            if rated_deployments
            else 0.0
        )
        
        # Calculate blueprint utilization
        blueprint_deployments = len([d for d in period_deployments if d.blueprint_id])
        yaml_fallback = len(period_deployments) - blueprint_deployments
        blueprint_utilization = (
            blueprint_deployments / len(period_deployments) * 100
            if period_deployments
            else 0.0
        )
        
        summary = AnalyticsSummary(
            period_start=period_start,
            period_end=period_end,
            total_synergies=total_synergies or 0,
            synergies_deployed=synergies_deployed,
            adoption_rate=adoption_rate,
            total_executions=total_executions,
            successful_executions=total_executions - total_failures,
            success_rate=success_rate,
            patterns_used=len(self._pattern_outcomes),
            patterns_successful=sum(1 for outcomes in self._pattern_outcomes.values() if all(outcomes)),
            pattern_quality=pattern_quality,
            total_ratings=len(rated_deployments),
            average_rating=average_rating,
            blueprint_deployments=blueprint_deployments,
            yaml_fallback_deployments=yaml_fallback,
            blueprint_utilization_rate=blueprint_utilization,
        )
        
        logger.info(
            f"Analytics summary: adoption={adoption_rate:.1f}% (target 30%), "
            f"success={success_rate:.1f}% (target 85%), "
            f"pattern_quality={pattern_quality:.1f}% (target 90%), "
            f"satisfaction={average_rating:.1f} (target 4.0+)"
        )
        
        return summary
    
    def get_target_progress(self, total_synergies: int = 0) -> dict[str, Any]:
        """
        Get progress toward target metrics from RECOMMENDATIONS_FEASIBILITY_ANALYSIS.md.
        
        Args:
            total_synergies: Total synergies generated
            
        Returns:
            Dictionary with target vs actual for each metric
        """
        summary = self.get_summary(days=30, total_synergies=total_synergies)
        
        return {
            "adoption_rate": {
                "target": 30.0,
                "actual": summary.adoption_rate,
                "achieved": summary.adoption_rate >= 30.0,
                "progress_pct": min(100, summary.adoption_rate / 30.0 * 100),
            },
            "success_rate": {
                "target": 85.0,
                "actual": summary.success_rate,
                "achieved": summary.success_rate >= 85.0,
                "progress_pct": min(100, summary.success_rate / 85.0 * 100),
            },
            "pattern_quality": {
                "target": 90.0,
                "actual": summary.pattern_quality,
                "achieved": summary.pattern_quality >= 90.0,
                "progress_pct": min(100, summary.pattern_quality / 90.0 * 100),
            },
            "user_satisfaction": {
                "target": 4.0,
                "actual": summary.average_rating,
                "achieved": summary.average_rating >= 4.0,
                "progress_pct": min(100, summary.average_rating / 4.0 * 100),
            },
        }
    
    def get_trending_blueprints(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get most deployed blueprints.
        
        Args:
            limit: Maximum number of blueprints to return
            
        Returns:
            List of trending blueprints with deployment counts
        """
        blueprint_counts: dict[str, int] = defaultdict(int)
        blueprint_success: dict[str, list[bool]] = defaultdict(list)
        blueprint_ratings: dict[str, list[float]] = defaultdict(list)
        
        for deployment in self._deployments:
            if deployment.blueprint_id:
                blueprint_counts[deployment.blueprint_id] += 1
                if deployment.success is not None:
                    blueprint_success[deployment.blueprint_id].append(deployment.success)
                if deployment.user_rating is not None:
                    blueprint_ratings[deployment.blueprint_id].append(deployment.user_rating)
        
        trending = []
        for blueprint_id, count in sorted(
            blueprint_counts.items(), key=lambda x: x[1], reverse=True
        )[:limit]:
            successes = blueprint_success.get(blueprint_id, [])
            ratings = blueprint_ratings.get(blueprint_id, [])
            
            trending.append({
                "blueprint_id": blueprint_id,
                "deployment_count": count,
                "success_rate": (
                    sum(successes) / len(successes) * 100 if successes else None
                ),
                "average_rating": (
                    sum(ratings) / len(ratings) if ratings else None
                ),
            })
        
        return trending
    
    def cleanup_old_metrics(self) -> int:
        """
        Remove metrics older than retention period.
        
        Returns:
            Number of metrics removed
        """
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
        original_count = len(self._deployments)
        
        self._deployments = [
            d for d in self._deployments
            if d.deployed_at >= cutoff
        ]
        
        removed = original_count - len(self._deployments)
        if removed > 0:
            logger.info(f"Cleaned up {removed} old deployment metrics")
        
        return removed
    
    def _find_deployment(self, automation_id: str) -> DeploymentMetric | None:
        """Find deployment metric by automation ID."""
        for deployment in reversed(self._deployments):
            if deployment.automation_id == automation_id:
                return deployment
        return None
