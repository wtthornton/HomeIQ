"""
Device Intelligence Service - Optimization Recommendation Engine

Intelligent recommendation engine that generates optimization suggestions
based on device health scores, usage patterns, and performance metrics.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class RecommendationCategory(Enum):
    """Categories of optimization recommendations."""
    ENERGY = "energy"
    PERFORMANCE = "performance"
    MAINTENANCE = "maintenance"
    CONFIGURATION = "configuration"
    USAGE_PATTERN = "usage_pattern"


class RecommendationPriority(Enum):
    """Priority levels for recommendations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OptimizationRecommendation:
    """Optimization recommendation data model."""

    def __init__(
        self,
        device_id: str,
        category: RecommendationCategory,
        title: str,
        description: str,
        priority: RecommendationPriority,
        confidence_score: float,
        estimated_impact: dict[str, Any],
        implementation_steps: list[str],
        prerequisites: list[str] = None,
        expires_at: datetime | None = None
    ):
        self.id = f"{device_id}_{category.value}_{int(datetime.now().timestamp())}"
        self.device_id = device_id
        self.category = category
        self.title = title
        self.description = description
        self.priority = priority
        self.confidence_score = confidence_score
        self.estimated_impact = estimated_impact
        self.implementation_steps = implementation_steps
        self.prerequisites = prerequisites or []
        self.created_at = datetime.now(timezone.utc)
        self.expires_at = expires_at
        self.status = "pending"


