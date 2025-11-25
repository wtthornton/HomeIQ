"""
Home Type Profiler

Extract home profile features from synthetic homes or production data.
Features include device composition, event patterns, spatial layout, and behavior patterns.
"""

import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class HomeTypeProfiler:
    """
    Extract home profile features from synthetic homes.
    
    Features:
    - Device composition (types, categories, counts, ratios)
    - Event patterns (frequencies, distributions, peak hours)
    - Spatial layout (areas, indoor/outdoor, distribution)
    - Behavior patterns (aggregated statistics)
    """
    
    def __init__(self):
        """Initialize home type profiler."""
        logger.info("HomeTypeProfiler initialized")
    
    async def profile_home(
        self,
        home_id: str,
        devices: list[dict[str, Any]],
        events: list[dict[str, Any]],
        areas: list[dict[str, Any]] | None = None,
        patterns: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """
        Create comprehensive home profile.
        
        Args:
            home_id: Home identifier
            devices: List of device dictionaries
            events: List of event dictionaries
            areas: Optional list of area dictionaries
            patterns: Optional list of detected patterns
        
        Returns:
            Dictionary with profile sections:
            {
                'device_composition': {...},
                'event_patterns': {...},
                'spatial_layout': {...},
                'behavior_patterns': {...}
            }
        """
        logger.info(f"Profiling home: {home_id} ({len(devices)} devices, {len(events)} events)")
        
        profile = {
            'home_id': home_id,
            'device_composition': self._extract_device_composition(devices),
            'event_patterns': self._extract_event_patterns(devices, events),
            'spatial_layout': self._extract_spatial_layout(devices, areas),
            'behavior_patterns': self._extract_behavior_patterns(events, patterns),
            'profiled_at': datetime.now(timezone.utc).isoformat()
        }
        
        return profile
    
    def _extract_device_composition(
        self,
        devices: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Extract device composition features.
        
        Args:
            devices: List of device dictionaries
        
        Returns:
            Device composition dictionary
        """
        if not devices:
            return {
                'total_devices': 0,
                'by_type': {},
                'by_category': {},
                'ratios': {}
            }
        
        # Count by device type
        device_types = Counter(d.get('device_type', 'unknown') for d in devices)
        
        # Count by category
        categories = Counter(d.get('category', 'unknown') for d in devices)
        
        # Calculate ratios
        total = len(devices)
        security_count = categories.get('security', 0)
        climate_count = categories.get('climate', 0)
        lighting_count = categories.get('lighting', 0)
        
        ratios = {
            'security_ratio': security_count / total if total > 0 else 0.0,
            'climate_ratio': climate_count / total if total > 0 else 0.0,
            'lighting_ratio': lighting_count / total if total > 0 else 0.0,
            'appliance_ratio': categories.get('appliances', 0) / total if total > 0 else 0.0,
            'monitoring_ratio': categories.get('monitoring', 0) / total if total > 0 else 0.0
        }
        
        return {
            'total_devices': total,
            'by_type': dict(device_types),
            'by_category': dict(categories),
            'ratios': ratios
        }
    
    def _extract_event_patterns(
        self,
        devices: list[dict[str, Any]],
        events: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Extract event pattern features.
        
        Args:
            devices: List of device dictionaries
            events: List of event dictionaries
        
        Returns:
            Event patterns dictionary
        """
        if not events:
            return {
                'total_events': 0,
                'events_per_day': 0.0,
                'by_device_type': {},
                'peak_hours': []
            }
        
        # Count events by device type
        device_type_map = {d.get('entity_id'): d.get('device_type', 'unknown') for d in devices}
        events_by_type = Counter()
        
        for event in events:
            entity_id = event.get('entity_id', '')
            device_type = device_type_map.get(entity_id, 'unknown')
            events_by_type[device_type] += 1
        
        # Calculate events per day (assuming events span multiple days)
        if events:
            first_time = datetime.fromisoformat(events[0]['timestamp'].replace('Z', '+00:00'))
            last_time = datetime.fromisoformat(events[-1]['timestamp'].replace('Z', '+00:00'))
            days = max(1, (last_time - first_time).days + 1)
            events_per_day = len(events) / days
        else:
            events_per_day = 0.0
        
        # Find peak hours (simplified - count events by hour)
        hour_counts = Counter()
        for event in events:
            try:
                timestamp = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                hour_counts[timestamp.hour] += 1
            except (ValueError, KeyError):
                continue
        
        # Top 3 peak hours
        peak_hours = [hour for hour, _ in hour_counts.most_common(3)]
        
        return {
            'total_events': len(events),
            'events_per_day': events_per_day,
            'by_device_type': dict(events_by_type),
            'peak_hours': peak_hours
        }
    
    def _extract_spatial_layout(
        self,
        devices: list[dict[str, Any]],
        areas: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """
        Extract spatial layout features.
        
        Args:
            devices: List of device dictionaries
            areas: Optional list of area dictionaries
        
        Returns:
            Spatial layout dictionary
        """
        if not devices:
            return {
                'area_count': 0,
                'indoor_ratio': 0.0,
                'devices_per_area': 0.0,
                'area_distribution': {}
            }
        
        # Count devices by area
        devices_by_area = Counter(d.get('area', 'unknown') for d in devices)
        
        # Calculate indoor/outdoor ratio if areas provided
        if areas:
            area_types = {area.get('name'): area.get('type', 'indoor') for area in areas}
            indoor_count = sum(
                count for area_name, count in devices_by_area.items()
                if area_types.get(area_name, 'indoor') == 'indoor'
            )
            total = sum(devices_by_area.values())
            indoor_ratio = indoor_count / total if total > 0 else 0.0
            area_count = len(areas)
        else:
            indoor_ratio = 0.0
            area_count = len(devices_by_area)
        
        # Average devices per area
        devices_per_area = len(devices) / area_count if area_count > 0 else 0.0
        
        return {
            'area_count': area_count,
            'indoor_ratio': indoor_ratio,
            'devices_per_area': devices_per_area,
            'area_distribution': dict(devices_by_area)
        }
    
    def _extract_behavior_patterns(
        self,
        events: list[dict[str, Any]],
        patterns: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """
        Extract behavior pattern features.
        
        Args:
            events: List of event dictionaries
            patterns: Optional list of detected patterns
        
        Returns:
            Behavior patterns dictionary
        """
        pattern_count = len(patterns) if patterns else 0
        
        # Calculate average confidence if patterns available
        if patterns:
            confidences = [p.get('confidence', 0.0) for p in patterns if 'confidence' in p]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        else:
            avg_confidence = 0.0
        
        # Calculate event diversity (unique entity IDs)
        unique_entities = len(set(e.get('entity_id', '') for e in events))
        total_events = len(events)
        diversity_ratio = unique_entities / total_events if total_events > 0 else 0.0
        
        return {
            'pattern_count': pattern_count,
            'avg_pattern_confidence': avg_confidence,
            'event_diversity': unique_entities,
            'diversity_ratio': diversity_ratio
        }

