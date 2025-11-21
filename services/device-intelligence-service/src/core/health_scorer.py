"""
Device Intelligence Service - Device Health Scorer

Comprehensive device health scoring algorithm that analyzes multiple factors
to generate a 0-100 health score for each device.
"""

import logging
import statistics
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class DeviceHealthScorer:
    """Comprehensive device health scoring algorithm."""

    def __init__(self):
        # Weight configuration for different factors
        self.weights = {
            "response_time": 0.25,
            "error_rate": 0.30,
            "battery_level": 0.20,
            "signal_strength": 0.15,
            "usage_pattern": 0.10,
        }

        # Thresholds for different performance levels
        self.thresholds = {
            "response_time": {"excellent": 100, "good": 500, "fair": 1000, "poor": 2000},
            "error_rate": {"excellent": 0.01, "good": 0.05, "fair": 0.10, "poor": 0.20},
            "battery_level": {"excellent": 80, "good": 60, "fair": 40, "poor": 20},
            "signal_strength": {"excellent": -50, "good": -60, "fair": -70, "poor": -80},
            "usage_pattern": {"excellent": 0.8, "good": 0.6, "fair": 0.4, "poor": 0.2},
        }

        # Health status thresholds
        self.health_status_thresholds = {
            "excellent": 90,
            "good": 75,
            "fair": 60,
            "poor": 40,
            "critical": 0,
        }

    async def calculate_health_score(self, device_id: str, metrics: dict[str, Any], historical_metrics: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """Calculate comprehensive health score for device."""
        try:
            # Use provided historical metrics or empty list
            if historical_metrics is None:
                historical_metrics = []

            # Calculate individual factor scores
            response_time_score = await self._calculate_response_time_score(metrics, historical_metrics)
            error_rate_score = await self._calculate_error_rate_score(metrics, historical_metrics)
            battery_score = await self._calculate_battery_score(metrics, historical_metrics)
            signal_score = await self._calculate_signal_score(metrics, historical_metrics)
            usage_score = await self._calculate_usage_score(metrics, historical_metrics)

            # Calculate weighted overall score
            overall_score = (
                response_time_score * self.weights["response_time"] +
                error_rate_score * self.weights["error_rate"] +
                battery_score * self.weights["battery_level"] +
                signal_score * self.weights["signal_strength"] +
                usage_score * self.weights["usage_pattern"]
            )

            # Apply trend adjustment
            trend_adjustment = await self._calculate_trend_adjustment(historical_metrics)
            adjusted_score = overall_score + trend_adjustment

            # Ensure score is within 0-100 range
            final_score = max(0, min(100, adjusted_score))

            # Generate recommendations
            recommendations = await self._generate_recommendations(device_id, metrics, final_score)

            return {
                "device_id": device_id,
                "overall_score": round(final_score, 1),
                "factor_scores": {
                    "response_time": round(response_time_score, 1),
                    "error_rate": round(error_rate_score, 1),
                    "battery_level": round(battery_score, 1),
                    "signal_strength": round(signal_score, 1),
                    "usage_pattern": round(usage_score, 1),
                },
                "weights": self.weights,
                "trend_adjustment": round(trend_adjustment, 1),
                "health_status": self._get_health_status(final_score),
                "recommendations": recommendations,
                "calculated_at": datetime.now(timezone.utc).isoformat(),
                "metrics_used": {
                    "current": metrics,
                    "historical_count": len(historical_metrics),
                },
            }

        except Exception as e:
            logger.exception(f"Error calculating health score for device {device_id}: {e}")
            return {
                "device_id": device_id,
                "overall_score": 0,
                "error": str(e),
                "calculated_at": datetime.now(timezone.utc).isoformat(),
            }

    async def _calculate_response_time_score(self, metrics: dict[str, Any], historical: list[dict[str, Any]]) -> float:
        """Calculate response time score (0-100)."""
        current_response_time = metrics.get("response_time", 0)

        # Score based on current response time
        if current_response_time <= self.thresholds["response_time"]["excellent"]:
            base_score = 100
        elif current_response_time <= self.thresholds["response_time"]["good"]:
            base_score = 80
        elif current_response_time <= self.thresholds["response_time"]["fair"]:
            base_score = 60
        elif current_response_time <= self.thresholds["response_time"]["poor"]:
            base_score = 40
        else:
            base_score = 20

        # Apply trend analysis
        if historical and len(historical) >= 3:
            recent_response_times = [m.get("response_time", 0) for m in historical[-10:] if m.get("response_time") is not None]
            if recent_response_times:
                avg_historical = statistics.mean(recent_response_times)
                if current_response_time < avg_historical * 0.9:  # 10% improvement
                    base_score += 10
                elif current_response_time > avg_historical * 1.1:  # 10% degradation
                    base_score -= 10

        return max(0, min(100, base_score))

    async def _calculate_error_rate_score(self, metrics: dict[str, Any], historical: list[dict[str, Any]]) -> float:
        """Calculate error rate score (0-100)."""
        current_error_rate = metrics.get("error_rate", 0)

        # Score based on current error rate
        if current_error_rate <= self.thresholds["error_rate"]["excellent"]:
            base_score = 100
        elif current_error_rate <= self.thresholds["error_rate"]["good"]:
            base_score = 80
        elif current_error_rate <= self.thresholds["error_rate"]["fair"]:
            base_score = 60
        elif current_error_rate <= self.thresholds["error_rate"]["poor"]:
            base_score = 40
        else:
            base_score = 20

        # Apply trend analysis
        if historical and len(historical) >= 3:
            recent_error_rates = [m.get("error_rate", 0) for m in historical[-10:] if m.get("error_rate") is not None]
            if recent_error_rates:
                avg_historical = statistics.mean(recent_error_rates)
                if current_error_rate < avg_historical * 0.9:  # 10% improvement
                    base_score += 10
                elif current_error_rate > avg_historical * 1.1:  # 10% degradation
                    base_score -= 10

        return max(0, min(100, base_score))

    async def _calculate_battery_score(self, metrics: dict[str, Any], historical: list[dict[str, Any]]) -> float:
        """Calculate battery level score (0-100)."""
        current_battery = metrics.get("battery_level", 100)

        # Score based on current battery level
        if current_battery >= self.thresholds["battery_level"]["excellent"]:
            base_score = 100
        elif current_battery >= self.thresholds["battery_level"]["good"]:
            base_score = 80
        elif current_battery >= self.thresholds["battery_level"]["fair"]:
            base_score = 60
        elif current_battery >= self.thresholds["battery_level"]["poor"]:
            base_score = 40
        else:
            base_score = 20

        # Apply trend analysis for battery degradation
        if historical and len(historical) >= 3:
            recent_battery_levels = [m.get("battery_level", 100) for m in historical[-10:] if m.get("battery_level") is not None]
            if recent_battery_levels:
                avg_historical = statistics.mean(recent_battery_levels)
                if current_battery < avg_historical * 0.95:  # 5% degradation
                    base_score -= 5

        return max(0, min(100, base_score))

    async def _calculate_signal_score(self, metrics: dict[str, Any], historical: list[dict[str, Any]]) -> float:
        """Calculate signal strength score (0-100)."""
        current_signal = metrics.get("signal_strength", -50)

        # Score based on current signal strength (dBm)
        if current_signal >= self.thresholds["signal_strength"]["excellent"]:
            base_score = 100
        elif current_signal >= self.thresholds["signal_strength"]["good"]:
            base_score = 80
        elif current_signal >= self.thresholds["signal_strength"]["fair"]:
            base_score = 60
        elif current_signal >= self.thresholds["signal_strength"]["poor"]:
            base_score = 40
        else:
            base_score = 20

        # Apply trend analysis
        if historical and len(historical) >= 3:
            recent_signal_strengths = [m.get("signal_strength", -50) for m in historical[-10:] if m.get("signal_strength") is not None]
            if recent_signal_strengths:
                avg_historical = statistics.mean(recent_signal_strengths)
                if current_signal > avg_historical + 5:  # 5dB improvement
                    base_score += 10
                elif current_signal < avg_historical - 5:  # 5dB degradation
                    base_score -= 10

        return max(0, min(100, base_score))

    async def _calculate_usage_score(self, metrics: dict[str, Any], historical: list[dict[str, Any]]) -> float:
        """Calculate usage pattern score (0-100)."""
        current_usage = metrics.get("usage_frequency", 0.5)

        # Score based on usage frequency (0-1 scale)
        if current_usage >= self.thresholds["usage_pattern"]["excellent"]:
            base_score = 100
        elif current_usage >= self.thresholds["usage_pattern"]["good"]:
            base_score = 80
        elif current_usage >= self.thresholds["usage_pattern"]["fair"]:
            base_score = 60
        elif current_usage >= self.thresholds["usage_pattern"]["poor"]:
            base_score = 40
        else:
            base_score = 20

        # Apply trend analysis
        if historical and len(historical) >= 3:
            recent_usage_frequencies = [m.get("usage_frequency", 0.5) for m in historical[-10:] if m.get("usage_frequency") is not None]
            if recent_usage_frequencies:
                avg_historical = statistics.mean(recent_usage_frequencies)
                if current_usage > avg_historical * 1.1:  # 10% increase
                    base_score += 10
                elif current_usage < avg_historical * 0.9:  # 10% decrease
                    base_score -= 10

        return max(0, min(100, base_score))

    async def _calculate_trend_adjustment(self, historical: list[dict[str, Any]]) -> float:
        """Calculate trend adjustment based on historical data."""
        if len(historical) < 5:
            return 0

        # Calculate trend for last 5 data points
        recent_scores = []
        for i in range(max(0, len(historical) - 5), len(historical)):
            metrics = historical[i]
            # Calculate a simple historical score
            score = 0
            score += min(100, max(0, 100 - metrics.get("response_time", 0) / 10))
            score += min(100, max(0, 100 - metrics.get("error_rate", 0) * 500))
            score += metrics.get("battery_level", 100)
            score += min(100, max(0, 100 + metrics.get("signal_strength", -50) + 80))
            recent_scores.append(score / 4)

        # Simple linear trend calculation
        if len(recent_scores) >= 2:
            trend = (recent_scores[-1] - recent_scores[0]) / len(recent_scores)
            return trend * 5  # Apply trend adjustment

        return 0

    def _get_health_status(self, score: float) -> str:
        """Get health status based on score."""
        if score >= self.health_status_thresholds["excellent"]:
            return "excellent"
        if score >= self.health_status_thresholds["good"]:
            return "good"
        if score >= self.health_status_thresholds["fair"]:
            return "fair"
        if score >= self.health_status_thresholds["poor"]:
            return "poor"
        return "critical"

    async def _generate_recommendations(self, device_id: str, metrics: dict[str, Any], score: float) -> list[str]:
        """Generate recommendations based on health score and metrics."""
        recommendations = []

        if score < 60:
            recommendations.append("Device requires immediate attention")

        if metrics.get("response_time", 0) > 1000:
            recommendations.append("Consider optimizing device response time")

        if metrics.get("error_rate", 0) > 0.1:
            recommendations.append("High error rate detected - check device connectivity")

        if metrics.get("battery_level", 100) < 20:
            recommendations.append("Low battery - consider replacing or charging")

        if metrics.get("signal_strength", -50) < -70:
            recommendations.append("Weak signal strength - consider repositioning device")

        if metrics.get("cpu_usage", 0) > 80:
            recommendations.append("High CPU usage - check for resource-intensive processes")

        if metrics.get("memory_usage", 0) > 90:
            recommendations.append("High memory usage - consider memory optimization")

        if metrics.get("temperature", 25) > 60:
            recommendations.append("High temperature - check device cooling and ventilation")

        if not recommendations:
            recommendations.append("Device is performing well")

        return recommendations

    def get_health_score_summary(self, health_scores: list[dict[str, Any]]) -> dict[str, Any]:
        """Get summary statistics for multiple device health scores."""
        if not health_scores:
            return {
                "total_devices": 0,
                "average_score": 0,
                "health_distribution": {},
                "recommendations_summary": [],
            }

        scores = [hs["overall_score"] for hs in health_scores]
        avg_score = statistics.mean(scores)

        # Calculate health distribution
        health_distribution = {
            "excellent": len([hs for hs in health_scores if hs["health_status"] == "excellent"]),
            "good": len([hs for hs in health_scores if hs["health_status"] == "good"]),
            "fair": len([hs for hs in health_scores if hs["health_status"] == "fair"]),
            "poor": len([hs for hs in health_scores if hs["health_status"] == "poor"]),
            "critical": len([hs for hs in health_scores if hs["health_status"] == "critical"]),
        }

        # Collect common recommendations
        all_recommendations = []
        for hs in health_scores:
            all_recommendations.extend(hs.get("recommendations", []))

        # Count recommendation frequency
        recommendation_counts = {}
        for rec in all_recommendations:
            recommendation_counts[rec] = recommendation_counts.get(rec, 0) + 1

        # Get top recommendations
        top_recommendations = sorted(recommendation_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_devices": len(health_scores),
            "average_score": round(avg_score, 1),
            "min_score": min(scores),
            "max_score": max(scores),
            "health_distribution": health_distribution,
            "recommendations_summary": [{"recommendation": rec, "count": count} for rec, count in top_recommendations],
        }


# Global health scorer instance
health_scorer = DeviceHealthScorer()
