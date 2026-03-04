"""
AI Automation Service - Main FastAPI Application

Epic 39, Story 39.10: Automation Service Foundation

This service was extracted from ai-automation-service for independent scaling and maintainability.
It handles:
- Automation suggestion generation
- YAML generation for Home Assistant automations
- Deployment of automations to Home Assistant
- Automation lifecycle management (enable/disable/rollback)
"""

import logging
import os

from homeiq_resilience import ServiceLifespan, create_app

# Setup logging (use shared logging config)
try:
    from homeiq_observability.logging_config import setup_logging

    logger = setup_logging("ai-automation-service", group_name="automation-intelligence")
except ImportError:
    # Fallback if shared logging not available
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ai-automation-service")

# Import shared error handler
try:
    from homeiq_data.error_handler import register_error_handlers
except ImportError:
    logger.warning("Shared error handler not available, using default error handling")
    register_error_handlers = None

# Import observability modules
try:
    from homeiq_observability.observability import (
        CorrelationMiddleware,
        instrument_fastapi,
        setup_tracing,
    )

    OBSERVABILITY_AVAILABLE = True
except ImportError:
    logger.warning("Observability modules not available")
    OBSERVABILITY_AVAILABLE = False

from .api import (
    analysis_router,
    automation_compile_router,
    automation_lifecycle_router,
    automation_plan_router,
    automation_validate_router,
    automation_yaml_validate_router,
    blueprint_validate_router,
    deployment_router,
    health_router,
    pattern_router,
    preference_router,
    scene_validate_router,
    script_validate_router,
    setup_validate_router,
    suggestion_router,
    synergy_router,
)
from .api.dependencies import close_clients, init_clients
from .api.middlewares import (
    AuthenticationMiddleware,
    RateLimitMiddleware,
    start_rate_limit_cleanup,
    stop_rate_limit_cleanup,
)
from .clients.data_api_client import DataAPIClient
from .clients.openai_client import OpenAIClient
from .config import settings
from .database import async_session_maker, init_db
from .services.suggestion_service import SuggestionService

# Scheduler for automatic suggestion generation
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    AsyncIOScheduler = None
    CronTrigger = None

scheduler: AsyncIOScheduler | None = None

# Module-level health checker, initialised during lifespan.
from homeiq_resilience import GroupHealthCheck

_group_health: GroupHealthCheck | None = None


def _parse_schedule_time() -> tuple[int, int]:
    """Parse scheduler_time (HH:MM) into (hour, minute). Raises ValueError if invalid."""
    schedule_time = settings.scheduler_time.split(":")
    if len(schedule_time) < 1 or len(schedule_time) > 2:
        msg = f"Invalid scheduler_time format: '{settings.scheduler_time}'. Expected 'HH:MM'."
        raise ValueError(msg)
    hour = int(schedule_time[0])
    minute = int(schedule_time[1]) if len(schedule_time) > 1 else 0
    if not (0 <= hour <= 23) or not (0 <= minute <= 59):
        msg = f"Invalid scheduler_time values: hour={hour}, minute={minute}"
        raise ValueError(msg)
    return hour, minute


def _start_scheduler() -> None:
    """Start the scheduler for automatic suggestion generation."""
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler()

    if not scheduler:
        return

    try:
        hour, minute = _parse_schedule_time()
        scheduler.add_job(
            generate_daily_suggestions,
            CronTrigger(hour=hour, minute=minute, timezone=settings.scheduler_timezone),
            id="daily_suggestion_generation",
            name="Daily Automation Suggestion Generation",
            replace_existing=True,
            max_instances=1,  # Prevent overlap
            coalesce=True,  # Skip if previous run still active
            misfire_grace_time=3600,  # Allow 1 hour delay if server was down
        )
        scheduler.start()

        job = scheduler.get_job("daily_suggestion_generation")
        next_run = job.next_run_time if job else None
        logger.info(
            "Scheduler started: daily suggestions at %s (%s)",
            settings.scheduler_time,
            settings.scheduler_timezone,
        )
        if next_run:
            logger.info("Next scheduled run: %s", next_run)
    except Exception as e:
        logger.error("Failed to start scheduler: %s", e, exc_info=True)
        logger.warning("Service will continue without automatic suggestion generation")


def _stop_scheduler() -> None:
    """Stop the scheduler gracefully."""
    global scheduler
    if scheduler and scheduler.running:
        try:
            scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")
        except Exception:
            logger.warning("Scheduler shutdown failed", exc_info=True)


async def generate_daily_suggestions() -> None:
    """Scheduled job to generate automation suggestions daily."""
    logger.info("Starting scheduled daily suggestion generation")

    try:
        async with async_session_maker() as db_session:
            data_api_client = DataAPIClient(base_url=settings.data_api_url)
            openai_client = OpenAIClient(
                api_key=settings.openai_api_key, model=settings.openai_model,
            )
            suggestion_service = SuggestionService(
                db=db_session, data_api_client=data_api_client, openai_client=openai_client,
            )

            suggestions = await suggestion_service.generate_suggestions(
                limit=settings.scheduler_suggestion_limit, days=30,
            )

            logger.info(
                "Scheduled suggestion generation complete: Generated %d suggestions",
                len(suggestions),
            )

            await data_api_client.close()

    except Exception:
        logger.exception("Error in scheduled suggestion generation")


