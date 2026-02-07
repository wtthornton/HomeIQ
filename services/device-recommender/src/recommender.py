"""
Device Recommendation Engine
Phase 3.3: Recommend devices based on requirements
"""

import logging
from typing import Any

logger = logging.getLogger("device-recommender")


class DeviceRecommender:
    """Engine for recommending devices"""

    def __init__(self, db_client: Any = None):
        """
        Initialize recommender.

        Args:
            db_client: Device Database client (optional)
        """
        self.db_client = db_client

    async def recommend_devices(
        self,
        device_type: str,
        requirements: dict[str, Any] | None = None,
        user_devices: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """
        Recommend devices based on requirements.

        Args:
            device_type: Device type (fridge, light, etc.)
            requirements: User requirements (price_range, features, etc.)
            user_devices: User's existing devices (for similarity matching)

        Returns:
            List of device recommendations
        """
        recommendations = []

        # Query Device Database if available
        if self.db_client and self.db_client.is_available():
            try:
                db_devices = await self.db_client.search_devices(
                    device_type=device_type,
                    filters=requirements or {}
                )

                for device in db_devices:
                    relevance = self._calculate_db_relevance(device, requirements)
                    recommendations.append({
                        "manufacturer": device.get("manufacturer"),
                        "model": device.get("model"),
                        "device_type": device_type,
                        "reason": "Recommended by Device Database",
                        "rating": device.get("rating"),
                        "features": device.get("features", []),
                        "price_range": device.get("price_range"),
                        "relevance_score": relevance,
                    })
            except Exception as e:
                logger.warning(f"Device Database search failed: {e}")

        # Find similar devices in user's home (exclude their own devices)
        if user_devices:
            similar = self._find_similar_devices(device_type, user_devices)
            for device in similar:
                satisfaction = self._calculate_user_satisfaction(device)
                recommendations.append({
                    "manufacturer": device.get("manufacturer"),
                    "model": device.get("model"),
                    "device_type": device_type,
                    "reason": "Similar to your existing device",
                    "user_rating": satisfaction,
                    "relevance_score": satisfaction * 0.9,
                })

        # Sort by relevance
        recommendations.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        return recommendations[:10]  # Top 10

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_db_relevance(
        device: dict[str, Any],
        requirements: dict[str, Any] | None,
    ) -> float:
        """Calculate relevance score for a device from the database.

        Scoring factors (all normalised to 0-1, then averaged):
        - Device rating (0-5 scaled to 0-1)
        - Feature match ratio against required features
        """
        scores: list[float] = []

        # Rating component (0-5 -> 0.0-1.0)
        rating = device.get("rating")
        if rating is not None:
            scores.append(min(max(float(rating) / 5.0, 0.0), 1.0))

        # Feature match component
        if requirements and requirements.get("features"):
            required_features = set(requirements["features"])
            device_features = set(device.get("features", []))
            if required_features:
                match_ratio = len(required_features & device_features) / len(required_features)
                scores.append(match_ratio)

        if not scores:
            return 0.5  # neutral default when no data is available

        return sum(scores) / len(scores)

    @staticmethod
    def _find_similar_devices(
        device_type: str,
        user_devices: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Find similar devices in user's home, excluding user's own devices."""
        similar = []
        for device in user_devices:
            if device.get("device_type") == device_type:
                # Exclude the user's own device by checking for a device_id marker
                if device.get("is_own_device"):
                    continue
                similar.append(device)
        return similar

    @staticmethod
    def _calculate_user_satisfaction(device: dict[str, Any]) -> float:
        """Calculate user satisfaction score for a device.

        Uses device health status and usage frequency to derive a score.
        """
        score = 0.5  # baseline

        # Health status contribution
        health = device.get("health_status", "").lower()
        health_map = {
            "excellent": 0.3,
            "good": 0.2,
            "fair": 0.1,
            "degraded": -0.1,
            "poor": -0.2,
        }
        score += health_map.get(health, 0.0)

        # Usage frequency contribution
        usage = device.get("usage_frequency", "").lower()
        usage_map = {
            "high": 0.2,
            "medium": 0.1,
            "low": 0.0,
            "none": -0.1,
        }
        score += usage_map.get(usage, 0.0)

        # Clamp to [0, 1]
        return min(max(score, 0.0), 1.0)
