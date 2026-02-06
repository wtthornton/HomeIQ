"""
API Routes for Energy Forecasting Service

Provides REST API endpoints for:
- Energy consumption forecasting
- Peak usage predictions
- Energy optimization recommendations
"""

import asyncio
import threading
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from .. import __version__

logger = structlog.get_logger(__name__)

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

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "forecast": [{"timestamp": "2026-02-06T00:00:00", "power_watts": 450.5}],
            "model_type": "nhits",
            "forecast_horizon_hours": 48,
            "generated_at": "2026-02-06T12:00:00",
        }
    })

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
# Thread-Safe Model Registry
# ============================================================================

@dataclass
class ModelRegistry:
    """Thread-safe model registry."""
    _forecaster: Any = None
    _model_path: Path = field(default_factory=lambda: Path("./models/energy_forecaster"))
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def get_forecaster(self):
        with self._lock:
            if self._forecaster is None:
                raise HTTPException(
                    status_code=503,
                    detail="Model not loaded. Please ensure the model is trained and available."
                )
            return self._forecaster

    def set_forecaster(self, forecaster):
        with self._lock:
            self._forecaster = forecaster

    @property
    def is_loaded(self) -> bool:
        with self._lock:
            return self._forecaster is not None

    @property
    def model_path(self) -> Path:
        return self._model_path

    @model_path.setter
    def model_path(self, value: Path):
        self._model_path = value


model_registry = ModelRegistry()


# ============================================================================
# Forecast Cache
# ============================================================================

_forecast_cache: dict[str, tuple[datetime, Any]] = {}
_cache_ttl_seconds = 300  # 5 minutes


def _get_cached_forecast(hours: int):
    """Get cached forecast if still valid."""
    key = f"forecast_{hours}"
    if key in _forecast_cache:
        cached_at, result = _forecast_cache[key]
        if (datetime.now() - cached_at).total_seconds() < _cache_ttl_seconds:
            return result
    return None


def _set_cached_forecast(hours: int, result):
    """Cache a forecast result."""
    _forecast_cache[f"forecast_{hours}"] = (datetime.now(), result)


# ============================================================================
# Model Loading
# ============================================================================

def load_model(path: Path | str | None = None) -> bool:
    """Load the forecasting model."""
    from ..models.energy_forecaster import EnergyForecaster

    if path is not None:
        model_registry.model_path = Path(path)

    model_path = model_registry.model_path

    # Check for config in either format
    config_json = model_path.with_suffix(".config.json")
    config_pkl = model_path.with_suffix(".config.pkl")

    if not config_json.exists() and not config_pkl.exists():
        logger.warning("Model config not found", path=str(model_path))
        return False

    try:
        forecaster = EnergyForecaster.load(model_path)
        model_registry.set_forecaster(forecaster)
        logger.info("Loaded model", path=str(model_path))
        return True
    except Exception as e:
        logger.error("Failed to load model", error=str(e), exc_info=True)
        return False


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint (liveness)."""
    return HealthResponse(
        status="healthy",
        service="energy-forecasting",
        version=__version__,
        model_loaded=model_registry.is_loaded,
    )


@router.get("/ready", response_model=HealthResponse)
async def readiness_check():
    """Readiness check - returns 503 if model is not loaded."""
    is_ready = model_registry.is_loaded
    if not is_ready:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return HealthResponse(
        status="ready",
        service="energy-forecasting",
        version=__version__,
        model_loaded=True,
    )


@router.get("/forecast", response_model=ForecastResponse)
async def get_forecast(
    hours: int = Query(48, ge=1, le=168, description="Forecast horizon in hours"),
):
    """
    Get energy consumption forecast.

    Returns predicted power consumption for the next N hours.
    """
    forecaster = model_registry.get_forecaster()

    # Check cache first
    cached = _get_cached_forecast(hours)
    if cached is not None:
        return cached

    try:
        # Run CPU-intensive prediction in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        forecast_series = await loop.run_in_executor(
            None, partial(forecaster.predict, n=hours)
        )

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

        result = ForecastResponse(
            forecast=forecast_points,
            model_type=forecaster.model_type,
            forecast_horizon_hours=hours,
            generated_at=datetime.now(),
        )

        # Cache result
        _set_cached_forecast(hours, result)

        return result

    except Exception as e:
        logger.error("Forecast error", exc_info=True, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while generating the forecast. Check service logs for details."
        )


@router.get("/peak-prediction", response_model=PeakPrediction)
async def get_peak_prediction():
    """
    Predict peak energy usage for the next 24 hours.

    Returns the hour with highest predicted consumption.
    """
    forecaster = model_registry.get_forecaster()

    try:
        # Run CPU-intensive prediction in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        forecast_series = await loop.run_in_executor(
            None, partial(forecaster.predict, n=24)
        )

        timestamps = forecast_series.time_index.to_pydatetime()
        values = forecast_series.values().flatten()

        # Find peak
        peak_idx = values.argmax()
        peak_timestamp = timestamps[peak_idx]
        peak_power = float(values[peak_idx])

        # Convert watts to kWh: each forecast point = 1 hour interval
        # kWh = sum(watts) * interval_hours / 1000
        interval_hours = 1  # Forecast points are hourly
        daily_total_kwh = float(values.sum()) * interval_hours / 1000

        return PeakPrediction(
            peak_hour=peak_timestamp.hour,
            peak_power_watts=peak_power,
            peak_timestamp=peak_timestamp,
            daily_total_kwh=daily_total_kwh,
        )

    except Exception as e:
        logger.error("Peak prediction error", exc_info=True, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while generating peak prediction. Check service logs for details."
        )


@router.get("/optimization", response_model=OptimizationRecommendation)
async def get_optimization_recommendation():
    """
    Get energy optimization recommendations.

    Suggests best and worst hours for running high-power appliances.
    """
    forecaster = model_registry.get_forecaster()

    try:
        # Run CPU-intensive prediction in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        forecast_series = await loop.run_in_executor(
            None, partial(forecaster.predict, n=24)
        )

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

        best_hours_str = ", ".join(f"{h}:00" for h in sorted(best_hours))
        avoid_hours_str = ", ".join(f"{h}:00" for h in sorted(avoid_hours))

        return OptimizationRecommendation(
            recommendation=(
                f"Best times for high-power activities: {best_hours_str}. "
                f"Avoid: {avoid_hours_str}."
            ),
            estimated_savings_kwh=round((peak_avg - offpeak_avg) / 1000, 2),
            estimated_savings_percent=round(savings_percent, 1),
            best_hours=best_hours,
            avoid_hours=avoid_hours,
        )

    except Exception as e:
        logger.error("Optimization error", exc_info=True, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while generating optimization recommendations. Check service logs for details."
        )


@router.get("/model/info")
async def get_model_info() -> dict[str, Any]:
    """Get information about the loaded model."""
    if not model_registry.is_loaded:
        return {
            "loaded": False,
            "model_path": str(model_registry.model_path),
        }

    forecaster = model_registry.get_forecaster()
    info = forecaster.get_model_info()
    info["loaded"] = True
    info["model_path"] = str(model_registry.model_path)

    return info
