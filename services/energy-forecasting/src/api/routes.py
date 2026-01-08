"""
API Routes for Energy Forecasting Service

Provides REST API endpoints for:
- Energy consumption forecasting
- Peak usage predictions
- Energy optimization recommendations
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["energy"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ForecastPoint(BaseModel):
    """Single forecast point."""
    
    timestamp: datetime
    power_watts: float
    lower_bound: float | None = None
    upper_bound: float | None = None


class ForecastResponse(BaseModel):
    """Energy forecast response."""
    
    forecast: list[ForecastPoint]
    model_type: str
    forecast_horizon_hours: int
    generated_at: datetime


class PeakPrediction(BaseModel):
    """Peak usage prediction."""
    
    peak_hour: int
    peak_power_watts: float
    peak_timestamp: datetime
    daily_total_kwh: float


class OptimizationRecommendation(BaseModel):
    """Energy optimization recommendation."""
    
    recommendation: str
    estimated_savings_kwh: float
    estimated_savings_percent: float
    best_hours: list[int]
    avoid_hours: list[int]


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    service: str
    version: str
    model_loaded: bool


# ============================================================================
# Global Model Instance
# ============================================================================

_forecaster = None
_model_path = Path("./models/energy_forecaster")


def get_forecaster():
    """Get the loaded forecaster."""
    global _forecaster
    if _forecaster is None:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Please ensure the model is trained and available."
        )
    return _forecaster


def load_model(path: Path | str | None = None) -> bool:
    """Load the forecasting model."""
    global _forecaster, _model_path
    
    from ..models.energy_forecaster import EnergyForecaster
    
    if path is not None:
        _model_path = Path(path)
    
    config_path = _model_path.with_suffix(".config.pkl")
    if not config_path.exists():
        logger.warning(f"Model config not found at {config_path}")
        return False
    
    try:
        _forecaster = EnergyForecaster.load(_model_path)
        logger.info(f"Loaded model from {_model_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return False


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="energy-forecasting",
        version="1.0.0",
        model_loaded=_forecaster is not None,
    )


@router.get("/forecast", response_model=ForecastResponse)
async def get_forecast(
    hours: int = Query(48, ge=1, le=168, description="Forecast horizon in hours"),
):
    """
    Get energy consumption forecast.
    
    Returns predicted power consumption for the next N hours.
    """
    forecaster = get_forecaster()
    
    try:
        # Generate forecast
        forecast_series = forecaster.predict(n=hours)
        
        # Convert to response format
        timestamps = forecast_series.time_index.to_pydatetime()
        values = forecast_series.values().flatten()
        
        forecast_points = [
            ForecastPoint(
                timestamp=ts,
                power_watts=float(val),
            )
            for ts, val in zip(timestamps, values)
        ]
        
        return ForecastResponse(
            forecast=forecast_points,
            model_type=forecaster.model_type,
            forecast_horizon_hours=hours,
            generated_at=datetime.now(),
        )
        
    except Exception as e:
        logger.error(f"Forecast error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/peak-prediction", response_model=PeakPrediction)
async def get_peak_prediction():
    """
    Predict peak energy usage for the next 24 hours.
    
    Returns the hour with highest predicted consumption.
    """
    forecaster = get_forecaster()
    
    try:
        # Get 24-hour forecast
        forecast_series = forecaster.predict(n=24)
        
        timestamps = forecast_series.time_index.to_pydatetime()
        values = forecast_series.values().flatten()
        
        # Find peak
        peak_idx = values.argmax()
        peak_timestamp = timestamps[peak_idx]
        peak_power = float(values[peak_idx])
        
        # Calculate daily total (kWh)
        daily_total_kwh = float(values.sum()) / 1000
        
        return PeakPrediction(
            peak_hour=peak_timestamp.hour,
            peak_power_watts=peak_power,
            peak_timestamp=peak_timestamp,
            daily_total_kwh=daily_total_kwh,
        )
        
    except Exception as e:
        logger.error(f"Peak prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optimization", response_model=OptimizationRecommendation)
async def get_optimization_recommendation():
    """
    Get energy optimization recommendations.
    
    Suggests best and worst hours for running high-power appliances.
    """
    forecaster = get_forecaster()
    
    try:
        # Get 24-hour forecast
        forecast_series = forecaster.predict(n=24)
        
        timestamps = forecast_series.time_index.to_pydatetime()
        values = forecast_series.values().flatten()
        
        # Find best (lowest) and worst (highest) hours
        hour_values = [(ts.hour, val) for ts, val in zip(timestamps, values)]
        hour_values.sort(key=lambda x: x[1])
        
        best_hours = [h for h, _ in hour_values[:4]]
        avoid_hours = [h for h, _ in hour_values[-4:]]
        
        # Estimate savings (shifting 1kWh from peak to off-peak)
        peak_avg = sum(v for _, v in hour_values[-4:]) / 4
        offpeak_avg = sum(v for _, v in hour_values[:4]) / 4
        
        savings_percent = (peak_avg - offpeak_avg) / peak_avg * 100 if peak_avg > 0 else 0
        
        return OptimizationRecommendation(
            recommendation=f"Shift high-power activities to {best_hours[0]}:00-{best_hours[-1]}:00 to reduce peak load",
            estimated_savings_kwh=round((peak_avg - offpeak_avg) / 1000, 2),
            estimated_savings_percent=round(savings_percent, 1),
            best_hours=best_hours,
            avoid_hours=avoid_hours,
        )
        
    except Exception as e:
        logger.error(f"Optimization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model/info")
async def get_model_info() -> dict[str, Any]:
    """Get information about the loaded model."""
    if _forecaster is None:
        return {
            "loaded": False,
            "model_path": str(_model_path),
        }
    
    info = _forecaster.get_model_info()
    info["loaded"] = True
    info["model_path"] = str(_model_path)
    
    return info
