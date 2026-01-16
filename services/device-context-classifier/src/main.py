"""
Device Context Classifier Service
Phase 2.1: Classify devices based on entity patterns

Analyzes entities to infer device types (fridge, car, 3D printer, etc.)
"""

import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from fastapi import FastAPI

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.logging_config import setup_logging

logger = setup_logging("device-context-classifier")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifecycle"""
    logger.info("Device Context Classifier Service starting up...")
    yield
    logger.info("Device Context Classifier Service shutting down...")


app = FastAPI(
    title="Device Context Classifier Service",
    version="1.0.0",
    description="Device type classification based on entity patterns",
    lifespan=lifespan
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "device-context-classifier",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint"""
    return {
        "service": "device-context-classifier",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    port = int(os.getenv("DEVICE_CONTEXT_CLASSIFIER_PORT", "8020"))
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )

