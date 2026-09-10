"""Pydantic request/response models for ML Service."""

from __future__ import annotations

import os
from typing import Annotated, Literal

from pydantic import BaseModel, Field

MAX_BATCH_SIZE = int(os.getenv("ML_MAX_BATCH_SIZE", "100"))


class ClusteringRequest(BaseModel):
    data: list[list[float]] = Field(..., description="Data points to cluster")
    algorithm: str = Field("kmeans", description="Clustering algorithm (kmeans, dbscan)")
    n_clusters: int | None = Field(None, description="Number of clusters (for KMeans)")
    eps: float | None = Field(None, description="Epsilon parameter (for DBSCAN)")


class ClusteringResponse(BaseModel):
    labels: list[int] = Field(..., description="Cluster labels")
    n_clusters: int = Field(..., description="Number of clusters found")
    algorithm: str = Field(..., description="Algorithm used")
    processing_time: float = Field(..., description="Processing time in seconds")


class AnomalyRequest(BaseModel):
    data: list[list[float]] = Field(..., description="Data points to analyze")
    contamination: float = Field(0.1, description="Expected proportion of outliers")


class AnomalyResponse(BaseModel):
    labels: list[int] = Field(..., description="Anomaly labels (1=normal, -1=anomaly)")
    scores: list[float] = Field(..., description="Anomaly scores")
    n_anomalies: int = Field(..., description="Number of anomalies detected")
    processing_time: float = Field(..., description="Processing time in seconds")


class BatchClusterOperation(BaseModel):
    type: Literal["cluster"]
    data: ClusteringRequest


class BatchAnomalyOperation(BaseModel):
    type: Literal["anomaly"]
    data: AnomalyRequest


BatchOperation = Annotated[
    BatchClusterOperation | BatchAnomalyOperation,
    Field(discriminator="type"),
]


class BatchProcessRequest(BaseModel):
    operations: list[BatchOperation] = Field(
        ...,
        description="List of operations to process",
        min_length=1,
        max_length=MAX_BATCH_SIZE,
    )


class BatchOperationResult(BaseModel):
    type: str
    status: str = "success"
    algorithm: str | None = None
    labels: list[int] | None = None
    n_clusters: int | None = None
    scores: list[float] | None = None
    n_anomalies: int | None = None
    error: str | None = None


class BatchProcessResponse(BaseModel):
    results: list[BatchOperationResult] = Field(..., description="Results for each operation")
    processing_time: float = Field(..., description="Total processing time in seconds")
