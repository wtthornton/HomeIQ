"""Shared response models for Data API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    """Standard API response."""

    success: bool
    data: Any | None = None
    message: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ErrorResponse(BaseModel):
    """Error response."""

    success: bool = False
    error: str
    error_code: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
