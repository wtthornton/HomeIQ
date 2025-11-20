"""
Device Discovery Routes

API endpoints for device possibilities and recommendations.

Epic AI-4, Story AI4.3
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..miner.database import get_db_session
from ..miner.repository import CorpusRepository
from ..recommendations.device_recommender import DeviceRecommendation, DeviceRecommender

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("/{device_type}/possibilities")
async def get_device_possibilities(
    device_type: str,
    user_devices: str = Query("", description="Comma-separated list of user's devices"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get automation possibilities for a specific device type
    
    Shows what you can automate with this device, categorized by use case.
    
    Example:
        GET /api/automation-miner/devices/motion_sensor/possibilities?user_devices=light,switch
    
    Returns:
        List of possibilities grouped by use case (energy, comfort, security, convenience)
    """
    logger.info(f"Device possibilities request: {device_type}")

    repo = CorpusRepository(db)
    recommender = DeviceRecommender(repo)

    user_device_list = [d.strip() for d in user_devices.split(',') if d.strip()]

    try:
        possibilities = await recommender.get_device_possibilities(
            device_type=device_type,
            user_devices=user_device_list
        )

        logger.info(f"Found {len(possibilities)} use cases for {device_type}")

        return {
            "device_type": device_type,
            "possibilities": possibilities,
            "count": len(possibilities)
        }

    except Exception as e:
        logger.error(f"Failed to get device possibilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations", response_model=list[DeviceRecommendation])
async def get_device_recommendations(
    user_devices: str = Query(..., description="Comma-separated list of user's current devices"),
    user_integrations: str = Query("", description="Comma-separated list of user's integrations"),
    limit: int = Query(10, ge=1, le=50, description="Maximum recommendations"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get device purchase recommendations based on ROI
    
    Analyzes which devices would unlock the most high-value automations
    and calculates ROI score for each.
    
    Example:
        GET /api/automation-miner/devices/recommendations?user_devices=light,switch&limit=5
    
    Returns:
        List of device recommendations sorted by ROI score (highest first)
    """
    logger.info("Device recommendations request")

    user_device_list = [d.strip() for d in user_devices.split(',') if d.strip()]
    user_integration_list = [i.strip() for i in user_integrations.split(',') if i.strip()]

    logger.info(f"User has {len(user_device_list)} devices, {len(user_integration_list)} integrations")

    repo = CorpusRepository(db)
    recommender = DeviceRecommender(repo)

    try:
        recommendations = await recommender.recommend_devices(
            user_devices=user_device_list,
            user_integrations=user_integration_list,
            limit=limit
        )

        logger.info(f"Generated {len(recommendations)} recommendations")

        if recommendations:
            logger.info(f"Top recommendation: {recommendations[0].device_type} (ROI: {recommendations[0].roi_score})")

        return recommendations

    except Exception as e:
        logger.error(f"Failed to generate recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

