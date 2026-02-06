"""
ML Service - Classical Machine Learning
Phase 1: Containerized AI Models

Provides classical ML algorithms for:
- Pattern clustering (KMeans, DBSCAN)
- Anomaly detection (Isolation Forest)
- Batch processing capabilities
"""

import asyncio
import functools
import json
import logging
import math
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal, Union

import numpy as np
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .algorithms.anomaly_detection import AnomalyDetectionManager
from .algorithms.clustering import ClusteringManager


# ---------------------------------------------------------------------------
# Structured JSON logging
# ---------------------------------------------------------------------------

class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON for structured log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        # Include any extra fields passed via the `extra` kwarg
        for key in ("clusters", "points", "eps", "anomalies"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def _setup_logging() -> logging.Logger:
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    return logging.getLogger(__name__)


logger = _setup_logging()


# ---------------------------------------------------------------------------
# Safety & resource guardrails
# ---------------------------------------------------------------------------

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

# Simple in-memory rate limiter (per-endpoint, sliding window)
RATE_LIMIT_WINDOW = int(os.getenv("ML_RATE_LIMIT_WINDOW", "60"))  # seconds
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("ML_RATE_LIMIT_MAX_REQUESTS", "120"))  # per window
_rate_limit_store: dict[str, list[float]] = {}


def _check_rate_limit(client_ip: str) -> bool:
    """Return True if the request is allowed, False if rate-limited."""
    now = time.monotonic()
    window = _rate_limit_store.setdefault(client_ip, [])
    # Prune expired entries
    cutoff = now - RATE_LIMIT_WINDOW
    _rate_limit_store[client_ip] = window = [t for t in window if t > cutoff]
    if len(window) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    window.append(now)
    return True


def _parse_allowed_origins(raw_origins: str | None) -> list[str]:
    if raw_origins:
        parsed = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
        if parsed:
            return parsed
    return DEFAULT_ALLOWED_ORIGINS


ALLOWED_ORIGINS = _parse_allowed_origins(os.getenv("ML_ALLOWED_ORIGINS"))


# ---------------------------------------------------------------------------
# Data validation helpers
# ---------------------------------------------------------------------------

def _estimate_payload_bytes(num_points: int, num_dimensions: int) -> int:
    # Approximate as float64 (8 bytes)
    return num_points * num_dimensions * 8


def _validate_data_matrix(data: list[list[float]]) -> tuple[int, int]:
    """Validate that *data* is a well-formed numeric matrix.

    Performs cheap Python-level type checks on a sample of rows, then
    converts the full dataset to a numpy array for fast NaN/Inf validation.
    """
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

    # Quick type-check on a sample of rows (or all if small)
    sample_size = min(num_points, 100)
    for row in data[:sample_size]:
        if not isinstance(row, list):
            raise ValueError("Each data row must be a list of floats.")
        if len(row) != first_row_length:
            raise ValueError("All rows must have the same number of features.")
        for value in row:
            if not isinstance(value, (int, float)):
                raise ValueError("All feature values must be numbers.")
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                raise ValueError("Data contains NaN or Inf values which are not supported.")

    # Fast numpy conversion validates the full dataset
    try:
        arr = np.array(data, dtype=np.float64)
    except (ValueError, TypeError) as exc:
        raise ValueError("All feature values must be numbers.") from exc

    if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
        raise ValueError("Data contains NaN or Inf values which are not supported.")

    if arr.ndim != 2 or arr.shape[1] != first_row_length:
        raise ValueError("All rows must have the same number of features.")

    estimated_size = _estimate_payload_bytes(num_points, first_row_length)
    if estimated_size > MAX_PAYLOAD_BYTES:
        max_mb = MAX_PAYLOAD_BYTES / (1024 * 1024)
        raise ValueError(f"Payload exceeds the maximum allowed size of {max_mb:.1f}MB.")

    return num_points, first_row_length


def _validate_contamination(contamination: float) -> None:
    if contamination <= 0 or contamination >= 0.5:
        raise ValueError("Contamination must be between 0 and 0.5 (exclusive).")


async def _run_cpu_bound(func: Any, *args: Any, **kwargs: Any) -> Any:
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


# ---------------------------------------------------------------------------
# Global managers (properly typed as Optional)
# ---------------------------------------------------------------------------

clustering_manager: ClusteringManager | None = None
anomaly_manager: AnomalyDetectionManager | None = None


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize ML managers on startup."""
    global clustering_manager, anomaly_manager

    logger.info("Starting ML Service...")
    try:
        clustering_manager = ClusteringManager()
        anomaly_manager = AnomalyDetectionManager()
        logger.info("ML Service started successfully")
    except Exception as e:
        logger.error("Failed to start ML Service: %s", e)
        raise

    yield

    # Cleanup on shutdown
    logger.info("ML Service shutting down")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ML Service",
    description="Classical machine learning algorithms for pattern detection",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware (restricted origins for single-home deployment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
)


# ---------------------------------------------------------------------------
# Request ID middleware for tracing
# ---------------------------------------------------------------------------

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    # Store on request state so handlers can access it
    request.state.request_id = request_id
    logger.info(
        "Request started",
        extra={"request_id": request_id, "path": str(request.url.path)},
    )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ---------------------------------------------------------------------------
# Rate-limiting middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Skip rate-limiting for health/readiness probes
    if request.url.path in ("/health", "/ready", "/algorithms/status"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT_MAX_REQUESTS} requests per {RATE_LIMIT_WINDOW}s.",
        )
    return await call_next(request)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

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


# Typed batch operation models (HIGH-3)
class BatchClusterOperation(BaseModel):
    type: Literal["cluster"]
    data: ClusteringRequest


class BatchAnomalyOperation(BaseModel):
    type: Literal["anomaly"]
    data: AnomalyRequest


BatchOperation = Annotated[
    Union[BatchClusterOperation, BatchAnomalyOperation],
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


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint (liveness)."""
    return {
        "status": "healthy",
        "service": "ml-service",
        "algorithms_available": {
            "clustering": ["kmeans", "dbscan"],
            "anomaly_detection": ["isolation_forest"],
        },
    }


