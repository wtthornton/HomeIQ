"""
FastAPI Application for Automation Miner

This service provides a REST API for querying the automation corpus.
It crawls community knowledge sources (GitHub, Discourse) to build a corpus
of Home Assistant automations for recommendation and discovery.

Architecture:
- FastAPI application with async/await support
- SQLAlchemy database layer for corpus storage
- Weekly refresh scheduler (APScheduler) for corpus updates
- Background initialization on startup (if corpus is empty or stale)

Key Features:
- Corpus initialization on startup (if needed)
- Weekly automated corpus refresh
- REST API for querying automations
- Device-based discovery endpoints
- Admin endpoints for corpus management
"""
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware

from ..config import settings
from ..miner.database import get_database
from .admin_routes import router as admin_router  # Story AI4.4
from .device_routes import router as device_router  # Story AI4.3
from .routes import router

# Configure logging
logging.basicConfig(
    level=logging.getLevelName(settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def _check_and_initialize_corpus(app_instance: FastAPI, db) -> None:
    """Check corpus status and initialize if needed."""
    try:
        from ..jobs.weekly_refresh import WeeklyRefreshJob
        from ..miner.repository import CorpusRepository
        import asyncio
        from datetime import datetime, timezone

        async with db.get_session() as session:
            repo = CorpusRepository(session)
            stats = await repo.get_stats()
            last_crawl = await repo.get_last_crawl_timestamp()

            # Check if initialization needed
            should_initialize = False
            reason = ""

            if stats['total'] == 0:
                should_initialize = True
                reason = "empty corpus"
                logger.info("Corpus is empty - will run initial population on startup")
            elif last_crawl:
                # Ensure timezone-aware comparison
                if last_crawl.tzinfo is None:
                    last_crawl = last_crawl.replace(tzinfo=timezone.utc)
                days_since = (datetime.now(timezone.utc) - last_crawl).days
                if days_since > 7:
                    should_initialize = True
                    reason = f"stale corpus ({days_since} days old)"
                    logger.info(f"Corpus is stale ({days_since} days) - will refresh on startup")
            else:
                should_initialize = True
                reason = "no last_crawl timestamp"
                logger.info("No last crawl timestamp - will initialize on startup")

            # Run initialization if needed
            if should_initialize:
                app_instance.state.initialization_in_progress = True

                logger.info(f"Starting corpus initialization ({reason})...")
                logger.info("   This will run in background during API startup")

                # Run refresh job (will populate or update corpus)
                job = WeeklyRefreshJob()

                async def run_init_and_track():
                    try:
                        await job.run()
                        app_instance.state.initialization_complete = True
                    except Exception as e:
                        logger.error(f"Initialization failed: {e}", exc_info=True)
                    finally:
                        app_instance.state.initialization_in_progress = False

                asyncio.create_task(run_init_and_track())

                logger.info("Corpus initialization started in background")
            else:
                app_instance.state.initialization_complete = True
                logger.info(
                    f"Corpus is fresh ({stats['total']} automations, "
                    f"last crawl: {last_crawl})"
                )

    except Exception as e:
        logger.warning(f"Startup initialization check failed: {e}")


async def _start_scheduler() -> object | None:
    """Start weekly refresh scheduler if enabled."""
    if not settings.enable_automation_miner:
        logger.info("ℹ️  Weekly refresh scheduler disabled (ENABLE_AUTOMATION_MINER=false)")
        return None
    
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from ..jobs.weekly_refresh import setup_weekly_refresh_job

        scheduler = AsyncIOScheduler()
        await setup_weekly_refresh_job(scheduler)
        scheduler.start()
        logger.info("✅ Weekly refresh scheduler started (every Sunday 2 AM)")
        return scheduler
    except Exception as e:
        logger.warning(f"⚠️ Failed to start weekly refresh scheduler: {e}")
        return None


async def _initialize_database() -> Any:
    """Initialize database connection and create tables."""
    db = get_database()
    await db.create_tables()
    # Migrate existing databases: add is_blueprint column if missing
    async with db.engine.begin() as conn:
        try:
            await conn.execute(text(
                "ALTER TABLE community_automations ADD COLUMN is_blueprint BOOLEAN NOT NULL DEFAULT 0"
            ))
            logger.info("Migration: added is_blueprint column")
        except Exception:
            pass  # Column already exists
    logger.info("Database initialized")
    return db


async def _shutdown_scheduler(scheduler: Any | None) -> None:
    """Shutdown scheduler gracefully if running."""
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("✅ Weekly refresh scheduler stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown.
    
    This lifespan context manager handles:
    - Database initialization and table creation
    - Corpus initialization on startup (if empty or stale)
    - Weekly refresh scheduler startup
    - Graceful shutdown of scheduler and database connections
    
    Args:
        app: FastAPI application instance
        
    Yields:
        None: Control is yielded to the application runtime
        
    Raises:
        Exception: If database initialization fails (prevents service startup)
    """
    logger.info("Starting Automation Miner API...")

    # Initialize app state
    app.state.initialization_in_progress = False
    app.state.initialization_complete = False

    # Initialize database
    db = await _initialize_database()

    # Initialize corpus on startup (Story AI4.4 enhancement)
    if settings.enable_automation_miner:
        await _check_and_initialize_corpus(app, db)

    # Start weekly refresh scheduler (Story AI4.4)
    scheduler = await _start_scheduler()

    yield

    # Cleanup
    logger.info("Shutting down Automation Miner API...")
    await _shutdown_scheduler(scheduler)
    await db.close()


# Create FastAPI application
app = FastAPI(
    title="Automation Miner API",
    description="Community knowledge crawler for Home Assistant automations",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://ai-automation-ui",
        "http://ai-automation-ui:80",
        "http://homeiq-dashboard",
        "http://homeiq-dashboard:80"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/automation-miner")
app.include_router(admin_router, prefix="/api/automation-miner")  # Story AI4.4: Admin endpoints
app.include_router(device_router, prefix="/api/automation-miner")  # Story AI4.3: Device discovery


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint
    
    Returns service status and corpus information.
    """
    from ..miner.database import get_db_session
    from ..miner.repository import CorpusRepository

    async for db in get_db_session():
        try:
            repo = CorpusRepository(db)
            stats = await repo.get_stats()
            last_crawl = await repo.get_last_crawl_timestamp()

            # Check initialization status
            init_complete = getattr(app.state, 'initialization_complete', False)
            init_in_progress = getattr(app.state, 'initialization_in_progress', False)

            if init_complete:
                init_status = "complete"
            elif init_in_progress:
                init_status = "in_progress"
            else:
                init_status = "not_started"

            return {
                "status": "healthy",
                "service": "automation-miner",
                "version": "0.1.0",
                "initialization": {
                    "status": init_status,
                    "in_progress": init_in_progress
                },
                "corpus": {
                    "total_automations": stats['total'],
                    "avg_quality": stats['avg_quality'],
                    "last_crawl": last_crawl.isoformat() if last_crawl else None
                },
                "enabled": settings.enable_automation_miner
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "service": "automation-miner"
                }
            )


@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint providing service information.
    
    Returns:
        dict: Service metadata including message, version, and endpoint links
    """
    return {
        "message": "Automation Miner API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8019)

