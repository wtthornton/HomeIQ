"""
FastAPI application setup for data-retention service.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.observability.correlation import CorrelationMiddleware

from .routers import health, policies, cleanup, backup, retention

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    # Lazy import to avoid circular dependency
    from ..main import DataRetentionService
    
    # Startup
    logger.info("Starting Data Retention Service...")
    service = DataRetentionService()
    app.state.service = service
    await service.start()
    logger.info("Data Retention Service started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Data Retention Service...")
    if hasattr(app.state, 'service') and app.state.service:
        await app.state.service.stop()
    logger.info("Data Retention Service stopped")


# Create FastAPI app
app = FastAPI(
    title="Data Retention Service",
    description="Service for data retention, cleanup, backup, and storage management",
    version="1.0.0",
    lifespan=lifespan
)

# Add correlation middleware (must be first)
app.add_middleware(CorrelationMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(policies.router)
app.include_router(cleanup.router)
app.include_router(backup.router)
app.include_router(retention.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "data-retention",
        "version": "1.0.0",
        "status": "operational"
    }

