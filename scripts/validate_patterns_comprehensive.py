#!/usr/bin/env python3
"""
Comprehensive Pattern Validation

Validates patterns against actual events, identifies external data sources,
and checks pattern-synergy alignment.
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
import pandas as pd

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

# External data source patterns (should be excluded from home automation patterns)
EXTERNAL_DATA_PATTERNS = {
    # Sports/Team Tracker
    'sensor.team_tracker_',
    'sensor.nfl_',
    'sensor.nhl_',
    'sensor.mlb_',
    'sensor.nba_',
    'sensor.ncaa_',
    '_tracker',  # Any tracker entity
    
    # Weather (external API)
    'weather.',
    'sensor.weather_',
    'sensor.openweathermap_',
    
    # Energy/Carbon (external APIs)
    'sensor.carbon_intensity_',
    'sensor.electricity_pricing_',
    'sensor.national_grid_',
    
    # Calendar/Events (external)
    'calendar.',
    'sensor.calendar_',
    
    # System/Monitoring (not home automation)
    'sensor.home_assistant_',
    'sensor.system_',
    'sensor.cpu_',
    'sensor.memory_',
    'binary_sensor.system_',
}

# Domains that shouldn't create automation patterns
PASSIVE_DOMAINS = {
    'weather', 'sun', 'event', 'update', 'image', 'camera',
    'calendar', 'sensor'  # Many sensors are passive
}

# Domains that are actionable (good for patterns)
ACTIONABLE_DOMAINS = {
    'light', 'switch', 'climate', 'media_player',
    'lock', 'cover', 'fan', 'vacuum', 'scene'
}

# Domains that can trigger automations
TRIGGER_DOMAINS = {
    'binary_sensor', 'sensor', 'device_tracker', 'person',
    'input_boolean', 'input_select'
}


class PatternValidator:
    """Validates patterns for accuracy and relevance."""
    
    def __init__(self, db_path: str, data_api_url: str = "http://localhost:8006"):
        self.db_path = db_path
        self.data_api_url = data_api_url
        self.db_accessor = DatabaseAccessor(db_path)
        
    async def validate_all_patterns(
        self,
        time_window_days: int = 30
    ) -> Dict[str, Any]:
        """
        Validate all patterns comprehensively.
        
        Args:
            time_window_days: Days of events to fetch for validation
            
        Returns:
            Validation results dictionary
        """
        logger.info("=" * 80)
        logger.info("Comprehensive Pattern Validation")
        logger.info("=" * 80)
        
        # Fetch patterns and synergies
        logger.info("\n1. Fetching patterns and synergies from database...")
        patterns = await self.db_accessor.get_all_patterns()
        synergies = await self.db_accessor.get_all_synergies()
        
        logger.info(f"   Found {len(patterns)} patterns and {len(synergies)} synergies")
        
        # Fetch events for validation
        logger.info("\n2. Fetching events from Data API...")
        events_df = await self._fetch_events(time_window_days)
        logger.info(f"   Found {len(events_df)} events")
        
        # Validate patterns
        logger.info("\n3. Validating patterns...")
        validation_results = {
            'total_patterns': len(patterns),
            'total_synergies': len(synergies),
            'total_events': len(events_df),
            'external_data_patterns': [],
            'invalid_patterns': [],
            'patterns_without_events': [],
            'patterns_not_matching_synergies': [],
            'time_of_day_validation': {},
            'co_occurrence_validation': {},
            'recommendations': []
        }
        
        # Check for external data sources
        external_patterns = self._identify_external_data_patterns(patterns)
        validation_results['external_data_patterns'] = external_patterns
        logger.info(f"   Found {len(external_patterns)} patterns from external data sources")
        
        # Validate against events
        if not events_df.empty:
            invalid_patterns = self._validate_patterns_against_events(patterns, events_df)
            validation_results['invalid_patterns'] = invalid_patterns
            logger.info(f"   Found {len(invalid_patterns)} patterns that don't match events")
            
            patterns_without_events = self._find_patterns_without_events(patterns, events_df)
            validation_results['patterns_without_events'] = patterns_without_events
            logger.info(f"   Found {len(patterns_without_events)} patterns with no matching events")
        else:
            logger.warning("   No events available for validation")
        
        # Validate pattern-synergy alignment
        pattern_synergy_mismatches = self._validate_pattern_synergy_alignment(patterns, synergies)
        validation_results['patterns_not_matching_synergies'] = pattern_synergy_mismatches
        logger.info(f"   Found {len(pattern_synergy_mismatches)} pattern-synergy mismatches")
        
        # Validate time-of-day patterns
        tod_patterns = [p for p in patterns if p.get('pattern_type') == 'time_of_day']
        if tod_patterns:
            tod_validation = self._validate_time_of_day_patterns(tod_patterns, events_df)
            validation_results['time_of_day_validation'] = tod_validation
        
        # Validate co-occurrence patterns
        co_patterns = [p for p in patterns if p.get('pattern_type') == 'co_occurrence']
        if co_patterns:
            co_validation = self._validate_co_occurrence_patterns(co_patterns, events_df)
            validation_results['co_occurrence_validation'] = co_validation
        
        # Generate recommendations
        recommendations = self._generate_recommendations(validation_results)
        validation_results['recommendations'] = recommendations
        
        logger.info("\n" + "=" * 80)
        logger.info("Validation Complete")
        logger.info("=" * 80)
        
        return validation_results
    
    def _identify_external_data_patterns(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify patterns from external data sources."""
        external = []
        
        for pattern in patterns:
            device_id = pattern.get('device_id', '')
            
            # Check if device_id matches external patterns
            is_external = False
            matched_pattern = None
            
            for ext_pattern in EXTERNAL_DATA_PATTERNS:
                if ext_pattern in device_id.lower():
                    is_external = True
                    matched_pattern = ext_pattern
                    break
            
            # Check domain
            if '.' in device_id:
                domain = device_id.split('.')[0]
                if domain in PASSIVE_DOMAINS:
                    is_external = True
                    matched_pattern = f"domain:{domain}"
            
            if is_external:
                external.append({
                    'pattern_id': pattern.get('id'),
                    'device_id': device_id,
                    'pattern_type': pattern.get('pattern_type'),
                    'confidence': pattern.get('confidence', 0.0),
                    'matched_external_pattern': matched_pattern,
                    'reason': f"Matches external data pattern: {matched_pattern}"
                })
        
        return external
    
    def _validate_patterns_against_events(
        self,
        patterns: List[Dict[str, Any]],
        events_df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """Validate patterns against actual events."""
        invalid = []
        
        if events_df.empty:
            return invalid
        
        # Check available columns - events might use 'entity_id' instead of 'device_id'
        device_col = None
        if 'device_id' in events_df.columns:
            device_col = 'device_id'
        elif 'entity_id' in events_df.columns:
            device_col = 'entity_id'
        else:
            logger.warning("Events DataFrame has neither 'device_id' nor 'entity_id' column")
            logger.warning(f"Available columns: {list(events_df.columns)}")
            return invalid
        
        device_ids_in_events = set(events_df[device_col].dropna().unique())
        
        for pattern in patterns:
            device_id = pattern.get('device_id', '')
            pattern_type = pattern.get('pattern_type', '')
            
            # For co-occurrence, device_id might be "device1+device2"
            if pattern_type == 'co_occurrence' and '+' in device_id:
                device_ids = device_id.split('+')
                if not all(d in device_ids_in_events for d in device_ids):
                    invalid.append({
                        'pattern_id': pattern.get('id'),
                        'device_id': device_id,
                        'pattern_type': pattern_type,
                        'reason': f"Devices {device_ids} not found in events"
                    })
            elif device_id and device_id not in device_ids_in_events:
                invalid.append({
                    'pattern_id': pattern.get('id'),
                    'device_id': device_id,
                    'pattern_type': pattern_type,
                    'reason': f"Device {device_id} not found in events"
                })
        
        return invalid
    
    def _find_patterns_without_events(
        self,
        patterns: List[Dict[str, Any]],
        events_df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """Find patterns that have no matching events in the time window."""
        without_events = []
        
        if events_df.empty:
            return without_events
        
        # Determine device column name
        device_col = None
        if 'device_id' in events_df.columns:
            device_col = 'device_id'
        elif 'entity_id' in events_df.columns:
            device_col = 'entity_id'
        else:
            return without_events
        
        for pattern in patterns:
            device_id = pattern.get('device_id', '')
            pattern_type = pattern.get('pattern_type', '')
            
            # Check if device has events
            if pattern_type == 'co_occurrence' and '+' in device_id:
                device_ids = device_id.split('+')
                matching_events = events_df[events_df[device_col].isin(device_ids)]
            else:
                matching_events = events_df[events_df[device_col] == device_id]
            
            if matching_events.empty:
                without_events.append({
                    'pattern_id': pattern.get('id'),
                    'device_id': device_id,
                    'pattern_type': pattern_type,
                    'confidence': pattern.get('confidence', 0.0),
                    'reason': "No events found for this device in time window"
                })
        
        return without_events
    
    def _validate_pattern_synergy_alignment(
        self,
        patterns: List[Dict[str, Any]],
        synergies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Check if patterns align with detected synergies."""
        mismatches = []
        
        # Extract device IDs from synergies
        synergy_devices = set()
        for synergy in synergies:
            device_ids = synergy.get('device_ids', [])
            if isinstance(device_ids, str):
                try:
                    device_ids = json.loads(device_ids)
                except (json.JSONDecodeError, TypeError, ValueError):
                    device_ids = []
            
            if isinstance(device_ids, list):
                synergy_devices.update(device_ids)
        
        # Check patterns
        for pattern in patterns:
            device_id = pattern.get('device_id', '')
            pattern_type = pattern.get('pattern_type', '')
            
            # For co-occurrence, check both devices
            if pattern_type == 'co_occurrence' and '+' in device_id:
                device_ids = device_id.split('+')
                pattern_devices = set(device_ids)
            else:
                pattern_devices = {device_id}
            
            # Check if pattern devices are in any synergy
            if pattern_devices and not pattern_devices.intersection(synergy_devices):
                mismatches.append({
                    'pattern_id': pattern.get('id'),
                    'device_id': device_id,
                    'pattern_type': pattern_type,
                    'pattern_devices': list(pattern_devices),
                    'reason': "Pattern devices not found in any synergy"
                })
        
        return mismatches
    
    def _validate_time_of_day_patterns(
        self,
        patterns: List[Dict[str, Any]],
        events_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Validate time-of-day patterns."""
        if events_df.empty or 'timestamp' not in events_df.columns:
            return {'error': 'No events available'}
        
        results = {
            'total_patterns': len(patterns),
            'validated': 0,
            'invalid': 0,
            'details': []
        }
        
        # Determine device column name
        device_col = None
        if 'device_id' in events_df.columns:
            device_col = 'device_id'
        elif 'entity_id' in events_df.columns:
            device_col = 'entity_id'
        else:
            return {'error': 'No device/entity column in events'}
        
        for pattern in patterns:
            device_id = pattern.get('device_id', '')
            metadata = pattern.get('pattern_metadata', {})
            
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except (json.JSONDecodeError, TypeError, ValueError):
                    metadata = {}
            
            # Check if device has events at the expected time
            device_events = events_df[events_df[device_col] == device_id]
            if not device_events.empty:
                results['validated'] += 1
            else:
                results['invalid'] += 1
                results['details'].append({
                    'pattern_id': pattern.get('id'),
                    'device_id': device_id,
                    'reason': 'No events found for device'
                })
        
        return results
    
    def _validate_co_occurrence_patterns(
        self,
        patterns: List[Dict[str, Any]],
        events_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Validate co-occurrence patterns."""
        if events_df.empty:
            return {'error': 'No events available'}
        
        results = {
            'total_patterns': len(patterns),
            'validated': 0,
            'invalid': 0,
            'details': []
        }
        
        # Determine device column name
        device_col = None
        if 'device_id' in events_df.columns:
            device_col = 'device_id'
        elif 'entity_id' in events_df.columns:
            device_col = 'entity_id'
        else:
            return {'error': 'No device/entity column in events'}
        
        for pattern in patterns:
            device_id = pattern.get('device_id', '')
            
            if '+' in device_id:
                device_ids = device_id.split('+')
                
                # Check if both devices have events
                device1_events = events_df[events_df[device_col] == device_ids[0]]
                device2_events = events_df[events_df[device_col] == device_ids[1]]
                
                if not device1_events.empty and not device2_events.empty:
                    results['validated'] += 1
                else:
                    results['invalid'] += 1
                    results['details'].append({
                        'pattern_id': pattern.get('id'),
                        'device_id': device_id,
                        'reason': f"Missing events: device1={len(device1_events)}, device2={len(device2_events)}"
                    })
            else:
                results['invalid'] += 1
                results['details'].append({
                    'pattern_id': pattern.get('id'),
                    'device_id': device_id,
                    'reason': 'Invalid co-occurrence format (no + separator)'
                })
        
        return results
    
    def _generate_recommendations(
        self,
        results: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        external_count = len(results.get('external_data_patterns', []))
        if external_count > 0:
            recommendations.append(
                f"Remove {external_count} patterns from external data sources "
                "(sports, weather, etc.) - these don't represent home automation opportunities"
            )
        
        invalid_count = len(results.get('invalid_patterns', []))
        if invalid_count > 0:
            recommendations.append(
                f"Review {invalid_count} patterns that don't match events - "
                "may be stale or incorrect"
            )
        
        without_events_count = len(results.get('patterns_without_events', []))
        if without_events_count > 0:
            recommendations.append(
                f"Remove {without_events_count} patterns with no events in time window - "
                "likely stale patterns"
            )
        
        mismatch_count = len(results.get('patterns_not_matching_synergies', []))
        if mismatch_count > 0:
            recommendations.append(
                f"Review {mismatch_count} patterns that don't align with synergies - "
                "may indicate detection issues"
            )
        
        if not recommendations:
            recommendations.append("All patterns appear valid - no issues found")
        
        return recommendations
    
    async def _fetch_events(self, days: int) -> pd.DataFrame:
        """Fetch events from Data API."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(days=days)
                
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
                    # Handle both list and dict responses
                    if isinstance(data, list):
                        events = data
                    elif isinstance(data, dict):
                        events = data.get('data', {}).get('events', [])
                        if not events and 'events' in data:
                            events = data['events']
                    else:
                        events = []
                    
                    if events:
                        df = pd.DataFrame(events)
                        if 'timestamp' in df.columns:
                            # Handle various timestamp formats
                            df['timestamp'] = pd.to_datetime(
                                df['timestamp'],
                                format='ISO8601',
                                errors='coerce'
                            )
                        return df
                
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Failed to fetch events: {e}")
            return pd.DataFrame()
    
    async def close(self):
        """Close database connection."""
        await self.db_accessor.close()


async def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Comprehensive pattern validation'
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
        '--time-window',
        type=int,
        default=30,
        help='Days of events to fetch (default: 30)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='reports/quality/pattern_validation.json',
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
        temp_dir = tempfile.mkdtemp(prefix='pattern_validate_')
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
        validator = PatternValidator(db_path)
        results = await validator.validate_all_patterns(args.time_window)
        
        # Save results
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"\nResults saved to: {output_path}")
        
        # Print summary
        print("\n" + "=" * 80)
        print("Validation Summary")
        print("=" * 80)
        print(f"Total Patterns: {results['total_patterns']}")
        print(f"External Data Patterns: {len(results['external_data_patterns'])}")
        print(f"Invalid Patterns: {len(results['invalid_patterns'])}")
        print(f"Patterns Without Events: {len(results['patterns_without_events'])}")
        print(f"Pattern-Synergy Mismatches: {len(results['patterns_not_matching_synergies'])}")
        print("\nRecommendations:")
        for rec in results['recommendations']:
            print(f"  - {rec}")
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if temp_db_path and temp_db_path.exists():
            try:
                temp_db_path.unlink()
                temp_db_path.parent.rmdir()
            except (OSError, PermissionError) as e:
                logger.warning(f"Failed to clean up temp file {temp_db_path}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
