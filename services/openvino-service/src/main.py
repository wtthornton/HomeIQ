"""
OpenVINO Service - Optimized Model Inference
Phase 1: Containerized AI Models

Provides optimized model inference for:
- all-MiniLM-L6-v2 (INT8) - Embeddings
- bge-reranker-base (INT8) - Re-ranking  
- flan-t5-small (INT8) - Classification
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .models.openvino_manager import OpenVINOManager

MAX_TEXTS = int(os.getenv("OPENVINO_MAX_TEXTS", "100"))
MAX_TEXT_LENGTH = int(os.getenv("OPENVINO_MAX_TEXT_LENGTH", "10000"))
MAX_RERANK_CANDIDATES = int(os.getenv("OPENVINO_MAX_RERANK_CANDIDATES", "200"))
MAX_TOP_K = int(os.getenv("OPENVINO_MAX_TOP_K", "50"))
MAX_QUERY_LENGTH = int(os.getenv("OPENVINO_MAX_QUERY_LENGTH", "2000"))
MAX_PATTERN_LENGTH = int(os.getenv("OPENVINO_MAX_PATTERN_LENGTH", "8000"))
PRELOAD_MODELS = os.getenv("OPENVINO_PRELOAD_MODELS", "false").lower() in {"1", "true", "yes"}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service guards & configuration
MAX_EMBEDDING_TEXTS = int(os.getenv("OPENVINO_MAX_EMBEDDING_TEXTS", "100"))
MAX_TEXT_LENGTH = int(os.getenv("OPENVINO_MAX_TEXT_LENGTH", "4000"))
MAX_RERANK_CANDIDATES = int(os.getenv("OPENVINO_MAX_RERANK_CANDIDATES", "200"))
MAX_RERANK_TOP_K = int(os.getenv("OPENVINO_MAX_RERANK_TOP_K", "50"))
MAX_PATTERN_LENGTH = int(os.getenv("OPENVINO_MAX_PATTERN_LENGTH", "4000"))
PRELOAD_MODELS = os.getenv("OPENVINO_PRELOAD_MODELS", "false").lower() in {"1", "true", "yes"}
MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "/app/models")

# Global model manager
openvino_manager: OpenVINOManager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global openvino_manager

    logger.info("🚀 Starting OpenVINO Service...")
    try:
        openvino_manager = OpenVINOManager()
        if PRELOAD_MODELS:
            await openvino_manager.initialize()
            logger.info("✅ OpenVINO Service started successfully (models preloaded)")
        else:
            logger.info("✅ OpenVINO Service started successfully (models will lazy-load)")
    except Exception:
        logger.exception("❌ Failed to start OpenVINO Service")
        raise

    yield

    # Shutdown
    logger.info("🛑 Shutting down OpenVINO Service...")
    if openvino_manager:
        await openvino_manager.cleanup()
    logger.info("✅ OpenVINO Service shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="OpenVINO Service",
    description="Optimized model inference using OpenVINO INT8 quantization",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
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


def _require_manager() -> OpenVINOManager:
    if not openvino_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    return openvino_manager


def _validate_text_batch(texts: list[str]) -> None:
    if not texts:
        raise HTTPException(status_code=400, detail="At least one text is required")
    if len(texts) > MAX_TEXTS:
        raise HTTPException(status_code=400, detail=f"Too many texts (max {MAX_TEXTS})")

    for idx, text in enumerate(texts):
        if not isinstance(text, str):
            raise HTTPException(status_code=400, detail=f"Text at index {idx} must be a string")
        if len(text) > MAX_TEXT_LENGTH:
            raise HTTPException(status_code=400, detail=f"Text at index {idx} exceeds {MAX_TEXT_LENGTH} characters")
        if not text.strip():
            raise HTTPException(status_code=400, detail="Texts cannot be empty strings")


def _validate_rerank_payload(query: str, candidates: list[dict[str, Any]], top_k: int) -> None:
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query text is required")
    if len(query) > MAX_QUERY_LENGTH:
        raise HTTPException(status_code=400, detail=f"Query exceeds {MAX_QUERY_LENGTH} characters")

    if not candidates:
        raise HTTPException(status_code=400, detail="At least one candidate is required")
    if len(candidates) > MAX_RERANK_CANDIDATES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many candidates (max {MAX_RERANK_CANDIDATES})"
        )

    for idx, candidate in enumerate(candidates):
        description = str(candidate.get("description", ""))
        if len(description) > MAX_TEXT_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Candidate description at index {idx} exceeds {MAX_TEXT_LENGTH} characters"
            )

    max_allowed = min(MAX_TOP_K, len(candidates))
    if top_k < 1 or top_k > max_allowed:
        raise HTTPException(
            status_code=400,
            detail=f"top_k must be between 1 and {max_allowed}"
        )


def _validate_pattern_description(description: str) -> None:
    if not description or not description.strip():
        raise HTTPException(status_code=400, detail="pattern_description cannot be empty")
    if len(description) > MAX_PATTERN_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"pattern_description exceeds {MAX_PATTERN_LENGTH} characters"
        )

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint - reports readiness and model status."""
    manager = _require_manager()
    readiness = manager.is_ready()

    model_status = manager.get_model_status()

    model_status = openvino_manager.get_model_status()
    ready_state = "ready" if model_status.get("all_models_loaded") else "warming"

    return {
        "status": "healthy" if readiness else "initializing",
        "service": "openvino-service",
        "ready": readiness,
        "models_loaded": model_status
    }

