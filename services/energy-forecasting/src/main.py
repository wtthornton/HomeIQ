"""
Energy Forecasting Service - Main Application

FastAPI service that provides energy consumption forecasting.

Port: 8037
"""

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from . import __version__
from .api.routes import router, load_model


def _configure_logging() -> None:
    """Configure structured logging for the service."""
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
            (
                structlog.dev.ConsoleRenderer()
                if os.getenv("DEBUG")
                else structlog.processors.JSONRenderer()
            ),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


# Configure structured logging
_configure_logging()
logger = structlog.get_logger(__name__)


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce request timeout."""

    def __init__(self, app, timeout: float = 30.0):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"detail": "Request timed out"},
            )


def _load_forecasting_model() -> None:
    """Load energy forecasting model if available."""
    model_path = Path(os.getenv("MODEL_PATH", "./models/energy_forecaster"))

    # Check for config in either format
    config_pkl = model_path.with_suffix(".config.pkl")
    config_json = model_path.with_suffix(".config.json")

    if config_pkl.exists() or config_json.exists():
        success = load_model(model_path)
        if success:
            logger.info("Model loaded successfully", path=str(model_path))
        else:
            logger.warning("Failed to load model", path=str(model_path))
    else:
        logger.info(
            "No model found. Train a model and save to the configured path.",
            path=str(model_path),
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Energy Forecasting Service...")

    # Load model
    _load_forecasting_model()

    yield

    # Shutdown
    logger.info("Shutting down Energy Forecasting Service...")


# Create FastAPI app
app = FastAPI(
    title="Energy Forecasting Service",
    description="ML-powered energy consumption forecasting for HomeIQ",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add timeout middleware
request_timeout = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
app.add_middleware(TimeoutMiddleware, timeout=request_timeout)

# Add CORS middleware with restrictive defaults
cors_origins = os.getenv("CORS_ORIGINS", "")
if cors_origins:
    origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
else:
    origins = ["http://localhost:3000", "http://localhost:8037"]
    logger.warning("CORS_ORIGINS not set, using restrictive defaults")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET"],  # This service only serves GET requests
    allow_headers=["*"],
)

# Include routers
app.include_router(router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "service": "energy-forecasting",
        "version": __version__,
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8037")),
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