# ---------------------------------------------------------------------------
# Startup / Shutdown hooks for ServiceLifespan
# ---------------------------------------------------------------------------

async def _startup() -> None:
    """Initialize all resources on startup."""
    global _group_health

    from homeiq_resilience import wait_for_dependency

    logger.info("Service Port: %s", settings.service_port)
    logger.info("Database: %s", settings.database_path)
    logger.info("Data API: %s", settings.data_api_url)

    # Initialize singleton HTTP clients (C4 fix)
    init_clients()

    # Initialize database
    db_ok = await init_db()
    if db_ok:
        logger.info("Database initialized")
    else:
        logger.warning("Database unavailable -- starting in degraded mode")

    # Probe cross-group dependencies (non-fatal)
    data_api_available = await wait_for_dependency(
        url=settings.data_api_url, name="data-api", max_retries=10,
    )

    # Structured group health
    _group_health = GroupHealthCheck(
        group_name="automation-intelligence", version="1.0.0",
    )
    _group_health.register_dependency("data-api", settings.data_api_url)
    if not data_api_available:
        _group_health.add_degraded_feature(
            "suggestion-generation (data-api unreachable at startup)",
        )

    # Setup observability if available
    if OBSERVABILITY_AVAILABLE:
        try:
            setup_tracing("ai-automation-service")
            logger.info("Observability initialized")
        except Exception:
            logger.warning("Observability setup failed", exc_info=True)

    # Start rate limit cleanup task
    try:
        await start_rate_limit_cleanup()
        logger.info("Rate limiting initialized")
    except Exception:
        logger.warning("Rate limit cleanup setup failed", exc_info=True)

    # Start scheduler for automatic suggestion generation (if enabled)
    if settings.scheduler_enabled and APSCHEDULER_AVAILABLE:
        _start_scheduler()
    elif not settings.scheduler_enabled:
        logger.info("Scheduler is disabled in settings")


async def _shutdown() -> None:
    """Cleanup all resources on shutdown."""
    _stop_scheduler()

    try:
        await stop_rate_limit_cleanup()
    except Exception:
        logger.warning("Rate limit cleanup shutdown failed", exc_info=True)

    try:
        await close_clients()
    except Exception:
        logger.warning("Client cleanup failed", exc_info=True)


# ---------------------------------------------------------------------------
# Lifespan (ServiceLifespan)
# ---------------------------------------------------------------------------

lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup, name="services")
lifespan.on_shutdown(_shutdown, name="services")


# ---------------------------------------------------------------------------
# App (create_app factory -- provides CORS, request-id, timing, exception handler)
# ---------------------------------------------------------------------------

app = create_app(
    title="AI Automation Service",
    version="1.0.0",
    description="Automation service for suggestion generation, YAML generation, and deployment to Home Assistant",
    lifespan=lifespan.handler,
    # No StandardHealthCheck -- this service has a custom health_router with metrics
    cors_origins=settings.get_cors_origins_list(),
    cors_allow_credentials=True,
)

# Register error handlers
if register_error_handlers:
    register_error_handlers(app)

# Instrument FastAPI for observability
if OBSERVABILITY_AVAILABLE:
    try:
        instrument_fastapi(app, "ai-automation-service")
        app.add_middleware(CorrelationMiddleware)
    except Exception:
        logger.warning("Failed to instrument FastAPI", exc_info=True)

# Authentication middleware (MANDATORY - cannot be disabled)
app.add_middleware(AuthenticationMiddleware)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Include routers
app.include_router(health_router, tags=["health"])
app.include_router(suggestion_router, tags=["suggestions"])
app.include_router(deployment_router, tags=["deployment"])
app.include_router(pattern_router.router, tags=["patterns"])
app.include_router(synergy_router.router, tags=["synergies"])
app.include_router(analysis_router.router, tags=["analysis"])
app.include_router(preference_router.router, tags=["preferences"])
# Hybrid Flow routers: Intent -> Plan -> Validate -> Compile -> Lifecycle
app.include_router(automation_plan_router.router, tags=["automation"])
app.include_router(automation_validate_router.router, tags=["automation"])
app.include_router(automation_yaml_validate_router.router, tags=["automation"])
app.include_router(automation_compile_router.router, tags=["automation"])
app.include_router(automation_lifecycle_router.router, tags=["automation"])

# Phase 2-4 validation routers (Reusable Pattern Framework)
app.include_router(blueprint_validate_router.router)
app.include_router(setup_validate_router.router)
app.include_router(scene_validate_router.router)
app.include_router(script_validate_router.router)


if __name__ == "__main__":
    import uvicorn

    # Default 127.0.0.1 for security (local-only). Set HOST=0.0.0.0 in Docker/container.
    host = os.getenv("HOST", "127.0.0.1")
    uvicorn.run(
        "main:app",
        host=host,
        port=settings.service_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
