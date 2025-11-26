"""
Device Recommender Service
Phase 3.3: Device recommendations and comparisons

Recommends devices based on user requirements, compares devices,
and provides device ratings from Device Database.
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

logger = setup_logging("device-recommender")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifecycle"""
    logger.info("Device Recommender Service starting up...")
    yield
    logger.info("Device Recommender Service shutting down...")


app = FastAPI(
    title="Device Recommender Service",
    version="1.0.0",
    description="Device recommendations and comparisons",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "device-recommender",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "device-recommender",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    port = int(os.getenv("DEVICE_RECOMMENDER_PORT", "8023"))
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )

