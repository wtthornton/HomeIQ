#!/usr/bin/env python3
"""
Validate Synergies Against Patterns

Validates all synergies in the database against patterns and updates
pattern_support_score and validated_by_patterns fields.

Usage:
    python scripts/validate_synergy_patterns.py --use-docker-db
"""

import argparse
import asyncio
import json
import logging
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.quality_evaluation.database_accessor import DatabaseAccessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def calculate_pattern_support_score(
    synergy: Dict[str, Any],
    patterns: List[Dict[str, Any]]
) -> tuple[float, List[int]]:
    """
    Calculate pattern support score for a synergy.
    
    Args:
        synergy: Synergy dictionary with device_ids
        patterns: List of pattern dictionaries
        
    Returns:
        Tuple of (support_score, supporting_pattern_ids)
    """
    device_ids = synergy.get('device_ids', [])
    if isinstance(device_ids, str):
        try:
            device_ids = json.loads(device_ids)
        except (json.JSONDecodeError, TypeError):
            device_ids = []
    
    if not device_ids or not isinstance(device_ids, list):
        return 0.0, []
    
    support_score = 0.0
    supporting_pattern_ids = []
    
    # Extract devices - handle both 2-device and n-level synergies
    trigger_device = device_ids[0] if len(device_ids) > 0 else None
    action_device = device_ids[1] if len(device_ids) > 1 else None
    all_synergy_devices = set(device_ids)  # All devices in synergy for matching
    
    # Criterion 1: Co-occurrence patterns (0.5 weight)
    for pattern in patterns:
        if pattern.get('pattern_type') == 'co_occurrence':
            pattern_device_id = pattern.get('device_id', '')
            pattern_metadata = pattern.get('pattern_metadata', {})
            
            # Co-occurrence patterns store device_id as "device1+device2"
            # Or check metadata for device1 and device2
            pattern_devices = []
            
            # Try to extract from device_id (format: "device1+device2")
            if '+' in pattern_device_id:
                pattern_devices = pattern_device_id.split('+')
            # Or check metadata
            elif isinstance(pattern_metadata, dict):
                if 'device1' in pattern_metadata and 'device2' in pattern_metadata:
                    pattern_devices = [pattern_metadata['device1'], pattern_metadata['device2']]
                elif 'devices' in pattern_metadata:
                    co_devices = pattern_metadata['devices']
                    if isinstance(co_devices, str):
                        try:
                            pattern_devices = json.loads(co_devices)
                        except (json.JSONDecodeError, TypeError):
                            pattern_devices = []
                    elif isinstance(co_devices, list):
                        pattern_devices = co_devices
            
            # Check if pattern involves devices from synergy
            if len(pattern_devices) >= 2:
                pattern_devices_set = set(pattern_devices)
                # Check if at least 2 devices from synergy match the pattern
                matching_devices = all_synergy_devices.intersection(pattern_devices_set)
                if len(matching_devices) >= 2:
                    # Strong match - both devices in pattern
                    contribution = pattern.get('confidence', 0.0) * 0.5
                    support_score += contribution
                    if pattern.get('id') and pattern['id'] not in supporting_pattern_ids:
                        supporting_pattern_ids.append(pattern['id'])
                elif len(matching_devices) == 1 and trigger_device and action_device:
                    # Partial match - one device matches
                    contribution = pattern.get('confidence', 0.0) * 0.25
                    support_score += contribution
    
    # Criterion 2: Time-of-day patterns for devices (0.3 weight)
    # Find time patterns for all devices in synergy
    device_time_patterns = {}
    for device_id in device_ids:
        time_patterns = [
            p for p in patterns
            if p.get('pattern_type') == 'time_of_day' and p.get('device_id') == device_id
        ]
        if time_patterns:
            device_time_patterns[device_id] = time_patterns
    
    # If multiple devices have time patterns, that's a strong signal
    if len(device_time_patterns) >= 2:
        # Multiple devices have time patterns - temporal alignment
        avg_confidence = sum(
            sum(p.get('confidence', 0.0) for p in patterns) / len(patterns)
            for patterns in device_time_patterns.values()
        ) / len(device_time_patterns)
        contribution = avg_confidence * 0.3
        support_score += contribution
    elif len(device_time_patterns) == 1:
        # Single device has time pattern - weaker signal
        patterns_list = list(device_time_patterns.values())[0]
        avg_confidence = sum(p.get('confidence', 0.0) for p in patterns_list) / len(patterns_list)
        contribution = avg_confidence * 0.15
        support_score += contribution
    
    # Criterion 3: Individual device patterns (0.2 weight)
    device_patterns = [
        p for p in patterns
        if p.get('device_id') in device_ids
    ]
    if device_patterns:
        avg_confidence = sum(p.get('confidence', 0.0) for p in device_patterns) / len(device_patterns)
        contribution = avg_confidence * 0.2
        support_score += contribution
    
    # Normalize to [0, 1]
    support_score = min(1.0, support_score)
    
    return support_score, supporting_pattern_ids


