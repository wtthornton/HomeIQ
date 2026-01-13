"""
Temporal Synergy Detector Module

Phase 2.3: Time-of-day pattern integration for synergy discovery.

Uses time-of-day patterns to discover temporal synergies and enhance
synergy scoring with temporal context.
"""

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TemporalSynergyDetector:
    """
    Detects temporal synergies based on time-of-day patterns.
    
    Discovers synergies where devices are used together at specific times,
    and enhances existing synergies with temporal context.
    
    Attributes:
        min_temporal_confidence: Minimum confidence for temporal patterns
        time_window_minutes: Time window for temporal pattern matching
    """
    
    def __init__(
        self,
        min_temporal_confidence: float = 0.6,
        time_window_minutes: int = 30
    ):
        """
        Initialize temporal synergy detector.
        
        Args:
            min_temporal_confidence: Minimum confidence for temporal patterns
            time_window_minutes: Time window for matching temporal patterns
        """
        self.min_temporal_confidence = min_temporal_confidence
        self.time_window_minutes = time_window_minutes
    
    async def discover_temporal_patterns(
        self,
        time_patterns: list[dict[str, Any]],
        entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Discover temporal patterns in device interactions.
        
        Finds devices that are consistently used together at similar times.
        
        Args:
            time_patterns: List of time-of-day pattern dictionaries from TimeOfDayPatternDetector
            entities: List of entity dictionaries
            
        Returns:
            List of temporal synergy dictionaries
        """
        if not time_patterns:
            logger.debug("No time patterns provided for temporal discovery")
            return []
        
        logger.info(f"🔍 Discovering temporal patterns from {len(time_patterns)} time-of-day patterns...")
        
        synergies: list[dict[str, Any]] = []
        
        # Group patterns by time window (hour + 30-min window)
        patterns_by_time: dict[str, list[dict[str, Any]]] = defaultdict(list)
        
        for pattern in time_patterns:
            if pattern.get('confidence', 0.0) < self.min_temporal_confidence:
                continue
            
            hour = pattern.get('hour', 0)
            minute = pattern.get('minute', 0)
            
            # Round to 30-minute windows
            time_window = f"{hour:02d}:{(minute // 30) * 30:02d}"
            patterns_by_time[time_window].append(pattern)
        
        # Find devices that share similar time windows
        for time_window, patterns in patterns_by_time.items():
            if len(patterns) < 2:
                continue
            
            # Group by device_id
            device_patterns: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for pattern in patterns:
                device_id = pattern.get('device_id', '')
                if device_id:
                    device_patterns[device_id].append(pattern)
            
            # Find devices in same time window (potential synergies)
            devices_in_window = list(device_patterns.keys())
            if len(devices_in_window) < 2:
                continue
            
            # Create synergies for device pairs in same time window
            for i, device1 in enumerate(devices_in_window):
                for device2 in devices_in_window[i+1:]:
                    # Get patterns for both devices
                    device1_patterns = device_patterns[device1]
                    device2_patterns = device_patterns[device2]
                    
                    if not device1_patterns or not device2_patterns:
                        continue
                    
                    # Calculate average confidence
                    avg_confidence = (
                        sum(p.get('confidence', 0.0) for p in device1_patterns) / len(device1_patterns) +
                        sum(p.get('confidence', 0.0) for p in device2_patterns) / len(device2_patterns)
                    ) / 2.0
                    
                    if avg_confidence >= self.min_temporal_confidence:
                        # Find entity areas
                        entity1 = next((e for e in entities if e.get('entity_id') == device1 or 
                                       e.get('entity_id', '').startswith(device1)), None)
                        entity2 = next((e for e in entities if e.get('entity_id') == device2 or 
                                       e.get('entity_id', '').startswith(device2)), None)
                        
                        area1 = entity1.get('area_id') if entity1 else None
                        area2 = entity2.get('area_id') if entity2 else None
                        area = area1 if area1 == area2 else None
                        
                        synergy = {
                            'synergy_id': str(uuid.uuid4()),
                            'synergy_type': 'schedule_based',
                            'devices': [device1, device2],
                            'trigger_entity': device1,
                            'action_entity': device2,
                            'area': area,
                            'impact_score': 0.65 + (avg_confidence * 0.2),  # 0.65-0.85 range
                            'confidence': avg_confidence,
                            'complexity': 'low',
                            'rationale': f'Temporal pattern: Devices activate together at {time_window}',
                            'synergy_depth': 2,
                            'chain_devices': [device1, device2],
                            'context_metadata': {
                                'detection_method': 'temporal_pattern',
                                'time_window': time_window,
                                'temporal_confidence': avg_confidence
                            }
                        }
                        synergies.append(synergy)
        
        logger.info(f"✅ Discovered {len(synergies)} temporal synergies")
        return synergies
    
    async def suggest_time_based_synergies(
        self,
        time_patterns: list[dict[str, Any]],
        entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Suggest time-based synergies (e.g., lights at sunset, climate at bedtime).
        
        Args:
            time_patterns: List of time-of-day patterns
            entities: List of entity dictionaries
            
        Returns:
            List of suggested time-based synergy dictionaries
        """
        suggestions: list[dict[str, Any]] = []
        
        # Common time-based patterns
        time_based_patterns = {
            'sunset': {'hour': 18, 'minute': 0, 'description': 'Lights at sunset'},
            'sunrise': {'hour': 6, 'minute': 0, 'description': 'Lights at sunrise'},
            'bedtime': {'hour': 22, 'minute': 0, 'description': 'Climate/lights at bedtime'},
            'morning': {'hour': 7, 'minute': 0, 'description': 'Morning routine (lights/climate)'}
        }
        
        for pattern_name, pattern_info in time_based_patterns.items():
            # Find devices with patterns near this time
            target_hour = pattern_info['hour']
            target_minute = pattern_info['minute']
            
            matching_patterns = [
                p for p in time_patterns
                if abs(p.get('hour', 0) - target_hour) <= 1 and
                   abs(p.get('minute', 0) - target_minute) <= 30
            ]
            
            if len(matching_patterns) >= 2:
                # Group by domain
                lights = [p for p in matching_patterns if 'light' in p.get('device_id', '').lower()]
                climate = [p for p in matching_patterns if 'climate' in p.get('device_id', '').lower()]
                
                if lights and climate:
                    suggestions.append({
                        'pattern_type': f'time_based_{pattern_name}',
                        'description': f'{pattern_info["description"]}: {len(lights)} lights + {len(climate)} climate devices',
                        'suggested_synergy': {
                            'devices': [lights[0].get('device_id'), climate[0].get('device_id')],
                            'complexity': 'low',
                            'rationale': f'Time-based synergy: {pattern_info["description"]}'
                        }
                    })
        
        logger.debug(f"Suggested {len(suggestions)} time-based synergies")
        return suggestions
    
    def enhance_with_temporal_context(
        self,
        synergy: dict[str, Any],
        time_patterns: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Enhance synergy with temporal context information.
        
        Args:
            synergy: Synergy dictionary to enhance
            time_patterns: List of time-of-day patterns
            
        Returns:
            Enhanced synergy dictionary
        """
        devices = synergy.get('devices', synergy.get('device_ids', []))
        if not devices:
            return synergy
        
        # Find time patterns for devices in synergy
        device_time_patterns = {}
        for device in devices:
            device_patterns = [
                p for p in time_patterns
                if p.get('device_id') == device or device in p.get('device_id', '')
            ]
            if device_patterns:
                device_time_patterns[device] = device_patterns
        
        if not device_time_patterns:
            return synergy
        
        # Enhance context_metadata
        if 'context_metadata' not in synergy:
            synergy['context_metadata'] = {}
        
        synergy['context_metadata']['temporal_patterns'] = {
            device: {
                'hour': patterns[0].get('hour'),
                'minute': patterns[0].get('minute'),
                'confidence': patterns[0].get('confidence')
            }
            for device, patterns in device_time_patterns.items()
            if patterns
        }
        
        return synergy
    
    def _get_seasonal_adjustment(
        self,
        synergy: dict[str, Any],
        current_date: Optional[datetime] = None
    ) -> float:
        """
        Get seasonal adjustment factor for synergy scoring.
        
        Some synergies are more valuable in certain seasons (e.g., climate
        adjustments in summer/winter, lighting in winter).
        
        Args:
            synergy: Synergy dictionary
            current_date: Current date (default: now)
            
        Returns:
            Seasonal adjustment factor (0.9-1.1)
        """
        if current_date is None:
            current_date = datetime.now(timezone.utc)
        
        month = current_date.month
        
        # Seasonal patterns
        # Summer: June-August (months 6-8) - climate synergies more valuable
        # Winter: December-February (months 12, 1, 2) - lighting synergies more valuable
        # Spring/Fall: March-May, September-November - neutral
        
        synergy_type = synergy.get('synergy_type', '')
        devices = synergy.get('devices', [])
        
        # Check for climate-related synergies
        has_climate = any('climate' in str(d).lower() for d in devices)
        # Check for lighting-related synergies
        has_lighting = any('light' in str(d).lower() for d in devices)
        
        if has_climate:
            # Climate synergies more valuable in summer/winter
            if month in [6, 7, 8, 12, 1, 2]:
                return 1.1  # 10% boost
        elif has_lighting:
            # Lighting synergies more valuable in winter (shorter days)
            if month in [12, 1, 2]:
                return 1.1  # 10% boost
        
        return 1.0  # No adjustment
