"""
Advanced Health Score Calculation Algorithm

Context7 Best Practices Applied:
- Type hints throughout
- Configurable weighting
- Extensible scoring system
"""
from enum import Enum


class ScoreComponent(Enum):
    """Health score component types"""
    HA_CORE = "ha_core"
    INTEGRATIONS = "integrations"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"


class HealthScoringAlgorithm:
    """
    Advanced health scoring with configurable weights and multi-factor analysis
    
    Default Weighting:
    - HA Core: 35% (reduced from 40% to accommodate reliability)
    - Integrations: 35% (reduced from 40%)
    - Performance: 15% (reduced from 20%)
    - Reliability: 15% (new - based on uptime and error rates)
    """

    def __init__(
        self,
        ha_core_weight: float = 0.35,
        integrations_weight: float = 0.35,
        performance_weight: float = 0.15,
        reliability_weight: float = 0.15
    ):
        """
        Initialize scoring algorithm with configurable weights
        
        Args:
            ha_core_weight: Weight for HA core status (0-1)
            integrations_weight: Weight for integrations health (0-1)
            performance_weight: Weight for performance metrics (0-1)
            reliability_weight: Weight for reliability metrics (0-1)
        """
        # Validate weights sum to 1.0
        total = ha_core_weight + integrations_weight + performance_weight + reliability_weight
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")

        self.weights = {
            ScoreComponent.HA_CORE: ha_core_weight,
            ScoreComponent.INTEGRATIONS: integrations_weight,
            ScoreComponent.PERFORMANCE: performance_weight,
            ScoreComponent.RELIABILITY: reliability_weight
        }

    def calculate_score(
        self,
        ha_status: dict,
        integrations: list[dict],
        performance: dict,
        reliability_data: dict = None
    ) -> tuple[int, dict[str, int]]:
        """
        Calculate overall health score with component breakdown
        
        Args:
            ha_status: HA core status data
            integrations: List of integration health data
            performance: Performance metrics
            reliability_data: Reliability metrics (optional)
            
        Returns:
            Tuple of (total_score, component_scores_breakdown)
        """
        component_scores = {}

        # Calculate HA Core score
        component_scores[ScoreComponent.HA_CORE.value] = self._score_ha_core(ha_status)

        # Calculate Integrations score
        component_scores[ScoreComponent.INTEGRATIONS.value] = self._score_integrations(integrations)

        # Calculate Performance score
        component_scores[ScoreComponent.PERFORMANCE.value] = self._score_performance(performance)

        # Calculate Reliability score
        if reliability_data:
            component_scores[ScoreComponent.RELIABILITY.value] = self._score_reliability(reliability_data)
        else:
            component_scores[ScoreComponent.RELIABILITY.value] = 100  # Default to perfect if no data

        # Calculate weighted total score
        total_score = sum(
            component_scores[component.value] * self.weights[component]
            for component in ScoreComponent
        )

        return int(total_score), component_scores

    def _score_ha_core(self, ha_status: dict) -> int:
        """
        Score HA core status
        
        Scoring:
        - healthy: 100 points
        - warning: 50 points (HA is running but has issues)
        - error/unknown: 25 points (HA might be running but can't verify)
        """
        status = ha_status.get("status", "unknown").lower()

        if status == "healthy":
            return 100
        elif status == "warning":
            return 50
        else:
            # Don't return 0 for error/unknown - give partial credit if HA URL is configured
            # This prevents health score from being 0 when HA is just unreachable
            return 25

    def _score_integrations(self, integrations: list[dict]) -> int:
        """
        Score integrations health
        
        Scoring:
        - Each healthy integration adds proportional points
        - Warning integrations count as 50% healthy
        - Error/not_configured count as 0%
        - Zigbee2MQTT is excluded (it's just MQTT with a different topic)
        """
        if not integrations:
            # If no integrations checked, give partial credit (system might be in setup)
            return 30

        # Filter out Zigbee2MQTT - it's not a separate integration, just MQTT with different topic
        relevant_integrations = [
            i for i in integrations
            if i.get("type") != "zigbee2mqtt"
        ]

        if not relevant_integrations:
            return 0

        total_score = 0
        for integration in relevant_integrations:
            status = integration.get("status", "error")

            if status == "healthy":
                total_score += 100
            elif status == "warning":
                total_score += 50
            # error and not_configured = 0 points

        # Average across relevant integrations only
        return int(total_score / len(relevant_integrations))

    def _score_performance(self, performance: dict) -> int:
        """
        Score performance metrics
        
        Scoring based on response time:
        - 0ms (no data/default): 80 points (assume good performance)
        - < 100ms: 100 points
        - < 250ms: 80 points
        - < 500ms: 60 points
        - < 1000ms: 30 points
        - >= 1000ms: 0 points
        """
        response_time = performance.get("response_time_ms", 0)

        # If response_time is 0, it might mean no data collected yet, give partial credit
        if response_time == 0:
            return 80
        elif response_time < 100:
            return 100
        elif response_time < 250:
            return 80
        elif response_time < 500:
            return 60
        elif response_time < 1000:
            return 30
        else:
            return 0

    def _score_reliability(self, reliability_data: dict) -> int:
        """
        Score reliability metrics
        
        Scoring:
        - Uptime percentage
        - Error rate (lower is better)
        - Connection stability
        """
        uptime_seconds = reliability_data.get("uptime_seconds", 0)
        error_count = reliability_data.get("error_count", 0)
        total_checks = reliability_data.get("total_checks", 1)

        # Uptime score (50 points max)
        # Perfect uptime = 50 points, scales down linearly
        if uptime_seconds >= 86400:  # 1 day+
            uptime_score = 50
        elif uptime_seconds >= 3600:  # 1 hour+
            uptime_score = 30
        elif uptime_seconds >= 600:  # 10 minutes+
            uptime_score = 10
        else:
            uptime_score = 0

        # Error rate score (50 points max)
        # 0 errors = 50 points, scales down based on error percentage
        if total_checks > 0:
            error_rate = error_count / total_checks
            error_score = max(0, 50 - (error_rate * 100))
        else:
            error_score = 50

        return int(uptime_score + error_score)

    def get_score_breakdown_explanation(
        self,
        total_score: int,
        component_scores: dict[str, int]
    ) -> dict:
        """
        Generate human-readable explanation of score breakdown
        
        Returns:
            Dictionary with score explanation and recommendations
        """
        explanations = []
        recommendations = []

        # HA Core analysis
        ha_score = component_scores.get(ScoreComponent.HA_CORE.value, 0)
        if ha_score < 100:
            explanations.append(f"HA Core score: {ha_score}/100 - Check Home Assistant status")
            if ha_score == 0:
                recommendations.append("Critical: Home Assistant core is not responding")

        # Integrations analysis
        int_score = component_scores.get(ScoreComponent.INTEGRATIONS.value, 0)
        if int_score < 100:
            explanations.append(f"Integrations score: {int_score}/100 - Some integrations need attention")
            if int_score < 50:
                recommendations.append("Fix integration errors to improve health score")

        # Performance analysis
        perf_score = component_scores.get(ScoreComponent.PERFORMANCE.value, 0)
        if perf_score < 80:
            explanations.append(f"Performance score: {perf_score}/100 - System response time is high")
            if perf_score < 50:
                recommendations.append("Investigate performance bottlenecks")

        # Reliability analysis
        rel_score = component_scores.get(ScoreComponent.RELIABILITY.value, 0)
        if rel_score < 80:
            explanations.append(f"Reliability score: {rel_score}/100 - Connection stability issues")
            if rel_score < 50:
                recommendations.append("Check for frequent disconnections or errors")

        # Overall assessment
        if total_score >= 80:
            overall = "Excellent - Your environment is healthy"
        elif total_score >= 50:
            overall = "Good - Minor issues detected"
        else:
            overall = "Critical - Immediate attention required"

        return {
            "total_score": total_score,
            "overall_assessment": overall,
            "component_scores": component_scores,
            "explanations": explanations,
            "recommendations": recommendations
        }

