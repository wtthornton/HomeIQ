"""
Device Intelligence Service - Health API

API endpoints for device health scoring and monitoring.
"""

import logging
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.cache import DeviceCache
from ..core.database import get_db_session
from ..core.device_state_tracker import device_state_tracker
from ..core.health_scorer import health_scorer
from ..core.repository import DeviceRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/health", tags=["Health"])


def get_device_repository() -> DeviceRepository:
    """Get device repository instance."""
    cache = DeviceCache()
    return DeviceRepository(cache)


@router.get("/scores")
async def get_all_health_scores(
    skip: int = Query(default=0, ge=0, description="Number of devices to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of devices to return"),
    min_score: int = Query(default=0, ge=0, le=100, description="Minimum health score filter"),
    max_score: int = Query(default=100, ge=0, le=100, description="Maximum health score filter"),
    health_status: str | None = Query(default=None, description="Filter by health status"),
    session: AsyncSession = Depends(get_db_session),
    repository: DeviceRepository = Depends(get_device_repository)
):
    """Get all device health scores with optional filtering."""
    try:
        health_scores = []

        # Get all devices from database
        devices = await repository.get_all_devices(session, limit=limit)

        for device in devices[skip:skip+limit]:
            try:
                # Get device health metrics from database
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

                    # Convert historical metrics to dict format
                    historical_metrics = []
                    for metric in metrics_list[:50]:  # Last 50 metrics
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
                    # Default metrics if no data available
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

                # Apply filters
                if min_score <= health_score["overall_score"] <= max_score:
                    if health_status is None or health_score["health_status"] == health_status:
                        health_scores.append(health_score)

            except Exception as e:
                logger.error(f"Error calculating health score for device {device.id}: {e}")
                continue

        # Get summary statistics
        summary = health_scorer.get_health_score_summary(health_scores)

        return {
            "health_scores": health_scores,
            "summary": summary,
            "filters_applied": {
                "skip": skip,
                "limit": limit,
                "min_score": min_score,
                "max_score": max_score,
                "health_status": health_status
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting all health scores: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get health scores: {str(e)}")


@router.get("/scores/{device_id}")
async def get_device_health_score(device_id: str):
    """Get specific device health score."""
    try:
        # Get device state
        device_state = device_state_tracker.get_device_state(device_id)
        if not device_state:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

        # Get current metrics
        current_metrics = {
            "response_time": device_state.get("response_time", 0),
            "error_rate": device_state.get("error_rate", 0),
            "battery_level": device_state.get("battery_level"),
            "signal_strength": device_state.get("signal_strength"),
            "usage_frequency": device_state.get("usage_frequency", 0.5),
            "cpu_usage": device_state.get("cpu_usage"),
            "memory_usage": device_state.get("memory_usage"),
            "temperature": device_state.get("temperature")
        }

        # Get historical metrics
        historical_metrics = device_state_tracker.get_device_metrics(device_id, limit=100)

        # Calculate health score
        health_score = await health_scorer.calculate_health_score(
            device_id, current_metrics, historical_metrics
        )

        return health_score

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting health score for device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get health score: {str(e)}")


@router.get("/trends/{device_id}")
async def get_device_health_trends(
    device_id: str,
    days: int = Query(default=7, ge=1, le=30, description="Number of days to analyze")
):
    """Get device health trends over time."""
    try:
        # Get device state
        device_state = device_state_tracker.get_device_state(device_id)
        if not device_state:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

        # Get historical metrics for the specified period
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        historical_metrics = device_state_tracker.get_device_metrics(device_id, limit=1000)

        # Filter by time range
        filtered_metrics = [
            m for m in historical_metrics
            if m["timestamp"] >= cutoff_time
        ]

        if not filtered_metrics:
            return {
                "device_id": device_id,
                "trends": [],
                "summary": {
                    "total_data_points": 0,
                    "time_range": f"{days} days",
                    "message": "No data available for the specified time range"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # Calculate health scores for each data point
        trends = []
        for metrics in filtered_metrics:
            try:
                health_score = await health_scorer.calculate_health_score(
                    device_id, metrics, []
                )
                trends.append({
                    "timestamp": metrics["timestamp"].isoformat(),
                    "overall_score": health_score["overall_score"],
                    "health_status": health_score["health_status"],
                    "factor_scores": health_score["factor_scores"]
                })
            except Exception as e:
                logger.warning(f"Error calculating trend score for {device_id}: {e}")
                continue

        # Calculate trend summary
        if trends:
            scores = [t["overall_score"] for t in trends]
            avg_score = statistics.mean(scores)
            min_score = min(scores)
            max_score = max(scores)

            # Calculate trend direction
            if len(scores) >= 2:
                first_half = scores[:len(scores)//2]
                second_half = scores[len(scores)//2:]
                trend_direction = "improving" if statistics.mean(second_half) > statistics.mean(first_half) else "declining"
            else:
                trend_direction = "insufficient_data"
        else:
            avg_score = min_score = max_score = 0
            trend_direction = "no_data"

        return {
            "device_id": device_id,
            "trends": trends,
            "summary": {
                "total_data_points": len(trends),
                "time_range": f"{days} days",
                "average_score": round(avg_score, 1),
                "min_score": min_score,
                "max_score": max_score,
                "trend_direction": trend_direction
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting health trends for device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get health trends: {str(e)}")


@router.get("/comparison")
async def compare_device_health_scores(
    device_ids: str | None = Query(default=None, description="Comma-separated list of device IDs to compare")
):
    """Compare device health scores."""
    try:
        # Get device IDs to compare
        if device_ids:
            target_device_ids = [d.strip() for d in device_ids.split(",")]
        else:
            # Compare all devices
            target_device_ids = list(device_state_tracker.get_all_device_states().keys())

        if not target_device_ids:
            return {
                "comparison": [],
                "summary": {
                    "total_devices": 0,
                    "message": "No devices found for comparison"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # Calculate health scores for each device
        health_scores = []
        for device_id in target_device_ids:
            try:
                device_state = device_state_tracker.get_device_state(device_id)
                if not device_state:
                    continue

                current_metrics = {
                    "response_time": device_state.get("response_time", 0),
                    "error_rate": device_state.get("error_rate", 0),
                    "battery_level": device_state.get("battery_level"),
                    "signal_strength": device_state.get("signal_strength"),
                    "usage_frequency": device_state.get("usage_frequency", 0.5),
                    "cpu_usage": device_state.get("cpu_usage"),
                    "memory_usage": device_state.get("memory_usage"),
                    "temperature": device_state.get("temperature")
                }

                historical_metrics = device_state_tracker.get_device_metrics(device_id, limit=50)

                health_score = await health_scorer.calculate_health_score(
                    device_id, current_metrics, historical_metrics
                )
                health_scores.append(health_score)

            except Exception as e:
                logger.error(f"Error calculating health score for device {device_id}: {e}")
                continue

        # Calculate comparison statistics
        if health_scores:
            scores = [hs["overall_score"] for hs in health_scores]
            avg_score = statistics.mean(scores)
            min_score = min(scores)
            max_score = max(scores)

            # Health distribution
            health_distribution = {
                "excellent": len([hs for hs in health_scores if hs["health_status"] == "excellent"]),
                "good": len([hs for hs in health_scores if hs["health_status"] == "good"]),
                "fair": len([hs for hs in health_scores if hs["health_status"] == "fair"]),
                "poor": len([hs for hs in health_scores if hs["health_status"] == "poor"]),
                "critical": len([hs for hs in health_scores if hs["health_status"] == "critical"])
            }

            # Top and bottom performers
            sorted_scores = sorted(health_scores, key=lambda x: x["overall_score"], reverse=True)
            top_performers = sorted_scores[:3]
            bottom_performers = sorted_scores[-3:]
        else:
            avg_score = min_score = max_score = 0
            health_distribution = {}
            top_performers = []
            bottom_performers = []

        return {
            "comparison": health_scores,
            "summary": {
                "total_devices": len(health_scores),
                "average_score": round(avg_score, 1),
                "min_score": min_score,
                "max_score": max_score,
                "health_distribution": health_distribution,
                "top_performers": top_performers,
                "bottom_performers": bottom_performers
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error comparing device health scores: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to compare health scores: {str(e)}")


@router.get("/summary")
async def get_health_summary():
    """Get overall health summary for all devices."""
    try:
        # Get all device states
        device_states = device_state_tracker.get_all_device_states()

        if not device_states:
            return {
                "summary": {
                    "total_devices": 0,
                    "message": "No devices found"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # Calculate health scores for all devices
        health_scores = []
        for device_id, state in device_states.items():
            try:
                current_metrics = {
                    "response_time": state.get("response_time", 0),
                    "error_rate": state.get("error_rate", 0),
                    "battery_level": state.get("battery_level"),
                    "signal_strength": state.get("signal_strength"),
                    "usage_frequency": state.get("usage_frequency", 0.5),
                    "cpu_usage": state.get("cpu_usage"),
                    "memory_usage": state.get("memory_usage"),
                    "temperature": state.get("temperature")
                }

                historical_metrics = device_state_tracker.get_device_metrics(device_id, limit=20)

                health_score = await health_scorer.calculate_health_score(
                    device_id, current_metrics, historical_metrics
                )
                health_scores.append(health_score)

            except Exception as e:
                logger.error(f"Error calculating health score for device {device_id}: {e}")
                continue

        # Get summary statistics
        summary = health_scorer.get_health_score_summary(health_scores)

        return {
            "summary": summary,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting health summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get health summary: {str(e)}")


@router.post("/calculate/{device_id}")
async def calculate_device_health_score(device_id: str, metrics: dict[str, Any]):
    """Calculate health score for a device with custom metrics."""
    try:
        # Calculate health score with provided metrics
        health_score = await health_scorer.calculate_health_score(device_id, metrics)

        return {
            "status": "success",
            "health_score": health_score,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error calculating custom health score for device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate health score: {str(e)}")
