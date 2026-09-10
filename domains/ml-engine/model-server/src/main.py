"""model-server - Merged ML Inference Service (TAP-7276).

One process, one model load. Folds three former ml-engine services into a
single FastAPI app, each mounted at its **exact existing route paths** so
consumers only need to change the host:

- openvino-service  -> /embeddings, /rerank, /classify, /models/status, /models/warmup
- ml-service         -> /cluster, /anomaly, /batch/process, /algorithms/status
- rag-service        -> /api/v1/rag/*, /api/v1/metrics, /health/ready (rag namespace)

``ner-service`` is dropped outright (no fold target — see
docs/architecture/collapse-map.md section C3).

The OpenVINO embedding/rerank model is owned by a single ``OpenVINOManager``
instance. RAG's retrieval path previously called that model over HTTP to a
separate container; it now goes through ``LocalOpenVINOBridge``, an in-process
adapter around the same manager instance, so the model loads exactly once
regardless of which former service's route triggered it.
"""

from __future__ import annotations

import asyncio
import functools
import time
from typing import Any

from fastapi import HTTPException, Request, status
from homeiq_observability.logging_config import setup_logging
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

# ---------------------------------------------------------------------------
# Former ml-service imports
# ---------------------------------------------------------------------------
from .ml.algorithms.anomaly_detection import AnomalyDetectionManager
from .ml.algorithms.clustering import ClusteringManager
from .ml.batch import process_single_operation
from .ml.config import settings as ml_settings
from .ml.middleware import (
    RATE_LIMIT_MAX_REQUESTS,
    RATE_LIMIT_WINDOW,
    _check_rate_limit,
    _parse_allowed_origins,
    _rate_limit_store,
)
from .ml.models import (
    AnomalyRequest,
    AnomalyResponse,
    BatchOperationResult,
    BatchProcessRequest,
    BatchProcessResponse,
    ClusteringRequest,
    ClusteringResponse,
)
from .ml.validation import (
    _estimate_payload_bytes,
    _validate_contamination,
    _validate_data_matrix,
)

# ---------------------------------------------------------------------------
# Former openvino-service imports
# ---------------------------------------------------------------------------
from .openvino.config import settings as openvino_settings
from .openvino.models.openvino_manager import OpenVINOManager
from .openvino.models_api import (
    ClassifyRequest,
    ClassifyResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    RerankRequest,
    RerankResponse,
)

# ---------------------------------------------------------------------------
# Former rag-service imports
# ---------------------------------------------------------------------------
from .rag.api import metrics_router, rag_router
from .rag.clients.openvino_client import LocalOpenVINOBridge
from .rag.database.session import init_db

# Re-export for backward compatibility with the merged test suite
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

logger = setup_logging("model-server", group_name="ml-engine")

MAX_CLUSTERS = ml_settings.ml_max_clusters
MAX_BATCH_SIZE = ml_settings.ml_max_batch_size
ALGORITHM_TIMEOUT_SECONDS = ml_settings.ml_algorithm_timeout_seconds


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
# Shared OpenVINO model + in-process bridge for RAG (one model, one load)
# ---------------------------------------------------------------------------

openvino_manager: OpenVINOManager | None = None
clustering_manager: ClusteringManager | None = None
anomaly_manager: AnomalyDetectionManager | None = None


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


async def _startup_openvino() -> None:
    """Initialize the single shared OpenVINO model manager."""
    global openvino_manager
    openvino_manager = OpenVINOManager(models_dir=openvino_settings.model_cache_dir)
    if openvino_settings.openvino_preload_models:
        await openvino_manager.initialize()
        logger.info("OpenVINO models preloaded")
    else:
        logger.info("OpenVINO models will lazy-load on first request")


async def _shutdown_openvino() -> None:
    global openvino_manager
    if openvino_manager:
        await openvino_manager.cleanup()
    openvino_manager = None


async def _startup_ml() -> None:
    """Initialize ML managers on startup."""
    global clustering_manager, anomaly_manager
    clustering_manager = ClusteringManager()
    anomaly_manager = AnomalyDetectionManager()


async def _startup_rag_db() -> None:
    """Initialize RAG's database connection."""
    db_ok = await init_db()
    if db_ok:
        logger.info("RAG database initialized")
    else:
        logger.warning("RAG database unavailable -- starting in degraded mode")


async def _startup_rag_bridge() -> None:
    """Wire RAG's embedding calls to the shared OpenVINO manager (one model, one load)."""
    app.state.openvino_client = LocalOpenVINOBridge(openvino_manager)  # type: ignore[arg-type]
    app.state.embedding_cache = {}


lifespan = ServiceLifespan("model-server")
lifespan.on_startup(_startup_openvino, name="openvino-model")
lifespan.on_startup(_startup_ml, name="ml-managers")
lifespan.on_startup(_startup_rag_db, name="rag-database")
lifespan.on_startup(_startup_rag_bridge, name="rag-openvino-bridge")
lifespan.on_shutdown(_shutdown_openvino, name="openvino-model")


# ---------------------------------------------------------------------------
# Health check (unified across all three former services)
# ---------------------------------------------------------------------------


async def _check_model_readiness() -> bool:
    """Check if at least one OpenVINO model is loaded."""
    if not openvino_manager:
        return False
    return openvino_manager.is_ready()


async def _check_ml_managers_ready() -> bool:
    return clustering_manager is not None and anomaly_manager is not None


health = StandardHealthCheck(
    service_name="model-server",
    version="1.0.0",
)
health.register_check("openvino-models", _check_model_readiness)
health.register_check("ml-managers", _check_ml_managers_ready)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_app(
    title="model-server",
    version="1.0.0",
    description=(
        "Merged ML inference service: OpenVINO embeddings/rerank/classify, "
        "classical ML algorithms, and RAG retrieval (TAP-7276)."
    ),
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=openvino_settings.get_cors_origins_list(),
)

app.include_router(rag_router.router)
app.include_router(metrics_router.router)


# ---------------------------------------------------------------------------
# Middleware (former openvino-service: request timing / metrics)
# ---------------------------------------------------------------------------


class MetricsMiddleware(BaseHTTPMiddleware):
    """Log request method, path, status code and duration for every request."""

    async def dispatch(self, request: StarletteRequest, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_seconds": round(duration, 4),
            },
        )
        return response


app.add_middleware(MetricsMiddleware)


# ---------------------------------------------------------------------------
# Middleware (former ml-service: rate limiting)
# ---------------------------------------------------------------------------


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
# Helpers (former openvino-service)
# ---------------------------------------------------------------------------


def _require_manager() -> OpenVINOManager:
    """Return the global manager or raise 503 if the service is not ready."""
    if not openvino_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    return openvino_manager


def _validate_text_batch(texts: list[str]) -> None:
    """Validate a batch of texts for the /embeddings endpoint."""
    if not texts:
        raise HTTPException(status_code=400, detail="At least one text is required")
    if len(texts) > openvino_settings.openvino_max_embedding_texts:
        raise HTTPException(
            status_code=400,
            detail=f"Too many texts (max {openvino_settings.openvino_max_embedding_texts})",
        )

    for idx, text in enumerate(texts):
        if not isinstance(text, str):
            raise HTTPException(status_code=400, detail=f"Text at index {idx} must be a string")
        if len(text) > openvino_settings.openvino_max_text_length:
            raise HTTPException(
                status_code=400,
                detail=f"Text at index {idx} exceeds {openvino_settings.openvino_max_text_length} characters",
            )
        if not text.strip():
            raise HTTPException(status_code=400, detail="Texts cannot be empty strings")


def _validate_rerank_payload(query: str, candidates: list[dict[str, Any]], top_k: int) -> None:
    """Validate the rerank request payload."""
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query text is required")
    if len(query) > openvino_settings.openvino_max_query_length:
        raise HTTPException(
            status_code=400,
            detail=f"Query exceeds {openvino_settings.openvino_max_query_length} characters",
        )

    if not candidates:
        raise HTTPException(status_code=400, detail="At least one candidate is required")
    if len(candidates) > openvino_settings.openvino_max_rerank_candidates:
        raise HTTPException(
            status_code=400,
            detail=f"Too many candidates (max {openvino_settings.openvino_max_rerank_candidates})",
        )

    for idx, candidate in enumerate(candidates):
        description = str(candidate.get("description", ""))
        if len(description) > openvino_settings.openvino_max_text_length:
            raise HTTPException(
                status_code=400,
                detail=f"Candidate description at index {idx} exceeds {openvino_settings.openvino_max_text_length} characters",
            )

    max_allowed = min(openvino_settings.openvino_max_rerank_top_k, len(candidates))
    if top_k < 1 or top_k > max_allowed:
        raise HTTPException(
            status_code=400,
            detail=f"top_k must be between 1 and {max_allowed}",
        )


def _validate_pattern_description(description: str) -> None:
    """Validate the pattern description for classification."""
    if not description or not description.strip():
        raise HTTPException(status_code=400, detail="pattern_description cannot be empty")
    if len(description) > openvino_settings.openvino_max_pattern_length:
        raise HTTPException(
            status_code=400,
            detail=f"pattern_description exceeds {openvino_settings.openvino_max_pattern_length} characters",
        )


