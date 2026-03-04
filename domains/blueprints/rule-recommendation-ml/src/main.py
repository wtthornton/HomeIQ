"""
Rule Recommendation ML Service - Main Application

FastAPI service that provides rule recommendations based on
the Wyze Rule Recommendation dataset.

Port: 8035
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import init_feedback_store, load_model, router


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


def _init_feedback_store() -> None:
    """Initialize the feedback persistence store."""
    db_path = Path(os.getenv("FEEDBACK_DB_PATH", "/data/feedback.db"))
    init_feedback_store(db_path)
    logger.info("Feedback store ready", path=str(db_path))


def _load_recommendation_model() -> None:
    """Load rule recommendation model if available."""
    model_path = Path(os.getenv("MODEL_PATH", "./models/rule_recommender.pkl"))
    if model_path.exists():
        success = load_model(model_path)
        if success:
            logger.info("Model loaded successfully", path=str(model_path))
        else:
            logger.warning("Failed to load model", path=str(model_path))
    else:
        logger.info(
            "No pre-trained model found. Train a model and save to the configured path.",
            path=str(model_path)
        )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Rule Recommendation ML Service...")

    # Initialize feedback store (must be before model load)
    _init_feedback_store()

    # Load model if it exists
    _load_recommendation_model()

    yield

    # Shutdown
    logger.info("Shutting down Rule Recommendation ML Service...")


# Create FastAPI app
app = FastAPI(
    title="Rule Recommendation ML Service",
    description="ML-powered rule recommendations for HomeIQ based on Wyze dataset",
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
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "service": "rule-recommendation-ml",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=os.getenv("HOST", "0.0.0.0"),  # noqa: S104  # Docker requires binding to all interfaces
        port=int(os.getenv("PORT", "8035")),
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