@app.get("/ready")
async def readiness_check() -> dict[str, str]:
    """Readiness check -- ensures managers are initialized."""
    if clustering_manager is None or anomaly_manager is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready"}


@app.get("/algorithms/status")
async def get_algorithm_status() -> dict[str, dict[str, str]]:
    """Get detailed algorithm status."""
    return {
        "clustering": {
            "kmeans": "available",
            "dbscan": "available",
        },
        "anomaly_detection": {
            "isolation_forest": "available",
        },
    }


@app.post("/cluster", response_model=ClusteringResponse)
async def cluster_data(request: ClusteringRequest) -> ClusteringResponse:
    """Cluster data using specified algorithm."""
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
async def detect_anomalies(request: AnomalyRequest) -> AnomalyResponse:
    """Detect anomalies in data using Isolation Forest."""
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


# ---------------------------------------------------------------------------
# Batch processing (concurrent, with per-operation error handling)
# ---------------------------------------------------------------------------

async def _process_single_operation(
    operation: Union[BatchClusterOperation, BatchAnomalyOperation],
) -> BatchOperationResult:
    """Process a single batch operation, returning a result dict.

    Errors are caught per-operation so that one failure does not abort the
    entire batch.
    """
    try:
        if operation.type == "cluster":
            req = operation.data
            if not clustering_manager:
                return BatchOperationResult(type="cluster", status="error", error="Clustering service not ready")

            num_points, _ = _validate_data_matrix(req.data)
            algorithm = req.algorithm.lower()

            if algorithm == "kmeans":
                if req.n_clusters is not None:
                    if req.n_clusters < 2 or req.n_clusters > MAX_CLUSTERS or req.n_clusters > num_points:
                        return BatchOperationResult(
                            type="cluster",
                            status="error",
                            error="Invalid n_clusters value supplied in batch operation.",
                        )

                labels, n_clusters = await _run_cpu_bound(
                    clustering_manager.kmeans_cluster,
                    req.data,
                    n_clusters=req.n_clusters,
                    max_clusters=MAX_CLUSTERS,
                )
            elif algorithm == "dbscan":
                if req.eps is not None and req.eps <= 0:
                    return BatchOperationResult(type="cluster", status="error", error="eps must be > 0.")

                labels, n_clusters = await _run_cpu_bound(
                    clustering_manager.dbscan_cluster,
                    req.data,
                    eps=req.eps,
                )
            else:
                return BatchOperationResult(
                    type="cluster",
                    status="error",
                    error=f"Unknown clustering algorithm: {algorithm}",
                )

            return BatchOperationResult(
                type="cluster",
                status="success",
                algorithm=algorithm,
                labels=labels,
                n_clusters=n_clusters,
            )

        elif operation.type == "anomaly":
            req = operation.data  # type: ignore[assignment]
            if not anomaly_manager:
                return BatchOperationResult(type="anomaly", status="error", error="Anomaly detection service not ready")

            _validate_data_matrix(req.data)
            _validate_contamination(req.contamination)

            labels, scores = await _run_cpu_bound(
                anomaly_manager.detect_anomalies,
                req.data,
                contamination=req.contamination,
            )

            return BatchOperationResult(
                type="anomaly",
                status="success",
                labels=labels,
                scores=scores,
                n_anomalies=sum(1 for label in labels if label == -1),
            )

        else:
            return BatchOperationResult(
                type=str(getattr(operation, "type", "unknown")),
                status="error",
                error="Unknown operation type",
            )

    except HTTPException as exc:
        return BatchOperationResult(
            type=operation.type,
            status="error",
            error=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
        )
    except ValueError as exc:
        return BatchOperationResult(type=operation.type, status="error", error=str(exc))
    except Exception:
        logger.exception("Unexpected error processing batch operation")
        return BatchOperationResult(
            type=operation.type,
            status="error",
            error="Operation failed due to an internal error.",
        )


@app.post("/batch/process", response_model=BatchProcessResponse)
async def batch_process(request: BatchProcessRequest) -> BatchProcessResponse:
    """Process multiple operations concurrently in a batch."""
    if len(request.operations) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size exceeds limit of {MAX_BATCH_SIZE} operations.",
        )

    start_time = time.time()

    # Run all operations concurrently via asyncio.gather
    results = await asyncio.gather(
        *[_process_single_operation(op) for op in request.operations],
        return_exceptions=True,
    )

    # Convert any unexpected exceptions to error results
    final_results: list[BatchOperationResult] = []
    for i, result in enumerate(results):
        if isinstance(result, BaseException):
            logger.exception("Unhandled batch operation exception", exc_info=result)
            final_results.append(
                BatchOperationResult(
                    type=request.operations[i].type,
                    status="error",
                    error="Operation failed due to an internal error.",
                )
            )
        else:
            final_results.append(result)

    processing_time = time.time() - start_time

    return BatchProcessResponse(
        results=final_results,
        processing_time=processing_time,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8020)
