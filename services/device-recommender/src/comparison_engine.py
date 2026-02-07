"""
Device Comparison Engine
Phase 3.3: Compare devices side-by-side
"""

import logging
from typing import Any

logger = logging.getLogger("device-recommender")


class DeviceComparisonEngine:
    """Engine for comparing devices"""

    def compare_devices(
        self,
        device_ids: list[str],
        devices: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Compare multiple devices.

        Args:
            device_ids: List of device IDs to compare
            devices: List of device dictionaries

        Returns:
            Comparison dictionary

        Raises:
            ValueError: If fewer than 2 matching devices are found
        """
        # Use set for O(1) lookup
        device_id_set = set(device_ids)
        devices_to_compare = [
            d for d in devices
            if d.get("device_id") in device_id_set
        ]

        if len(devices_to_compare) < 2:
            raise ValueError("Need at least 2 devices to compare")

        # Build comparison
        comparison = {
            "devices": devices_to_compare,
            "comparison_points": self._extract_comparison_points(devices_to_compare),
            "recommendation": self._generate_recommendation(devices_to_compare)
        }

        return comparison

    def _extract_comparison_points(
        self,
        devices: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Extract comparison points from devices"""
        points: dict[str, list[dict[str, Any]]] = {
            "power_consumption": [],
            "features": [],
            "ratings": [],
            "categories": []
        }

        for device in devices:
            if device.get("power_consumption_active_w") is not None:
                points["power_consumption"].append({
                    "device_id": device.get("device_id"),
                    "device_name": device.get("name"),
                    "power_w": device.get("power_consumption_active_w")
                })

            if device.get("community_rating") is not None:
                points["ratings"].append({
                    "device_id": device.get("device_id"),
                    "device_name": device.get("name"),
                    "rating": device.get("community_rating")
                })

            if device.get("device_category"):
                points["categories"].append({
                    "device_id": device.get("device_id"),
                    "device_name": device.get("name"),
                    "category": device.get("device_category")
                })

        return points

    def _generate_recommendation(
        self,
        devices: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate recommendation based on comparison"""
        if not devices:
            return {
                "recommended_device_id": None,
                "recommended_device_name": None,
                "reason": "No devices available for recommendation",
            }

        # Simple recommendation: device with highest rating
        best_device = max(
            devices,
            key=lambda d: d.get("community_rating", 0) or 0
        )

        return {
            "recommended_device_id": best_device.get("device_id"),
            "recommended_device_name": best_device.get("name"),
            "reason": "Highest community rating"
        }
