"""Pydantic models for activity-writer service."""

from __future__ import annotations

from pydantic import BaseModel


class SensorReading(BaseModel):
    """Single 1-min bucket feature vector."""

    motion: float = 0.0
    door: float = 0.0
    temperature: float = 20.0
    humidity: float = 50.0
    power: float = 0.0


class PredictResponse(BaseModel):
    """Activity recognition predict response."""

    activity: str
    activity_id: int
    confidence: float
    probabilities: dict[str, float] | None = None
