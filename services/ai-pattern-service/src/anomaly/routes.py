"""
Anomaly Detection API Routes

Phase 5: FastAPI endpoints for anomaly detection service.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .detector import DeviceAnomalyDetector, AnomalyAlertManager, AnomalyResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/anomaly", tags=["anomaly"])

# Global instances (in production, use dependency injection)
detector = DeviceAnomalyDetector(contamination=0.05, use_ensemble=True)
alert_manager = AnomalyAlertManager(max_alerts=1000)


# Request/Response Models
class TrainRequest(BaseModel):
    """Request to train anomaly detector for a device."""
    device_id: str = Field(..., description="Unique device identifier")
    data: list[list[float]] = Field(..., description="Training data (samples x features)")
    feature_names: list[str] | None = Field(
        None, description="Optional feature names"
    )


class PredictRequest(BaseModel):
    """Request to detect anomalies."""
    device_id: str = Field(..., description="Device identifier")
    data: list[list[float]] = Field(..., description="Data to check (samples x features)")
    device_name: str | None = Field(None, description="Human-readable device name")
    anomaly_type: str = Field("behavior", description="Type: behavior, energy, availability")


class AlertResponse(BaseModel):
    """Response with anomaly alerts."""
    alerts: list[dict[str, Any]]
    total: int
    summary: dict[str, Any] | None = None


class TrainResponse(BaseModel):
    """Response after training."""
    success: bool
    device_id: str
    message: str
    model_info: dict[str, Any] | None = None


class PredictResponse(BaseModel):
    """Response with predictions."""
    device_id: str
    anomalies_detected: int
    results: list[dict[str, Any]]


# API Endpoints
@router.post("/train", response_model=TrainResponse)
async def train_detector(request: TrainRequest) -> TrainResponse:
    """
    Train anomaly detector for a specific device.
    
    Requires at least 100 samples of normal behavior data.
    """
    import numpy as np
    
    try:
        data = np.array(request.data)
        
        if len(data) < 100:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient training data: {len(data)} < 100 required"
            )
        
        success = detector.fit(
            device_id=request.device_id,
            normal_patterns=data,
            feature_names=request.feature_names,
        )
        
        if not success:
            return TrainResponse(
                success=False,
                device_id=request.device_id,
                message="Training failed - check logs for details",
            )
        
        model_info = detector.get_model_info(request.device_id)
        
        return TrainResponse(
            success=True,
            device_id=request.device_id,
            message=f"Successfully trained on {len(data)} samples",
            model_info=model_info,
        )
        
    except Exception as e:
        logger.error(f"Training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict", response_model=PredictResponse)
async def predict_anomalies(request: PredictRequest) -> PredictResponse:
    """
    Detect anomalies in new data for a trained device.
    """
    import numpy as np
    
    if request.device_id not in detector.device_models:
        raise HTTPException(
            status_code=404,
            detail=f"No trained model for device: {request.device_id}"
        )
    
    try:
        data = np.array(request.data)
        
        results = detector.predict(
            device_id=request.device_id,
            new_data=data,
            device_name=request.device_name,
            anomaly_type=request.anomaly_type,
        )
        
        # Add anomalies to alert manager
        for result in results:
            alert_manager.add_alert(result)
        
        return PredictResponse(
            device_id=request.device_id,
            anomalies_detected=sum(1 for r in results if r.is_anomaly),
            results=[r.to_dict() for r in results],
        )
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts", response_model=AlertResponse)
async def get_alerts(
    min_severity: str = Query("low", description="Minimum severity: low, medium, high"),
    anomaly_type: str | None = Query(None, description="Filter by type"),
    limit: int = Query(50, ge=1, le=200, description="Maximum alerts to return"),
    include_acknowledged: bool = Query(False, description="Include acknowledged alerts"),
    include_summary: bool = Query(True, description="Include summary statistics"),
) -> AlertResponse:
    """
    Get anomaly alerts with filtering.
    
    Used by the health dashboard to display active anomalies.
    """
    alerts = alert_manager.get_alerts(
        min_severity=min_severity,
        anomaly_type=anomaly_type,
        limit=limit,
        include_acknowledged=include_acknowledged,
    )
    
    summary = alert_manager.get_summary() if include_summary else None
    
    return AlertResponse(
        alerts=alerts,
        total=len(alerts),
        summary=summary,
    )


@router.post("/alerts/{device_id}/acknowledge")
async def acknowledge_alert(
    device_id: str,
    timestamp: str = Query(..., description="Alert timestamp (ISO format)"),
) -> dict[str, bool]:
    """Acknowledge an alert."""
    success = alert_manager.acknowledge_alert(device_id, timestamp)
    return {"acknowledged": success}


@router.delete("/alerts/old")
async def clear_old_alerts(
    hours: int = Query(24, ge=1, le=168, description="Clear alerts older than hours"),
) -> dict[str, int]:
    """Clear alerts older than specified hours."""
    cleared = alert_manager.clear_old_alerts(hours)
    return {"cleared": cleared}


@router.get("/models")
async def list_trained_models() -> dict[str, list[str]]:
    """List all devices with trained anomaly detection models."""
    return {"devices": detector.list_trained_devices()}


@router.get("/models/{device_id}")
async def get_model_info(device_id: str) -> dict[str, Any]:
    """Get information about a trained model."""
    info = detector.get_model_info(device_id)
    
    if not info:
        raise HTTPException(
            status_code=404,
            detail=f"No trained model for device: {device_id}"
        )
    
    return info


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint for anomaly detection service."""
    return {
        "status": "healthy",
        "trained_devices": len(detector.device_models),
        "active_alerts": len(alert_manager.alerts),
        "summary": alert_manager.get_summary(),
    }
