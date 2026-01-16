"""
Device Setup Assistant Service
Phase 2.3: Provide setup guides and detect setup issues for new devices
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

logger = setup_logging("device-setup-assistant")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifecycle"""
    logger.info("Device Setup Assistant Service starting up...")
    yield
    logger.info("Device Setup Assistant Service shutting down...")


app = FastAPI(
    title="Device Setup Assistant Service",
    version="1.0.0",
    description="Device setup guides and issue detection",
    lifespan=lifespan
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "device-setup-assistant",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint"""
    return {
        "service": "device-setup-assistant",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    port = int(os.getenv("DEVICE_SETUP_ASSISTANT_PORT", "8021"))
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )

