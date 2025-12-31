#!/usr/bin/env python3
"""
Filter Inactive Devices from Patterns and Synergies

Filters patterns and synergies to only show devices that have been active
within a specified time window. Devices that are inactive (turned off, removed,
or not used) are excluded from display but patterns are preserved for
historical reference.
"""

import asyncio
import json
import logging
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import httpx

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

# Device activity time windows (2025 best practices)
ACTIVITY_WINDOWS = {
    'recent': 7,      # 7 days - devices used in last week
    'active': 30,     # 30 days - devices used in last month
    'seasonal': 90,   # 90 days - devices used in last quarter (seasonal)
    'historical': 365 # 365 days - devices used in last year (historical)
}

# Domain-specific activity windows (some devices used less frequently)
DOMAIN_ACTIVITY_WINDOWS = {
    'climate': 30,        # Thermostats - monthly usage
    'vacuum': 7,          # Vacuums - weekly usage
    'irrigation': 90,     # Irrigation - seasonal
    'fan': 30,            # Fans - seasonal
    'cover': 30,          # Blinds - monthly
    'light': 7,           # Lights - daily/weekly
    'switch': 7,          # Switches - daily/weekly
    'lock': 7,            # Locks - daily
    'media_player': 7,    # Media players - daily/weekly
    'binary_sensor': 7,   # Motion sensors - daily
    'sensor': 30,         # Sensors - monthly (some are passive)
}


