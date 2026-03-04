"""Pydantic request/response models for AI Core Service endpoints."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class AnalysisRequest(BaseModel):
    """Request model for the /analyze endpoint."""

    data: list[dict[str, Any]] = Field(
        ..., description="Data to analyze", min_length=1, max_length=1000
    )
    analysis_type: str = Field(
        ..., description="Type of analysis to perform", min_length=1, max_length=100
    )
    options: dict[str, Any] = Field(
        default_factory=dict, description="Analysis options", max_length=50
    )

    @field_validator("data")
    @classmethod
    def validate_data_size(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate data size and content."""
        if not v:
            raise ValueError("Data list cannot be empty")
        if len(v) > 1000:
            raise ValueError("Data list cannot exceed 1000 items")
        for item in v:
            if not isinstance(item, dict):
                raise ValueError("All data items must be dictionaries")
            if len(str(item)) > 10000:
                raise ValueError("Individual data items cannot exceed 10KB")
        return v

    @field_validator("analysis_type")
    @classmethod
    def validate_analysis_type(cls, v: str) -> str:
        """Validate analysis type."""
        allowed_types = {"pattern_detection", "clustering", "anomaly_detection", "basic"}
        if v not in allowed_types:
            raise ValueError(
                f"Analysis type must be one of: {', '.join(sorted(allowed_types))}"
            )
        return v


class AnalysisResponse(BaseModel):
    """Response model for the /analyze endpoint."""

    results: dict[str, Any] = Field(..., description="Analysis results")
    services_used: list[str] = Field(..., description="Services used in analysis")
    processing_time: float = Field(..., description="Total processing time in seconds")


class PatternDetectionRequest(BaseModel):
    """Request model for the /patterns endpoint."""

    patterns: list[dict[str, Any]] = Field(
        ..., description="Patterns to detect", min_length=1, max_length=500
    )
    detection_type: str = Field(
        "full", description="Type of pattern detection", max_length=50
    )

    @field_validator("patterns")
    @classmethod
    def validate_patterns(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate patterns list."""
        if not v:
            raise ValueError("Patterns list cannot be empty")
        if len(v) > 500:
            raise ValueError("Patterns list cannot exceed 500 items")
        for pattern in v:
            if not isinstance(pattern, dict):
                raise ValueError("All patterns must be dictionaries")
            if len(str(pattern)) > 5000:
                raise ValueError("Individual patterns cannot exceed 5KB")
        return v

    @field_validator("detection_type")
    @classmethod
    def validate_detection_type(cls, v: str) -> str:
        """Validate detection type."""
        allowed_types = {"full", "basic", "quick"}
        if v not in allowed_types:
            raise ValueError(
                f"Detection type must be one of: {', '.join(sorted(allowed_types))}"
            )
        return v


class PatternDetectionResponse(BaseModel):
    """Response model for the /patterns endpoint."""

    detected_patterns: list[dict[str, Any]] = Field(..., description="Detected patterns")
    services_used: list[str] = Field(..., description="Services used")
    processing_time: float = Field(..., description="Processing time in seconds")


class SuggestionRequest(BaseModel):
    """Request model for the /suggestions endpoint."""

    context: dict[str, Any] = Field(..., description="Context for suggestions")
    suggestion_type: str = Field(
        ..., description="Type of suggestions to generate", min_length=1, max_length=100
    )

    @field_validator("context")
    @classmethod
    def validate_context(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate context size."""
        if not v:
            raise ValueError("Context cannot be empty")
        if len(str(v)) > 5000:
            raise ValueError("Context cannot exceed 5KB")
        return v

    @field_validator("suggestion_type")
    @classmethod
    def validate_suggestion_type(cls, v: str) -> str:
        """Validate suggestion type."""
        allowed_types = {
            "automation_improvements",
            "energy_optimization",
            "comfort",
            "security",
            "convenience",
        }
        if v not in allowed_types:
            raise ValueError(
                f"Suggestion type must be one of: {', '.join(sorted(allowed_types))}"
            )
        return v


class SuggestionResponse(BaseModel):
    """Response model for the /suggestions endpoint."""

    suggestions: list[dict[str, Any]] = Field(..., description="Generated suggestions")
    services_used: list[str] = Field(..., description="Services used")
    processing_time: float = Field(..., description="Processing time in seconds")
