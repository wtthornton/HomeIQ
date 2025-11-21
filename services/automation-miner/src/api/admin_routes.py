"""
Admin Routes for Automation Miner

Manual job triggers and management endpoints.

Epic AI-4, Story AI4.4
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.jobs.weekly_refresh import WeeklyRefreshJob
from src.miner.database import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/refresh/trigger")
async def trigger_manual_refresh(background_tasks: BackgroundTasks):
    """
    Manually trigger corpus refresh

    Runs the weekly refresh job immediately in the background.
    Useful for testing or recovering from failed scheduled runs.
    """
    logger.info("Manual corpus refresh triggered via API")

    job = WeeklyRefreshJob()
    background_tasks.add_task(job.run)

    return {
        "status": "triggered",
        "message": "Weekly refresh job started in background",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/refresh/status")
async def get_refresh_status(db: AsyncSession = Depends(get_db_session)):
    """
    Get weekly refresh job status

    Returns information about the last refresh and next scheduled run.
    """
    from src.miner.repository import CorpusRepository

    try:
        repo = CorpusRepository(db)
        last_crawl = await repo.get_last_crawl_timestamp()
        stats = await repo.get_stats()

        # Calculate next refresh time (Sunday 2 AM)
        now = datetime.now(timezone.utc)
        if last_crawl:
            # Ensure timezone-aware comparison
            if last_crawl.tzinfo is None:
                last_crawl = last_crawl.replace(tzinfo=timezone.utc)
            days_since = (now - last_crawl).days
        else:
            days_since = None

        # Calculate next Sunday 2 AM
        days_until_sunday = (6 - now.weekday()) % 7  # Days until next Sunday
        if days_until_sunday == 0 and now.hour >= 2:
            # If it's Sunday and past 2 AM, next refresh is next Sunday
            days_until_sunday = 7

        next_sunday = now.replace(hour=2, minute=0, second=0, microsecond=0)
        if days_until_sunday > 0:
            from datetime import timedelta
            next_sunday = next_sunday + timedelta(days=days_until_sunday)
        elif now.hour >= 2:
            from datetime import timedelta
            next_sunday = next_sunday + timedelta(days=7)

        next_refresh = next_sunday.isoformat()

        return {
            "last_refresh": last_crawl.isoformat() if last_crawl else None,
            "days_since_refresh": days_since,
            "next_refresh": next_refresh,
            "corpus_total": stats["total"],
            "corpus_quality": stats["avg_quality"],
            "status": "healthy" if (not last_crawl or days_since <= 7) else "stale",
        }

    except Exception as e:
        logger.exception(f"Failed to get refresh status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