def _validate_kmeans_params(n_clusters: int | None, num_points: int) -> None:
    if n_clusters is None:
        return
    if n_clusters < 2:
        raise HTTPException(status_code=400, detail="n_clusters must be >= 2.")
    if n_clusters > MAX_CLUSTERS:
        raise HTTPException(status_code=400, detail=f"n_clusters must be <= {MAX_CLUSTERS}.")
    if n_clusters > num_points:
        raise HTTPException(status_code=400, detail="n_clusters cannot exceed the number of data points.")


# ---------------------------------------------------------------------------
# API Endpoints -- former openvino-service (unchanged paths)
# ---------------------------------------------------------------------------


@app.get("/models/status")
async def get_model_status():
    """Get detailed model status."""
    manager = _require_manager()
    return manager.get_model_status()


@app.post("/models/warmup")
async def warmup_models():
    """Pre-load all models (useful for orchestrators)."""
    manager = _require_manager()
    await manager.initialize()
    return {"status": "all_models_loaded", "models": manager.get_model_status()}


@app.post("/embeddings", response_model=EmbeddingResponse)
async def generate_embeddings(request: EmbeddingRequest):
    """Generate embeddings for texts."""
    manager = _require_manager()
    _validate_text_batch(request.texts)

    try:
        start_time = time.perf_counter()

        embeddings = await manager.generate_embeddings(
            texts=request.texts,
            normalize=request.normalize,
        )

        processing_time = time.perf_counter() - start_time

        return EmbeddingResponse(
            embeddings=embeddings.tolist(),
            model_name="BAAI/bge-large-en-v1.5",
            processing_time=processing_time,
        )

    except TimeoutError as exc:
        timeout = manager.inference_timeout
        logger.warning("Embedding generation timed out after %.2fs", timeout)
        raise HTTPException(
            status_code=504,
            detail=f"Embedding generation timed out after {timeout} seconds",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error generating embeddings")
        raise HTTPException(status_code=500, detail="Embedding generation failed") from exc


@app.post("/rerank", response_model=RerankResponse)
async def rerank_candidates(request: RerankRequest):
    """Re-rank candidates using bge-reranker."""
    manager = _require_manager()
    _validate_rerank_payload(request.query, request.candidates, request.top_k)

    max_allowed = min(openvino_settings.openvino_max_rerank_top_k, len(request.candidates))
    top_k = max(1, min(request.top_k, max_allowed))

    try:
        start_time = time.perf_counter()

        ranked_candidates = await manager.rerank(
            query=request.query,
            candidates=request.candidates,
            top_k=top_k,
        )

        processing_time = time.perf_counter() - start_time

        return RerankResponse(
            ranked_candidates=ranked_candidates,
            model_name="bge-reranker-base",
            processing_time=processing_time,
        )

    except TimeoutError as exc:
        timeout = manager.inference_timeout
        logger.warning("Re-ranking timed out after %.2fs", timeout)
        raise HTTPException(
            status_code=504,
            detail=f"Re-ranking timed out after {timeout} seconds",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error re-ranking candidates")
        raise HTTPException(status_code=500, detail="Re-ranking failed") from exc


@app.post("/classify", response_model=ClassifyResponse)
async def classify_pattern(request: ClassifyRequest):
    """Classify pattern using flan-t5-small."""
    manager = _require_manager()
    _validate_pattern_description(request.pattern_description)

    try:
        start_time = time.perf_counter()

        classification = await manager.classify_pattern(
            pattern_description=request.pattern_description,
        )

        processing_time = time.perf_counter() - start_time

        return ClassifyResponse(
            category=classification["category"],
            priority=classification["priority"],
            model_name="flan-t5-small",
            processing_time=processing_time,
        )

    except TimeoutError as exc:
        timeout = manager.inference_timeout
        logger.warning("Pattern classification timed out after %.2fs", timeout)
        raise HTTPException(
            status_code=504,
            detail=f"Classification timed out after {timeout} seconds",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error classifying pattern")
        raise HTTPException(status_code=500, detail="Classification failed") from exc


# ---------------------------------------------------------------------------
# API Endpoints -- former ml-service (unchanged paths)
# ---------------------------------------------------------------------------


@app.get("/algorithms/status")
async def get_algorithm_status() -> dict[str, dict[str, str]]:
    return {
        "clustering": {"kmeans": "available", "dbscan": "available"},
        "anomaly_detection": {"isolation_forest": "available"},
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