class InactiveDeviceFilter:
    """Filters patterns and synergies by device activity."""
    
    def __init__(
        self,
        db_path: str,
        data_api_url: str = "http://localhost:8006",
        activity_window_days: int = 30
    ):
        self.db_path = db_path
        self.data_api_url = data_api_url
        self.activity_window_days = activity_window_days
        self.db_accessor = DatabaseAccessor(db_path)
        self.active_devices: Set[str] = set()
        
    async def identify_active_devices(
        self,
        activity_window_days: Optional[int] = None
    ) -> Set[str]:
        """
        Identify devices that have been active within the time window.
        
        Args:
            activity_window_days: Days to look back (default: self.activity_window_days)
            
        Returns:
            Set of active device IDs
        """
        window_days = activity_window_days or self.activity_window_days
        
        logger.info(f"Identifying active devices (last {window_days} days)...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(days=window_days)
                
                params = {
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'limit': 50000
                }
                
                response = await client.get(
                    f"{self.data_api_url}/api/v1/events",
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Handle multiple response formats
                    if isinstance(data, list):
                        events = data
                    elif isinstance(data, dict):
                        # Try different response formats
                        events = data.get('data', {}).get('events', [])
                        if not events:
                            events = data.get('events', [])
                        if not events and 'results' in data:
                            events = data.get('results', [])
                        if not events and isinstance(data.get('data'), list):
                            events = data.get('data', [])
                    else:
                        events = []
                    
                    # Extract unique entity IDs from events
                    entity_ids = set()
                    for event in events:
                        # Check multiple possible field names
                        entity_id = (
                            event.get('entity_id') or 
                            event.get('device_id') or
                            event.get('entity') or
                            (event.get('attributes', {}) or {}).get('entity_id')
                        )
                        if entity_id:
                            entity_ids.add(entity_id)
                    
                    # Use entity_ids as device_ids (entities represent devices)
                    device_ids = entity_ids
                    
                    logger.info(f"Found {len(device_ids)} active devices in last {window_days} days")
                    self.active_devices = device_ids
                    return device_ids
                else:
                    logger.warning(f"Failed to fetch events: {response.status_code}")
                    return set()
        except Exception as e:
            logger.error(f"Error identifying active devices: {e}")
            return set()
    
    async def filter_patterns_by_activity(
        self,
        patterns: List[Dict[str, Any]],
        active_devices: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        Filter patterns to only include those with active devices.
        
        Args:
            patterns: List of pattern dictionaries
            active_devices: Set of active device IDs (if None, will fetch)
            
        Returns:
            Dictionary with filtered patterns and statistics
        """
        if active_devices is None:
            active_devices = await self.identify_active_devices()
        
        if not active_devices:
            logger.warning("No active devices found - returning all patterns")
            return {
                'total_patterns': len(patterns),
                'active_patterns': len(patterns),
                'inactive_patterns': 0,
                'filtered_patterns': patterns
            }
        
        active_patterns = []
        inactive_patterns = []
        
        for pattern in patterns:
            device_id = pattern.get('device_id', '')
            pattern_type = pattern.get('pattern_type', '')
            
            # For co-occurrence patterns, check both devices
            if pattern_type == 'co_occurrence' and '+' in device_id:
                device_ids = device_id.split('+')
                is_active = any(d in active_devices for d in device_ids)
            else:
                is_active = device_id in active_devices
            
            if is_active:
                active_patterns.append(pattern)
            else:
                inactive_patterns.append(pattern)
        
        logger.info(f"Filtered patterns: {len(active_patterns)} active, {len(inactive_patterns)} inactive")
        
        return {
            'total_patterns': len(patterns),
            'active_patterns': len(active_patterns),
            'inactive_patterns': len(inactive_patterns),
            'filtered_patterns': active_patterns,
            'inactive_patterns_list': inactive_patterns
        }
    
    async def filter_synergies_by_activity(
        self,
        synergies: List[Dict[str, Any]],
        active_devices: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        Filter synergies to only include those with active devices.
        
        Args:
            synergies: List of synergy dictionaries
            active_devices: Set of active device IDs (if None, will fetch)
            
        Returns:
            Dictionary with filtered synergies and statistics
        """
        if active_devices is None:
            active_devices = await self.identify_active_devices()
        
        if not active_devices:
            logger.warning("No active devices found - returning all synergies")
            return {
                'total_synergies': len(synergies),
                'active_synergies': len(synergies),
                'inactive_synergies': 0,
                'filtered_synergies': synergies
            }
        
        active_synergies = []
        inactive_synergies = []
        
        for synergy in synergies:
            device_ids_raw = synergy.get('device_ids', [])
            
            # Parse device_ids
            if isinstance(device_ids_raw, str):
                try:
                    device_ids = json.loads(device_ids_raw)
                except:
                    device_ids = []
            else:
                device_ids = device_ids_raw if isinstance(device_ids_raw, list) else []
            
            # Check if any device in synergy is active
            is_active = any(d in active_devices for d in device_ids) if device_ids else False
            
            if is_active:
                active_synergies.append(synergy)
            else:
                inactive_synergies.append(synergy)
        
        logger.info(f"Filtered synergies: {len(active_synergies)} active, {len(inactive_synergies)} inactive")
        
        return {
            'total_synergies': len(synergies),
            'active_synergies': len(active_synergies),
            'inactive_synergies': len(inactive_synergies),
            'filtered_synergies': active_synergies,
            'inactive_synergies_list': inactive_synergies
        }
    
    async def analyze_device_activity(
        self,
        activity_window_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze device activity and provide recommendations.
        
        Args:
            activity_window_days: Days to analyze (default: self.activity_window_days)
            
        Returns:
            Analysis results with recommendations
        """
        window_days = activity_window_days or self.activity_window_days
        
        logger.info("=" * 80)
        logger.info("Device Activity Analysis")
        logger.info("=" * 80)
        
        # Fetch patterns and synergies
        patterns = await self.db_accessor.get_all_patterns()
        synergies = await self.db_accessor.get_all_synergies()
        
        logger.info(f"Found {len(patterns)} patterns and {len(synergies)} synergies")
        
        # Identify active devices
        active_devices = await self.identify_active_devices(window_days)
        
        # Filter patterns
        pattern_results = await self.filter_patterns_by_activity(patterns, active_devices)
        
        # Filter synergies
        synergy_results = await self.filter_synergies_by_activity(synergies, active_devices)
        
        # Generate recommendations
        recommendations = self._generate_activity_recommendations(
            pattern_results,
            synergy_results,
            window_days
        )
        
        results = {
            'activity_window_days': window_days,
            'active_devices_count': len(active_devices),
            'patterns': pattern_results,
            'synergies': synergy_results,
            'recommendations': recommendations
        }
        
        logger.info("\n" + "=" * 80)
        logger.info("Analysis Complete")
        logger.info("=" * 80)
        
        return results
    
    def _generate_activity_recommendations(
        self,
        pattern_results: Dict[str, Any],
        synergy_results: Dict[str, Any],
        window_days: int
    ) -> List[str]:
        """Generate recommendations based on activity analysis."""
        recommendations = []
        
        inactive_pattern_pct = (
            pattern_results['inactive_patterns'] / pattern_results['total_patterns'] * 100
            if pattern_results['total_patterns'] > 0 else 0
        )
        
        inactive_synergy_pct = (
            synergy_results['inactive_synergies'] / synergy_results['total_synergies'] * 100
            if synergy_results['total_synergies'] > 0 else 0
        )
        
        if inactive_pattern_pct > 50:
            recommendations.append(
                f"High inactive pattern rate ({inactive_pattern_pct:.0f}%) - "
                f"consider archiving patterns older than {window_days} days"
            )
        
        if inactive_synergy_pct > 50:
            recommendations.append(
                f"High inactive synergy rate ({inactive_synergy_pct:.0f}%) - "
                f"consider filtering synergies by device activity"
            )
        
        if window_days < 30:
            recommendations.append(
                f"Using {window_days}-day window - consider 30 days for seasonal devices"
            )
        
        if not recommendations:
            recommendations.append(
                f"Device activity looks healthy - {pattern_results['active_patterns']} active patterns, "
                f"{synergy_results['active_synergies']} active synergies"
            )
        
        return recommendations
    
    async def close(self):
        """Close database connection."""
        await self.db_accessor.close()


async def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Filter inactive devices from patterns and synergies'
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
        '--activity-window',
        type=int,
        default=30,
        choices=[7, 30, 90, 365],
        help='Activity window in days (default: 30)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='reports/quality/device_activity_analysis.json',
        help='Output file path'
    )
    
    args = parser.parse_args()
    
    # Handle Docker database
    db_path = args.db_path
    temp_db_path = None
    
    if args.use_docker_db:
        import subprocess
        import tempfile
        
        logger.info(f"Copying database from Docker container: {args.docker_container}")
        temp_dir = tempfile.mkdtemp(prefix='device_activity_')
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
        filter_tool = InactiveDeviceFilter(
            db_path,
            activity_window_days=args.activity_window
        )
        
        results = await filter_tool.analyze_device_activity()
        
        # Save results
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"\nResults saved to: {output_path}")
        
        # Print summary
        print("\n" + "=" * 80)
        print("Device Activity Analysis Summary")
        print("=" * 80)
        print(f"Activity Window: {args.activity_window} days")
        print(f"Active Devices: {results['active_devices_count']}")
        print(f"\nPatterns:")
        print(f"  Total: {results['patterns']['total_patterns']}")
        print(f"  Active: {results['patterns']['active_patterns']}")
        print(f"  Inactive: {results['patterns']['inactive_patterns']}")
        print(f"\nSynergies:")
        print(f"  Total: {results['synergies']['total_synergies']}")
        print(f"  Active: {results['synergies']['active_synergies']}")
        print(f"  Inactive: {results['synergies']['inactive_synergies']}")
        print("\nRecommendations:")
        for rec in results['recommendations']:
            print(f"  - {rec}")
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
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
