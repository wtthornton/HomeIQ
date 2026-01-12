#!/usr/bin/env python3
"""
Cleanup Stale Synergies

2025 Enhancement: Clean up stale synergies (inactive devices, low quality, old).

Removes synergies that:
- All devices inactive for >90 days
- Quality score below threshold
- Created >1 year ago with no activity
- Filtered synergies (filter_reason set)
"""

import asyncio
import json
import logging
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.quality_evaluation.database_accessor import DatabaseAccessor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Default thresholds
DEFAULT_INACTIVE_DAYS = 90
DEFAULT_MIN_QUALITY_SCORE = 0.30
DEFAULT_MAX_AGE_DAYS = 365


async def cleanup_stale_synergies(
    db_path: str,
    inactive_days: int = DEFAULT_INACTIVE_DAYS,
    min_quality_score: float = DEFAULT_MIN_QUALITY_SCORE,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    dry_run: bool = True,
    use_docker_db: bool = False
) -> Dict[str, Any]:
    """
    Clean up stale synergies (inactive devices, low quality, old).
    
    Args:
        db_path: Path to SQLite database (if use_docker_db=False)
        inactive_days: Devices inactive for this many days are considered stale
        min_quality_score: Remove synergies below this quality score
        max_age_days: Remove synergies older than this (with no activity)
        dry_run: If True, only report what would be removed
        use_docker_db: If True, use Docker database path
    
    Returns:
        {
            'total_synergies': int,
            'removed_count': int,
            'removed_reasons': dict,
            'remaining_count': int,
            'dry_run': bool
        }
    """
    # Initialize database accessor
    db_accessor = DatabaseAccessor(use_docker_db=use_docker_db)
    if use_docker_db:
        db_path = db_accessor.db_path
    
    logger.info(f"Starting stale synergy cleanup (dry_run={dry_run})")
    logger.info(f"Thresholds: inactive_days={inactive_days}, min_quality={min_quality_score}, max_age={max_age_days}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Fetch all synergies
        cursor.execute("""
            SELECT 
                synergy_id,
                synergy_type,
                device_ids,
                impact_score,
                confidence,
                quality_score,
                quality_tier,
                filter_reason,
                created_at,
                pattern_support_score,
                validated_by_patterns
            FROM synergy_opportunities
        """)
        
        all_synergies = cursor.fetchall()
        total_synergies = len(all_synergies)
        logger.info(f"Found {total_synergies} total synergies")
        
        # Get active devices (if DataAPI available)
        active_devices: Optional[Set[str]] = None
        try:
            import httpx
            # Import path uses underscore, not hyphen
            import sys
            sys.path.insert(0, str(project_root / "services" / "ai-pattern-service" / "src"))
            from clients.data_api_client import DataAPIClient
            from services.device_activity import DeviceActivityService
            
            async with DataAPIClient(base_url="http://data-api:8006") as data_client:
                activity_service = DeviceActivityService(data_api_client=data_client)
                active_devices_set = await activity_service.get_active_devices(
                    window_days=inactive_days,
                    data_api_client=data_client
                )
                if active_devices_set:
                    active_devices = active_devices_set
                    logger.info(f"Found {len(active_devices)} active devices")
        except Exception as e:
            logger.warning(f"Could not fetch active devices: {e}. Will skip device activity check.")
        
        # Calculate cutoff dates
        now = datetime.now(timezone.utc)
        inactive_cutoff = now - timedelta(days=inactive_days)
        max_age_cutoff = now - timedelta(days=max_age_days)
        
        # Analyze synergies
        removed_count = 0
        removed_reasons: Dict[str, int] = {
            'filtered': 0,
            'low_quality': 0,
            'inactive_devices': 0,
            'too_old': 0,
            'missing_quality_score': 0
        }
        to_remove: List[str] = []  # synergy_ids to remove
        
        for row in all_synergies:
            synergy_id = row['synergy_id']
            should_remove = False
            remove_reason = None
            
            # Check if already filtered
            filter_reason = row['filter_reason']
            if filter_reason:
                should_remove = True
                remove_reason = 'filtered'
                removed_reasons['filtered'] += 1
            
            # Check quality score
            if not should_remove:
                quality_score = row['quality_score']
                if quality_score is None:
                    # Missing quality score - calculate or mark for review
                    # For cleanup, we'll skip these (they need quality scores calculated first)
                    continue
                elif quality_score < min_quality_score:
                    should_remove = True
                    remove_reason = 'low_quality'
                    removed_reasons['low_quality'] += 1
            
            # Check device activity
            if not should_remove and active_devices is not None:
                device_ids_str = row['device_ids']
                if device_ids_str:
                    try:
                        device_ids = json.loads(device_ids_str) if isinstance(device_ids_str, str) else device_ids_str
                        if isinstance(device_ids, list) and device_ids:
                            # Check if all devices are inactive
                            all_inactive = all(d not in active_devices for d in device_ids)
                            if all_inactive:
                                should_remove = True
                                remove_reason = 'inactive_devices'
                                removed_reasons['inactive_devices'] += 1
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to parse device_ids for {synergy_id}: {e}")
            
            # Check age (only for low-quality synergies)
            if not should_remove:
                created_at_str = row['created_at']
                if created_at_str:
                    try:
                        if isinstance(created_at_str, str):
                            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        else:
                            created_at = created_at_str
                        
                        if created_at < max_age_cutoff:
                            quality_score = row['quality_score'] or 0.0
                            # Only remove old synergies if they're low quality
                            if quality_score < 0.50:  # Medium quality threshold
                                should_remove = True
                                remove_reason = 'too_old'
                                removed_reasons['too_old'] += 1
                    except Exception as e:
                        logger.warning(f"Failed to parse created_at for {synergy_id}: {e}")
            
            if should_remove:
                to_remove.append(synergy_id)
                logger.debug(f"Marked for removal: {synergy_id} ({remove_reason})")
        
        # Remove synergies (or just report if dry_run)
        if dry_run:
            logger.info(f"DRY RUN: Would remove {len(to_remove)} synergies")
            for reason, count in removed_reasons.items():
                if count > 0:
                    logger.info(f"  {reason}: {count}")
        else:
            if to_remove:
                # Delete in batches
                batch_size = 100
                for i in range(0, len(to_remove), batch_size):
                    batch = to_remove[i:i + batch_size]
                    placeholders = ','.join('?' * len(batch))
                    cursor.execute(
                        f"DELETE FROM synergy_opportunities WHERE synergy_id IN ({placeholders})",
                        batch
                    )
                    removed_count += cursor.rowcount
                
                conn.commit()
                logger.info(f"Removed {removed_count} stale synergies from database")
                for reason, count in removed_reasons.items():
                    if count > 0:
                        logger.info(f"  {reason}: {count}")
            else:
                logger.info("No synergies to remove")
        
        remaining_count = total_synergies - len(to_remove)
        
        return {
            'total_synergies': total_synergies,
            'removed_count': len(to_remove) if dry_run else removed_count,
            'removed_reasons': removed_reasons,
            'remaining_count': remaining_count,
            'dry_run': dry_run
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup stale synergies: {e}", exc_info=True)
        conn.rollback()
        raise
    finally:
        conn.close()


async def main():
    """Main entry point for script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Cleanup stale synergies')
    parser.add_argument('--db-path', type=str, help='Path to SQLite database')
    parser.add_argument('--use-docker-db', action='store_true', help='Use Docker database path')
    parser.add_argument('--inactive-days', type=int, default=DEFAULT_INACTIVE_DAYS, help='Devices inactive for this many days')
    parser.add_argument('--min-quality-score', type=float, default=DEFAULT_MIN_QUALITY_SCORE, help='Minimum quality score threshold')
    parser.add_argument('--max-age-days', type=int, default=DEFAULT_MAX_AGE_DAYS, help='Maximum age in days')
    parser.add_argument('--dry-run', action='store_true', default=True, help='Dry run (default: True)')
    parser.add_argument('--execute', action='store_true', help='Actually remove synergies (overrides --dry-run)')
    
    args = parser.parse_args()
    
    dry_run = not args.execute if args.execute else args.dry_run
    
    result = await cleanup_stale_synergies(
        db_path=args.db_path or '',
        inactive_days=args.inactive_days,
        min_quality_score=args.min_quality_score,
        max_age_days=args.max_age_days,
        dry_run=dry_run,
        use_docker_db=args.use_docker_db
    )
    
    print(f"\n{'='*60}")
    print(f"Cleanup Results ({'DRY RUN' if dry_run else 'EXECUTED'})")
    print(f"{'='*60}")
    print(f"Total synergies: {result['total_synergies']}")
    print(f"Removed: {result['removed_count']}")
    print(f"Remaining: {result['remaining_count']}")
    print(f"\nRemoval reasons:")
    for reason, count in result['removed_reasons'].items():
        if count > 0:
            print(f"  {reason}: {count}")
    print(f"{'='*60}\n")
    
    if dry_run:
        print("This was a dry run. Use --execute to actually remove synergies.")


if __name__ == '__main__':
    asyncio.run(main())
