"""ML Service - Classical Machine Learning.

Provides classical ML algorithms for pattern clustering (KMeans, DBSCAN),
anomaly detection (Isolation Forest), and batch processing.
"""

from __future__ import annotations

import asyncio
import functools
import time
from typing import Any

from fastapi import HTTPException, Request, status
from homeiq_resilience import ServiceLifespan, create_app

from .algorithms.anomaly_detection import AnomalyDetectionManager
from .algorithms.clustering import ClusteringManager
from .batch import process_single_operation
from .config import settings
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

logger = setup_ml_logging()

MAX_CLUSTERS = settings.ml_max_clusters
MAX_BATCH_SIZE = settings.ml_max_batch_size
ALGORITHM_TIMEOUT_SECONDS = settings.ml_algorithm_timeout_seconds


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


async def _startup_ml() -> None:
    """Initialize ML managers on startup."""
    global clustering_manager, anomaly_manager
    clustering_manager = ClusteringManager()
    anomaly_manager = AnomalyDetectionManager()


lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup_ml, name="ml-managers")


# ---------------------------------------------------------------------------
# App (no StandardHealthCheck — custom /health preserves algorithms_available)
# ---------------------------------------------------------------------------

app = create_app(
    title="ML Service",
    version="1.0.0",
    description="Classical machine learning algorithms for pattern detection",
    lifespan=lifespan.handler,
    cors_origins=settings.get_cors_origins_list(),
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path in ("/health", "/ready", "/algorithms/status", "/"):
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
        "status": "healthy",
        "service": settings.service_name,
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
        return ClusteringResponse(
            labels=labels,
            n_clusters=n_clusters,
            algorithm=algorithm,
            processing_time=time.time() - start_time,
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
            anomaly_manager.detect_anomalies,
            request.data,
            contamination=request.contamination,
        )
        return AnomalyResponse(
            labels=labels,
            scores=scores,
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
            final_results.append(
                BatchOperationResult(
                    type=request.operations[i].type,
                    status="error",
                    error="Operation failed due to an internal error.",
                )
            )
        else:
            final_results.append(result)
    return BatchProcessResponse(results=final_results, processing_time=time.time() - start_time)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=settings.service_port, reload=True)  # noqa: S104
