"""
OpenVINO Service - Optimized Model Inference
Phase 1: Containerized AI Models

Provides optimized model inference for:
- all-MiniLM-L6-v2 (INT8) - Embeddings
- bge-reranker-base (INT8) - Re-ranking  
- flan-t5-small (INT8) - Classification
"""

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .models.openvino_manager import OpenVINOManager

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
        openvino_manager = OpenVINOManager(models_dir=MODEL_CACHE_DIR)
        if PRELOAD_MODELS:
            logger.info("⏳ Pre-loading OpenVINO models at startup (override via OPENVINO_PRELOAD_MODELS)")
            await openvino_manager.initialize()
        else:
            logger.info("✅ OpenVINO Service started in lazy-loading mode (set OPENVINO_PRELOAD_MODELS=1 to warm models)")
    except Exception as e:
        logger.error(f"❌ Failed to start OpenVINO Service: {e}")
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
    texts: List[str] = Field(..., description="List of texts to embed")
    normalize: bool = Field(True, description="Normalize embeddings")

class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]] = Field(..., description="Generated embeddings")
    model_name: str = Field(..., description="Model used")
    processing_time: float = Field(..., description="Processing time in seconds")

class RerankRequest(BaseModel):
    query: str = Field(..., description="Query text")
    candidates: List[Dict[str, Any]] = Field(..., description="Candidates to re-rank")
    top_k: int = Field(10, description="Number of top results to return")

class RerankResponse(BaseModel):
    ranked_candidates: List[Dict[str, Any]] = Field(..., description="Re-ranked candidates")
    model_name: str = Field(..., description="Model used")
    processing_time: float = Field(..., description="Processing time in seconds")

class ClassifyRequest(BaseModel):
    pattern_description: str = Field(..., description="Pattern description to classify")

class ClassifyResponse(BaseModel):
    category: str = Field(..., description="Pattern category")
    priority: str = Field(..., description="Pattern priority")
    model_name: str = Field(..., description="Model used")
    processing_time: float = Field(..., description="Processing time in seconds")


def _validate_text_batch(texts: List[str]) -> None:
    if not texts:
        raise HTTPException(status_code=400, detail="At least one text is required")
    if len(texts) > MAX_EMBEDDING_TEXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Too many texts supplied (max {MAX_EMBEDDING_TEXTS})"
        )
    for text in texts:
        if text is None:
            raise HTTPException(status_code=400, detail="Texts cannot be null")
        if len(text) > MAX_TEXT_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Text exceeds maximum length of {MAX_TEXT_LENGTH} characters"
            )


def _validate_rerank_request(request: RerankRequest) -> int:
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query text cannot be empty")
    if len(request.query) > MAX_TEXT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Query exceeds maximum length of {MAX_TEXT_LENGTH} characters"
        )
    if not request.candidates:
        raise HTTPException(status_code=400, detail="At least one candidate is required")
    if len(request.candidates) > MAX_RERANK_CANDIDATES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many candidates supplied (max {MAX_RERANK_CANDIDATES})"
        )
    if request.top_k <= 0:
        raise HTTPException(status_code=400, detail="top_k must be greater than zero")
    
    return min(request.top_k, len(request.candidates), MAX_RERANK_TOP_K)


def _validate_pattern_description(description: str) -> None:
    if not description or not description.strip():
        raise HTTPException(status_code=400, detail="Pattern description is required")
    if len(description) > MAX_PATTERN_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Pattern description exceeds {MAX_PATTERN_LENGTH} characters"
        )

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint with model readiness information"""
    if not openvino_manager:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    model_status = openvino_manager.get_model_status()
    ready_state = "ready" if model_status.get("all_models_loaded") else "warming"
    
    return {
        "status": ready_state,
        "service": "openvino-service",
        "ready": model_status.get("ready_for_requests", False),
        "details": model_status
    }

@app.get("/models/status")
async def get_model_status():
    """Get detailed model status"""
    if not openvino_manager:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return openvino_manager.get_model_status()

@app.post("/embeddings", response_model=EmbeddingResponse)
async def generate_embeddings(request: EmbeddingRequest):
    """Generate embeddings for texts"""
    if not openvino_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    _validate_text_batch(request.texts)
    
    try:
        start_time = time.perf_counter()
        
        embeddings = await openvino_manager.generate_embeddings(
            texts=request.texts,
            normalize=request.normalize
        )
        
        processing_time = time.perf_counter() - start_time
        
        return EmbeddingResponse(
            embeddings=embeddings.tolist(),
            model_name="all-MiniLM-L6-v2",
            processing_time=processing_time
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Error generating embeddings")
        raise HTTPException(status_code=500, detail="Embedding generation failed")

@app.post("/rerank", response_model=RerankResponse)
async def rerank_candidates(request: RerankRequest):
    """Re-rank candidates using bge-reranker"""
    if not openvino_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    top_k = _validate_rerank_request(request)
    
    try:
        start_time = time.perf_counter()
        
        ranked_candidates = await openvino_manager.rerank(
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
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Error re-ranking candidates")
        raise HTTPException(status_code=500, detail="Re-ranking failed")

@app.post("/classify", response_model=ClassifyResponse)
async def classify_pattern(request: ClassifyRequest):
    """Classify pattern using flan-t5-small"""
    if not openvino_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    _validate_pattern_description(request.pattern_description)
    
    try:
        start_time = time.perf_counter()
        
        classification = await openvino_manager.classify_pattern(
            pattern_description=request.pattern_description
        )
        
        processing_time = time.perf_counter() - start_time
        
        return ClassifyResponse(
            category=classification['category'],
            priority=classification['priority'],
            model_name="flan-t5-small",
            processing_time=processing_time
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Error classifying pattern")
        raise HTTPException(status_code=500, detail="Classification failed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8019)
