"""
RAG Service - Main FastAPI Application

Standalone RAG (Retrieval-Augmented Generation) microservice.
Following 2025 patterns: FastAPI, async/await, SQLAlchemy async.

This service provides:
- Semantic knowledge storage and retrieval
- Embedding-based similarity search
- OpenVINO service integration
- Metrics tracking for monitoring
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Setup logging (use shared logging config)
try:
    from shared.logging_config import setup_logging
    logger = setup_logging("rag-service")
except ImportError:
    # Fallback if shared logging not available
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("rag-service")

# Import shared error handler
try:
    from shared.error_handler import register_error_handlers
except ImportError:
    logger.warning("Shared error handler not available, using default error handling")
    register_error_handlers = None

# Import observability modules
try:
    from shared.observability import CorrelationMiddleware, instrument_fastapi, setup_tracing
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    logger.warning("Observability modules not available")
    OBSERVABILITY_AVAILABLE = False

from .api import health_router, metrics_router, rag_router
from .clients.openvino_client import OpenVINOClient
from .config import settings
from .database.session import init_db


async def _initialize_database() -> None:
    """Initialize database connection."""
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}", exc_info=True)
        raise


async def _setup_observability() -> None:
    """Setup observability if available."""
    if OBSERVABILITY_AVAILABLE:
        try:
            setup_tracing("rag-service")
            logger.info("✅ Observability initialized")
        except Exception as e:
            logger.warning(f"Observability setup failed: {e}")


# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize service on startup and cleanup on shutdown.
    
    This lifespan context manager handles:
    - Database initialization
    - Observability setup (if available)
    - Graceful shutdown
    
    Args:
        app: FastAPI application instance
    
    Yields:
        None: Control is yielded to the application runtime
    
    Raises:
        Exception: If database initialization fails (prevents service startup)
    """
    logger.info("=" * 60)
    logger.info("RAG Service Starting Up")
    logger.info("=" * 60)
    logger.info(f"Service Port: {settings.service_port}")
    logger.info(f"Database: {settings.database_path}")
    logger.info(f"OpenVINO Service: {settings.openvino_service_url}")
    logger.info(f"Embedding Cache Size: {settings.embedding_cache_size}")
    logger.info("=" * 60)
    
    # Initialize database
    await _initialize_database()

    # Create singleton OpenVINO client
    openvino_client = OpenVINOClient(base_url=settings.openvino_service_url)
    app.state.openvino_client = openvino_client

    # Create singleton embedding cache
    app.state.embedding_cache: dict[str, Any] = {}

    # Setup observability if available
    await _setup_observability()

    logger.info("[OK] RAG Service startup complete")
    logger.info("=" * 60)

    yield

    # Shutdown
    logger.info("=" * 60)
    logger.info("RAG Service Shutting Down")
    await openvino_client.close()
    logger.info("=" * 60)

# Create FastAPI app
app = FastAPI(
    title="RAG Service",
    description="Semantic knowledge storage and retrieval service with embeddings",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Register error handlers
if register_error_handlers:
    register_error_handlers(app)

# Instrument FastAPI for observability
if OBSERVABILITY_AVAILABLE:
    try:
        instrument_fastapi(app, "rag-service")
        app.add_middleware(CorrelationMiddleware)
    except Exception as e:
        logger.warning(f"Failed to instrument FastAPI: {e}")

# Include routers
app.include_router(health_router.router)
app.include_router(rag_router.router)
app.include_router(metrics_router.router)

@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint.
    
    Returns:
        Service information including name, version, and status.
    """
    return {
        "service": "rag-service",
        "version": "1.0.0",
        "status": "operational"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
