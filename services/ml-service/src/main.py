"""
ML Service - Classical Machine Learning
Phase 1: Containerized AI Models

Provides classical ML algorithms for:
- Pattern clustering (KMeans, DBSCAN)
- Anomaly detection (Isolation Forest)
- Feature importance (Random Forest)
- Batch processing capabilities
"""

import asyncio
import functools
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .algorithms.anomaly_detection import AnomalyDetectionManager
from .algorithms.clustering import ClusteringManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Safety & resource guardrails (2025 patterns)
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

MAX_PAYLOAD_BYTES = int(os.getenv("ML_MAX_PAYLOAD_BYTES", str(10 * 1024 * 1024)))  # 10MB
MAX_DIMENSIONS = int(os.getenv("ML_MAX_DIMENSIONS", "1000"))
MAX_CLUSTERS = int(os.getenv("ML_MAX_CLUSTERS", "100"))
MAX_BATCH_SIZE = int(os.getenv("ML_MAX_BATCH_SIZE", "100"))
MAX_DATA_POINTS = int(os.getenv("ML_MAX_DATA_POINTS", "50000"))
ALGORITHM_TIMEOUT_SECONDS = float(os.getenv("ML_ALGORITHM_TIMEOUT_SECONDS", "8"))


def _parse_allowed_origins(raw_origins: str | None) -> list[str]:
    if raw_origins:
        parsed = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
        if parsed:
            return parsed
    return DEFAULT_ALLOWED_ORIGINS


ALLOWED_ORIGINS = _parse_allowed_origins(os.getenv("ML_ALLOWED_ORIGINS"))


def _estimate_payload_bytes(num_points: int, num_dimensions: int) -> int:
    # Approximate as float64 (8 bytes)
    return num_points * num_dimensions * 8


def _validate_data_matrix(data: list[list[float]]) -> tuple[int, int]:
    if not isinstance(data, list) or not data:
        raise ValueError("Data must contain at least one row.")

    first_row_length = len(data[0])
    if first_row_length == 0:
        raise ValueError("Data rows must contain at least one feature.")
    if first_row_length > MAX_DIMENSIONS:
        raise ValueError(f"Maximum supported dimensions is {MAX_DIMENSIONS}.")

    num_points = len(data)
    if num_points > MAX_DATA_POINTS:
        raise ValueError(f"Maximum supported data points is {MAX_DATA_POINTS}.")

    for index, row in enumerate(data):
        if not isinstance(row, list):
            raise ValueError("Each data row must be a list of floats.")
        if len(row) != first_row_length:
            raise ValueError("All rows must have the same number of features.")
        for value in row:
            if not isinstance(value, (int, float)):
                raise ValueError("All feature values must be numbers.")

    estimated_size = _estimate_payload_bytes(num_points, first_row_length)
    if estimated_size > MAX_PAYLOAD_BYTES:
        max_mb = MAX_PAYLOAD_BYTES / (1024 * 1024)
        raise ValueError(f"Payload exceeds the maximum allowed size of {max_mb:.1f}MB.")

    return num_points, first_row_length


def _validate_contamination(contamination: float) -> None:
    if contamination <= 0 or contamination >= 0.5:
        raise ValueError("Contamination must be between 0 and 0.5 (exclusive).")


async def _run_cpu_bound(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    partial = functools.partial(func, *args, **kwargs)
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, partial),
            timeout=ALGORITHM_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        logger.error("Operation timed out: %s", getattr(func, "__name__", "unknown"))
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Processing timed out. Reduce data size or complexity and try again.",
        ) from exc

