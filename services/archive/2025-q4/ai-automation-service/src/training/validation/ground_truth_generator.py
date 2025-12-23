"""
Ground Truth Generator

Auto-generate expected patterns from synthetic homes for validation.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PatternType(str, Enum):
    """Types of automation patterns (HA 2024 standard)."""
    TIME_OF_DAY = "time_of_day"
    CO_OCCURRENCE = "co_occurrence"
    WEATHER_DRIVEN = "weather_driven"
    ENERGY_AWARE = "energy_aware"
    PRESENCE_AWARE = "presence_aware"
    MULTI_DEVICE_SYNERGY = "multi_device_synergy"


class ExpectedPattern(BaseModel):
    """Expected automation pattern in synthetic home."""
    pattern_id: str
    pattern_type: PatternType
    description: str
    devices: list[str]  # All involved entity IDs
    trigger_device: str | None = None
    action_devices: list[str]
    conditions: dict[str, Any] = Field(default_factory=dict)
    frequency: str  # "daily", "hourly", "weekly", "multiple_daily"
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)


class GroundTruth(BaseModel):
    """Ground truth for a synthetic home."""
    home_id: str
    home_type: str
    expected_patterns: list[ExpectedPattern]
    metadata: dict[str, Any] = Field(default_factory=dict)
    generated_at: str


class GroundTruthGenerator:
    """
    Generate ground truth annotations from synthetic homes.
    
    Auto-generates expected patterns based on:
    - Device types and areas
    - Time-of-day patterns (lights at sunset)
    - Motion-triggered automations
    - Climate automations
    - Multi-device synergies
    """
    
    def __init__(self):
        """Initialize ground truth generator."""
        logger.info("GroundTruthGenerator initialized")
    
    def generate_ground_truth(
        self,
        home_data: dict[str, Any],
        devices: list[dict[str, Any]],
        areas: list[dict[str, Any]]
    ) -> GroundTruth:
        """
        Generate ground truth annotations from synthetic home.
        
        Args:
            home_data: Synthetic home configuration
            devices: Generated devices
            areas: Generated areas
        
        Returns:
            Ground truth with expected patterns
        """
        home_id = home_data.get('home_id', f"home_{hash(str(home_data)) % 10000:04d}")
        home_type = home_data.get('home_type', 'single_family_house')
        
        expected_patterns = []
        
        # Pattern 1: Time-of-day patterns (lights at sunset)
        expected_patterns.extend(
            self._generate_time_of_day_patterns(devices, areas)
        )
        
        # Pattern 2: Motion-triggered lights (co-occurrence)
        expected_patterns.extend(
            self._generate_motion_light_patterns(devices, areas)
        )
        
        # Pattern 3: Climate automations
        expected_patterns.extend(
            self._generate_climate_patterns(devices, areas)
        )
        
        # Pattern 4: Multi-device synergies
        expected_patterns.extend(
            self._generate_synergy_patterns(devices, areas)
        )
        
        logger.info(f"✅ Generated ground truth with {len(expected_patterns)} expected patterns")
        
        return GroundTruth(
            home_id=home_id,
            home_type=home_type,
            expected_patterns=expected_patterns,
            metadata={
                'areas': len(areas),
                'devices': len(devices),
                'device_breakdown': self._get_device_breakdown(devices)
            },
            generated_at=datetime.now().isoformat()
        )
    
    def _generate_time_of_day_patterns(
        self,
        devices: list[dict[str, Any]],
        areas: list[dict[str, Any]]
    ) -> list[ExpectedPattern]:
        """Generate time-of-day patterns (lights at sunset/sunrise)."""
        patterns = []
        
        # Get all lights
        light_devices = [d for d in devices if d.get('device_type') == 'light']
        
        if not light_devices:
            return patterns
        
        # Pattern: All lights turn on at sunset
        patterns.append(ExpectedPattern(
            pattern_id="tod_all_lights_sunset",
            pattern_type=PatternType.TIME_OF_DAY,
            description="All lights turn on at sunset",
            devices=[d['entity_id'] for d in light_devices],
            trigger_device=None,
            action_devices=[d['entity_id'] for d in light_devices],
            conditions={"time": "sunset", "days": "all"},
            frequency="daily",
            confidence=0.9
        ))
        
        # Pattern: Living area lights at sunset (higher confidence)
        living_areas = ['Living Room', 'Family Room', 'Great Room', 'Kitchen']
        living_lights = [d for d in light_devices if d.get('area') in living_areas]
        if living_lights:
            patterns.append(ExpectedPattern(
                pattern_id="tod_living_lights_sunset",
                pattern_type=PatternType.TIME_OF_DAY,
                description="Living area lights turn on at sunset",
                devices=[d['entity_id'] for d in living_lights],
                trigger_device=None,
                action_devices=[d['entity_id'] for d in living_lights],
                conditions={"time": "sunset", "days": "all", "area": "living"},
                frequency="daily",
                confidence=0.95
            ))
        
        return patterns
    
    def _generate_motion_light_patterns(
        self,
        devices: list[dict[str, Any]],
        areas: list[dict[str, Any]]
    ) -> list[ExpectedPattern]:
        """Generate motion-triggered light patterns."""
        patterns = []
        
        # Get motion sensors and lights
        motion_sensors = [d for d in devices if d.get('device_class') == 'motion']
        light_devices = [d for d in devices if d.get('device_type') == 'light']
        
        if not motion_sensors or not light_devices:
            return patterns
        
        # For each motion sensor, find lights in same area
        for sensor in motion_sensors:
            area = sensor.get('area')
            if not area:
                continue
            
            # Find lights in same area
            area_lights = [d for d in light_devices if d.get('area') == area]
            if not area_lights:
                continue
            
            pattern_id = f"motion_{area.lower().replace(' ', '_')}_lights"
            patterns.append(ExpectedPattern(
                pattern_id=pattern_id,
                pattern_type=PatternType.CO_OCCURRENCE,
                description=f"Motion in {area} triggers lights",
                devices=[sensor['entity_id']] + [l['entity_id'] for l in area_lights],
                trigger_device=sensor['entity_id'],
                action_devices=[l['entity_id'] for l in area_lights],
                conditions={"motion": "detected", "area": area},
                frequency="multiple_daily",
                confidence=0.85
            ))
        
        return patterns
    
    def _generate_climate_patterns(
        self,
        devices: list[dict[str, Any]],
        areas: list[dict[str, Any]]
    ) -> list[ExpectedPattern]:
        """Generate climate automation patterns."""
        patterns = []
        
        # Get climate devices and temperature sensors
        climate_devices = [d for d in devices if d.get('device_type') == 'climate']
        temp_sensors = [d for d in devices if d.get('device_class') == 'temperature']
        
        if not climate_devices:
            return patterns
        
        # Pattern: Thermostat adjusts based on time of day
        for climate in climate_devices:
            patterns.append(ExpectedPattern(
                pattern_id=f"climate_{climate['area'].lower().replace(' ', '_')}_schedule",
                pattern_type=PatternType.TIME_OF_DAY,
                description=f"Thermostat in {climate['area']} follows daily schedule",
                devices=[climate['entity_id']],
                trigger_device=None,
                action_devices=[climate['entity_id']],
                conditions={"time": "schedule", "temperature": "setpoint"},
                frequency="daily",
                confidence=0.8
            ))
        
        return patterns
    
    def _generate_synergy_patterns(
        self,
        devices: list[dict[str, Any]],
        areas: list[dict[str, Any]]
    ) -> list[ExpectedPattern]:
        """Generate multi-device synergy patterns."""
        patterns = []
        
        # Get door sensors and lights
        door_sensors = [d for d in devices if d.get('device_class') == 'door']
        light_devices = [d for d in devices if d.get('device_type') == 'light']
        
        # Pattern: Door opens + lights turn on (if after sunset)
        for door in door_sensors:
            area = door.get('area')
            if not area:
                continue
            
            nearby_lights = [d for d in light_devices if d.get('area') == area]
            if nearby_lights:
                patterns.append(ExpectedPattern(
                    pattern_id=f"synergy_{area.lower().replace(' ', '_')}_door_lights",
                    pattern_type=PatternType.MULTI_DEVICE_SYNERGY,
                    description=f"Door opens in {area}, lights turn on",
                    devices=[door['entity_id']] + [l['entity_id'] for l in nearby_lights],
                    trigger_device=door['entity_id'],
                    action_devices=[l['entity_id'] for l in nearby_lights],
                    conditions={"door": "opened", "time": "after_sunset"},
                    frequency="multiple_daily",
                    confidence=0.75
                ))
        
        return patterns
    
    def _get_device_breakdown(
        self,
        devices: list[dict[str, Any]]
    ) -> dict[str, int]:
        """Get device count breakdown by type."""
        breakdown: dict[str, int] = {}
        for device in devices:
            device_type = device.get('device_type', 'unknown')
            breakdown[device_type] = breakdown.get(device_type, 0) + 1
        return breakdown

