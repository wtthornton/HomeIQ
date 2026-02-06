"""
FastAPI application setup for data-retention service.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

from shared.observability.correlation import CorrelationMiddleware

from .routers import health, policies, cleanup, backup, retention

logger = logging.getLogger(__name__)

# --- Authentication ---
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    """Verify the API key for mutation endpoints."""
    expected_key = os.getenv("DATA_RETENTION_API_KEY")
    if not expected_key:
        raise HTTPException(status_code=500, detail="API key not configured")
    if not api_key or api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key


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

# Add CORS middleware (restricted origins)
ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

# Include routers - GET-only routers (monitoring) without auth
app.include_router(health.router)

# Mutation routers require API key authentication
app.include_router(policies.router, dependencies=[Depends(verify_api_key)])
app.include_router(cleanup.router, dependencies=[Depends(verify_api_key)])
app.include_router(backup.router, dependencies=[Depends(verify_api_key)])
app.include_router(retention.router, dependencies=[Depends(verify_api_key)])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "data-retention",
        "version": "1.0.0",
        "status": "operational"
    }

