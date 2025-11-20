"""
Predictive Analytics API Router

This module provides REST API endpoints for predictive analytics functionality
including failure predictions, maintenance recommendations, and model management.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.cache import DeviceCache
from ..core.database import get_db_session
from ..core.predictive_analytics import PredictiveAnalyticsEngine
from ..core.repository import DeviceRepository

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/predictions", tags=["Predictions"])

# Global analytics engine instance
_analytics_engine: PredictiveAnalyticsEngine | None = None


def get_analytics_engine() -> PredictiveAnalyticsEngine:
    """Get or create analytics engine instance."""
    global _analytics_engine
    if _analytics_engine is None:
        _analytics_engine = PredictiveAnalyticsEngine()
    return _analytics_engine


def get_device_repository() -> DeviceRepository:
    """Get device repository instance."""
    cache = DeviceCache()
    return DeviceRepository(cache)


class PredictionRequest(BaseModel):
    """Request model for prediction operations."""
    device_id: str
    metrics: dict[str, Any]


class TrainingRequest(BaseModel):
    """Request model for model training."""
    force_retrain: bool = False
    days_back: int = 180


@router.get("/failures")
async def get_failure_predictions(
    skip: int = 0,
    limit: int = 100,
    min_probability: float = 0.0,
    max_probability: float = 1.0,
    risk_level: str | None = None,
    session: AsyncSession = Depends(get_db_session),
    repository: DeviceRepository = Depends(get_device_repository),
    analytics_engine: PredictiveAnalyticsEngine = Depends(get_analytics_engine)
):
    """Get failure predictions for all devices."""
    try:
        devices = await repository.get_all_devices(session, limit=limit)
        devices_metrics = {}

        for device in devices:
            metrics_list = await repository.get_device_health_metrics(session, device.id)
            # Convert DeviceHealthMetric objects to dictionary format
            if metrics_list:
                # Use the most recent metric
                latest_metric = metrics_list[0]
                metrics = {
                    "response_time": latest_metric.response_time or 0,
                    "error_rate": latest_metric.error_rate or 0,
                    "battery_level": latest_metric.battery_level or 0,
                    "signal_strength": latest_metric.signal_strength or 0,
                    "usage_frequency": latest_metric.usage_frequency or 0,
                    "temperature": latest_metric.temperature or 0,
                    "humidity": latest_metric.humidity or 0,
                    "uptime_hours": latest_metric.uptime_hours or 0,
                    "restart_count": latest_metric.restart_count or 0,
                    "connection_drops": latest_metric.connection_drops or 0,
                    "data_transfer_rate": latest_metric.data_transfer_rate or 0
                }
            else:
                # Default metrics if no data available
                metrics = {
                    "response_time": 0, "error_rate": 0, "battery_level": 0,
                    "signal_strength": 0, "usage_frequency": 0, "temperature": 0,
                    "humidity": 0, "uptime_hours": 0, "restart_count": 0,
                    "connection_drops": 0, "data_transfer_rate": 0
                }
            devices_metrics[device.id] = metrics

        predictions = await analytics_engine.predict_all_devices(devices_metrics)

        # Apply filters
        filtered_predictions = []
        for prediction in predictions:
            probability = prediction.get("failure_probability", 0) / 100

            if min_probability <= probability <= max_probability:
                if risk_level is None or prediction.get("risk_level") == risk_level:
                    filtered_predictions.append(prediction)

        return {
            "total_predictions": len(filtered_predictions),
            "predictions": filtered_predictions,
            "filters": {
                "min_probability": min_probability,
                "max_probability": max_probability,
                "risk_level": risk_level
            }
        }

    except Exception as e:
        logger.error(f"❌ Error getting failure predictions: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting predictions: {str(e)}")


@router.get("/failures/{device_id}")
async def get_device_failure_prediction(
    device_id: str,
    session: AsyncSession = Depends(get_db_session),
    repository: DeviceRepository = Depends(get_device_repository),
    analytics_engine: PredictiveAnalyticsEngine = Depends(get_analytics_engine)
):
    """Get failure prediction for specific device."""
    try:
        device = await repository.get_device(session, device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        metrics_list = await repository.get_device_health_metrics(session, device_id)
        if not metrics_list:
            raise HTTPException(status_code=404, detail="Device metrics not found")

        # Convert DeviceHealthMetric objects to dictionary format
        latest_metric = metrics_list[0]
        metrics = {
            "response_time": latest_metric.response_time or 0,
            "error_rate": latest_metric.error_rate or 0,
            "battery_level": latest_metric.battery_level or 0,
            "signal_strength": latest_metric.signal_strength or 0,
            "usage_frequency": latest_metric.usage_frequency or 0,
            "temperature": latest_metric.temperature or 0,
            "humidity": latest_metric.humidity or 0,
            "uptime_hours": latest_metric.uptime_hours or 0,
            "restart_count": latest_metric.restart_count or 0,
            "connection_drops": latest_metric.connection_drops or 0,
            "data_transfer_rate": latest_metric.data_transfer_rate or 0
        }
        prediction = await analytics_engine.predict_device_failure(device_id, metrics)

        return prediction

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting prediction for device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting prediction: {str(e)}")


@router.get("/maintenance")
async def get_maintenance_recommendations(
    session: AsyncSession = Depends(get_db_session),
    repository: DeviceRepository = Depends(get_device_repository),
    analytics_engine: PredictiveAnalyticsEngine = Depends(get_analytics_engine)
):
    """Get maintenance recommendations for all devices."""
    try:
        devices = await repository.get_all_devices(session)
        recommendations = []

        for device in devices:
            metrics = await repository.get_device_health_metrics(session, device.id)
            prediction = await analytics_engine.predict_device_failure(device.id, metrics)

            if prediction.get("failure_probability", 0) > 30:  # > 30% failure risk
                recommendations.append({
                    "device_id": device.id,
                    "device_name": device.name,
                    "failure_probability": prediction["failure_probability"],
                    "risk_level": prediction["risk_level"],
                    "recommendations": prediction["recommendations"],
                    "priority": "high" if prediction["failure_probability"] > 60 else "medium",
                    "predicted_at": prediction["predicted_at"]
                })

        # Sort by failure probability (highest first)
        recommendations.sort(key=lambda x: x["failure_probability"], reverse=True)

        return {
            "total_recommendations": len(recommendations),
            "recommendations": recommendations
        }

    except Exception as e:
        logger.error(f"❌ Error getting maintenance recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting recommendations: {str(e)}")


@router.post("/train")
async def trigger_model_training(
    request: TrainingRequest,
    background_tasks: BackgroundTasks,
    analytics_engine: PredictiveAnalyticsEngine = Depends(get_analytics_engine)
):
    """Trigger model retraining."""
    try:
        if request.force_retrain or not analytics_engine.is_trained:
            # Pass days_back parameter to training
            background_tasks.add_task(analytics_engine.train_models, days_back=request.days_back)

            return {
                "message": "Model training started",
                "status": "training",
                "force_retrain": request.force_retrain,
                "days_back": request.days_back,
                "started_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "message": "Models are already trained",
                "status": "trained",
                "force_retrain": request.force_retrain,
                "current_version": analytics_engine.model_metadata.get("version", "unknown"),
                "started_at": datetime.now(timezone.utc).isoformat()
            }

    except Exception as e:
        logger.error(f"❌ Error starting model training: {e}")
        raise HTTPException(status_code=500, detail=f"Error starting training: {str(e)}")


@router.get("/models/status")
async def get_model_status(
    analytics_engine: PredictiveAnalyticsEngine = Depends(get_analytics_engine)
):
    """Get model status and performance."""
    try:
        status = analytics_engine.get_model_status()
        return status

    except Exception as e:
        logger.error(f"❌ Error getting model status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


@router.get("/models/compare")
async def compare_models(
    analytics_engine: PredictiveAnalyticsEngine = Depends(get_analytics_engine)
):
    """Compare current model with previous version (if backup exists)."""
    try:
        import json
        from pathlib import Path

        models_dir = Path(analytics_engine.models_dir)
        metadata_path = models_dir / "model_metadata.json"

        # Get current model metadata
        current_metadata = analytics_engine.model_metadata

        # Find most recent backup
        backup_files = sorted(
            models_dir.glob("failure_prediction_model.pkl.backup_*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if not backup_files:
            return {
                "message": "No backup models found for comparison",
                "current_version": current_metadata.get("version", "unknown"),
                "comparison_available": False
            }

        # Try to load backup metadata (if it exists)
        backup_metadata = None
        backup_path = backup_files[0]
        # Extract timestamp from filename like "failure_prediction_model.pkl.backup_20251116_223737"
        backup_timestamp = backup_path.name.split("backup_")[-1] if "backup_" in backup_path.name else None

        # Look for backup metadata (if saved separately)
        backup_metadata_path = models_dir / f"model_metadata.backup_{backup_timestamp}.json"
        if backup_metadata_path.exists():
            try:
                with open(backup_metadata_path) as f:
                    backup_metadata = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load backup metadata: {e}")

        # Compare if we have both
        comparison = {
            "current_version": current_metadata.get("version", "unknown"),
            "backup_timestamp": backup_timestamp,
            "comparison_available": backup_metadata is not None
        }

        if backup_metadata:
            # Compare versions
            comparison["version_change"] = {
                "from": backup_metadata.get("version", "unknown"),
                "to": current_metadata.get("version", "unknown")
            }

            # Compare performance
            current_perf = current_metadata.get("model_performance", {})
            backup_perf = backup_metadata.get("model_performance", {})

            comparison["performance"] = {
                "current": current_perf,
                "previous": backup_perf,
                "changes": {}
            }

            for metric in ["accuracy", "precision", "recall", "f1_score"]:
                current_val = current_perf.get(metric, 0)
                backup_val = backup_perf.get(metric, 0)
                if current_val and backup_val:
                    diff = current_val - backup_val
                    comparison["performance"]["changes"][metric] = {
                        "difference": round(diff, 4),
                        "percent_change": round((diff / backup_val) * 100, 2) if backup_val > 0 else 0,
                        "improved": diff > 0
                    }

            # Compare training data
            current_stats = current_metadata.get("training_data_stats", {})
            backup_stats = backup_metadata.get("training_data_stats", {})

            comparison["training_data"] = {
                "current": current_stats,
                "previous": backup_stats
            }

            # Compare data sources
            comparison["data_source"] = {
                "current": current_metadata.get("data_source", "unknown"),
                "previous": backup_metadata.get("data_source", "unknown")
            }

        return comparison

    except Exception as e:
        logger.error(f"❌ Error comparing models: {e}")
        raise HTTPException(status_code=500, detail=f"Error comparing models: {str(e)}")


@router.post("/predict")
async def predict_device_failure(
    request: PredictionRequest,
    analytics_engine: PredictiveAnalyticsEngine = Depends(get_analytics_engine)
):
    """Predict device failure with custom metrics."""
    try:
        prediction = await analytics_engine.predict_device_failure(
            request.device_id,
            request.metrics
        )

        return prediction

    except Exception as e:
        logger.error(f"❌ Error predicting failure for device {request.device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error making prediction: {str(e)}")


@router.get("/health")
async def get_predictions_health():
    """Get predictions service health status."""
    try:
        analytics_engine = get_analytics_engine()

        return {
            "service": "Predictive Analytics",
            "status": "operational",
            "models_trained": analytics_engine.is_trained,
            "feature_count": len(analytics_engine.feature_columns),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Error getting predictions health: {e}")
        return {
            "service": "Predictive Analytics",
            "status": "error",
            "error": str(e),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
