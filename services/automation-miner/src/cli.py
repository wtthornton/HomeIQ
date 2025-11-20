"""
CLI for Automation Miner

Provides manual crawl triggers and management commands.
"""
import asyncio
import logging
import sys
from datetime import datetime, timezone
from uuid import uuid4

import click

from .config import settings
from .miner.database import get_database
from .miner.discourse_client import DiscourseClient
from .miner.parser import AutomationParser
from .miner.repository import CorpusRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def run_initial_crawl(
    min_likes: int = None,
    limit: int = None,
    dry_run: bool = False
):
    """
    Run initial corpus crawl
    
    Args:
        min_likes: Minimum likes threshold
        limit: Maximum posts to fetch
        dry_run: If True, don't save to database
    """
    correlation_id = str(uuid4())
    logger.info(f"[{correlation_id}] Starting initial corpus crawl...")
    logger.info(f"  min_likes: {min_likes or settings.discourse_min_likes}")
    logger.info(f"  limit: {limit or settings.crawler_max_posts}")
    logger.info(f"  dry_run: {dry_run}")

    # Initialize components
    db = get_database()
    await db.create_tables()

    parser = AutomationParser()

    # Statistics
    stats = {
        'fetched': 0,
        'parsed': 0,
        'skipped': 0,
        'added': 0,
        'failed': 0
    }

    async with DiscourseClient() as client:
        async with db.get_session() as db_session:
            repo = CorpusRepository(db_session)

            # Fetch blueprints in batches
            page = 0
            total_fetched = 0
            batch_size = settings.crawler_batch_size

            while total_fetched < (limit or settings.crawler_max_posts):
                logger.info(f"[{correlation_id}] Fetching page {page}...")

                try:
                    # Fetch blueprint posts
                    topics = await client.fetch_blueprints(
                        min_likes=min_likes or settings.discourse_min_likes,
                        limit=batch_size,
                        page=page
                    )

                    if not topics:
                        logger.info(f"[{correlation_id}] No more topics found")
                        break

                    stats['fetched'] += len(topics)
                    total_fetched += len(topics)

                    # Process each topic
                    batch_to_add = []

                    for topic in topics:
                        try:
                            # Fetch full post details
                            post_data = await client.fetch_post_details(
                                topic['id'],
                                correlation_id=correlation_id
                            )

                            if not post_data:
                                logger.warning(f"No data for topic {topic['id']}")
                                stats['skipped'] += 1
                                continue

                            # Parse automation
                            parsed = parser.parse_automation(post_data)

                            if not parsed:
                                logger.warning(f"Failed to parse topic {topic['id']}")
                                stats['failed'] += 1
                                continue

                            # Create metadata
                            metadata = parser.create_metadata(post_data, parsed)
                            stats['parsed'] += 1

                            # Check for duplicates
                            if not dry_run:
                                is_dup = await repo.is_duplicate(metadata)
                                if is_dup:
                                    logger.debug(f"Skipping duplicate: {metadata.title}")
                                    stats['skipped'] += 1
                                    continue

                            batch_to_add.append(metadata)

                        except Exception as e:
                            logger.error(f"Error processing topic {topic['id']}: {e}")
                            stats['failed'] += 1
                            continue

                    # Save batch
                    if batch_to_add and not dry_run:
                        logger.info(f"[{correlation_id}] Saving batch of {len(batch_to_add)} automations...")
                        saved = await repo.save_batch(batch_to_add)
                        stats['added'] += saved
                    elif batch_to_add and dry_run:
                        logger.info(f"[{correlation_id}] DRY RUN: Would save {len(batch_to_add)} automations")
                        stats['added'] += len(batch_to_add)

                    # Log progress
                    logger.info(
                        f"[{correlation_id}] Progress: "
                        f"fetched={stats['fetched']}, "
                        f"parsed={stats['parsed']}, "
                        f"added={stats['added']}, "
                        f"skipped={stats['skipped']}, "
                        f"failed={stats['failed']}"
                    )

                    page += 1

                    # Check if we've reached limit
                    if limit and total_fetched >= limit:
                        break

                except Exception as e:
                    logger.error(f"Error fetching page {page}: {e}")
                    break

            # Update last crawl timestamp
            if not dry_run:
                await repo.set_last_crawl_timestamp(datetime.now(timezone.utc))

            # Final stats
            logger.info(f"[{correlation_id}] ✅ Initial crawl complete!")
            logger.info(f"  Fetched: {stats['fetched']} topics")
            logger.info(f"  Parsed: {stats['parsed']} automations")
            logger.info(f"  Added: {stats['added']} to corpus")
            logger.info(f"  Skipped: {stats['skipped']} (duplicates)")
            logger.info(f"  Failed: {stats['failed']}")

            if not dry_run:
                # Get final corpus stats
                corpus_stats = await repo.get_stats()
                logger.info(f"  Total corpus: {corpus_stats['total']} automations")
                logger.info(f"  Avg quality: {corpus_stats['avg_quality']:.3f}")

    await db.close()


@click.group()
def cli():
    """Automation Miner CLI"""
    pass


@cli.command()
@click.option('--min-likes', type=int, help='Minimum likes threshold')
@click.option('--limit', type=int, help='Maximum posts to fetch')
@click.option('--dry-run', is_flag=True, help='Show changes without saving')
def crawl(min_likes, limit, dry_run):
    """Trigger initial corpus crawl"""
    click.echo("🕷️  Starting Automation Miner crawl...")
    click.echo(f"   Min likes: {min_likes or settings.discourse_min_likes}")
    click.echo(f"   Limit: {limit or settings.crawler_max_posts}")
    click.echo(f"   Dry run: {dry_run}")
    click.echo()

    try:
        asyncio.run(run_initial_crawl(min_likes, limit, dry_run))
        click.echo()
        click.echo("✅ Crawl complete!")
    except KeyboardInterrupt:
        click.echo()
        click.echo("❌ Crawl cancelled by user")
        sys.exit(1)
    except Exception as e:
        click.echo()
        click.echo(f"❌ Crawl failed: {e}")
        sys.exit(1)


@cli.command()
def stats():
    """Show corpus statistics"""
    async def get_stats():
        db = get_database()
        async with db.get_session() as db_session:
            repo = CorpusRepository(db_session)
            return await repo.get_stats()

    stats_data = asyncio.run(get_stats())

    click.echo("📊 Automation Miner Corpus Statistics")
    click.echo()
    click.echo(f"Total automations: {stats_data['total']}")
    click.echo(f"Average quality: {stats_data['avg_quality']:.3f}")
    click.echo(f"Device types: {stats_data['device_count']}")
    click.echo(f"Integrations: {stats_data['integration_count']}")
    click.echo()
    click.echo("By use case:")
    for use_case, count in stats_data['by_use_case'].items():
        click.echo(f"  {use_case}: {count}")
    click.echo()
    click.echo("By complexity:")
    for complexity, count in stats_data['by_complexity'].items():
        click.echo(f"  {complexity}: {count}")
    click.echo()
    if stats_data['last_crawl_time']:
        click.echo(f"Last crawl: {stats_data['last_crawl_time']}")


if __name__ == '__main__':
    cli()

