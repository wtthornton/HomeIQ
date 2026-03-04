"""Pydantic request/response models for OpenVINO Service endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class EmbeddingRequest(BaseModel):
    """Request model for the /embeddings endpoint."""

    texts: list[str] = Field(..., description="List of texts to embed")
    normalize: bool = Field(True, description="Normalize embeddings")


class EmbeddingResponse(BaseModel):
    """Response model for the /embeddings endpoint."""

    embeddings: list[list[float]] = Field(..., description="Generated embeddings")
    model_name: str = Field(..., description="Model used")
    processing_time: float = Field(..., description="Processing time in seconds")


class RerankRequest(BaseModel):
    """Request model for the /rerank endpoint."""

    query: str = Field(..., description="Query text")
    candidates: list[dict[str, Any]] = Field(..., description="Candidates to re-rank")
    top_k: int = Field(10, description="Number of top results to return")


class RerankResponse(BaseModel):
    """Response model for the /rerank endpoint."""

    ranked_candidates: list[dict[str, Any]] = Field(..., description="Re-ranked candidates")
    model_name: str = Field(..., description="Model used")
    processing_time: float = Field(..., description="Processing time in seconds")


class ClassifyRequest(BaseModel):
    """Request model for the /classify endpoint."""

    pattern_description: str = Field(..., description="Pattern description to classify")


class ClassifyResponse(BaseModel):
    """Response model for the /classify endpoint."""

    category: str = Field(..., description="Pattern category")
    priority: str = Field(..., description="Pattern priority")
    model_name: str = Field(..., description="Model used")
    processing_time: float = Field(..., description="Processing time in seconds")