async def validate_all_synergies(
    db_path: str,
    min_support_threshold: float = 0.7
) -> Dict[str, Any]:
    """
    Validate all synergies against patterns and update database.
    
    Args:
        db_path: Path to database file
        min_support_threshold: Minimum support score to set validated_by_patterns=True
        
    Returns:
        Dictionary with validation results
    """
    db_accessor = DatabaseAccessor(db_path)
    
    try:
        # Fetch all patterns and synergies
        logger.info("Fetching patterns and synergies from database...")
        patterns = await db_accessor.get_all_patterns()
        synergies = await db_accessor.get_all_synergies()
        
        logger.info(f"Found {len(patterns)} patterns and {len(synergies)} synergies")
        
        if not patterns:
            logger.warning("No patterns found - cannot validate synergies")
            return {
                'total_synergies': len(synergies),
                'validated': 0,
                'updated': 0,
                'errors': []
            }
        
        # Validate each synergy
        validated_count = 0
        updated_count = 0
        errors = []
        
        # Connect to database for updates (use same connection as accessor)
        import sqlite3
        if db_accessor.conn is None:
            db_accessor.conn = sqlite3.connect(db_path)
            db_accessor.conn.row_factory = sqlite3.Row
        
        conn = db_accessor.conn
        
        for synergy in synergies:
            try:
                synergy_id = synergy.get('synergy_id')
                if not synergy_id:
                    # Try to get from id field
                    synergy_id = synergy.get('id')
                    if not synergy_id:
                        logger.warning(f"Skipping synergy without synergy_id: {synergy.get('synergy_type', 'unknown')}")
                        continue
                
                # Calculate support score
                support_score, supporting_pattern_ids = calculate_pattern_support_score(
                    synergy, patterns
                )
                
                # Determine if validated
                validated_by_patterns = support_score >= min_support_threshold
                
                # Update database
                update_query = """
                    UPDATE synergy_opportunities
                    SET pattern_support_score = ?,
                        validated_by_patterns = ?,
                        supporting_pattern_ids = ?
                    WHERE synergy_id = ?
                """
                
                supporting_patterns_json = json.dumps(supporting_pattern_ids) if supporting_pattern_ids else None
                
                cursor = conn.execute(update_query, (
                    support_score,
                    1 if validated_by_patterns else 0,  # SQLite uses 0/1 for boolean
                    supporting_patterns_json,
                    synergy_id
                ))
                
                if cursor.rowcount > 0:
                    updated_count += 1
                    if validated_by_patterns:
                        validated_count += 1
                else:
                    logger.warning(f"No rows updated for synergy_id: {synergy_id}")
                
                if updated_count % 10 == 0:
                    logger.info(f"Validated {updated_count}/{len(synergies)} synergies...")
                    
            except Exception as e:
                error_msg = f"Error validating synergy {synergy.get('synergy_id', 'unknown')}: {e}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
        
        # Commit changes
        conn.commit()
        
        logger.info(f"✅ Validated {validated_count}/{len(synergies)} synergies (support >= {min_support_threshold})")
        logger.info(f"✅ Updated {updated_count} synergies in database")
        
        return {
            'total_synergies': len(synergies),
            'validated': validated_count,
            'updated': updated_count,
            'errors': errors,
            'min_support_threshold': min_support_threshold
        }
        
    finally:
        await db_accessor.close()


async def main() -> None:
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Validate synergies against patterns and update pattern_support_score'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default='data/ai_automation.db',
        help='Database path (default: data/ai_automation.db)'
    )
    parser.add_argument(
        '--docker-container',
        type=str,
        default='ai-pattern-service',
        help='Docker container name to copy database from (default: ai-pattern-service)'
    )
    parser.add_argument(
        '--use-docker-db',
        action='store_true',
        help='Copy database from Docker container instead of using local path'
    )
    parser.add_argument(
        '--min-support-threshold',
        type=float,
        default=0.7,
        help='Minimum support score to set validated_by_patterns=True (default: 0.7)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Handle Docker database access
    db_path = args.db_path
    temp_db_path = None
    
    if args.use_docker_db:
        logger.info(f"Copying database from Docker container: {args.docker_container}")
        try:
            temp_dir = tempfile.mkdtemp(prefix='synergy_validate_')
            temp_db_path = Path(temp_dir) / 'ai_automation.db'
            
            copy_cmd = [
                'docker', 'cp',
                f'{args.docker_container}:/app/data/ai_automation.db',
                str(temp_db_path)
            ]
            subprocess.run(copy_cmd, check=True, capture_output=True)
            db_path = str(temp_db_path)
            logger.info(f"Database copied from Docker to: {db_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to copy database from Docker: {e.stderr.decode()}")
            sys.exit(1)
        except FileNotFoundError:
            logger.error("Docker command not found. Please install Docker or use --db-path with local database.")
            sys.exit(1)
    
    try:
        logger.info("=" * 80)
        logger.info("Synergy Pattern Validation")
        logger.info("=" * 80)
        
        results = await validate_all_synergies(db_path, args.min_support_threshold)
        
        logger.info("=" * 80)
        logger.info("Validation Complete!")
        logger.info(f"Total Synergies: {results['total_synergies']}")
        logger.info(f"Validated (score >= {args.min_support_threshold}): {results['validated']}")
        logger.info(f"Updated: {results['updated']}")
        if results['errors']:
            logger.warning(f"Errors: {len(results['errors'])}")
        logger.info("=" * 80)
        
        # If using Docker, copy updated database back
        if args.use_docker_db and temp_db_path and temp_db_path.exists():
            logger.info("Copying updated database back to Docker container...")
            try:
                copy_back_cmd = [
                    'docker', 'cp',
                    str(temp_db_path),
                    f'{args.docker_container}:/app/data/ai_automation.db'
                ]
                subprocess.run(copy_back_cmd, check=True, capture_output=True)
                logger.info("✅ Database updated in Docker container")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to copy database back to Docker: {e.stderr.decode()}")
                logger.warning("Database was updated locally but not in Docker container")
        
    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if temp_db_path and temp_db_path.exists():
            try:
                temp_db_path.unlink()
                temp_db_path.parent.rmdir()
            except Exception as e:
                logger.warning(f"Failed to clean up temp database: {e}")


if __name__ == "__main__":
    asyncio.run(main())
