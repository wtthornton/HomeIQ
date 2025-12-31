#!/usr/bin/env python3
"""
Fix Pattern Issues

Removes invalid patterns and fixes issues identified by validation.
"""

import asyncio
import json
import logging
import sqlite3
import sys
from pathlib import Path
from typing import List, Dict, Any

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
    db_path: str,
    validation_results_path: str,
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Fix pattern issues based on validation results.
    
    Args:
        db_path: Path to database
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
    
    db_accessor = DatabaseAccessor(db_path)
    
    try:
        # Connect to database
        import sqlite3
        if db_accessor.conn is None:
            db_accessor.conn = sqlite3.connect(db_path)
            db_accessor.conn.row_factory = sqlite3.Row
        
        conn = db_accessor.conn
        
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
                    conn.execute("DELETE FROM patterns WHERE id = ?", (pattern_id,))
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
                    conn.execute("DELETE FROM patterns WHERE id = ?", (pattern_id,))
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
                    conn.execute("DELETE FROM patterns WHERE id = ?", (pattern_id,))
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
        
    finally:
        await db_accessor.close()


async def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fix pattern issues identified by validation'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default='data/ai_automation.db',
        help='Database path'
    )
    parser.add_argument(
        '--docker-container',
        type=str,
        default='ai-pattern-service',
        help='Docker container name'
    )
    parser.add_argument(
        '--use-docker-db',
        action='store_true',
        help='Copy database from Docker container'
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
    
    # Handle Docker database
    db_path = args.db_path
    temp_db_path = None
    
    if args.use_docker_db:
        import subprocess
        import tempfile
        
        logger.info(f"Copying database from Docker container: {args.docker_container}")
        temp_dir = tempfile.mkdtemp(prefix='pattern_fix_')
        temp_db_path = Path(temp_dir) / 'ai_automation.db'
        
        try:
            subprocess.run([
                'docker', 'cp',
                f'{args.docker_container}:/app/data/ai_automation.db',
                str(temp_db_path)
            ], check=True, capture_output=True)
            db_path = str(temp_db_path)
            logger.info(f"Database copied to: {db_path}")
        except Exception as e:
            logger.error(f"Failed to copy database: {e}")
            sys.exit(1)
    
    try:
        results = await fix_pattern_issues(
            db_path,
            args.validation_results,
            dry_run=args.dry_run
        )
        
        # If using Docker and not dry run, copy database back
        if args.use_docker_db and not args.dry_run and temp_db_path and temp_db_path.exists():
            logger.info("\nCopying updated database back to Docker container...")
            try:
                subprocess.run([
                    'docker', 'cp',
                    str(temp_db_path),
                    f'{args.docker_container}:/app/data/ai_automation.db'
                ], check=True, capture_output=True)
                logger.info("[OK] Database updated in Docker container")
            except Exception as e:
                logger.error(f"Failed to copy database back: {e}")
        
    except Exception as e:
        logger.error(f"Fix failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if temp_db_path and temp_db_path.exists():
            try:
                temp_db_path.unlink()
                temp_db_path.parent.rmdir()
            except:
                pass


if __name__ == "__main__":
    asyncio.run(main())
