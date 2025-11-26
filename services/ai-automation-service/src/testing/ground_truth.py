"""
Ground Truth Extraction and Validation

Phase 2: Pattern Testing - Ground Truth Utilities

Extracts and validates ground truth patterns and synergies from datasets.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class GroundTruthExtractor:
    """Extract ground truth patterns and synergies from datasets"""
    
    def __init__(self, dataset_data: dict[str, Any]):
        """
        Initialize ground truth extractor.
        
        Args:
            dataset_data: Dataset data from HomeAssistantDatasetLoader
        """
        self.dataset_data = dataset_data
        self.devices = dataset_data.get('devices', [])
        self.areas = dataset_data.get('areas', [])
        self.events = dataset_data.get('events', [])
    
    def extract_patterns(self) -> list[dict[str, Any]]:
        """
        Extract expected patterns from dataset.
        
        Tries multiple sources:
        1. explicit expected_patterns.json
        2. Device relationships (heuristic)
        3. Event patterns (heuristic)
        
        Returns:
            List of ground truth pattern dictionaries
        """
        patterns = []
        
        # Try explicit ground truth first
        if self.dataset_data.get('expected_patterns'):
            logger.info(f"Using explicit expected_patterns: {len(self.dataset_data['expected_patterns'])} patterns")
            return self.dataset_data['expected_patterns']
        
        # Extract from device relationships
        device_patterns = self._extract_patterns_from_devices()
        patterns.extend(device_patterns)
        
        # Extract from events (if available)
        if self.events:
            event_patterns = self._extract_patterns_from_events()
            patterns.extend(event_patterns)
        
        logger.info(f"Extracted {len(patterns)} ground truth patterns")
        return patterns
    
    def extract_synergies(self) -> list[dict[str, Any]]:
        """
        Extract expected synergies from dataset.
        
        Returns:
            List of ground truth synergy dictionaries
        """
        synergies = []
        
        # Try explicit ground truth first
        if self.dataset_data.get('expected_synergies'):
            logger.info(f"Using explicit expected_synergies: {len(self.dataset_data['expected_synergies'])} synergies")
            return self.dataset_data['expected_synergies']
        
        # Extract from device relationships
        device_synergies = self._extract_synergies_from_devices()
        synergies.extend(device_synergies)
        
        logger.info(f"Extracted {len(synergies)} ground truth synergies")
        return synergies
    
    def _extract_patterns_from_devices(self) -> list[dict[str, Any]]:
        """Extract patterns from device configuration"""
        patterns = []
        
        # Group devices by area
        devices_by_area: dict[str, list[dict]] = {}
        for device in self.devices:
            area_name = device.get('area', 'unknown')
            if area_name not in devices_by_area:
                devices_by_area[area_name] = []
            devices_by_area[area_name].append(device)
        
        # Find co-occurrence patterns (devices in same area)
        for area_name, area_devices in devices_by_area.items():
            if len(area_devices) < 2:
                continue
            
            # Create co-occurrence patterns for device pairs
            for i, device1 in enumerate(area_devices):
                for device2 in area_devices[i+1:]:
                    entity1 = device1.get('entity_id', '')
                    entity2 = device2.get('entity_id', '')
                    
                    if entity1 and entity2:
                        patterns.append({
                            'pattern_type': 'co_occurrence',
                            'device1': entity1,
                            'device2': entity2,
                            'area': area_name,
                            'confidence': 0.8,  # High confidence for same-area devices
                            'description': f"Co-occurrence: {entity1} and {entity2} in {area_name}"
                        })
        
        return patterns
    
    def _extract_patterns_from_events(self) -> list[dict[str, Any]]:
        """Extract patterns from event history"""
        patterns = []
        
        if not self.events:
            return patterns
        
        # Group events by entity
        events_by_entity: dict[str, list[dict]] = {}
        for event in self.events:
            entity_id = event.get('entity_id')
            if entity_id:
                if entity_id not in events_by_entity:
                    events_by_entity[entity_id] = []
                events_by_entity[entity_id].append(event)
        
        # Find time-of-day patterns (entities with consistent timing)
        for entity_id, entity_events in events_by_entity.items():
            if len(entity_events) < 3:
                continue
            
            # Group events by hour of day
            events_by_hour: dict[int, int] = {}
            for event in entity_events:
                timestamp = event.get('timestamp', '')
                if timestamp:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        hour = dt.hour
                        events_by_hour[hour] = events_by_hour.get(hour, 0) + 1
                    except Exception:
                        continue
            
            # If entity has events at same hour 3+ times, it's a time-of-day pattern
            for hour, count in events_by_hour.items():
                if count >= 3:
                    patterns.append({
                        'pattern_type': 'time_of_day',
                        'entity_id': entity_id,
                        'time': f"{hour:02d}:00",
                        'confidence': min(0.9, 0.7 + (count / 10) * 0.2),
                        'description': f"Time-of-day pattern: {entity_id} at {hour:02d}:00"
                    })
        
        return patterns
    
    def _extract_synergies_from_devices(self) -> list[dict[str, Any]]:
        """Extract synergies from device relationships"""
        synergies = []
        
        # Group devices by area
        devices_by_area: dict[str, list[dict]] = {}
        for device in self.devices:
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
                    motion_entity = motion.get('entity_id', '')
                    light_entity = light.get('entity_id', '')
                    
                    if motion_entity and light_entity:
                        synergies.append({
                            'trigger_entity': motion_entity,
                            'action_entity': light_entity,
                            'relationship_type': 'motion_to_light',
                            'confidence': 0.9,
                            'area': area_name,
                            'description': f"Motion sensor {motion_entity} → Light {light_entity} in {area_name}"
                        })
        
        # Find door → lock relationships
        for area_name, area_devices in devices_by_area.items():
            door_sensors = [
                d for d in area_devices
                if d.get('device_type') == 'binary_sensor' and
                   d.get('device_class') == 'door'
            ]
            locks = [
                d for d in area_devices
                if d.get('device_type') == 'lock'
            ]
            
            for door in door_sensors:
                for lock in locks:
                    door_entity = door.get('entity_id', '')
                    lock_entity = lock.get('entity_id', '')
                    
                    if door_entity and lock_entity:
                        synergies.append({
                            'trigger_entity': door_entity,
                            'action_entity': lock_entity,
                            'relationship_type': 'door_to_lock',
                            'confidence': 1.0,  # Security - high confidence
                            'area': area_name,
                            'description': f"Door sensor {door_entity} → Lock {lock_entity} in {area_name}"
                        })
        
        return synergies


def save_ground_truth(
    patterns: list[dict[str, Any]],
    synergies: list[dict[str, Any]],
    output_path: Path
):
    """
    Save ground truth patterns and synergies to JSON file.
    
    Args:
        patterns: List of ground truth patterns
        synergies: List of ground truth synergies
        output_path: Path to save JSON file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        'patterns': patterns,
        'synergies': synergies,
        'metadata': {
            'total_patterns': len(patterns),
            'total_synergies': len(synergies),
            'pattern_types': list(set(p.get('pattern_type', 'unknown') for p in patterns)),
            'relationship_types': list(set(s.get('relationship_type', 'unknown') for s in synergies))
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved ground truth to {output_path}: {len(patterns)} patterns, {len(synergies)} synergies")

