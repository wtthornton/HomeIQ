"""
OpenVINO Service - Optimized Model Inference
Phase 1: Containerized AI Models

Provides optimized model inference for:
- BAAI/bge-large-en-v1.5 (1024-dim) - Embeddings [Epic 47]
- bge-reranker-base - Re-ranking
- flan-t5-small - Classification
"""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

from .models.openvino_manager import OpenVINOManager

# ---------------------------------------------------------------------------
# Structured JSON Logging (ENH-4)
# ---------------------------------------------------------------------------

class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for log aggregation systems."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "method"):
            log_entry["method"] = record.method
        if hasattr(record, "path"):
            log_entry["path"] = record.path
        if hasattr(record, "status_code"):
            log_entry["status_code"] = record.status_code
        if hasattr(record, "duration_seconds"):
            log_entry["duration_seconds"] = record.duration_seconds
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


# Configure structured logging
_handler = logging.StreamHandler()
_handler.setFormatter(JSONFormatter())
logging.basicConfig(level=logging.INFO, handlers=[_handler])
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Service guards & configuration (CRIT-1: single authoritative block)
# ---------------------------------------------------------------------------
MAX_EMBEDDING_TEXTS = int(os.getenv("OPENVINO_MAX_EMBEDDING_TEXTS", "100"))
MAX_TEXT_LENGTH = int(os.getenv("OPENVINO_MAX_TEXT_LENGTH", "4000"))
MAX_RERANK_CANDIDATES = int(os.getenv("OPENVINO_MAX_RERANK_CANDIDATES", "200"))
MAX_RERANK_TOP_K = int(os.getenv("OPENVINO_MAX_RERANK_TOP_K", "50"))
MAX_QUERY_LENGTH = int(os.getenv("OPENVINO_MAX_QUERY_LENGTH", "2000"))
MAX_PATTERN_LENGTH = int(os.getenv("OPENVINO_MAX_PATTERN_LENGTH", "4000"))
PRELOAD_MODELS = os.getenv("OPENVINO_PRELOAD_MODELS", "false").lower() in {"1", "true", "yes"}
MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "/app/models")

# Optional API key authentication (SEC-2)
API_KEY = os.getenv("OPENVINO_API_KEY")

