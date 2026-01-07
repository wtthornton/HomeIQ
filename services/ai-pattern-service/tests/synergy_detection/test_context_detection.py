"""
Integration tests for ContextAwareDetector module.

Tests the context-aware detection functionality including:
- Weather + Climate synergies
- Weather + Cover synergies
- Energy + High-power device synergies
- Weather + Light synergies
"""

import pytest
import uuid

import sys
from pathlib import Path

# Add src/synergy_detection to path directly (avoid __init__.py import issues)
src_path = Path(__file__).parent.parent.parent / "src" / "synergy_detection"
sys.path.insert(0, str(src_path))

from context_detection import (
    ContextAwareDetector,
    MAX_CONTEXT_SYNERGIES,
    MAX_DEVICES_PER_CONTEXT_TYPE,
    HIGH_POWER_DOMAINS,
)


class TestContextAwareDetector:
    """Test ContextAwareDetector class."""

    @pytest.fixture
    def detector(self):
        """Create a ContextAwareDetector instance."""
        return ContextAwareDetector()

    @pytest.fixture
    def detector_with_area_lookup(self):
        """Create a detector with area lookup function."""
        def area_lookup(entity_ids, entities):
            for entity_id in entity_ids:
                for entity in entities:
                    if entity.get("entity_id") == entity_id:
                        return entity.get("area_id")
            return None
        
        return ContextAwareDetector(area_lookup_fn=area_lookup)

    @pytest.fixture
    def comprehensive_entities(self):
        """Create comprehensive entities for testing."""
        return [
            # Weather
            {"entity_id": "weather.forecast_home", "area_id": None},
            
            # Climate devices
            {"entity_id": "climate.living_room_ac", "area_id": "living_room"},
            {"entity_id": "climate.bedroom_ac", "area_id": "bedroom"},
            
            # Cover devices
            {"entity_id": "cover.living_room_blinds", "area_id": "living_room"},
            {"entity_id": "cover.bedroom_blinds", "area_id": "bedroom"},
            
            # Light devices
            {"entity_id": "light.living_room", "area_id": "living_room"},
            {"entity_id": "light.bedroom", "area_id": "bedroom"},
            {"entity_id": "light.kitchen", "area_id": "kitchen"},
            
            # Energy sensors
            {"entity_id": "sensor.energy_consumption", "area_id": None},
            {"entity_id": "sensor.power_usage", "area_id": None},
            
            # High-power devices
            {"entity_id": "climate.main_hvac", "area_id": None},
            {"entity_id": "water_heater.main", "area_id": "utility"},
        ]

    @pytest.fixture
    def minimal_entities(self):
        """Create minimal entities with only weather."""
        return [
            {"entity_id": "weather.forecast_home", "area_id": None},
            {"entity_id": "sensor.temperature", "area_id": "living_room"},
        ]

    def test_find_devices_by_prefix(self, detector, comprehensive_entities):
        """Test finding devices by prefix."""
        climate_devices = detector._find_devices_by_prefix(comprehensive_entities, "climate.")
        assert len(climate_devices) == 3
        assert "climate.living_room_ac" in climate_devices
        
        cover_devices = detector._find_devices_by_prefix(comprehensive_entities, "cover.")
        assert len(cover_devices) == 2

    def test_find_weather_entities(self, detector, comprehensive_entities):
        """Test finding weather entities."""
        weather = detector._find_weather_entities(comprehensive_entities)
        assert len(weather) == 1
        assert weather[0]["entity_id"] == "weather.forecast_home"

    def test_find_energy_sensors(self, detector, comprehensive_entities):
        """Test finding energy sensors."""
        energy = detector._find_energy_sensors(comprehensive_entities)
        assert len(energy) == 2
        assert any("energy" in e["entity_id"] for e in energy)
        assert any("power" in e["entity_id"] for e in energy)

    def test_find_high_power_devices(self, detector, comprehensive_entities):
        """Test finding high-power devices."""
        high_power = detector._find_high_power_devices(comprehensive_entities)
        
        # Should include climate and water_heater
        assert any("climate" in d for d in high_power)
        assert any("water_heater" in d for d in high_power)

    def test_get_area_with_lookup(self, detector_with_area_lookup, comprehensive_entities):
        """Test area lookup with function."""
        area = detector_with_area_lookup._get_area(
            ["climate.living_room_ac"],
            comprehensive_entities
        )
        assert area == "living_room"

    def test_get_area_without_lookup(self, detector, comprehensive_entities):
        """Test area lookup without function (default implementation)."""
        area = detector._get_area(
            ["climate.living_room_ac"],
            comprehensive_entities
        )
        assert area == "living_room"

    def test_create_weather_climate_synergy(self, detector):
        """Test creating weather + climate synergy."""
        synergy = detector._create_weather_climate_synergy(
            "weather.forecast",
            "climate.living_room",
            "living_room"
        )
        
        assert synergy["synergy_type"] == "context_aware"
        assert synergy["context_metadata"]["context_type"] == "weather_climate"
        assert "energy_savings" in synergy["context_metadata"]["benefits"]
        assert synergy["impact_score"] == 0.75
        assert synergy["complexity"] == "medium"

    def test_create_weather_cover_synergy(self, detector):
        """Test creating weather + cover synergy."""
        synergy = detector._create_weather_cover_synergy(
            "weather.forecast",
            "cover.blinds",
            "living_room"
        )
        
        assert synergy["synergy_type"] == "context_aware"
        assert synergy["context_metadata"]["context_type"] == "weather_cover"
        assert synergy["impact_score"] == 0.70
        assert synergy["complexity"] == "low"

    def test_create_energy_scheduling_synergy(self, detector):
        """Test creating energy scheduling synergy."""
        synergy = detector._create_energy_scheduling_synergy(
            "sensor.energy_price",
            "climate.hvac",
            None
        )
        
        assert synergy["synergy_type"] == "context_aware"
        assert synergy["context_metadata"]["context_type"] == "energy_scheduling"
        assert "cost_reduction" in synergy["context_metadata"]["benefits"]
        assert synergy["impact_score"] == 0.80

    def test_create_weather_lighting_synergy(self, detector):
        """Test creating weather + lighting synergy."""
        synergy = detector._create_weather_lighting_synergy(
            "weather.forecast",
            "light.living_room",
            "living_room"
        )
        
        assert synergy["synergy_type"] == "context_aware"
        assert synergy["context_metadata"]["context_type"] == "weather_lighting"
        assert "comfort" in synergy["context_metadata"]["benefits"]
        assert synergy["impact_score"] == 0.65

    @pytest.mark.asyncio
    async def test_detect_context_aware_synergies(self, detector, comprehensive_entities):
        """Test detecting all context-aware synergies."""
        synergies = await detector.detect_context_aware_synergies(comprehensive_entities)
        
        # Should find multiple synergies
        assert len(synergies) >= 1
        
        # Check variety of context types
        context_types = set(s["context_metadata"]["context_type"] for s in synergies)
        
        # Should have weather_climate (weather + climate devices present)
        assert "weather_climate" in context_types
        
        # Should have weather_cover (weather + cover devices present)
        assert "weather_cover" in context_types
        
        # All should be context_aware type
        for synergy in synergies:
            assert synergy["synergy_type"] == "context_aware"
            assert "benefits" in synergy["context_metadata"]

    @pytest.mark.asyncio
    async def test_detect_context_aware_synergies_minimal(self, detector, minimal_entities):
        """Test with minimal entities (only weather)."""
        synergies = await detector.detect_context_aware_synergies(minimal_entities)
        
        # Should find no synergies (no actionable devices)
        assert len(synergies) == 0

    @pytest.mark.asyncio
    async def test_detect_context_aware_synergies_max_limit(self, detector):
        """Test that detection respects max synergies limit."""
        # Create many entities to trigger limit
        entities = [{"entity_id": "weather.forecast", "area_id": None}]
        
        # Add many climate devices
        for i in range(50):
            entities.append({
                "entity_id": f"climate.ac_{i}",
                "area_id": f"room_{i}"
            })
        
        # Add many cover devices
        for i in range(50):
            entities.append({
                "entity_id": f"cover.blinds_{i}",
                "area_id": f"room_{i}"
            })
        
        synergies = await detector.detect_context_aware_synergies(entities)
        
        assert len(synergies) <= MAX_CONTEXT_SYNERGIES

    @pytest.mark.asyncio
    async def test_detect_context_aware_synergies_per_type_limit(self, detector):
        """Test that detection limits devices per context type."""
        entities = [
            {"entity_id": "weather.forecast", "area_id": None},
        ]
        
        # Add many climate devices
        for i in range(20):
            entities.append({
                "entity_id": f"climate.ac_{i}",
                "area_id": f"room_{i}"
            })
        
        synergies = await detector.detect_context_aware_synergies(entities)
        
        # Count weather_climate synergies
        weather_climate = [
            s for s in synergies
            if s["context_metadata"]["context_type"] == "weather_climate"
        ]
        
        # Should be limited to MAX_DEVICES_PER_CONTEXT_TYPE
        assert len(weather_climate) <= MAX_DEVICES_PER_CONTEXT_TYPE


class TestContextAwareDetectorConstants:
    """Test configuration constants."""

    def test_high_power_domains(self):
        """Test high-power domains are correct."""
        assert "climate" in HIGH_POWER_DOMAINS
        assert "water_heater" in HIGH_POWER_DOMAINS
        assert "ev_charger" in HIGH_POWER_DOMAINS
        assert "dryer" in HIGH_POWER_DOMAINS
        assert "washer" in HIGH_POWER_DOMAINS
        assert "dishwasher" in HIGH_POWER_DOMAINS
        
        # Should not include low-power devices
        assert "light" not in HIGH_POWER_DOMAINS
        assert "switch" not in HIGH_POWER_DOMAINS

    def test_max_context_synergies(self):
        """Test max synergies limit."""
        assert MAX_CONTEXT_SYNERGIES == 30

    def test_max_devices_per_type(self):
        """Test max devices per context type."""
        assert MAX_DEVICES_PER_CONTEXT_TYPE == 5
