"""
Device Recommendation Engine
Phase 3.3: Recommend devices based on requirements
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


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
                    recommendations.append({
                        "manufacturer": device.get("manufacturer"),
                        "model": device.get("model"),
                        "device_type": device_type,
                        "reason": "Recommended by Device Database",
                        "rating": device.get("rating"),
                        "features": device.get("features", []),
                        "price_range": device.get("price_range"),
                        "relevance_score": 0.8
                    })
            except Exception as e:
                logger.warning(f"Device Database search failed: {e}")
        
        # Find similar devices in user's home
        if user_devices:
            similar = self._find_similar_devices(device_type, user_devices)
            for device in similar:
                recommendations.append({
                    "manufacturer": device.get("manufacturer"),
                    "model": device.get("model"),
                    "device_type": device_type,
                    "reason": "Similar to your existing device",
                    "user_rating": self._calculate_user_satisfaction(device),
                    "relevance_score": 0.7
                })
        
        # Sort by relevance
        recommendations.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return recommendations[:10]  # Top 10

    def _find_similar_devices(
        self,
        device_type: str,
        user_devices: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Find similar devices in user's home"""
        similar = []
        for device in user_devices:
            if device.get("device_type") == device_type:
                similar.append(device)
        return similar

    def _calculate_user_satisfaction(self, device: dict[str, Any]) -> float:
        """Calculate user satisfaction score for a device"""
        # Simplified: would analyze usage patterns, health, etc.
        return 0.8  # Placeholder

