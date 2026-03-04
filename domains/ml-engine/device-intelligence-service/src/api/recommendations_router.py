"""
Device Intelligence Service - Recommendations API

API endpoints for optimization recommendations and impact analysis.
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.cache import DeviceCache
from ..core.database import get_db_session
from ..core.health_scorer import health_scorer
from ..core.recommendation_engine import (
    OptimizationRecommendation,
    RecommendationCategory,
    RecommendationPriority,
    recommendation_engine,
)
from ..core.repository import DeviceRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])


def get_device_repository() -> DeviceRepository:
    """Get device repository instance."""
    cache = DeviceCache()
    return DeviceRepository(cache)


@router.get("/")
async def get_all_recommendations(
    skip: int = Query(default=0, ge=0, description="Number of recommendations to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of recommendations to return"),
    category: str | None = Query(default=None, description="Filter by recommendation category"),
    priority: str | None = Query(default=None, description="Filter by priority level"),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0, description="Minimum confidence score"),
    session: AsyncSession = Depends(get_db_session),
    repository: DeviceRepository = Depends(get_device_repository)
):
    """Get all optimization recommendations with optional filtering."""
    try:
        all_recommendations = []

        # Get all devices
        devices = await repository.get_all_devices(session, limit=1000)

        for device in devices:
            try:
                # Get device health metrics
                metrics_list = await repository.get_device_health_metrics(session, device.id)

                if metrics_list:
                    # Use the most recent metric
                    latest_metric = metrics_list[0]
                    current_metrics = {
                        "response_time": latest_metric.response_time or 0,
                        "error_rate": latest_metric.error_rate or 0,
                        "battery_level": latest_metric.battery_level or 100,
                        "signal_strength": latest_metric.signal_strength or -50,
                        "usage_frequency": latest_metric.usage_frequency or 0.5,
                        "cpu_usage": latest_metric.cpu_usage or 0,
                        "memory_usage": latest_metric.memory_usage or 0,
                        "temperature": latest_metric.temperature or 25
                    }

                    # Convert historical metrics
                    historical_metrics = []
                    for metric in metrics_list[:50]:
                        historical_metrics.append({
                            "response_time": metric.response_time or 0,
                            "error_rate": metric.error_rate or 0,
                            "battery_level": metric.battery_level or 100,
                            "signal_strength": metric.signal_strength or -50,
                            "usage_frequency": metric.usage_frequency or 0.5,
                            "cpu_usage": metric.cpu_usage or 0,
                            "memory_usage": metric.memory_usage or 0,
                            "temperature": metric.temperature or 25,
                            "timestamp": metric.timestamp
                        })
                else:
                    # Default metrics
                    current_metrics = {
                        "response_time": 0, "error_rate": 0, "battery_level": 100,
                        "signal_strength": -50, "usage_frequency": 0.5, "cpu_usage": 0,
                        "memory_usage": 0, "temperature": 25
                    }
                    historical_metrics = []

                # Calculate health score
                health_score = await health_scorer.calculate_health_score(
                    device.id, current_metrics, historical_metrics
                )

                # Generate recommendations
                device_recommendations = await recommendation_engine.generate_recommendations(
                    device.id, health_score, current_metrics, historical_metrics
                )

                all_recommendations.extend(device_recommendations)

            except Exception as e:
                logger.error(f"Error processing device {device.id}: {e}")
                continue

        # Apply filters
        filtered_recommendations = []
        for rec in all_recommendations:
            # Category filter
            if category and rec.category.value != category:
                continue

            # Priority filter
            if priority and rec.priority.value != priority:
                continue

            # Confidence filter
            if rec.confidence_score < min_confidence:
                continue

            filtered_recommendations.append(rec)

        # Apply pagination
        paginated_recommendations = filtered_recommendations[skip:skip+limit]

        # Convert to response format
        recommendations_data = []
        for rec in paginated_recommendations:
            recommendations_data.append({
                "id": rec.id,
                "device_id": rec.device_id,
                "category": rec.category.value,
                "title": rec.title,
                "description": rec.description,
                "priority": rec.priority.value,
                "confidence_score": rec.confidence_score,
                "estimated_impact": rec.estimated_impact,
                "implementation_steps": rec.implementation_steps,
                "prerequisites": rec.prerequisites,
                "created_at": rec.created_at.isoformat(),
                "expires_at": rec.expires_at.isoformat() if rec.expires_at else None,
                "status": rec.status
            })

        # Get impact analysis
        impact_analysis = await recommendation_engine.get_recommendation_impact_analysis(
            filtered_recommendations
        )

        return {
            "recommendations": recommendations_data,
            "total_count": len(filtered_recommendations),
            "impact_analysis": impact_analysis,
            "filters_applied": {
                "skip": skip,
                "limit": limit,
                "category": category,
                "priority": priority,
                "min_confidence": min_confidence
            },
            "timestamp": datetime.now(UTC).isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{device_id}")
async def get_device_recommendations(
    device_id: str,
    category: str | None = Query(default=None, description="Filter by recommendation category"),
    priority: str | None = Query(default=None, description="Filter by priority level"),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0, description="Minimum confidence score"),
    session: AsyncSession = Depends(get_db_session),
    repository: DeviceRepository = Depends(get_device_repository)
):
    """Get optimization recommendations for a specific device."""
    try:
        # Get device
        device = await repository.get_device(session, device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        # Get device health metrics
        metrics_list = await repository.get_device_health_metrics(session, device_id)

        if metrics_list:
            # Use the most recent metric
            latest_metric = metrics_list[0]
            current_metrics = {
                "response_time": latest_metric.response_time or 0,
                "error_rate": latest_metric.error_rate or 0,
                "battery_level": latest_metric.battery_level or 100,
                "signal_strength": latest_metric.signal_strength or -50,
                "usage_frequency": latest_metric.usage_frequency or 0.5,
                "cpu_usage": latest_metric.cpu_usage or 0,
                "memory_usage": latest_metric.memory_usage or 0,
                "temperature": latest_metric.temperature or 25
            }

            # Convert historical metrics
            historical_metrics = []
            for metric in metrics_list[:50]:
                historical_metrics.append({
                    "response_time": metric.response_time or 0,
                    "error_rate": metric.error_rate or 0,
                    "battery_level": metric.battery_level or 100,
                    "signal_strength": metric.signal_strength or -50,
                    "usage_frequency": metric.usage_frequency or 0.5,
                    "cpu_usage": metric.cpu_usage or 0,
                    "memory_usage": metric.memory_usage or 0,
                    "temperature": metric.temperature or 25,
                    "timestamp": metric.timestamp
                })
        else:
            # Default metrics
            current_metrics = {
                "response_time": 0, "error_rate": 0, "battery_level": 100,
                "signal_strength": -50, "usage_frequency": 0.5, "cpu_usage": 0,
                "memory_usage": 0, "temperature": 25
            }
            historical_metrics = []

        # Calculate health score
        health_score = await health_scorer.calculate_health_score(
            device_id, current_metrics, historical_metrics
        )

        # Generate recommendations
        recommendations = await recommendation_engine.generate_recommendations(
            device_id, health_score, current_metrics, historical_metrics
        )

        # Apply filters
        filtered_recommendations = []
        for rec in recommendations:
            # Category filter
            if category and rec.category.value != category:
                continue

            # Priority filter
            if priority and rec.priority.value != priority:
                continue

            # Confidence filter
            if rec.confidence_score < min_confidence:
                continue

            filtered_recommendations.append(rec)

        # Convert to response format
        recommendations_data = []
        for rec in filtered_recommendations:
            recommendations_data.append({
                "id": rec.id,
                "device_id": rec.device_id,
                "category": rec.category.value,
                "title": rec.title,
                "description": rec.description,
                "priority": rec.priority.value,
                "confidence_score": rec.confidence_score,
                "estimated_impact": rec.estimated_impact,
                "implementation_steps": rec.implementation_steps,
                "prerequisites": rec.prerequisites,
                "created_at": rec.created_at.isoformat(),
                "expires_at": rec.expires_at.isoformat() if rec.expires_at else None,
                "status": rec.status
            })

        # Get impact analysis
        impact_analysis = await recommendation_engine.get_recommendation_impact_analysis(
            filtered_recommendations
        )

        return {
            "device_id": device_id,
            "device_name": device.name,
            "recommendations": recommendations_data,
            "total_count": len(filtered_recommendations),
            "impact_analysis": impact_analysis,
            "filters_applied": {
                "category": category,
                "priority": priority,
                "min_confidence": min_confidence
            },
            "timestamp": datetime.now(UTC).isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendations for device {device_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/categories/{category}")
async def get_recommendations_by_category(
    category: str,
    skip: int = Query(default=0, ge=0, description="Number of recommendations to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of recommendations to return"),
    priority: str | None = Query(default=None, description="Filter by priority level"),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0, description="Minimum confidence score"),
    session: AsyncSession = Depends(get_db_session),
    repository: DeviceRepository = Depends(get_device_repository)
):
    """Get recommendations filtered by category."""
    try:
        # Validate category
        try:
            RecommendationCategory(category)  # validates the category value
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category. Must be one of: {[c.value for c in RecommendationCategory]}"
            ) from exc

        # Get all recommendations with category filter
        response = await get_all_recommendations(
            skip=skip, limit=limit, category=category, priority=priority,
            min_confidence=min_confidence, session=session, repository=repository
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendations by category {category}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/impact/analysis")
async def get_recommendation_impact_analysis(
    session: AsyncSession = Depends(get_db_session),
    repository: DeviceRepository = Depends(get_device_repository)
):
    """Get comprehensive impact analysis of all recommendations."""
    try:
        # Get all recommendations
        response = await get_all_recommendations(
            skip=0, limit=1000, session=session, repository=repository
        )

        # Extract recommendations for analysis
        recommendations = []
        for rec_data in response["recommendations"]:
            # Create temporary recommendation object for analysis
            rec = OptimizationRecommendation(
                device_id=rec_data["device_id"],
                category=RecommendationCategory(rec_data["category"]),
                title=rec_data["title"],
                description=rec_data["description"],
                priority=RecommendationPriority(rec_data["priority"]),
                confidence_score=rec_data["confidence_score"],
                estimated_impact=rec_data["estimated_impact"],
                implementation_steps=rec_data["implementation_steps"],
                prerequisites=rec_data["prerequisites"]
            )
            recommendations.append(rec)

        # Get impact analysis
        impact_analysis = await recommendation_engine.get_recommendation_impact_analysis(recommendations)

        return {
            "impact_analysis": impact_analysis,
            "total_recommendations": len(recommendations),
            "timestamp": datetime.now(UTC).isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting impact analysis: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/apply")
async def apply_recommendation(
    recommendation_id: str,
    session: AsyncSession = Depends(get_db_session),
    repository: DeviceRepository = Depends(get_device_repository)
):
    """Apply a recommendation by validating, checking prerequisites, and marking as applied."""
    try:
        # Step 1: Parse recommendation_id to extract device_id and category.
        # Format: {device_id}_{category}_{timestamp}
        parts = recommendation_id.rsplit("_", 2)
        if len(parts) < 3:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid recommendation_id format: {recommendation_id}"
            )
        device_id, category_value, _timestamp = parts

        # Validate category value
        try:
            RecommendationCategory(category_value)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category '{category_value}' in recommendation_id"
            ) from exc

        # Step 2: Check if already applied
        if recommendation_engine.is_applied(recommendation_id):
            raise HTTPException(
                status_code=409,
                detail="Recommendation has already been applied"
            )

        # Step 3: Validate device exists
        device = await repository.get_device(session, device_id)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")

        # Generate current recommendations to find the matching one
        metrics_list = await repository.get_device_health_metrics(session, device_id)
        if metrics_list:
            latest_metric = metrics_list[0]
            current_metrics = {
                "response_time": latest_metric.response_time or 0,
                "error_rate": latest_metric.error_rate or 0,
                "battery_level": latest_metric.battery_level or 100,
                "signal_strength": latest_metric.signal_strength or -50,
                "usage_frequency": latest_metric.usage_frequency or 0.5,
                "cpu_usage": latest_metric.cpu_usage or 0,
                "memory_usage": latest_metric.memory_usage or 0,
                "temperature": latest_metric.temperature or 25,
            }
            historical_metrics = [
                {
                    "response_time": m.response_time or 0,
                    "error_rate": m.error_rate or 0,
                    "battery_level": m.battery_level or 100,
                    "signal_strength": m.signal_strength or -50,
                    "usage_frequency": m.usage_frequency or 0.5,
                    "cpu_usage": m.cpu_usage or 0,
                    "memory_usage": m.memory_usage or 0,
                    "temperature": m.temperature or 25,
                    "timestamp": m.timestamp,
                }
                for m in metrics_list[:50]
            ]
        else:
            current_metrics = {
                "response_time": 0, "error_rate": 0, "battery_level": 100,
                "signal_strength": -50, "usage_frequency": 0.5, "cpu_usage": 0,
                "memory_usage": 0, "temperature": 25,
            }
            historical_metrics = []

        health_score = await health_scorer.calculate_health_score(
            device_id, current_metrics, historical_metrics
        )
        recommendations = await recommendation_engine.generate_recommendations(
            device_id, health_score, current_metrics, historical_metrics
        )

        # Find the matching recommendation by device_id and category
        matched = next(
            (r for r in recommendations if r.device_id == device_id and r.category.value == category_value),
            None,
        )
        if not matched:
            raise HTTPException(
                status_code=404,
                detail=f"No active recommendation found for device '{device_id}' in category '{category_value}'"
            )

        # Step 4: Mark recommendation as applied
        matched.status = "applied"
        recommendation_engine.mark_applied(recommendation_id)

        # Step 5: Log the application event
        logger.info(
            "Applied recommendation %s for device %s (category=%s, priority=%s)",
            recommendation_id, device_id, matched.category.value, matched.priority.value,
        )

        return {
            "message": "Recommendation applied successfully",
            "recommendation_id": recommendation_id,
            "device_id": device_id,
            "category": matched.category.value,
            "title": matched.title,
            "priority": matched.priority.value,
            "implementation_steps": matched.implementation_steps,
            "prerequisites": matched.prerequisites,
            "status": matched.status,
            "applied_at": datetime.now(UTC).isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error applying recommendation %s: %s", recommendation_id, e)
        raise HTTPException(status_code=500, detail="Internal server error") from e