# Global model manager
openvino_manager: OpenVINOManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global openvino_manager

    logger.info("[START] Starting OpenVINO Service...")
    try:
        openvino_manager = OpenVINOManager()
        if PRELOAD_MODELS:
            await openvino_manager.initialize()
            logger.info("[OK] OpenVINO Service started successfully (models preloaded)")
        else:
            logger.info("[OK] OpenVINO Service started successfully (models will lazy-load)")
    except Exception:
        logger.exception("[FAIL] Failed to start OpenVINO Service")
        raise

    yield

    # Shutdown
    logger.info("[STOP] Shutting down OpenVINO Service...")
    if openvino_manager:
        await openvino_manager.cleanup()
    logger.info("[OK] OpenVINO Service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="OpenVINO Service",
    description="Optimized model inference using OpenVINO INT8 quantization",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware (MED-4: Request timing / metrics)
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


# HIGH-1: Restrict CORS to known consumers (internal service)
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # health-dashboard
        "http://localhost:3001",   # dev dashboard
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class EmbeddingRequest(BaseModel):
    texts: list[str] = Field(..., description="List of texts to embed")
    normalize: bool = Field(True, description="Normalize embeddings")


class EmbeddingResponse(BaseModel):
    embeddings: list[list[float]] = Field(..., description="Generated embeddings")
    model_name: str = Field(..., description="Model used")
    processing_time: float = Field(..., description="Processing time in seconds")


class RerankRequest(BaseModel):
    query: str = Field(..., description="Query text")
    candidates: list[dict[str, Any]] = Field(..., description="Candidates to re-rank")
    top_k: int = Field(10, description="Number of top results to return")


class RerankResponse(BaseModel):
    ranked_candidates: list[dict[str, Any]] = Field(..., description="Re-ranked candidates")
    model_name: str = Field(..., description="Model used")
    processing_time: float = Field(..., description="Processing time in seconds")


class ClassifyRequest(BaseModel):
    pattern_description: str = Field(..., description="Pattern description to classify")


class ClassifyResponse(BaseModel):
    category: str = Field(..., description="Pattern category")
    priority: str = Field(..., description="Pattern priority")
    model_name: str = Field(..., description="Model used")
    processing_time: float = Field(..., description="Processing time in seconds")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_manager() -> OpenVINOManager:
    """Return the global manager or raise 503 if the service is not ready."""
    if not openvino_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    return openvino_manager


async def _verify_api_key(request: Request) -> None:
    """SEC-2: Validate optional API key header."""
    if API_KEY and request.headers.get("X-API-Key") != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def _validate_text_batch(texts: list[str]) -> None:
    """Validate a batch of texts for the /embeddings endpoint."""
    if not texts:
        raise HTTPException(status_code=400, detail="At least one text is required")
    if len(texts) > MAX_EMBEDDING_TEXTS:
        raise HTTPException(status_code=400, detail="Too many texts (max %d)" % MAX_EMBEDDING_TEXTS)

    for idx, text in enumerate(texts):
        if not isinstance(text, str):
            raise HTTPException(status_code=400, detail="Text at index %d must be a string" % idx)
        if len(text) > MAX_TEXT_LENGTH:
            raise HTTPException(status_code=400, detail="Text at index %d exceeds %d characters" % (idx, MAX_TEXT_LENGTH))
        if not text.strip():
            raise HTTPException(status_code=400, detail="Texts cannot be empty strings")


def _validate_rerank_payload(query: str, candidates: list[dict[str, Any]], top_k: int) -> None:
    """Validate the rerank request payload."""
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query text is required")
    if len(query) > MAX_QUERY_LENGTH:
        raise HTTPException(status_code=400, detail="Query exceeds %d characters" % MAX_QUERY_LENGTH)

    if not candidates:
        raise HTTPException(status_code=400, detail="At least one candidate is required")
    if len(candidates) > MAX_RERANK_CANDIDATES:
        raise HTTPException(
            status_code=400,
            detail="Too many candidates (max %d)" % MAX_RERANK_CANDIDATES,
        )

    for idx, candidate in enumerate(candidates):
        description = str(candidate.get("description", ""))
        if len(description) > MAX_TEXT_LENGTH:
            raise HTTPException(
                status_code=400,
                detail="Candidate description at index %d exceeds %d characters" % (idx, MAX_TEXT_LENGTH),
            )

    max_allowed = min(MAX_RERANK_TOP_K, len(candidates))
    if top_k < 1 or top_k > max_allowed:
        raise HTTPException(
            status_code=400,
            detail="top_k must be between 1 and %d" % max_allowed,
        )


def _validate_pattern_description(description: str) -> None:
    """Validate the pattern description for classification."""
    if not description or not description.strip():
        raise HTTPException(status_code=400, detail="pattern_description cannot be empty")
    if len(description) > MAX_PATTERN_LENGTH:
        raise HTTPException(
            status_code=400,
            detail="pattern_description exceeds %d characters" % MAX_PATTERN_LENGTH,
        )


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    """Health check endpoint - reports readiness and model status (CRIT-3 + MED-3 fixed)."""
    manager = _require_manager()
    readiness = manager.is_ready()
    model_status = manager.get_model_status()

    any_model_loaded = any([
        model_status["embedding_loaded"],
        model_status["reranker_loaded"],
        model_status["classifier_loaded"],
    ])

    return {
        "status": "healthy" if readiness else "initializing",
        "service": "openvino-service",
        "ready": readiness,
        "models_ready": any_model_loaded,
        "models_loaded": model_status,
    }


@app.get("/models/status")
async def get_model_status():
    """Get detailed model status."""
    manager = _require_manager()
    return manager.get_model_status()


@app.post("/models/warmup")
async def warmup_models():
    """ENH-2: Pre-load all models (useful for orchestrators)."""
    manager = _require_manager()
    await manager.initialize()
    return {"status": "all_models_loaded", "models": manager.get_model_status()}


@app.post("/embeddings", response_model=EmbeddingResponse)
async def generate_embeddings(request: EmbeddingRequest):
    """Generate embeddings for texts."""
    manager = _require_manager()
    _validate_text_batch(request.texts)  # CRIT-2: single validation call

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

    except asyncio.TimeoutError:
        timeout = manager.inference_timeout
        logger.warning("Embedding generation timed out after %.2fs", timeout)
        raise HTTPException(status_code=504, detail="Embedding generation timed out after %s seconds" % timeout)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error generating embeddings")
        raise HTTPException(status_code=500, detail="Embedding generation failed")


@app.post("/rerank", response_model=RerankResponse)
async def rerank_candidates(request: RerankRequest):
    """Re-rank candidates using bge-reranker."""
    manager = _require_manager()
    _validate_rerank_payload(request.query, request.candidates, request.top_k)

    max_allowed = min(MAX_RERANK_TOP_K, len(request.candidates))
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

    except asyncio.TimeoutError:
        timeout = manager.inference_timeout
        logger.warning("Re-ranking timed out after %.2fs", timeout)
        raise HTTPException(status_code=504, detail="Re-ranking timed out after %s seconds" % timeout)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error re-ranking candidates")
        raise HTTPException(status_code=500, detail="Re-ranking failed")


@app.post("/classify", response_model=ClassifyResponse)
async def classify_pattern(request: ClassifyRequest):
    """Classify pattern using flan-t5-small."""
    manager = _require_manager()
    _validate_pattern_description(request.pattern_description)  # CRIT-2: single validation call

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

    except asyncio.TimeoutError:
        timeout = manager.inference_timeout
        logger.warning("Pattern classification timed out after %.2fs", timeout)
        raise HTTPException(status_code=504, detail="Classification timed out after %s seconds" % timeout)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error classifying pattern")
        raise HTTPException(status_code=500, detail="Classification failed")


# ---------------------------------------------------------------------------
# Entrypoint (LOW-1: configurable port)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8019"))
    uvicorn.run(app, host="0.0.0.0", port=port)
