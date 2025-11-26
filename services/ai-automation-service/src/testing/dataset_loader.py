"""
Home Assistant Dataset Loader

Loads synthetic home datasets from home-assistant-datasets repository
for testing pattern detection, synergy detection, and automation generation.

Phase 1: Foundation - Dataset Loading
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class HomeAssistantDatasetLoader:
    """Load synthetic home datasets for testing"""
    
    def __init__(self, dataset_root: str | Path | None = None):
        """
        Initialize dataset loader.
        
        Args:
            dataset_root: Root directory containing datasets.
                         Defaults to tests/datasets/datasets/ if not provided.
        """
        if dataset_root is None:
            # Default to tests/datasets/datasets/ (git submodule location)
            project_root = Path(__file__).parent.parent.parent.parent.parent
            dataset_root = project_root / "tests" / "datasets" / "datasets"
        else:
            dataset_root = Path(dataset_root)
        
        self.dataset_root = dataset_root
        logger.info(f"Dataset loader initialized with root: {self.dataset_root}")
    
    def list_available_datasets(self) -> list[str]:
        """
        List all available datasets in the dataset root.
        
        Returns:
            List of dataset names (directory names)
        """
        if not self.dataset_root.exists():
            logger.warning(f"Dataset root does not exist: {self.dataset_root}")
            return []
        
        datasets = [
            d.name for d in self.dataset_root.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        ]
        
        logger.info(f"Found {len(datasets)} datasets: {datasets}")
        return datasets
    
    async def load_synthetic_home(self, dataset_name: str) -> dict[str, Any]:
        """
        Load synthetic home configuration from dataset.
        
        Args:
            dataset_name: Name of dataset (e.g., 'assist-mini', 'assist', 'intents')
        
        Returns:
            Dictionary containing:
            - 'home': Home configuration
            - 'areas': List of area definitions
            - 'devices': List of device definitions
            - 'events': List of synthetic events (if available)
            - 'expected_patterns': Ground truth patterns (if available)
            - 'expected_synergies': Ground truth synergies (if available)
        
        Raises:
            FileNotFoundError: If dataset directory doesn't exist
            ValueError: If dataset format is invalid
        """
        dataset_path = self.dataset_root / dataset_name
        
        if not dataset_path.exists():
            raise FileNotFoundError(
                f"Dataset '{dataset_name}' not found at {dataset_path}. "
                f"Available datasets: {self.list_available_datasets()}"
            )
        
        logger.info(f"Loading dataset: {dataset_name} from {dataset_path}")
        
        result: dict[str, Any] = {
            'dataset_name': dataset_name,
            'dataset_path': str(dataset_path),
            'home': {},
            'areas': [],
            'devices': [],
            'events': [],
            'expected_patterns': [],
            'expected_synergies': []
        }
        
        # Try to load home.yaml (Synthetic Home format)
        home_yaml = dataset_path / "home.yaml"
        if home_yaml.exists():
            logger.info(f"Loading home.yaml from {home_yaml}")
            with open(home_yaml, 'r', encoding='utf-8') as f:
                home_data = yaml.safe_load(f)
            
            # Extract home configuration
            result['home'] = home_data.get('home', {})
            result['areas'] = home_data.get('areas', [])
            result['devices'] = home_data.get('devices', [])
            
            logger.info(f"Loaded {len(result['areas'])} areas, {len(result['devices'])} devices")
        
        # Try to load events.json or events.yaml
        events_json = dataset_path / "events.json"
        events_yaml = dataset_path / "events.yaml"
        
        if events_json.exists():
            logger.info(f"Loading events.json from {events_json}")
            with open(events_json, 'r', encoding='utf-8') as f:
                result['events'] = json.load(f)
        elif events_yaml.exists():
            logger.info(f"Loading events.yaml from {events_yaml}")
            with open(events_yaml, 'r', encoding='utf-8') as f:
                result['events'] = yaml.safe_load(f)
        
        # Try to load ground truth patterns
        patterns_json = dataset_path / "expected_patterns.json"
        if patterns_json.exists():
            logger.info(f"Loading expected_patterns.json from {patterns_json}")
            with open(patterns_json, 'r', encoding='utf-8') as f:
                result['expected_patterns'] = json.load(f)
        
        # Try to load ground truth synergies
        synergies_json = dataset_path / "expected_synergies.json"
        if synergies_json.exists():
            logger.info(f"Loading expected_synergies.json from {synergies_json}")
            with open(synergies_json, 'r', encoding='utf-8') as f:
                result['expected_synergies'] = json.load(f)
        
        # Extract device relationships from home configuration
        if not result['expected_synergies'] and result['devices']:
            result['expected_synergies'] = self._extract_relationships_from_devices(
                result['devices'], result['areas']
            )
        
        logger.info(f"✅ Loaded dataset '{dataset_name}': "
                   f"{len(result['devices'])} devices, "
                   f"{len(result['events'])} events, "
                   f"{len(result['expected_patterns'])} expected patterns, "
                   f"{len(result['expected_synergies'])} expected synergies")
        
        return result
    
    def _extract_relationships_from_devices(
        self,
        devices: list[dict[str, Any]],
        areas: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Extract expected device relationships from device configuration.
        
        This is a heuristic extraction - in a real dataset, relationships
        would be explicitly defined. This method infers relationships based on:
        - Device types (motion sensors → lights)
        - Area co-location
        - Device naming patterns
        
        Args:
            devices: List of device definitions
            areas: List of area definitions
        
        Returns:
            List of expected synergy relationships
        """
        relationships = []
        
        # Group devices by area
        devices_by_area: dict[str, list[dict]] = {}
        for device in devices:
            area_name = device.get('area', 'unknown')
            if area_name not in devices_by_area:
                devices_by_area[area_name] = []
            devices_by_area[area_name].append(device)
        
        # Find motion → light relationships
        for area_name, area_devices in devices_by_area.items():
            motion_sensors = [
                d for d in area_devices
                if d.get('device_type') == 'binary_sensor' and
                   d.get('device_class') == 'motion'
            ]
            lights = [
                d for d in area_devices
                if d.get('device_type') == 'light'
            ]
            
            for motion in motion_sensors:
                for light in lights:
                    relationships.append({
                        'trigger_entity': motion.get('entity_id', ''),
                        'action_entity': light.get('entity_id', ''),
                        'relationship_type': 'motion_to_light',
                        'confidence': 0.9,
                        'area': area_name
                    })
        
        logger.info(f"Extracted {len(relationships)} relationships from device configuration")
        return relationships
    
    def _get_events_per_device_per_day(self, device_type: str) -> float:
        """
        Get recommended events per day for device type (50% of production).
        
        Based on production data analysis:
        - VERY HIGH: image (279/day), sun (212/day) → 140, 106
        - HIGH: binary_sensor (73/day), sensor (52/day), media_player (55/day) → 36, 26, 28
        - MEDIUM: light (21/day), weather (19/day), vacuum (16/day) → 11, 9, 8
        - LOW: switch (0.19/day), button (0.19/day), automation (2.5/day) → 3, 2, 10 (minimum)
        """
        frequencies = {
            # VERY HIGH (>100/day in production)
            'image': 140,           # Cameras - continuous updates
            'sun': 106,             # Sun position - continuous
            
            # HIGH (20-100/day in production)
            'binary_sensor': 36,    # Motion, door sensors - frequent
            'sensor': 26,           # Temperature, light sensors - periodic
            'media_player': 28,     # Playback state changes
            
            # MEDIUM (5-20/day in production)
            'light': 11,           # On/off cycles
            'weather': 9,          # Periodic updates
            'vacuum': 8,           # Status updates
            'device_tracker': 5,   # Location updates
            'person': 5,           # Presence changes
            
            # LOW (<5/day in production) - with minimums
            'scene': 4,            # Manual activations
            'select': 3,           # Configuration changes
            'automation': 10,      # Trigger events (minimum for testing)
            'switch': 3,          # Manual toggles (minimum)
            'button': 2,          # Manual presses (minimum)
            'event': 2,           # System events (minimum)
            'remote': 2,          # Remote control (minimum)
            'zone': 2,            # Zone changes (minimum)
            'number': 2,          # Number inputs (minimum)
            'update': 2,          # Update checks (minimum)
            'climate': 3,         # Thermostat (minimum)
            'cover': 2,           # Blinds, garage (minimum)
            'lock': 2,            # Smart locks (minimum)
            'fan': 3,             # Fans (minimum)
        }
        
        # Return device-type-specific frequency or default
        return frequencies.get(device_type, 7.5)  # Default: average
    
    def generate_synthetic_events(
        self,
        home_data: dict[str, Any],
        days: int = 7,
        events_per_day: int = 50
    ) -> list[dict[str, Any]]:
        """
        Generate synthetic events from home configuration.
        
        Uses device-type-specific event frequencies based on production data.
        Events are distributed proportionally to device types.
        
        Args:
            home_data: Home configuration from load_synthetic_home()
            days: Number of days of events to generate
            events_per_day: Target events per day (if None, calculated from devices)
        
        Returns:
            List of synthetic event dictionaries
        """
        from datetime import datetime, timedelta, timezone
        import random
        
        events = []
        devices = home_data.get('devices', [])
        
        if not devices:
            logger.warning("No devices found in home_data, cannot generate events")
            return events
        
        # Calculate device-type-specific event frequencies
        device_events = {}
        total_events_per_day = 0
        
        for device in devices:
            device_type = device.get('device_type', 'default')
            entity_id = device.get('entity_id', f"unknown.{device.get('name', 'device')}")
            
            events_per_device = self._get_events_per_device_per_day(device_type)
            
            if entity_id not in device_events:
                device_events[entity_id] = {
                    'device': device,
                    'events_per_day': events_per_device,
                    'device_type': device_type
                }
                total_events_per_day += events_per_device
        
        # If events_per_day is provided, scale proportionally
        if events_per_day and total_events_per_day > 0:
            scale_factor = events_per_day / total_events_per_day
            for entity_id in device_events:
                device_events[entity_id]['events_per_day'] *= scale_factor
        
        start_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Generate events for each device based on its frequency
        for day in range(days):
            day_start = start_time + timedelta(days=day)
            
            for entity_id, device_info in device_events.items():
                device = device_info['device']
                device_type = device_info['device_type']
                events_for_device = int(device_info['events_per_day'])
                
                for _ in range(events_for_device):
                    # Generate random state based on device type
                    if device_type == 'light':
                        state = random.choice(['on', 'off'])
                    elif device_type == 'binary_sensor':
                        state = random.choice(['on', 'off'])
                    elif device_type == 'sensor':
                        state = str(random.randint(0, 100))
                    elif device_type == 'image':
                        state = 'idle'  # Camera states
                    elif device_type == 'media_player':
                        state = random.choice(['playing', 'paused', 'idle', 'off'])
                    elif device_type == 'climate':
                        state = str(random.randint(65, 75))  # Temperature
                    elif device_type == 'cover':
                        state = random.choice(['open', 'closed', 'opening', 'closing'])
                    elif device_type == 'switch':
                        state = random.choice(['on', 'off'])
                    elif device_type == 'vacuum':
                        state = random.choice(['cleaning', 'docked', 'idle', 'returning'])
                    else:
                        state = 'unknown'
                    
                    event_time = day_start + timedelta(
                        hours=random.randint(0, 23),
                        minutes=random.randint(0, 59),
                        seconds=random.randint(0, 59)
                    )
                    
                    events.append({
                        'event_type': 'state_changed',
                        'entity_id': entity_id,
                        'state': state,
                        'timestamp': event_time.isoformat(),
                        'attributes': {
                            'device_type': device_type,
                            'area': device.get('area', 'unknown')
                        }
                    })
        
        logger.info(f"Generated {len(events)} synthetic events over {days} days "
                   f"({len(device_events)} devices, {total_events_per_day:.1f} events/day)")
        return events

