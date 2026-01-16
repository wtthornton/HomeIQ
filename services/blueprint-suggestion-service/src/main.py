"""Main FastAPI application for Blueprint Suggestion Service."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import settings
from .database import close_db, init_db


def _configure_logging() -> None:
    """Configure logging for the service."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


# Configure logging
_configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup
    logger.info(f"Starting {settings.service_name} on port {settings.service_port}")
    await init_db()
    logger.info("Blueprint Suggestion Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Blueprint Suggestion Service...")
    await close_db()
    logger.info("Blueprint Suggestion Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Blueprint Suggestion Service",
    description="Matches Home Assistant Blueprints to devices and provides scored suggestions",
    version="1.0.0",
    lifespan=lifespan,
)

def _get_cors_origins() -> list[str]:
    """Get list of allowed CORS origins."""
    # CRITICAL: In production, replace ["*"] with specific origins
    # Using ["*"] with allow_credentials=True is a security vulnerability
    cors_origins_env = settings.cors_origins if hasattr(settings, "cors_origins") else None
    if cors_origins_env:
        return [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
    return ["*"]  # Development default


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.service_name}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=True,
    )
