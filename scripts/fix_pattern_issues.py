#!/usr/bin/env python3
"""
Fix Pattern Issues

Removes invalid patterns and fixes issues identified by validation.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

import psycopg2
import psycopg2.extras

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

# PostgreSQL connection URL
POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://homeiq:homeiq@localhost:5432/homeiq")

# External data source patterns (should be removed)
EXTERNAL_DATA_PATTERNS = {
    'sensor.team_tracker_',
    'sensor.nfl_',
    'sensor.nhl_',
    'sensor.mlb_',
    'sensor.nba_',
    'sensor.ncaa_',
    '_tracker',
    'weather.',
    'sensor.weather_',
    'sensor.openweathermap_',
    'sensor.carbon_intensity_',
    'sensor.electricity_pricing_',
    'sensor.national_grid_',
    'calendar.',
    'sensor.calendar_',
}


async def fix_pattern_issues(
    pg_url: str,
    validation_results_path: str,
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Fix pattern issues based on validation results.

    Args:
        pg_url: PostgreSQL connection URL
        validation_results_path: Path to validation results JSON
        dry_run: If True, only report what would be fixed

    Returns:
        Dictionary with fix results
    """
    logger.info("=" * 80)
    logger.info("Pattern Issues Fix")
    logger.info("=" * 80)

    # Load validation results
    with open(validation_results_path, 'r') as f:
        validation_results = json.load(f)

    conn = psycopg2.connect(pg_url)
    conn.autocommit = False
    cursor = conn.cursor()

    try:
        fix_results = {
            'external_patterns_removed': 0,
            'invalid_patterns_removed': 0,
            'stale_patterns_removed': 0,
            'total_removed': 0,
            'dry_run': dry_run
        }

        # 1. Remove external data patterns
        logger.info("\n1. Removing external data patterns...")
        external_patterns = validation_results.get('external_data_patterns', [])
        for pattern in external_patterns:
            pattern_id = pattern.get('pattern_id')
            device_id = pattern.get('device_id')

            if pattern_id:
                if not dry_run:
                    cursor.execute("DELETE FROM patterns.patterns WHERE id = %s", (pattern_id,))
                fix_results['external_patterns_removed'] += 1
                logger.info(f"   {'[DRY RUN] Would remove' if dry_run else 'Removed'} pattern {pattern_id} ({device_id})")

        # 2. Remove invalid patterns (don't match events)
        logger.info("\n2. Removing invalid patterns...")
        invalid_patterns = validation_results.get('invalid_patterns', [])
        for pattern in invalid_patterns:
            pattern_id = pattern.get('pattern_id')
            device_id = pattern.get('device_id')

            if pattern_id:
                if not dry_run:
                    cursor.execute("DELETE FROM patterns.patterns WHERE id = %s", (pattern_id,))
                fix_results['invalid_patterns_removed'] += 1
                logger.info(f"   {'[DRY RUN] Would remove' if dry_run else 'Removed'} invalid pattern {pattern_id} ({device_id})")

        # 3. Remove stale patterns (no events in time window)
        logger.info("\n3. Removing stale patterns...")
        stale_patterns = validation_results.get('patterns_without_events', [])
        for pattern in stale_patterns:
            pattern_id = pattern.get('pattern_id')
            device_id = pattern.get('device_id')

            if pattern_id:
                if not dry_run:
                    cursor.execute("DELETE FROM patterns.patterns WHERE id = %s", (pattern_id,))
                fix_results['stale_patterns_removed'] += 1
                logger.info(f"   {'[DRY RUN] Would remove' if dry_run else 'Removed'} stale pattern {pattern_id} ({device_id})")

        fix_results['total_removed'] = (
            fix_results['external_patterns_removed'] +
            fix_results['invalid_patterns_removed'] +
            fix_results['stale_patterns_removed']
        )

        if not dry_run:
            conn.commit()
            logger.info(f"\n[OK] Committed changes to database")
        else:
            conn.rollback()
            logger.info(f"\n[DRY RUN] No changes committed")

        logger.info("\n" + "=" * 80)
        logger.info("Fix Summary")
        logger.info("=" * 80)
        logger.info(f"External patterns: {fix_results['external_patterns_removed']}")
        logger.info(f"Invalid patterns: {fix_results['invalid_patterns_removed']}")
        logger.info(f"Stale patterns: {fix_results['stale_patterns_removed']}")
        logger.info(f"Total to remove: {fix_results['total_removed']}")
        logger.info("=" * 80)

        return fix_results

    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()


async def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Fix pattern issues identified by validation'
    )
    parser.add_argument(
        '--pg-url',
        type=str,
        default=POSTGRES_URL,
        help='PostgreSQL connection URL'
    )
    parser.add_argument(
        '--validation-results',
        type=str,
        default='reports/quality/pattern_validation.json',
        help='Path to validation results JSON'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Dry run mode (default: True, use --no-dry-run to apply changes)'
    )
    parser.add_argument(
        '--no-dry-run',
        action='store_false',
        dest='dry_run',
        help='Apply changes (disable dry run)'
    )

    args = parser.parse_args()

    try:
        results = await fix_pattern_issues(
            args.pg_url,
            args.validation_results,
            dry_run=args.dry_run
        )
    except Exception as e:
        logger.error(f"Fix failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
