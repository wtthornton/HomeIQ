"""
FastAPI Application for Automation Miner

Provides REST API for querying the automation corpus.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import settings
from ..miner.database import get_database
from .routes import router
from .admin_routes import router as admin_router  # Story AI4.4
from .device_routes import router as device_router  # Story AI4.3

# Configure logging
logging.basicConfig(
    level=logging.getLevelName(settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown
    
    Creates database tables and starts weekly refresh scheduler.
    """
    logger.info("Starting Automation Miner API...")
    
    # Initialize database
    db = get_database()
    await db.create_tables()
    logger.info("Database initialized")
    
    # Initialize corpus on startup (Story AI4.4 enhancement)
    if settings.enable_automation_miner:
        try:
            from ..jobs.weekly_refresh import WeeklyRefreshJob
            from ..miner.repository import CorpusRepository
            
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
                    logger.info("🔍 Corpus is empty - will run initial population on startup")
                elif last_crawl:
                    from datetime import datetime, timedelta
                    days_since = (datetime.utcnow() - last_crawl).days
                    if days_since > 7:
                        should_initialize = True
                        reason = f"stale corpus ({days_since} days old)"
                        logger.info(f"🔍 Corpus is stale ({days_since} days) - will refresh on startup")
                else:
                    should_initialize = True
                    reason = "no last_crawl timestamp"
                    logger.info("🔍 No last crawl timestamp - will initialize on startup")
                
                # Run initialization if needed
                if should_initialize:
                    logger.info(f"🚀 Starting corpus initialization ({reason})...")
                    logger.info("   This will run in background during API startup")
                    
                    # Run refresh job (will populate or update corpus)
                    job = WeeklyRefreshJob()
                    
                    # Import asyncio to run in background
                    import asyncio
                    asyncio.create_task(job.run())
                    
                    logger.info("✅ Corpus initialization started in background")
                else:
                    logger.info(f"✅ Corpus is fresh ({stats['total']} automations, last crawl: {last_crawl})")
        
        except Exception as e:
            logger.warning(f"⚠️ Startup initialization check failed: {e}")
    
    # Start weekly refresh scheduler (Story AI4.4)
    scheduler = None
    if settings.enable_automation_miner:
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from ..jobs.weekly_refresh import setup_weekly_refresh_job
            
            scheduler = AsyncIOScheduler()
            await setup_weekly_refresh_job(scheduler)
            scheduler.start()
            logger.info("✅ Weekly refresh scheduler started (every Sunday 2 AM)")
        except Exception as e:
            logger.warning(f"⚠️ Failed to start weekly refresh scheduler: {e}")
            scheduler = None
    else:
        logger.info("ℹ️  Weekly refresh scheduler disabled (ENABLE_AUTOMATION_MINER=false)")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Automation Miner API...")
    
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("✅ Weekly refresh scheduler stopped")
    
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
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/automation-miner")
app.include_router(admin_router, prefix="/api/automation-miner")  # Story AI4.4: Admin endpoints
app.include_router(device_router, prefix="/api/automation-miner")  # Story AI4.3: Device discovery


@app.get("/health")
async def health_check():
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
            
            return {
                "status": "healthy",
                "service": "automation-miner",
                "version": "0.1.0",
                "corpus": {
                    "total_automations": stats['total'],
                    "avg_quality": stats['avg_quality'],
                    "last_crawl": last_crawl.isoformat() if last_crawl else None
                },
                "enabled": settings.enable_automation_miner
            }
        
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "service": "automation-miner",
                "error": str(e)
            }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Automation Miner API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8019)

