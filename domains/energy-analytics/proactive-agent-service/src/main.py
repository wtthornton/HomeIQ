"""
Proactive Agent Service - Context-aware automation suggestions
Epic AI-21: Proactive Conversational Agent Service

Responsibilities:
- Context analysis (weather, sports, energy, historical patterns)
- Smart prompt generation
- Agent-to-agent communication with HA AI Agent Service
- Scheduled proactive suggestion generation

Story 33.4: Memory-aware proactive suggestions using Memory Brain integration.
"""

from __future__ import annotations

import logging

try:
    from homeiq_observability.logging_config import setup_logging
except ImportError:
    logging.basicConfig(level=logging.INFO)
    setup_logging = lambda name, **_kw: logging.getLogger(name)  # noqa: E731

from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

try:
    from homeiq_resilience import GroupHealthCheck, wait_for_dependency
except ImportError:
    GroupHealthCheck = None  # type: ignore[assignment,misc]
    wait_for_dependency = None  # type: ignore[assignment]

try:
    from homeiq_memory import MemoryClient, MemorySearch

    _MEMORY_AVAILABLE = True
except ImportError:
    MemoryClient = None  # type: ignore[assignment,misc]
    MemorySearch = None  # type: ignore[assignment,misc]
    _MEMORY_AVAILABLE = False

from .api.health import router as health_router
from .api.health import set_scheduler_service_for_health
from .api.suggestions import router as suggestions_router
from .api.suggestions import set_scheduler_service
from .api.task_router import router as task_router
from .api.task_router import set_cron_scheduler
from .config import Settings
from .database import close_database, init_database
from .services.scheduler_service import SchedulerService
from .services.suggestion_pipeline_service import SuggestionPipelineService
from .services.task_executor import TaskExecutor
from .services.task_scheduler import CronTaskScheduler

# Configure structured logging
logger = setup_logging("proactive-agent-service", group_name="automation-intelligence")

# Global settings instance
settings = Settings()

# Global scheduler instance (existing suggestions scheduler)
scheduler_service: SchedulerService | None = None

# Global cron task scheduler (Epic 27)
cron_task_scheduler: CronTaskScheduler | None = None

# Global memory instances (Story 33.4)
memory_client: MemoryClient | None = None
memory_search: MemorySearch | None = None

# Global group health check
_group_health: GroupHealthCheck | None = None


# ---------------------------------------------------------------------------
# Startup / Shutdown helpers
# ---------------------------------------------------------------------------

async def _startup_dependencies() -> None:
    """Probe cross-group dependencies (non-fatal)."""
    if wait_for_dependency is not None:
        await wait_for_dependency(url="http://data-api:8006", name="data-api", max_retries=10)
        await wait_for_dependency(url="http://weather-api:8009", name="weather-api", max_retries=10)

    global _group_health
    if GroupHealthCheck is not None:
        _group_health = GroupHealthCheck(
            group_name="automation-intelligence", version="1.0.0",
        )
        _group_health.register_dependency("data-api", "http://data-api:8006")
        _group_health.register_dependency("weather-api", "http://weather-api:8009")


async def _startup_db() -> None:
    """Initialize database connection."""
    success = await init_database(settings)
    if success:
        logger.info("Database initialized")
    else:
        logger.warning("Database unavailable -- starting in degraded mode")


async def _startup_memory() -> None:
    """Initialize Memory Brain client and search (Story 33.4)."""
    global memory_client, memory_search

    if not settings.memory_enabled:
        logger.info("Memory integration disabled in settings")
        return

    if not _MEMORY_AVAILABLE:
        logger.info("homeiq-memory not installed, memory features disabled")
        return

    try:
        memory_client = MemoryClient(
            db_url=settings.memory_database_url or settings.postgres_dsn,
        )
        initialized = await memory_client.initialize()
        if initialized and memory_client._session_maker:
            memory_search = MemorySearch(
                session_factory=memory_client._session_maker,
                embedding_generator=memory_client.embedding_generator,
            )
            logger.info("Memory Brain initialized for proactive suggestions")
        else:
            logger.warning("Memory Brain initialization failed, suggestions degraded")
            memory_client = None
            memory_search = None
    except Exception as e:
        logger.warning(f"Failed to initialize Memory Brain: {e}")
        memory_client = None
        memory_search = None


async def _shutdown_memory() -> None:
    """Close Memory Brain resources."""
    global memory_client, memory_search

    if memory_client:
        try:
            await memory_client.close()
        except Exception as e:
            logger.warning(f"Error closing Memory Brain: {e}")
        memory_client = None
    memory_search = None


async def _startup_scheduler() -> None:
    """Initialize and start the scheduler service."""
    global scheduler_service  # noqa: PLW0603
    # Pass memory_search for memory-aware suggestions (Story 33.4)
    pipeline_service = SuggestionPipelineService(memory_search=memory_search)
    scheduler_service = SchedulerService(settings, pipeline_service=pipeline_service)
    scheduler_service.start()
    set_scheduler_service(scheduler_service)
    set_scheduler_service_for_health(scheduler_service)
    memory_status = "enabled" if memory_search else "disabled"
    logger.info(f"Scheduler initialized (memory={memory_status})")


async def _shutdown_scheduler() -> None:
    """Stop scheduler on shutdown."""
    global scheduler_service
    if scheduler_service:
        scheduler_service.stop()
        scheduler_service = None


async def _startup_cron_scheduler() -> None:
    """Initialize and start the cron task scheduler (Epic 27)."""
    global cron_task_scheduler  # noqa: PLW0603
    if not settings.cron_scheduler_enabled:
        logger.info("Cron task scheduler disabled in settings")
        return
    executor = TaskExecutor(settings)
    cron_task_scheduler = CronTaskScheduler(settings, executor)
    set_cron_scheduler(cron_task_scheduler)
    await cron_task_scheduler.start()
    logger.info("Cron task scheduler started")


async def _shutdown_cron_scheduler() -> None:
    """Stop the cron task scheduler."""
    global cron_task_scheduler  # noqa: PLW0603
    if cron_task_scheduler:
        await cron_task_scheduler.stop()
        cron_task_scheduler = None


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup_dependencies, name="dependencies")
lifespan.on_startup(_startup_db, name="database")
lifespan.on_startup(_startup_memory, name="memory")  # Story 33.4
lifespan.on_startup(_startup_scheduler, name="scheduler")
lifespan.on_startup(_startup_cron_scheduler, name="cron_scheduler")
lifespan.on_shutdown(_shutdown_cron_scheduler, name="cron_scheduler")
lifespan.on_shutdown(_shutdown_scheduler, name="scheduler")
lifespan.on_shutdown(_shutdown_memory, name="memory")  # Story 33.4
lifespan.on_shutdown(close_database, name="database")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

health = StandardHealthCheck(
    service_name=settings.service_name,
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_app(
    title="Proactive Agent Service",
    version="1.0.0",
    description="Context-aware proactive automation suggestions",
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=settings.get_cors_origins_list(),
)

# Register routers
app.include_router(health_router)
app.include_router(suggestions_router)
app.include_router(task_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        reload=True,
    )
