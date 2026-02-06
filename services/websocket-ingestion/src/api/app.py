"""
FastAPI application setup for websocket-ingestion service.
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from shared.observability.correlation import CorrelationMiddleware

from .routers import health, event_rate, discovery, filter, websocket

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    # Lazy import to avoid circular dependency
    from ..main import WebSocketIngestionService
    
    # Startup
    logger.info("Starting WebSocket Ingestion Service...")
    service = WebSocketIngestionService()
    app.state.service = service
    await service.start()
    logger.info("WebSocket Ingestion Service started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down WebSocket Ingestion Service...")
    if hasattr(app.state, 'service') and app.state.service:
        await app.state.service.stop()
    logger.info("WebSocket Ingestion Service stopped")


# Create FastAPI app
app = FastAPI(
    title="WebSocket Ingestion Service",
    description="Service for ingesting Home Assistant WebSocket events",
    version="1.0.0",
    lifespan=lifespan
)

# Add correlation middleware (must be first)
app.add_middleware(CorrelationMiddleware)

# Add CORS middleware
allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# Include routers
app.include_router(health.router)
app.include_router(event_rate.router)
app.include_router(discovery.router)
app.include_router(filter.router)
app.include_router(websocket.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "websocket-ingestion",
        "version": "1.0.0",
        "status": "operational"
    }

