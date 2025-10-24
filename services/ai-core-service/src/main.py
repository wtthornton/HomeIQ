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

import logging
import os
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .orchestrator.service_manager import ServiceManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global service manager
service_manager: ServiceManager = None

# Create FastAPI app
app = FastAPI(
    title="AI Core Service",
    description="Orchestrator for containerized AI models",
    version="1.0.0"
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

# Initialize service manager
@app.on_event("startup")
async def startup_event():
    """Initialize service manager on startup"""
    global service_manager
    
    logger.info("🚀 Starting AI Core Service...")
    try:
        # Get service URLs from environment
        openvino_url = os.getenv("OPENVINO_SERVICE_URL", "http://openvino-service:8019")
        ml_url = os.getenv("ML_SERVICE_URL", "http://ml-service:8020")
        ner_url = os.getenv("NER_SERVICE_URL", "http://ner-service:8019")
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
async def get_service_status():
    """Get detailed service status"""
    if not service_manager:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return await service_manager.get_service_status()

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_data(request: AnalysisRequest):
    """Perform comprehensive data analysis"""
    if not service_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        import time
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
    
    except Exception as e:
        logger.error(f"Error in data analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

@app.post("/patterns", response_model=PatternDetectionResponse)
async def detect_patterns(request: PatternDetectionRequest):
    """Detect patterns in data"""
    if not service_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        import time
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
    
    except Exception as e:
        logger.error(f"Error in pattern detection: {e}")
        raise HTTPException(status_code=500, detail=f"Pattern detection failed: {e}")

@app.post("/suggestions", response_model=SuggestionResponse)
async def generate_suggestions(request: SuggestionRequest):
    """Generate AI suggestions"""
    if not service_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        import time
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
    
    except Exception as e:
        logger.error(f"Error generating suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Suggestion generation failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8018)
