"""
Device Database Client Service
Phase 3.1: Client for external Device Database API

Queries external Device Database API (when available), caches device information locally,
and falls back to local intelligence if Device Database unavailable.
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

logger = setup_logging("device-database-client")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifecycle"""
    logger.info("Device Database Client Service starting up...")
    yield
    logger.info("Device Database Client Service shutting down...")


app = FastAPI(
    title="Device Database Client Service",
    version="1.0.0",
    description="Client for external Device Database API with local caching",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "device-database-client",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "device-database-client",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    port = int(os.getenv("DEVICE_DATABASE_CLIENT_PORT", "8022"))
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )

