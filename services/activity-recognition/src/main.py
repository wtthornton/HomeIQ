"""
Activity Recognition Service - Main Application

FastAPI service that provides activity recognition from sensor data.

Port: 8036
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router, load_model

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer() if os.getenv("DEBUG") else structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Activity Recognition Service...")
    
    # Load ONNX model
    model_path = Path(os.getenv("MODEL_PATH", "./models/activity_lstm.onnx"))
    if model_path.exists():
        success = load_model(model_path)
        if success:
            logger.info("ONNX model loaded successfully", path=str(model_path))
        else:
            logger.warning("Failed to load ONNX model", path=str(model_path))
    else:
        logger.info(
            "No ONNX model found. Train a model and export to ONNX.",
            path=str(model_path)
        )
    
    yield
    
    # Shutdown
    logger.info("Shutting down Activity Recognition Service...")


# Create FastAPI app
app = FastAPI(
    title="Activity Recognition Service",
    description="ML-powered activity recognition from smart home sensors",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "activity-recognition",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8036")),
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
