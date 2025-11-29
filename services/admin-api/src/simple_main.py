"""
Simplified Admin API for Dashboard Integration
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path so we can import shared module
# In container: /app/shared exists, so add /app to path
# In dev: ../../../shared exists, so add parent to path
if os.path.exists('/app/shared'):
    sys.path.insert(0, '/app')
else:
    # Fallback for local development
    parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    if os.path.exists(os.path.join(parent_dir, 'shared')):
        sys.path.insert(0, parent_dir)

from shared.endpoints import create_integration_router, simple_health_router
from src.config_manager import config_manager

health_router = simple_health_router
integration_router = create_integration_router(config_manager)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting simplified Admin API service...")
    yield
    logger.info("Shutting down simplified Admin API service...")


# Create FastAPI app
app = FastAPI(
    title="HA Ingestor Admin API - Simplified",
    description="Simplified Admin API for Dashboard Integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include health router
app.include_router(health_router, prefix="/api/v1", tags=["Health"])

# Include integration management router
app.include_router(integration_router, prefix="/api/v1", tags=["Integration Management"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "HA Ingestor Admin API - Simplified",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8004"))

    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