@app.get("/models/status")
async def get_model_status():
    """Get detailed model status"""
    manager = _require_manager()
    return manager.get_model_status()

@app.post("/embeddings", response_model=EmbeddingResponse)
async def generate_embeddings(request: EmbeddingRequest):
    """Generate embeddings for texts"""
    manager = _require_manager()
    _validate_text_batch(request.texts)

    _validate_text_batch(request.texts)

    try:
        start_time = time.perf_counter()

        embeddings = await manager.generate_embeddings(
            texts=request.texts,
            normalize=request.normalize
        )

        processing_time = time.perf_counter() - start_time

        # Epic 47: Use dynamic model name from manager
        model_name = manager.embedding_model_name if hasattr(manager, 'embedding_model_name') else "all-MiniLM-L6-v2"
        
        return EmbeddingResponse(
            embeddings=embeddings.tolist(),
            model_name=model_name,
            processing_time=processing_time
        )

    except asyncio.TimeoutError:
        timeout = manager.inference_timeout
        logger.warning("Embedding generation timed out after %.2fs", timeout)
        raise HTTPException(status_code=504, detail=f"Embedding generation timed out after {timeout} seconds")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error generating embeddings")
        raise HTTPException(status_code=500, detail="Embedding generation failed")

@app.post("/rerank", response_model=RerankResponse)
async def rerank_candidates(request: RerankRequest):
    """Re-rank candidates using bge-reranker"""
    manager = _require_manager()
    _validate_rerank_payload(request.query, request.candidates, request.top_k)

    max_allowed = min(MAX_RERANK_TOP_K, len(request.candidates))
    top_k = max(1, min(request.top_k, max_allowed))

    try:
        start_time = time.perf_counter()

        ranked_candidates = await manager.rerank(
            query=request.query,
            candidates=request.candidates,
            top_k=top_k
        )

        processing_time = time.perf_counter() - start_time

        return RerankResponse(
            ranked_candidates=ranked_candidates,
            model_name="bge-reranker-base",
            processing_time=processing_time
        )

    except asyncio.TimeoutError:
        timeout = manager.inference_timeout
        logger.warning("Re-ranking timed out after %.2fs", timeout)
        raise HTTPException(status_code=504, detail=f"Re-ranking timed out after {timeout} seconds")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error re-ranking candidates")
        raise HTTPException(status_code=500, detail="Re-ranking failed")

@app.post("/classify", response_model=ClassifyResponse)
async def classify_pattern(request: ClassifyRequest):
    """Classify pattern using flan-t5-small"""
    manager = _require_manager()
    _validate_pattern_description(request.pattern_description)

    _validate_pattern_description(request.pattern_description)

    try:
        start_time = time.perf_counter()

        classification = await manager.classify_pattern(
            pattern_description=request.pattern_description
        )

        processing_time = time.perf_counter() - start_time

        return ClassifyResponse(
            category=classification['category'],
            priority=classification['priority'],
            model_name="flan-t5-small",
            processing_time=processing_time
        )

    except asyncio.TimeoutError:
        timeout = manager.inference_timeout
        logger.warning("Pattern classification timed out after %.2fs", timeout)
        raise HTTPException(status_code=504, detail=f"Classification timed out after {timeout} seconds")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error classifying pattern")
        raise HTTPException(status_code=500, detail="Classification failed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8019)
