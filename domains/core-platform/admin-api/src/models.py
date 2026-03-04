"""Pydantic response models for the Admin API service.

Defines the standard API response and error response models
used across all endpoints.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    """Standard API response model for successful operations."""

    success: bool = Field(description="Whether the request was successful")
    data: Any | None = Field(default=None, description="Response data")
    message: str | None = Field(default=None, description="Response message")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="Response timestamp",
    )
    request_id: str | None = Field(default=None, description="Request ID for tracking")


class ErrorResponse(BaseModel):
    """Error response model for failed operations."""

    success: bool = Field(default=False, description="Always false for errors")
    error: str = Field(description="Error message")
    error_code: str | None = Field(default=None, description="Error code")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="Error timestamp",
    )
    request_id: str | None = Field(default=None, description="Request ID for tracking")
