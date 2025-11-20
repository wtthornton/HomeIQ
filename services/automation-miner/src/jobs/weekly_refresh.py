"""
Weekly Corpus Refresh Job

Runs every Sunday at 2 AM to keep corpus fresh with new community automations.

Epic AI-4, Story AI4.4
"""
import logging
from datetime import datetime, timezone
from uuid import uuid4

from ..config import settings
from ..miner.database import get_database
from ..miner.discourse_client import DiscourseClient
from ..miner.parser import AutomationParser
from ..miner.repository import CorpusRepository

logger = logging.getLogger(__name__)


class WeeklyRefreshJob:
    """Weekly corpus refresh job"""

    def __init__(self):
        """Initialize weekly refresh job"""
        self.client = None
        self.parser = AutomationParser()

    async def run(self):
        """
        Weekly corpus refresh
        
        Runs every Sunday at 2 AM:
        1. Fetch new/updated posts since last crawl
        2. Update existing automations (vote counts may have changed)
        3. Prune low-quality entries
        4. Invalidate caches
        """
        correlation_id = str(uuid4())
        logger.info(f"[{correlation_id}] ═══════════════════════════════════════")
        logger.info(f"[{correlation_id}] 🔄 Weekly Corpus Refresh Started")
        logger.info(f"[{correlation_id}] ═══════════════════════════════════════")
        logger.info(f"[{correlation_id}] Timestamp: {datetime.now(timezone.utc).isoformat()}")

        db = get_database()

        try:
            async with DiscourseClient() as client:
                async with db.get_session() as db_session:
                    repo = CorpusRepository(db_session)

                    # Step 1: Get last crawl timestamp (ensure timezone-aware)
                    last_crawl = await repo.get_last_crawl_timestamp()
                    if last_crawl and last_crawl.tzinfo is None:
                        # Make timezone-aware if naive
                        last_crawl = last_crawl.replace(tzinfo=timezone.utc)
                    logger.info(f"[{correlation_id}] Last crawl: {last_crawl}")

                    # Step 2: Fetch new/updated posts
                    logger.info(f"[{correlation_id}] Step 1: Fetching new/updated posts...")

                    new_posts = await client.fetch_blueprints(
                        min_likes=100,  # Lower threshold for recent posts
                        since=last_crawl,
                        limit=500
                    )

                    logger.info(f"[{correlation_id}] Found {len(new_posts)} new/updated posts")

                    # Step 3: Process new posts
                    logger.info(f"[{correlation_id}] Step 2: Processing new posts...")

                    added_count = 0
                    updated_count = 0
                    skipped_count = 0

                    for post in new_posts:
                        try:
                            # Fetch full post details
                            details = await client.fetch_post_details(
                                post['id'],
                                correlation_id=correlation_id
                            )

                            if not details:
                                continue

                            # Parse automation
                            parsed = self.parser.parse_automation(details)
                            if not parsed:
                                continue

                            # Create metadata
                            metadata = self.parser.create_metadata(details, parsed)

                            # Check if exists
                            existing = await repo.get_by_source_id(
                                source='discourse',
                                source_id=metadata.source_id
                            )

                            if existing:
                                # Update if votes changed
                                if existing.vote_count != metadata.vote_count:
                                    await repo.save_automation(metadata)
                                    updated_count += 1
                                else:
                                    skipped_count += 1
                            else:
                                # Add new
                                if not await repo.is_duplicate(metadata):
                                    await repo.save_automation(metadata)
                                    added_count += 1
                                else:
                                    skipped_count += 1

                        except Exception as e:
                            logger.error(f"[{correlation_id}] Failed to process post {post['id']}: {e}")
                            continue

                    logger.info(f"[{correlation_id}]   Added: {added_count} new automations")
                    logger.info(f"[{correlation_id}]   Updated: {updated_count} vote counts")
                    logger.info(f"[{correlation_id}]   Skipped: {skipped_count} unchanged")

                    # Step 4: Prune low-quality entries
                    logger.info(f"[{correlation_id}] Step 3: Pruning low-quality entries...")

                    pruned_count = await repo.prune_low_quality(
                        quality_threshold=settings.pruning_quality_threshold,
                        age_days=settings.pruning_age_days
                    )

                    logger.info(f"[{correlation_id}]   Pruned: {pruned_count} low-quality automations")

                    # Step 5: Update last crawl timestamp (use timezone-aware)
                    await repo.set_last_crawl_timestamp(datetime.now(timezone.utc))

                    # Step 6: Get final stats
                    stats = await repo.get_stats()

                    logger.info(f"[{correlation_id}] ═══════════════════════════════════════")
                    logger.info(f"[{correlation_id}] ✅ Weekly Refresh Complete!")
                    logger.info(f"[{correlation_id}] ═══════════════════════════════════════")
                    logger.info(f"[{correlation_id}]   Added: {added_count} new automations")
                    logger.info(f"[{correlation_id}]   Updated: {updated_count} quality scores")
                    logger.info(f"[{correlation_id}]   Pruned: {pruned_count} stale entries")
                    logger.info(f"[{correlation_id}]   Total corpus: {stats['total']} automations")
                    logger.info(f"[{correlation_id}]   Avg quality: {stats['avg_quality']:.3f}")
                    logger.info(f"[{correlation_id}]   Last crawl: {datetime.now(timezone.utc).isoformat()}")

        except Exception as e:
            logger.error(f"[{correlation_id}] ❌ Weekly refresh failed: {e}", exc_info=True)
            raise

        finally:
            await db.close()


async def setup_weekly_refresh_job(scheduler):
    """
    Setup weekly refresh job with APScheduler
    
    Args:
        scheduler: APScheduler AsyncIOScheduler instance
    
    Usage:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        
        scheduler = AsyncIOScheduler()
        await setup_weekly_refresh_job(scheduler)
        scheduler.start()
    """
    from apscheduler.triggers.cron import CronTrigger

    job = WeeklyRefreshJob()

    scheduler.add_job(
        job.run,
        CronTrigger(day_of_week='sun', hour=2, minute=0),  # Sunday 2 AM
        id='weekly_corpus_refresh',
        name='Weekly Corpus Refresh (Epic AI-4)',
        replace_existing=True,
        max_instances=1,  # Prevent overlap
        coalesce=True,  # Skip if previous run still active
        misfire_grace_time=3600  # Allow 1 hour delay if server was down
    )

    logger.info("✅ Weekly refresh job scheduled: Every Sunday at 2 AM")