# Global managers
clustering_manager: ClusteringManager = None
anomaly_manager: AnomalyDetectionManager = None

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize ML managers on startup"""
    global clustering_manager, anomaly_manager

    logger.info("🚀 Starting ML Service...")
    try:
        clustering_manager = ClusteringManager()
        anomaly_manager = AnomalyDetectionManager()
        logger.info("✅ ML Service started successfully")
    except Exception as e:
        logger.error(f"❌ Failed to start ML Service: {e}")
        raise

    yield

    # Cleanup on shutdown (if needed)
    logger.info("🛑 ML Service shutting down")

# Create FastAPI app
app = FastAPI(
    title="ML Service",
    description="Classical machine learning algorithms for pattern detection",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware (restricted origins for single-home deployment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# Pydantic models
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

class BatchProcessRequest(BaseModel):
    operations: list[dict[str, Any]] = Field(
        ...,
        description="List of operations to process",
        min_length=1,
        max_length=MAX_BATCH_SIZE,
    )

class BatchProcessResponse(BaseModel):
    results: list[dict[str, Any]] = Field(..., description="Results for each operation")
    processing_time: float = Field(..., description="Total processing time in seconds")

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ml-service",
        "algorithms_available": {
            "clustering": ["kmeans", "dbscan"],
            "anomaly_detection": ["isolation_forest"]
        }
    }

@app.get("/algorithms/status")
async def get_algorithm_status():
    """Get detailed algorithm status"""
    return {
        "clustering": {
            "kmeans": "available",
            "dbscan": "available"
        },
        "anomaly_detection": {
            "isolation_forest": "available"
        }
    }

@app.post("/cluster", response_model=ClusteringResponse)
async def cluster_data(request: ClusteringRequest):
    """Cluster data using specified algorithm"""
    if not clustering_manager:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        num_points, _ = _validate_data_matrix(request.data)
        start_time = time.time()

        algorithm = request.algorithm.lower()

        if algorithm == "kmeans":
            if request.n_clusters is not None:
                if request.n_clusters < 2:
                    raise HTTPException(status_code=400, detail="n_clusters must be >= 2.")
                if request.n_clusters > MAX_CLUSTERS:
                    raise HTTPException(
                        status_code=400,
                        detail=f"n_clusters must be <= {MAX_CLUSTERS}.",
                    )
                if request.n_clusters > num_points:
                    raise HTTPException(
                        status_code=400,
                        detail="n_clusters cannot exceed the number of data points.",
                    )

            labels, n_clusters = await _run_cpu_bound(
                clustering_manager.kmeans_cluster,
                request.data,
                n_clusters=request.n_clusters,
                max_clusters=MAX_CLUSTERS,
            )
        elif algorithm == "dbscan":
            if request.eps is not None and request.eps <= 0:
                raise HTTPException(status_code=400, detail="eps must be > 0.")

            labels, n_clusters = await _run_cpu_bound(
                clustering_manager.dbscan_cluster,
                request.data,
                eps=request.eps,
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown algorithm: {request.algorithm}")

        processing_time = time.time() - start_time

        return ClusteringResponse(
            labels=labels,
            n_clusters=n_clusters,
            algorithm=algorithm,
            processing_time=processing_time,
        )

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("Error clustering data")
        raise HTTPException(
            status_code=500,
            detail="Clustering failed due to an internal error.",
        )

@app.post("/anomaly", response_model=AnomalyResponse)
async def detect_anomalies(request: AnomalyRequest):
    """Detect anomalies in data using Isolation Forest"""
    if not anomaly_manager:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        _validate_data_matrix(request.data)
        _validate_contamination(request.contamination)

        start_time = time.time()

        labels, scores = await _run_cpu_bound(
            anomaly_manager.detect_anomalies,
            request.data,
            contamination=request.contamination,
        )

        n_anomalies = sum(1 for label in labels if label == -1)
        processing_time = time.time() - start_time

        return AnomalyResponse(
            labels=labels,
            scores=scores,
            n_anomalies=n_anomalies,
            processing_time=processing_time,
        )

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("Error detecting anomalies")
        raise HTTPException(
            status_code=500,
            detail="Anomaly detection failed due to an internal error.",
        )

@app.post("/batch/process", response_model=BatchProcessResponse)
async def batch_process(request: BatchProcessRequest):
    """Process multiple operations in batch"""
    if len(request.operations) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size exceeds limit of {MAX_BATCH_SIZE} operations.",
        )

    try:
        start_time = time.time()
        results = []

        for operation in request.operations:
            op_type = operation.get("type")
            op_data = operation.get("data", {})

            if op_type == "cluster":
                if not clustering_manager:
                    raise HTTPException(status_code=503, detail="Clustering service not ready")

                algorithm = op_data.get("algorithm", "kmeans")
                data = op_data.get("data", [])
                num_points, _ = _validate_data_matrix(data)

                if algorithm == "kmeans":
                    n_clusters = op_data.get("n_clusters")
                    if n_clusters is not None:
                        if n_clusters < 2 or n_clusters > MAX_CLUSTERS or n_clusters > num_points:
                            raise HTTPException(
                                status_code=400,
                                detail="Invalid n_clusters value supplied in batch operation.",
                            )

                    labels, n_clusters = await _run_cpu_bound(
                        clustering_manager.kmeans_cluster,
                        data,
                        n_clusters=n_clusters,
                        max_clusters=MAX_CLUSTERS,
                    )
                elif algorithm == "dbscan":
                    eps = op_data.get("eps")
                    if eps is not None and eps <= 0:
                        raise HTTPException(status_code=400, detail="eps must be > 0.")

                    labels, n_clusters = await _run_cpu_bound(
                        clustering_manager.dbscan_cluster,
                        data,
                        eps=eps,
                    )
                else:
                    raise HTTPException(status_code=400, detail=f"Unknown clustering algorithm: {algorithm}")

                results.append(
                    {
                        "type": "cluster",
                        "algorithm": algorithm,
                        "labels": labels,
                        "n_clusters": n_clusters,
                    }
                )

            elif op_type == "anomaly":
                if not anomaly_manager:
                    raise HTTPException(status_code=503, detail="Anomaly detection service not ready")

                data = op_data.get("data", [])
                contamination = op_data.get("contamination", 0.1)
                _validate_data_matrix(data)
                _validate_contamination(contamination)

                labels, scores = await _run_cpu_bound(
                    anomaly_manager.detect_anomalies,
                    data,
                    contamination=contamination,
                )

                results.append(
                    {
                        "type": "anomaly",
                        "labels": labels,
                        "scores": scores,
                        "n_anomalies": sum(1 for label in labels if label == -1),
                    }
                )

            else:
                raise HTTPException(status_code=400, detail=f"Unknown operation type: {op_type}")

        processing_time = time.time() - start_time

        return BatchProcessResponse(
            results=results,
            processing_time=processing_time,
        )

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("Error in batch processing")
        raise HTTPException(
            status_code=500,
            detail="Batch processing failed due to an internal error.",
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)
