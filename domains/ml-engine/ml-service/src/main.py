"""ML Service - Classical Machine Learning.

Provides classical ML algorithms for pattern clustering (KMeans, DBSCAN),
anomaly detection (Isolation Forest), and batch processing.
"""

from __future__ import annotations

import asyncio
import functools
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

from .algorithms.anomaly_detection import AnomalyDetectionManager
from .algorithms.clustering import ClusteringManager
from .batch import process_single_operation
from .logging_config import setup_ml_logging
from .middleware import (
    RATE_LIMIT_MAX_REQUESTS,
    RATE_LIMIT_WINDOW,
    _check_rate_limit,
    _parse_allowed_origins,
    _rate_limit_store,
)
from .models import (
    AnomalyRequest,
    AnomalyResponse,
    BatchOperationResult,
    BatchProcessRequest,
    BatchProcessResponse,
    ClusteringRequest,
    ClusteringResponse,
)
from .validation import (
    _estimate_payload_bytes,
    _validate_contamination,
    _validate_data_matrix,
)

# Re-export for backward compatibility with tests
__all__ = [
    "_check_rate_limit",
    "_estimate_payload_bytes",
    "_parse_allowed_origins",
    "_rate_limit_store",
    "_run_cpu_bound",
    "_validate_contamination",
    "_validate_data_matrix",
    "app",
]

MAX_CLUSTERS = int(os.getenv("ML_MAX_CLUSTERS", "100"))
MAX_BATCH_SIZE = int(os.getenv("ML_MAX_BATCH_SIZE", "100"))
ALGORITHM_TIMEOUT_SECONDS = float(os.getenv("ML_ALGORITHM_TIMEOUT_SECONDS", "8"))

logger = setup_ml_logging()
ALLOWED_ORIGINS = _parse_allowed_origins(os.getenv("ML_ALLOWED_ORIGINS"))


async def _run_cpu_bound(func: Any, *args: Any, **kwargs: Any) -> Any:
    """Run a CPU-bound function in a thread pool with timeout."""
    loop = asyncio.get_running_loop()
    partial = functools.partial(func, *args, **kwargs)
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, partial),
            timeout=ALGORITHM_TIMEOUT_SECONDS,
        )
    except TimeoutError as exc:
        logger.error("Operation timed out: %s", getattr(func, "__name__", "unknown"))
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Processing timed out. Reduce data size or complexity and try again.",
        ) from exc


# ---------------------------------------------------------------------------
# Global managers and lifespan
# ---------------------------------------------------------------------------

clustering_manager: ClusteringManager | None = None
anomaly_manager: AnomalyDetectionManager | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
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
    logger.info("ML Service shutting down")


app = FastAPI(
    title="ML Service",
    description="Classical machine learning algorithms for pattern detection",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
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
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint (liveness)."""
    return {
        "status": "healthy", "service": "ml-service",
        "algorithms_available": {
            "clustering": ["kmeans", "dbscan"],
            "anomaly_detection": ["isolation_forest"],
        },
    }


@app.get("/ready")
async def readiness_check() -> dict[str, str]:
    if clustering_manager is None or anomaly_manager is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready"}


@app.get("/algorithms/status")
async def get_algorithm_status() -> dict[str, dict[str, str]]:
    return {
        "clustering": {"kmeans": "available", "dbscan": "available"},
        "anomaly_detection": {"isolation_forest": "available"},
    }


def _validate_kmeans_params(n_clusters: int | None, num_points: int) -> None:
    if n_clusters is None:
        return
    if n_clusters < 2:
        raise HTTPException(status_code=400, detail="n_clusters must be >= 2.")
    if n_clusters > MAX_CLUSTERS:
        raise HTTPException(status_code=400, detail=f"n_clusters must be <= {MAX_CLUSTERS}.")
    if n_clusters > num_points:
        raise HTTPException(status_code=400, detail="n_clusters cannot exceed the number of data points.")


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
            _validate_kmeans_params(request.n_clusters, num_points)
            labels, n_clusters = await _run_cpu_bound(
                clustering_manager.kmeans_cluster, request.data,
                n_clusters=request.n_clusters, max_clusters=MAX_CLUSTERS,
            )
        elif algorithm == "dbscan":
            if request.eps is not None and request.eps <= 0:
                raise HTTPException(status_code=400, detail="eps must be > 0.")
            labels, n_clusters = await _run_cpu_bound(
                clustering_manager.dbscan_cluster, request.data, eps=request.eps,
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown algorithm: {request.algorithm}")
        return ClusteringResponse(
            labels=labels, n_clusters=n_clusters,
            algorithm=algorithm, processing_time=time.time() - start_time,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error clustering data")
        raise HTTPException(status_code=500, detail="Clustering failed due to an internal error.") from exc


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
            anomaly_manager.detect_anomalies, request.data,
            contamination=request.contamination,
        )
        return AnomalyResponse(
            labels=labels, scores=scores,
            n_anomalies=sum(1 for label in labels if label == -1),
            processing_time=time.time() - start_time,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error detecting anomalies")
        raise HTTPException(status_code=500, detail="Anomaly detection failed due to an internal error.") from exc


@app.post("/batch/process", response_model=BatchProcessResponse)
async def batch_process(request: BatchProcessRequest) -> BatchProcessResponse:
    """Process multiple operations concurrently in a batch."""
    if len(request.operations) > MAX_BATCH_SIZE:
        raise HTTPException(status_code=400, detail=f"Batch size exceeds limit of {MAX_BATCH_SIZE} operations.")
    start_time = time.time()
    results = await asyncio.gather(
        *[
            process_single_operation(op, clustering_manager, anomaly_manager, _run_cpu_bound, MAX_CLUSTERS)
            for op in request.operations
        ],
        return_exceptions=True,
    )
    final_results: list[BatchOperationResult] = []
    for i, result in enumerate(results):
        if isinstance(result, BaseException):
            logger.exception("Unhandled batch operation exception", exc_info=result)
            final_results.append(BatchOperationResult(
                type=request.operations[i].type, status="error",
                error="Operation failed due to an internal error.",
            ))
        else:
            final_results.append(result)
    return BatchProcessResponse(results=final_results, processing_time=time.time() - start_time)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)  # noqa: S104
