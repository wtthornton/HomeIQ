"""
Proactive Agent Service - Context-aware automation suggestions
Epic AI-21: Proactive Conversational Agent Service

Responsibilities:
- Context analysis (weather, sports, energy, historical patterns)
- Smart prompt generation
- Agent-to-agent communication with HA AI Agent Service
- Scheduled proactive suggestion generation
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add shared directory to path for imports (robust path resolution)
shared_path_override = os.getenv('HOMEIQ_SHARED_PATH')
try:
    app_root = Path(__file__).resolve().parents[1]  # typically /app
except Exception:
    app_root = Path("/app")

candidate_paths = []
if shared_path_override:
    candidate_paths.append(Path(shared_path_override).expanduser())
candidate_paths.extend([
    app_root / "shared",
    Path("/app/shared"),
    Path.cwd() / "shared",
])

shared_path: Path | None = None
for p in candidate_paths:
    if p.exists():
        shared_path = p.resolve()
        break

if shared_path and str(shared_path) not in sys.path:
    sys.path.append(str(shared_path))
elif not shared_path:
    logging.warning("[proactive-agent-service] Warning: could not locate 'shared' directory in expected locations")

try:
    from shared.logging_config import setup_logging  # noqa: E402
except ImportError:
    # Fallback if shared logging not available
    logging.basicConfig(level=logging.INFO)
    setup_logging = lambda name: logging.getLogger(name)  # noqa: E731

from .config import Settings
from .api.health import router as health_router, set_scheduler_service_for_health
from .api.suggestions import router as suggestions_router, set_scheduler_service
from .database import init_database, close_database
from .services.scheduler_service import SchedulerService
from .services.suggestion_pipeline_service import SuggestionPipelineService

# Configure structured logging
logger = setup_logging("proactive-agent-service")

# Global settings instance
settings: Settings | None = None
# Global scheduler instance
scheduler_service: SchedulerService | None = None


def _parse_allowed_origins() -> list[str]:
    """Parse comma-delimited allowed origins from environment."""
    raw_origins = os.getenv("PROACTIVE_AGENT_ALLOWED_ORIGINS")
    if raw_origins:
        parsed = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
        if parsed:
            return parsed
    return ["http://localhost:3000", "http://localhost:3001"]


ALLOWED_ORIGINS = _parse_allowed_origins()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize services on startup, cleanup on shutdown"""
    global settings

    logger.info("Starting Proactive Agent Service...")
    try:
        # Load settings
        settings = Settings()
        logger.info(f"Settings loaded (Port: {settings.service_port})")

        # Initialize database (Story AI21.8)
        await init_database(settings)
        logger.info("Database initialized")

        # Initialize scheduler (Story AI21.7)
        global scheduler_service
        pipeline_service = SuggestionPipelineService()
        scheduler_service = SchedulerService(settings, pipeline_service=pipeline_service)
        scheduler_service.start()
        set_scheduler_service(scheduler_service)  # Set for suggestions API endpoints
        set_scheduler_service_for_health(scheduler_service)  # Set for health endpoint
        logger.info("Scheduler initialized")

        logger.info("Proactive Agent Service started successfully")
    except Exception as e:
        logger.error(f"Failed to start Proactive Agent Service: {e}", exc_info=True)
        raise

    yield

    # Cleanup on shutdown
    logger.info("Proactive Agent Service shutting down")
    if scheduler_service:
        scheduler_service.stop()
        scheduler_service = None
    await close_database()
    settings = None


# Create FastAPI app
app = FastAPI(
    title="Proactive Agent Service",
    description="Context-aware proactive automation suggestions",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Register routers
app.include_router(health_router)
app.include_router(suggestions_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8031)