class RecommendationEngine:
    """Intelligent optimization recommendation engine."""

    def __init__(self):
        # Recommendation thresholds
        self.thresholds = {
            "low_health_score": 60,
            "high_error_rate": 0.1,
            "low_battery": 20,
            "poor_signal": -70,
            "high_response_time": 1000,
            "high_cpu_usage": 80,
            "high_memory_usage": 80,
            "high_temperature": 40
        }

        # Impact multipliers for different categories
        self.impact_multipliers = {
            RecommendationCategory.ENERGY: {"energy_savings": 0.15, "cost_reduction": 0.10},
            RecommendationCategory.PERFORMANCE: {"response_time": 0.20, "reliability": 0.25},
            RecommendationCategory.MAINTENANCE: {"uptime": 0.30, "longevity": 0.40},
            RecommendationCategory.CONFIGURATION: {"efficiency": 0.20, "security": 0.15},
            RecommendationCategory.USAGE_PATTERN: {"optimization": 0.25, "automation": 0.20}
        }

    async def generate_recommendations(
        self,
        device_id: str,
        health_score: dict[str, Any],
        device_metrics: dict[str, Any],
        historical_metrics: list[dict[str, Any]] = None
    ) -> list[OptimizationRecommendation]:
        """Generate optimization recommendations for a device."""
        recommendations = []

        try:
            # Generate recommendations for each category
            recommendations.extend(await self._generate_energy_recommendations(
                device_id, health_score, device_metrics, historical_metrics
            ))
            recommendations.extend(await self._generate_performance_recommendations(
                device_id, health_score, device_metrics, historical_metrics
            ))
            recommendations.extend(await self._generate_maintenance_recommendations(
                device_id, health_score, device_metrics, historical_metrics
            ))
            recommendations.extend(await self._generate_configuration_recommendations(
                device_id, health_score, device_metrics, historical_metrics
            ))
            recommendations.extend(await self._generate_usage_pattern_recommendations(
                device_id, health_score, device_metrics, historical_metrics
            ))

            # Sort by priority rank and confidence (MED-5: fix alphabetical enum sorting)
            _PRIORITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            recommendations.sort(
                key=lambda r: (_PRIORITY_RANK.get(r.priority.value, 0), r.confidence_score),
                reverse=True
            )

            logger.info("Generated %d recommendations for device %s", len(recommendations), device_id)
            return recommendations

        except Exception as e:
            logger.error("Error generating recommendations for device %s: %s", device_id, e)
            return []

    async def _generate_energy_recommendations(
        self, device_id: str, health_score: dict[str, Any],
        metrics: dict[str, Any], historical: list[dict[str, Any]]
    ) -> list[OptimizationRecommendation]:
        """Generate energy optimization recommendations."""
        recommendations = []

        # Battery optimization
        battery_level = metrics.get("battery_level", 100)
        if battery_level < self.thresholds["low_battery"]:
            recommendations.append(OptimizationRecommendation(
                device_id=device_id,
                category=RecommendationCategory.ENERGY,
                title="Replace or Charge Battery",
                description=f"Device battery is at {battery_level}%, which may cause performance issues.",
                priority=RecommendationPriority.HIGH if battery_level < 10 else RecommendationPriority.MEDIUM,
                confidence_score=0.9,
                estimated_impact={
                    "energy_savings": "15-25%",
                    "performance_improvement": "20-30%",
                    "reliability_increase": "40-50%"
                },
                implementation_steps=[
                    "Check device manual for battery replacement procedure",
                    "Order replacement battery if needed",
                    "Schedule maintenance window for replacement",
                    "Test device functionality after replacement"
                ],
                prerequisites=["Device access", "Replacement battery"]
            ))

        # Usage pattern optimization
        usage_frequency = metrics.get("usage_frequency", 0.5)
        if usage_frequency > 0.8:
            recommendations.append(OptimizationRecommendation(
                device_id=device_id,
                category=RecommendationCategory.ENERGY,
                title="Optimize Usage Schedule",
                description="Device is used frequently. Consider scheduling optimization to reduce energy consumption.",
                priority=RecommendationPriority.MEDIUM,
                confidence_score=0.7,
                estimated_impact={
                    "energy_savings": "10-20%",
                    "cost_reduction": "8-15%",
                    "device_longevity": "15-25%"
                },
                implementation_steps=[
                    "Analyze current usage patterns",
                    "Identify peak usage times",
                    "Implement smart scheduling",
                    "Monitor energy consumption changes"
                ]
            ))

        return recommendations

    async def _generate_performance_recommendations(
        self, device_id: str, health_score: dict[str, Any],
        metrics: dict[str, Any], historical: list[dict[str, Any]]
    ) -> list[OptimizationRecommendation]:
        """Generate performance optimization recommendations."""
        recommendations = []

        # Response time optimization
        response_time = metrics.get("response_time", 0)
        if response_time > self.thresholds["high_response_time"]:
            recommendations.append(OptimizationRecommendation(
                device_id=device_id,
                category=RecommendationCategory.PERFORMANCE,
                title="Optimize Response Time",
                description=f"Device response time is {response_time}ms, which is above optimal threshold.",
                priority=RecommendationPriority.HIGH,
                confidence_score=0.8,
                estimated_impact={
                    "response_time_improvement": "30-50%",
                    "user_experience": "Significantly improved",
                    "reliability": "20-30%"
                },
                implementation_steps=[
                    "Check network connectivity",
                    "Verify device firmware is up to date",
                    "Optimize device configuration",
                    "Consider device replacement if hardware is outdated"
                ]
            ))

        # Error rate optimization
        error_rate = metrics.get("error_rate", 0)
        if error_rate > self.thresholds["high_error_rate"]:
            recommendations.append(OptimizationRecommendation(
                device_id=device_id,
                category=RecommendationCategory.PERFORMANCE,
                title="Reduce Error Rate",
                description=f"Device error rate is {error_rate:.2%}, indicating potential issues.",
                priority=RecommendationPriority.CRITICAL,
                confidence_score=0.9,
                estimated_impact={
                    "reliability_improvement": "40-60%",
                    "user_satisfaction": "Significantly improved",
                    "maintenance_costs": "Reduced by 25-40%"
                },
                implementation_steps=[
                    "Investigate error logs",
                    "Check device connectivity",
                    "Verify configuration settings",
                    "Consider firmware update or device replacement"
                ]
            ))

        return recommendations

    async def _generate_maintenance_recommendations(
        self, device_id: str, health_score: dict[str, Any],
        metrics: dict[str, Any], historical: list[dict[str, Any]]
    ) -> list[OptimizationRecommendation]:
        """Generate maintenance recommendations."""
        recommendations = []

        overall_score = health_score.get("overall_score", 100)
        if overall_score < self.thresholds["low_health_score"]:
            recommendations.append(OptimizationRecommendation(
                device_id=device_id,
                category=RecommendationCategory.MAINTENANCE,
                title="Schedule Preventive Maintenance",
                description=f"Device health score is {overall_score}, indicating maintenance is needed.",
                priority=RecommendationPriority.HIGH,
                confidence_score=0.8,
                estimated_impact={
                    "uptime_improvement": "30-50%",
                    "longevity": "40-60%",
                    "performance": "25-40%"
                },
                implementation_steps=[
                    "Schedule maintenance window",
                    "Prepare maintenance checklist",
                    "Gather required tools and parts",
                    "Perform comprehensive device check",
                    "Update maintenance records"
                ],
                prerequisites=["Maintenance tools", "Device documentation"]
            ))

        # Temperature-based maintenance
        temperature = metrics.get("temperature", 25)
        if temperature > self.thresholds["high_temperature"]:
            recommendations.append(OptimizationRecommendation(
                device_id=device_id,
                category=RecommendationCategory.MAINTENANCE,
                title="Address Temperature Issues",
                description=f"Device temperature is {temperature}°C, which may cause performance degradation.",
                priority=RecommendationPriority.MEDIUM,
                confidence_score=0.7,
                estimated_impact={
                    "performance_stability": "20-30%",
                    "component_longevity": "30-40%",
                    "energy_efficiency": "10-15%"
                },
                implementation_steps=[
                    "Check device ventilation",
                    "Clean air vents and filters",
                    "Verify ambient temperature",
                    "Consider additional cooling if needed"
                ]
            ))

        return recommendations

    async def _generate_configuration_recommendations(
        self, device_id: str, health_score: dict[str, Any],
        metrics: dict[str, Any], historical: list[dict[str, Any]]
    ) -> list[OptimizationRecommendation]:
        """Generate configuration optimization recommendations."""
        recommendations = []

        # Signal strength optimization
        signal_strength = metrics.get("signal_strength", -50)
        if signal_strength < self.thresholds["poor_signal"]:
            recommendations.append(OptimizationRecommendation(
                device_id=device_id,
                category=RecommendationCategory.CONFIGURATION,
                title="Improve Signal Strength",
                description=f"Device signal strength is {signal_strength}dBm, which may affect connectivity.",
                priority=RecommendationPriority.MEDIUM,
                confidence_score=0.8,
                estimated_impact={
                    "connectivity_reliability": "40-60%",
                    "response_time": "20-30%",
                    "data_transfer": "25-35%"
                },
                implementation_steps=[
                    "Check antenna positioning",
                    "Verify router/access point location",
                    "Consider signal booster or repeater",
                    "Update device firmware",
                    "Test connectivity improvements"
                ]
            ))

        # Resource usage optimization
        cpu_usage = metrics.get("cpu_usage", 0)
        memory_usage = metrics.get("memory_usage", 0)

        if cpu_usage > self.thresholds["high_cpu_usage"] or memory_usage > self.thresholds["high_memory_usage"]:
            recommendations.append(OptimizationRecommendation(
                device_id=device_id,
                category=RecommendationCategory.CONFIGURATION,
                title="Optimize Resource Usage",
                description=f"Device resource usage is high (CPU: {cpu_usage}%, Memory: {memory_usage}%).",
                priority=RecommendationPriority.MEDIUM,
                confidence_score=0.7,
                estimated_impact={
                    "performance": "25-40%",
                    "stability": "30-50%",
                    "energy_efficiency": "15-25%"
                },
                implementation_steps=[
                    "Review running processes",
                    "Optimize device configuration",
                    "Close unnecessary applications",
                    "Consider hardware upgrade if needed"
                ]
            ))

        return recommendations

    async def _generate_usage_pattern_recommendations(
        self, device_id: str, health_score: dict[str, Any],
        metrics: dict[str, Any], historical: list[dict[str, Any]]
    ) -> list[OptimizationRecommendation]:
        """Generate usage pattern optimization recommendations."""
        recommendations = []

        # Usage frequency analysis
        usage_frequency = metrics.get("usage_frequency", 0.5)

        if usage_frequency < 0.2:
            recommendations.append(OptimizationRecommendation(
                device_id=device_id,
                category=RecommendationCategory.USAGE_PATTERN,
                title="Optimize Device Usage",
                description="Device is used infrequently. Consider automation or scheduling optimization.",
                priority=RecommendationPriority.LOW,
                confidence_score=0.6,
                estimated_impact={
                    "automation_efficiency": "30-50%",
                    "energy_savings": "20-30%",
                    "convenience": "Significantly improved"
                },
                implementation_steps=[
                    "Analyze usage patterns",
                    "Identify automation opportunities",
                    "Create smart schedules",
                    "Implement automated triggers",
                    "Monitor effectiveness"
                ]
            ))

        elif usage_frequency > 0.8:
            recommendations.append(OptimizationRecommendation(
                device_id=device_id,
                category=RecommendationCategory.USAGE_PATTERN,
                title="Balance Device Usage",
                description="Device is used very frequently. Consider load balancing or optimization.",
                priority=RecommendationPriority.MEDIUM,
                confidence_score=0.7,
                estimated_impact={
                    "performance": "20-30%",
                    "longevity": "25-40%",
                    "efficiency": "15-25%"
                },
                implementation_steps=[
                    "Analyze peak usage times",
                    "Implement usage scheduling",
                    "Consider load balancing",
                    "Monitor performance improvements"
                ]
            ))

        return recommendations

    async def get_recommendation_impact_analysis(self, recommendations: list[OptimizationRecommendation]) -> dict[str, Any]:
        """Analyze the potential impact of recommendations."""
        if not recommendations:
            return {"total_impact": 0, "categories": {}, "priority_distribution": {}}

        # Calculate total impact by category
        category_impact = {}
        priority_distribution = {}

        for rec in recommendations:
            # Category impact
            if rec.category.value not in category_impact:
                category_impact[rec.category.value] = {
                    "count": 0,
                    "total_confidence": 0,
                    "avg_confidence": 0
                }

            category_impact[rec.category.value]["count"] += 1
            category_impact[rec.category.value]["total_confidence"] += rec.confidence_score

            # Priority distribution
            if rec.priority.value not in priority_distribution:
                priority_distribution[rec.priority.value] = 0
            priority_distribution[rec.priority.value] += 1

        # Calculate average confidence by category
        for category in category_impact:
            count = category_impact[category]["count"]
            category_impact[category]["avg_confidence"] = (
                category_impact[category]["total_confidence"] / count
            )

        return {
            "total_recommendations": len(recommendations),
            "categories": category_impact,
            "priority_distribution": priority_distribution,
            "high_confidence_count": len([r for r in recommendations if r.confidence_score > 0.8]),
            "critical_priority_count": len([r for r in recommendations if r.priority == RecommendationPriority.CRITICAL])
        }


# Global recommendation engine instance
recommendation_engine = RecommendationEngine()
