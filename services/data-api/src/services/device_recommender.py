"""
Device Recommender Service Integration
Phase 3.3: Device recommendations and comparisons
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class DeviceRecommenderService:
    """Service for device recommendations"""

    def __init__(self):
        """Initialize recommender service"""
        self._recommender = None
        self._comparison_engine = None
        self._db_client = None

    def _get_recommender(self):
        """Get recommender (lazy import)"""
        if self._recommender is None:
            try:
                import sys
                sys.path.append(os.path.join(os.path.dirname(__file__), '../../../device-recommender/src'))
                from recommender import DeviceRecommender
                from db_client import DeviceDatabaseClient
                
                db_client = DeviceDatabaseClient()
                self._db_client = db_client
                self._recommender = DeviceRecommender(db_client=db_client)
            except ImportError:
                logger.warning("Device recommender not available")
                return None
        return self._recommender

    def _get_comparison_engine(self):
        """Get comparison engine (lazy import)"""
        if self._comparison_engine is None:
            try:
                import sys
                sys.path.append(os.path.join(os.path.dirname(__file__), '../../../device-recommender/src'))
                from comparison_engine import DeviceComparisonEngine
                self._comparison_engine = DeviceComparisonEngine()
            except ImportError:
                logger.warning("Device comparison engine not available")
                return None
        return self._comparison_engine

    async def recommend_devices(
        self,
        device_type: str,
        requirements: dict[str, Any] | None = None,
        user_devices: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """
        Get device recommendations.
        
        Args:
            device_type: Device type
            requirements: User requirements
            user_devices: User's existing devices
            
        Returns:
            List of recommendations
        """
        recommender = self._get_recommender()
        if not recommender:
            return []
        
        try:
            return await recommender.recommend_devices(
                device_type=device_type,
                requirements=requirements,
                user_devices=user_devices
            )
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return []

    def compare_devices(
        self,
        device_ids: list[str],
        devices: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Compare devices.
        
        Args:
            device_ids: Device IDs to compare
            devices: Device data
            
        Returns:
            Comparison result
        """
        engine = self._get_comparison_engine()
        if not engine:
            return {
                "message": "Comparison engine not available",
                "devices": []
            }
        
        try:
            return engine.compare_devices(device_ids, devices)
        except Exception as e:
            logger.error(f"Error comparing devices: {e}")
            return {
                "message": f"Comparison failed: {str(e)}",
                "devices": []
            }

    def find_similar_devices(
        self,
        device_id: str,
        all_devices: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Find similar devices.
        
        Args:
            device_id: Reference device ID
            all_devices: All available devices
            
        Returns:
            List of similar devices
        """
        # Find reference device
        reference = next(
            (d for d in all_devices if d.get("device_id") == device_id),
            None
        )
        
        if not reference:
            return []
        
        # Find similar devices (same type, manufacturer, or category)
        similar = []
        ref_type = reference.get("device_type")
        ref_manufacturer = reference.get("manufacturer")
        ref_category = reference.get("device_category")
        
        for device in all_devices:
            if device.get("device_id") == device_id:
                continue
            
            # Score similarity
            score = 0.0
            if device.get("device_type") == ref_type:
                score += 0.5
            if device.get("manufacturer") == ref_manufacturer:
                score += 0.3
            if device.get("device_category") == ref_category:
                score += 0.2
            
            if score > 0.3:
                device["similarity_score"] = score
                similar.append(device)
        
        # Sort by similarity
        similar.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
        
        return similar[:10]  # Top 10


# Singleton instance
_recommender_service: DeviceRecommenderService | None = None


def get_recommender_service() -> DeviceRecommenderService:
    """Get singleton recommender service instance"""
    global _recommender_service
    if _recommender_service is None:
        _recommender_service = DeviceRecommenderService()
    return _recommender_service

