"""
Predictive Analytics API Router

This module provides REST API endpoints for predictive analytics functionality
including failure predictions, maintenance recommendations, and model management.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from starlette.requests import Request
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
        from ..config import Settings
        settings = Settings()
        _analytics_engine = PredictiveAnalyticsEngine(settings)
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


class IncrementalUpdateRequest(BaseModel):
    """Request model for incremental model updates."""
    new_data: list[dict[str, Any]]
    device_ids: list[str] | None = None


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


@router.post("/incremental-update")
async def incremental_update(
    request: IncrementalUpdateRequest,
    background_tasks: BackgroundTasks,
    analytics_engine: PredictiveAnalyticsEngine = Depends(get_analytics_engine)
):
    """
    Update model incrementally with new data (10-50x faster than full retrain).
    
    Requires ML_USE_INCREMENTAL=true in configuration.
    """
    try:
        from ..config import Settings
        settings = Settings()
        
        if not settings.ML_USE_INCREMENTAL:
            raise HTTPException(
                status_code=400,
                detail="Incremental learning not enabled. Set ML_USE_INCREMENTAL=true"
            )
        
        if not analytics_engine.is_trained:
            raise HTTPException(
                status_code=400,
                detail="Model not trained. Train model first before incremental updates."
            )
        
        # Process incremental update in background
        background_tasks.add_task(
            analytics_engine.incremental_update,
            request.new_data
        )
        
        return {
            "message": "Incremental update started",
            "status": "updating",
            "samples": len(request.new_data),
            "started_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error starting incremental update: {e}")
        raise HTTPException(status_code=500, detail=f"Error starting incremental update: {str(e)}")


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


@router.post("/train/schedule")
async def trigger_training_now(
    request: Request,
    mode: str | None = None
):
    """
    Manually trigger model training immediately.
    
    Epic 46.2: Built-in Nightly Training Scheduler
    
    Args:
        mode: Optional training mode ('full' or 'incremental'). Uses default from settings if not provided.
    
    Returns:
        Training status and information
    """
    try:
        # Get scheduler from app state
        if not hasattr(request.app.state, 'training_scheduler'):
            raise HTTPException(
                status_code=503,
                detail="Training scheduler not available"
            )
        
        scheduler: TrainingScheduler = request.app.state.training_scheduler
        
        # Validate mode if provided
        if mode and mode not in ['full', 'incremental']:
            raise HTTPException(
                status_code=400,
                detail="Mode must be 'full' or 'incremental'"
            )
        
        # Trigger training
        result = await scheduler.trigger_training_now(mode=mode)
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error triggering training: {e}")
        raise HTTPException(status_code=500, detail=f"Error triggering training: {str(e)}")


@router.get("/train/status")
async def get_training_status(request: Request):
    """
    Get training scheduler status and information.
    
    Epic 46.2: Built-in Nightly Training Scheduler
    
    Returns:
        Scheduler status, last training info, and next run time
    """
    try:
        # Get scheduler from app state
        if not hasattr(request.app.state, 'training_scheduler'):
            return {
                "enabled": False,
                "message": "Training scheduler not available"
            }
        
        scheduler: TrainingScheduler = request.app.state.training_scheduler
        return scheduler.get_status()
    
    except Exception as e:
        logger.error(f"❌ Error getting training status: {e}")
        return {
            "enabled": False,
            "error": str(e)
        }


@router.get("/models/version")
async def get_model_version(
    engine: PredictiveAnalyticsEngine = Depends(get_analytics_engine)
):
    """
    Get model version and metadata (2025: Production deployment endpoint).
    
    Returns:
        Model version, training date, and performance metrics
    """
    try:
        if not engine.is_trained:
            raise HTTPException(
                status_code=404,
                detail="Models not trained or loaded"
            )
        
        metadata = engine.model_metadata.copy() if hasattr(engine, 'model_metadata') else {}
        
        return {
            "version": metadata.get("version", "unknown"),
            "training_date": metadata.get("training_date"),
            "model_performance": engine.model_performance,
            "training_data_stats": metadata.get("training_data_stats", {}),
            "model_type": metadata.get("model_type", "unknown"),
            "scikit_learn_version": metadata.get("scikit_learn_version"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model version: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting model version: {str(e)}")


@router.get("/models/health")
async def get_model_health(
    engine: PredictiveAnalyticsEngine = Depends(get_analytics_engine)
):
    """
    Health check endpoint for ML models (2025: Production deployment).
    
    Returns:
        Health status with detailed diagnostics
    """
    try:
        import os
        from pathlib import Path
        
        models_dir = Path(engine.models_dir)
        
        # Check all required files
        failure_model_path = models_dir / "failure_prediction_model.pkl"
        anomaly_model_path = models_dir / "anomaly_detection_model.pkl"
        metadata_path = models_dir / "model_metadata.json"
        
        checks = {
            "models_loaded": engine.is_trained,
            "failure_model_exists": failure_model_path.exists(),
            "anomaly_model_exists": anomaly_model_path.exists(),
            "metadata_exists": metadata_path.exists(),
            "models_dir_exists": models_dir.exists()
        }
        
        # Calculate overall health
        all_checks_passed = all(checks.values())
        health_status = "healthy" if all_checks_passed else "unhealthy"
        
        # Get file sizes if they exist
        file_sizes = {}
        if failure_model_path.exists():
            file_sizes["failure_model"] = failure_model_path.stat().st_size
        if anomaly_model_path.exists():
            file_sizes["anomaly_model"] = anomaly_model_path.stat().st_size
        if metadata_path.exists():
            file_sizes["metadata"] = metadata_path.stat().st_size
        
        # Get model metadata if available
        metadata = {}
        if metadata_path.exists():
            try:
                import json
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load metadata: {e}")
        
        return {
            "status": health_status,
            "checks": checks,
            "file_sizes": file_sizes,
            "model_version": metadata.get("version", "unknown"),
            "training_date": metadata.get("training_date"),
            "model_performance": engine.model_performance if engine.is_trained else {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error in model health check: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }