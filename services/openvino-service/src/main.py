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
from contextlib import asynccontextmanager
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .models.openvino_manager import OpenVINOManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model manager
openvino_manager: OpenVINOManager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global openvino_manager
    
    # Startup
    logger.info("🚀 Starting OpenVINO Service...")
    try:
        openvino_manager = OpenVINOManager()
        await openvino_manager.initialize()
        logger.info("✅ OpenVINO Service started successfully")
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

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not openvino_manager or not openvino_manager.is_ready():
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return {
        "status": "healthy",
        "service": "openvino-service",
        "models_loaded": openvino_manager.get_model_status()
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
    
    try:
        import time
        start_time = time.time()
        
        embeddings = await openvino_manager.generate_embeddings(
            texts=request.texts,
            normalize=request.normalize
        )
        
        processing_time = time.time() - start_time
        
        return EmbeddingResponse(
            embeddings=embeddings.tolist(),
            model_name="all-MiniLM-L6-v2",
            processing_time=processing_time
        )
    
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {e}")

@app.post("/rerank", response_model=RerankResponse)
async def rerank_candidates(request: RerankRequest):
    """Re-rank candidates using bge-reranker"""
    if not openvino_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        import time
        start_time = time.time()
        
        ranked_candidates = await openvino_manager.rerank(
            query=request.query,
            candidates=request.candidates,
            top_k=request.top_k
        )
        
        processing_time = time.time() - start_time
        
        return RerankResponse(
            ranked_candidates=ranked_candidates,
            model_name="bge-reranker-base",
            processing_time=processing_time
        )
    
    except Exception as e:
        logger.error(f"Error re-ranking candidates: {e}")
        raise HTTPException(status_code=500, detail=f"Re-ranking failed: {e}")

@app.post("/classify", response_model=ClassifyResponse)
async def classify_pattern(request: ClassifyRequest):
    """Classify pattern using flan-t5-small"""
    if not openvino_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        import time
        start_time = time.time()
        
        classification = await openvino_manager.classify_pattern(
            pattern_description=request.pattern_description
        )
        
        processing_time = time.time() - start_time
        
        return ClassifyResponse(
            category=classification['category'],
            priority=classification['priority'],
            model_name="flan-t5-small",
            processing_time=processing_time
        )
    
    except Exception as e:
        logger.error(f"Error classifying pattern: {e}")
        raise HTTPException(status_code=500, detail=f"Classification failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8019)
