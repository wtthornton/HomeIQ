"""
OpenAI Client Service - Containerized OpenAI Integration
Provides OpenAI-based entity extraction as a microservice
"""

import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global OpenAI client
openai_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for service initialization and cleanup
    
    Context7 Pattern: Modern FastAPI lifespan management
    Replaces deprecated @app.on_event("startup") and @app.on_event("shutdown")
    """
    global openai_client
    
    # Startup: Initialize OpenAI client
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("No OpenAI API key provided, service will be disabled")
        else:
            openai_client = AsyncOpenAI(api_key=api_key)
            logger.info("OpenAI client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
    
    yield
    
    # Shutdown: Cleanup resources
    if openai_client:
        # OpenAI client doesn't require explicit cleanup, but we can clear the reference
        openai_client = None
        logger.info("OpenAI client cleaned up")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="OpenAI Client Service",
    description="OpenAI API client for complex entity extraction",
    version="1.0.0",
    lifespan=lifespan
)

class OpenAIExtractionRequest(BaseModel):
    query: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.1
    max_tokens: int = 300

class OpenAIExtractionResponse(BaseModel):
    entities: list[dict[str, Any]]
    processing_time: float
    model_used: str
    tokens_used: int
    cost_usd: float

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy" if openai_client else "disabled",
        "client_initialized": openai_client is not None,
        "api_key_configured": bool(os.getenv("OPENAI_API_KEY"))
    }

@app.post("/extract", response_model=OpenAIExtractionResponse)
async def extract_entities(request: OpenAIExtractionRequest):
    """
    Extract entities from query using OpenAI
    
    Args:
        request: OpenAI extraction request
        
    Returns:
        OpenAIExtractionResponse with extracted entities and metadata
    """
    if openai_client is None:
        raise HTTPException(status_code=503, detail="OpenAI client not initialized")

    start_time = time.time()

    try:
        prompt = f"""
        Extract entities from this Home Assistant automation query: "{request.query}"
        
        Return JSON with:
        {{
            "areas": ["office", "kitchen", "bedroom"],
            "devices": ["lights", "door sensor", "thermostat"],
            "actions": ["turn on", "flash", "monitor"],
            "intent": "automation"
        }}
        
        Focus on:
        - Room/area names
        - Device types (lights, sensors, switches, etc.)
        - Actions (turn on, flash, monitor, etc.)
        - Time references (morning, evening, sunset, etc.)
        """

        response = await openai_client.chat.completions.create(
            model=request.model,
            messages=[
                {"role": "system", "content": "You are a Home Assistant entity extraction expert. Extract entities from user queries for home automation."},
                {"role": "user", "content": prompt}
            ],
            temperature=request.temperature,
            max_completion_tokens=request.max_tokens  # Use max_completion_tokens for newer models
        )

        # Parse response
        content = response.choices[0].message.content
        entities = _parse_openai_response(content)

        processing_time = time.time() - start_time

        # Calculate cost (GPT-4o-mini pricing)
        tokens_used = response.usage.total_tokens
        cost_usd = tokens_used * 0.0004 / 1000  # $0.0004 per 1K tokens

        logger.info(f"Extracted {len(entities)} entities in {processing_time:.3f}s, cost: ${cost_usd:.6f}")

        return OpenAIExtractionResponse(
            entities=entities,
            processing_time=processing_time,
            model_used=request.model,
            tokens_used=tokens_used,
            cost_usd=cost_usd
        )

    except Exception as e:
        logger.error(f"OpenAI extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

def _parse_openai_response(content: str) -> list[dict[str, Any]]:
    """Parse OpenAI JSON response into entity format"""
    try:
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())

            entities = []
            # Convert OpenAI format to our entity format
            for area in data.get('areas', []):
                entities.append({
                    'name': area,
                    'type': 'area',
                    'domain': 'unknown',
                    'confidence': 0.9,
                    'extraction_method': 'openai'
                })

            for device in data.get('devices', []):
                entities.append({
                    'name': device,
                    'type': 'device',
                    'domain': 'unknown',
                    'confidence': 0.9,
                    'extraction_method': 'openai'
                })

            return entities
    except Exception as e:
        logger.error(f"Failed to parse OpenAI response: {e}")

    return []

@app.get("/model-info")
async def get_model_info():
    """Get information about available models"""
    return {
        "available_models": ["gpt-4o-mini", "gpt-3.5-turbo"],
        "default_model": "gpt-4o-mini",
        "cost_per_1k_tokens": 0.0004,
        "max_tokens": 300,
        "temperature_range": [0.0, 2.0]
    }

@app.get("/stats")
async def get_stats():
    """Get service statistics"""
    return {
        "service": "OpenAI Client Service",
        "status": "running" if openai_client else "disabled",
        "client_initialized": openai_client is not None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)
