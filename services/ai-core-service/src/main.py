"""
AI Core Service - Orchestrator
Phase 1: Containerized AI Models

Responsibilities:
- Service orchestration
- Request routing
- Circuit breaker patterns
- Fallback mechanisms
- Business logic
"""

import asyncio
import logging
import os
import secrets
import time
from collections import deque
from contextlib import asynccontextmanager
from typing import Any, Deque, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from .orchestrator.service_manager import ServiceManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances populated during startup
service_manager: Optional[ServiceManager] = None
api_key_value: Optional[str] = None


def _parse_allowed_origins() -> List[str]:
    """Parse comma-delimited allowed origins from environment."""
    raw_origins = os.getenv("AI_CORE_ALLOWED_ORIGINS")
    if raw_origins:
        parsed = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
        if parsed:
            return parsed
    return ["http://localhost:3000", "http://localhost:3001"]


RATE_LIMIT_REQUESTS = int(os.getenv("AI_CORE_RATE_LIMIT", "60"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("AI_CORE_RATE_LIMIT_WINDOW", "60"))
ALLOWED_ORIGINS = _parse_allowed_origins()


class RateLimiter:
    """Simple in-memory sliding window rate limiter."""

    def __init__(self, limit: int, window_seconds: int):
        self.limit = max(limit, 1)
        self.window = max(window_seconds, 1)
        self._requests: Dict[str, Deque[float]] = {}
        self._lock = asyncio.Lock()

    async def check(self, identifier: str) -> None:
        """Check and record a request for the given identifier."""
        async with self._lock:
            now = time.monotonic()
            window_start = now - self.window
            entries = self._requests.setdefault(identifier, deque())

            while entries and entries[0] < window_start:
                entries.popleft()

            if len(entries) >= self.limit:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")

            entries.append(now)


rate_limiter = RateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(provided_key: Optional[str] = Security(api_key_header)) -> str:
    """Validate API key from request headers."""
    global api_key_value

    if api_key_value is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    if not provided_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    if not secrets.compare_digest(provided_key, api_key_value):
        raise HTTPException(status_code=401, detail="Invalid API key")

    return provided_key


async def enforce_rate_limit(
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> None:
    """Enforce per-client + key rate limiting."""
    client_host = request.client.host if request.client else "unknown"
    identifier = f"{client_host}:{api_key}"
    await rate_limiter.check(identifier)

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize service manager on startup"""
    global service_manager, api_key_value

    logger.info("🚀 Starting AI Core Service...")
    try:
        api_key_value = os.getenv("AI_CORE_API_KEY")
        if not api_key_value:
            raise RuntimeError("AI_CORE_API_KEY environment variable must be set")

        # Get service URLs from environment
        openvino_url = os.getenv("OPENVINO_SERVICE_URL", "http://openvino-service:8019")
        ml_url = os.getenv("ML_SERVICE_URL", "http://ml-service:8020")
        ner_url = os.getenv("NER_SERVICE_URL", "http://ner-service:8031")
        openai_url = os.getenv("OPENAI_SERVICE_URL", "http://openai-service:8020")

        service_manager = ServiceManager(
            openvino_url=openvino_url,
            ml_url=ml_url,
            ner_url=ner_url,
            openai_url=openai_url
        )

        await service_manager.initialize()
        logger.info("✅ AI Core Service started successfully")
    except Exception as e:
        logger.error(f"❌ Failed to start AI Core Service: {e}")
        raise

    yield

    # Cleanup on shutdown (if needed)
    logger.info("🛑 AI Core Service shutting down")
    if service_manager:
        await service_manager.aclose()
    api_key_value = None

# Create FastAPI app
app = FastAPI(
    title="AI Core Service",
    description="Orchestrator for containerized AI models",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

# Pydantic models
class AnalysisRequest(BaseModel):
    data: List[Dict[str, Any]] = Field(..., description="Data to analyze")
    analysis_type: str = Field(..., description="Type of analysis to perform")
    options: Dict[str, Any] = Field(default_factory=dict, description="Analysis options")

class AnalysisResponse(BaseModel):
    results: Dict[str, Any] = Field(..., description="Analysis results")
    services_used: List[str] = Field(..., description="Services used in analysis")
    processing_time: float = Field(..., description="Total processing time in seconds")

class PatternDetectionRequest(BaseModel):
    patterns: List[Dict[str, Any]] = Field(..., description="Patterns to detect")
    detection_type: str = Field("full", description="Type of pattern detection")

class PatternDetectionResponse(BaseModel):
    detected_patterns: List[Dict[str, Any]] = Field(..., description="Detected patterns")
    services_used: List[str] = Field(..., description="Services used")
    processing_time: float = Field(..., description="Processing time in seconds")

class SuggestionRequest(BaseModel):
    context: Dict[str, Any] = Field(..., description="Context for suggestions")
    suggestion_type: str = Field(..., description="Type of suggestions to generate")

class SuggestionResponse(BaseModel):
    suggestions: List[Dict[str, Any]] = Field(..., description="Generated suggestions")
    services_used: List[str] = Field(..., description="Services used")
    processing_time: float = Field(..., description="Processing time in seconds")

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not service_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    service_status = await service_manager.get_service_status()
    
    return {
        "status": "healthy",
        "service": "ai-core-service",
        "services": service_status
    }

@app.get("/services/status")
async def get_service_status(_: None = Depends(enforce_rate_limit)):
    """Get detailed service status"""
    if not service_manager:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return await service_manager.get_service_status()

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_data(
    request: AnalysisRequest,
    _: None = Depends(enforce_rate_limit),
):
    """Perform comprehensive data analysis"""
    if not service_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        start_time = time.time()
        
        results, services_used = await service_manager.analyze_data(
            data=request.data,
            analysis_type=request.analysis_type,
            options=request.options
        )
        
        processing_time = time.time() - start_time
        
        return AnalysisResponse(
            results=results,
            services_used=services_used,
            processing_time=processing_time
        )
    
    except Exception:
        logger.exception("Error in data analysis")
        raise HTTPException(status_code=500, detail="Analysis failed")

@app.post("/patterns", response_model=PatternDetectionResponse)
async def detect_patterns(
    request: PatternDetectionRequest,
    _: None = Depends(enforce_rate_limit),
):
    """Detect patterns in data"""
    if not service_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        start_time = time.time()
        
        patterns, services_used = await service_manager.detect_patterns(
            patterns=request.patterns,
            detection_type=request.detection_type
        )
        
        processing_time = time.time() - start_time
        
        return PatternDetectionResponse(
            detected_patterns=patterns,
            services_used=services_used,
            processing_time=processing_time
        )
    
    except Exception:
        logger.exception("Error in pattern detection")
        raise HTTPException(status_code=500, detail="Pattern detection failed")

@app.post("/suggestions", response_model=SuggestionResponse)
async def generate_suggestions(
    request: SuggestionRequest,
    _: None = Depends(enforce_rate_limit),
):
    """Generate AI suggestions"""
    if not service_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        start_time = time.time()
        
        suggestions, services_used = await service_manager.generate_suggestions(
            context=request.context,
            suggestion_type=request.suggestion_type
        )
        
        processing_time = time.time() - start_time
        
        return SuggestionResponse(
            suggestions=suggestions,
            services_used=services_used,
            processing_time=processing_time
        )
    
    except Exception:
        logger.exception("Error generating suggestions")
        raise HTTPException(status_code=500, detail="Suggestion generation failed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8018)
