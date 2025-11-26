"""
Device Health Monitor Service
Phase 1.2: Monitor device health and provide maintenance insights

Analyzes device response times, battery levels, power consumption, and generates health reports.
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

logger = setup_logging("device-health-monitor")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifecycle"""
    # Startup
    logger.info("Device Health Monitor Service starting up...")
    yield
    # Shutdown
    logger.info("Device Health Monitor Service shutting down...")


app = FastAPI(
    title="Device Health Monitor Service",
    version="1.0.0",
    description="Device health monitoring and maintenance insights",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "device-health-monitor",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "device-health-monitor",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    port = int(os.getenv("DEVICE_HEALTH_MONITOR_PORT", "8019"))
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )

