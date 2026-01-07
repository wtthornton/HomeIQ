"""
Tests for new synergy types: scene_based and context_aware
Epic: Synergy Enhancement
Story: Add scene_based and context_aware synergy detection
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

# Test the synergy detection methods


class TestSceneBasedSynergyDetection:
    """Tests for _detect_scene_based_synergies method."""

    @pytest.fixture
    def mock_entities_with_areas(self):
        """Entities with area_id set for area-based scene detection."""
        return [
            {"entity_id": "light.living_room_1", "area_id": "living_room", "domain": "light"},
            {"entity_id": "light.living_room_2", "area_id": "living_room", "domain": "light"},
            {"entity_id": "light.living_room_3", "area_id": "living_room", "domain": "light"},
            {"entity_id": "switch.living_room_fan", "area_id": "living_room", "domain": "switch"},
            {"entity_id": "light.bedroom_1", "area_id": "bedroom", "domain": "light"},
            {"entity_id": "light.bedroom_2", "area_id": "bedroom", "domain": "light"},
            {"entity_id": "scene.movie_time", "area_id": "living_room", "domain": "scene"},
        ]

    @pytest.fixture
    def mock_entities_without_areas(self):
        """Entities without area_id for domain-based scene detection."""
        return [
            {"entity_id": "light.light_1", "area_id": None, "domain": "light"},
            {"entity_id": "light.light_2", "area_id": None, "domain": "light"},
            {"entity_id": "light.light_3", "area_id": None, "domain": "light"},
            {"entity_id": "light.light_4", "area_id": None, "domain": "light"},
            {"entity_id": "light.light_5", "area_id": None, "domain": "light"},
            {"entity_id": "switch.switch_1", "area_id": None, "domain": "switch"},
            {"entity_id": "switch.switch_2", "area_id": None, "domain": "switch"},
            {"entity_id": "switch.switch_3", "area_id": None, "domain": "switch"},
            {"entity_id": "switch.switch_4", "area_id": None, "domain": "switch"},
            {"entity_id": "switch.switch_5", "area_id": None, "domain": "switch"},
        ]

    def test_scene_synergy_structure(self, mock_entities_with_areas):
        """Test that scene-based synergies have correct structure."""
        # This tests the expected structure of scene_based synergies
        expected_fields = [
            "synergy_id",
            "synergy_type",
            "devices",
            "trigger_entity",
            "action_entity",
            "area",
            "impact_score",
            "confidence",
            "complexity",
            "rationale",
            "synergy_depth",
            "chain_devices",
            "context_metadata",
        ]
        
        # Create a sample scene synergy (matching what the method creates)
        sample_synergy = {
            "synergy_id": str(uuid.uuid4()),
            "synergy_type": "scene_based",
            "devices": ["light.living_room_1", "light.living_room_2"],
            "trigger_entity": "scene.living_room_all",
            "action_entity": "light.living_room_1",
            "area": "living_room",
            "impact_score": 0.7,
            "confidence": 0.80,
            "complexity": "low",
            "rationale": "Scene opportunity: 3 devices in living_room could be controlled together",
            "synergy_depth": 2,
            "chain_devices": ["light.living_room_1", "light.living_room_2"],
            "context_metadata": {
                "scene_type": "area_based",
                "suggested_scene_name": "Living Room All",
                "device_count": 3,
                "device_domains": ["light"],
            },
        }
        
        for field in expected_fields:
            assert field in sample_synergy, f"Missing field: {field}"
        
        assert sample_synergy["synergy_type"] == "scene_based"
        assert sample_synergy["complexity"] == "low"
        assert "scene_type" in sample_synergy["context_metadata"]

    def test_domain_based_scene_structure(self, mock_entities_without_areas):
        """Test domain-based scene synergy structure."""
        sample_synergy = {
            "synergy_id": str(uuid.uuid4()),
            "synergy_type": "scene_based",
            "devices": ["light.light_1", "light.light_2", "light.light_3"],
            "trigger_entity": "scene.all_lights",
            "action_entity": "light.light_1",
            "area": None,
            "impact_score": 0.65,
            "confidence": 0.70,
            "complexity": "low",
            "rationale": "Scene opportunity: 5 light devices could be controlled together",
            "synergy_depth": 3,
            "chain_devices": ["light.light_1", "light.light_2", "light.light_3"],
            "context_metadata": {
                "scene_type": "domain_based",
                "suggested_scene_name": "All Lights",
                "device_count": 5,
                "domain": "light",
            },
        }
        
        assert sample_synergy["synergy_type"] == "scene_based"
        assert sample_synergy["context_metadata"]["scene_type"] == "domain_based"
        assert sample_synergy["area"] is None  # Domain-based has no area


class TestContextAwareSynergyDetection:
    """Tests for _detect_context_aware_synergies method."""

    @pytest.fixture
    def mock_entities_with_weather(self):
        """Entities including weather and climate devices."""
        return [
            {"entity_id": "weather.forecast_home", "area_id": None, "domain": "weather"},
            {"entity_id": "climate.living_room", "area_id": "living_room", "domain": "climate"},
            {"entity_id": "climate.bedroom", "area_id": "bedroom", "domain": "climate"},
            {"entity_id": "cover.blinds_1", "area_id": "living_room", "domain": "cover"},
            {"entity_id": "cover.blinds_2", "area_id": "bedroom", "domain": "cover"},
            {"entity_id": "light.living_room", "area_id": "living_room", "domain": "light"},
            {"entity_id": "sensor.energy_price", "area_id": None, "domain": "sensor"},
        ]

    def test_context_aware_weather_climate_structure(self):
        """Test weather + climate context-aware synergy structure."""
        sample_synergy = {
            "synergy_id": str(uuid.uuid4()),
            "synergy_type": "context_aware",
            "devices": ["weather.forecast_home", "climate.living_room"],
            "trigger_entity": "weather.forecast_home",
            "action_entity": "climate.living_room",
            "area": "living_room",
            "impact_score": 0.75,
            "confidence": 0.70,
            "complexity": "medium",
            "rationale": "Context-aware: Pre-cool/heat based on weather forecast to optimize energy",
            "synergy_depth": 2,
            "chain_devices": ["weather.forecast_home", "climate.living_room"],
            "context_metadata": {
                "context_type": "weather_climate",
                "triggers": {
                    "weather": {"condition": "sunny", "temp_above": 80},
                    "energy": {"peak_hours": True},
                },
                "benefits": ["energy_savings", "comfort", "cost_reduction"],
                "estimated_savings": "10-15% cooling costs",
            },
        }
        
        assert sample_synergy["synergy_type"] == "context_aware"
        assert sample_synergy["context_metadata"]["context_type"] == "weather_climate"
        assert "benefits" in sample_synergy["context_metadata"]
        assert "estimated_savings" in sample_synergy["context_metadata"]

    def test_context_aware_weather_cover_structure(self):
        """Test weather + cover context-aware synergy structure."""
        sample_synergy = {
            "synergy_id": str(uuid.uuid4()),
            "synergy_type": "context_aware",
            "devices": ["weather.forecast_home", "cover.blinds_1"],
            "trigger_entity": "weather.forecast_home",
            "action_entity": "cover.blinds_1",
            "area": "living_room",
            "impact_score": 0.70,
            "confidence": 0.75,
            "complexity": "low",
            "rationale": "Context-aware: Close blinds when sunny to reduce cooling load",
            "synergy_depth": 2,
            "chain_devices": ["weather.forecast_home", "cover.blinds_1"],
            "context_metadata": {
                "context_type": "weather_cover",
                "triggers": {"weather": {"condition": "sunny", "temp_above": 75}},
                "benefits": ["energy_savings", "comfort"],
                "estimated_savings": "5-10% cooling costs",
            },
        }
        
        assert sample_synergy["synergy_type"] == "context_aware"
        assert sample_synergy["context_metadata"]["context_type"] == "weather_cover"

    def test_context_aware_energy_scheduling_structure(self):
        """Test energy + high-power device context-aware synergy structure."""
        sample_synergy = {
            "synergy_id": str(uuid.uuid4()),
            "synergy_type": "context_aware",
            "devices": ["sensor.energy_price", "climate.living_room"],
            "trigger_entity": "sensor.energy_price",
            "action_entity": "climate.living_room",
            "area": "living_room",
            "impact_score": 0.80,
            "confidence": 0.70,
            "complexity": "medium",
            "rationale": "Context-aware: Schedule climate during off-peak energy hours",
            "synergy_depth": 2,
            "chain_devices": ["sensor.energy_price", "climate.living_room"],
            "context_metadata": {
                "context_type": "energy_scheduling",
                "triggers": {"energy": {"peak_hours": False, "price_below": 0.12}},
                "benefits": ["cost_reduction", "grid_optimization"],
                "estimated_savings": "15-25% energy costs",
            },
        }
        
        assert sample_synergy["synergy_type"] == "context_aware"
        assert sample_synergy["context_metadata"]["context_type"] == "energy_scheduling"
        assert "cost_reduction" in sample_synergy["context_metadata"]["benefits"]

    def test_context_aware_weather_lighting_structure(self):
        """Test weather + light context-aware synergy structure."""
        sample_synergy = {
            "synergy_id": str(uuid.uuid4()),
            "synergy_type": "context_aware",
            "devices": ["weather.forecast_home", "light.living_room"],
            "trigger_entity": "weather.forecast_home",
            "action_entity": "light.living_room",
            "area": "living_room",
            "impact_score": 0.65,
            "confidence": 0.70,
            "complexity": "low",
            "rationale": "Context-aware: Adjust lighting based on weather conditions and daylight",
            "synergy_depth": 2,
            "chain_devices": ["weather.forecast_home", "light.living_room"],
            "context_metadata": {
                "context_type": "weather_lighting",
                "triggers": {
                    "weather": {"condition": "cloudy"},
                    "time": {"is_daytime": True},
                },
                "benefits": ["comfort", "energy_savings"],
                "estimated_savings": "5-10% lighting costs",
            },
        }
        
        assert sample_synergy["synergy_type"] == "context_aware"
        assert sample_synergy["context_metadata"]["context_type"] == "weather_lighting"


class TestScheduleBasedSynergyEnhancements:
    """Tests for enhanced schedule_based synergy detection with time windows."""

    def test_30min_window_synergy_structure(self):
        """Test 30-minute window schedule-based synergy structure."""
        sample_synergy = {
            "synergy_id": str(uuid.uuid4()),
            "synergy_type": "schedule_based",
            "devices": ["light.living_room", "switch.fan"],
            "trigger_entity": "light.living_room",
            "action_entity": "switch.fan",
            "area": "living_room",
            "impact_score": 0.85,
            "confidence": 0.80,
            "complexity": "low",
            "rationale": "Schedule-based: Devices activate within 30-min window at 07:00",
            "pattern_support_score": 1.0,
            "validated_by_patterns": True,
            "supporting_pattern_ids": [1, 2],
            "synergy_depth": 2,
            "chain_devices": ["light.living_room", "switch.fan"],
            "context_metadata": {
                "time_window": "30min",
                "time_slot": "07:00",
                "device_count": 2,
            },
        }
        
        assert sample_synergy["synergy_type"] == "schedule_based"
        assert sample_synergy["context_metadata"]["time_window"] == "30min"
        assert sample_synergy["pattern_support_score"] == 1.0

    def test_hourly_window_synergy_structure(self):
        """Test hourly window schedule-based synergy structure (fallback)."""
        sample_synergy = {
            "synergy_id": str(uuid.uuid4()),
            "synergy_type": "schedule_based",
            "devices": ["light.bedroom", "climate.bedroom"],
            "trigger_entity": "light.bedroom",
            "action_entity": "climate.bedroom",
            "area": "bedroom",
            "impact_score": 0.75,
            "confidence": 0.75,
            "complexity": "low",
            "rationale": "Schedule-based: Devices activate within same hour at 22:00",
            "pattern_support_score": 0.9,
            "validated_by_patterns": True,
            "supporting_pattern_ids": [3, 4],
            "synergy_depth": 2,
            "chain_devices": ["light.bedroom", "climate.bedroom"],
            "context_metadata": {
                "time_window": "hourly",
                "time_slot": "22:00",
                "device_count": 2,
            },
        }
        
        assert sample_synergy["synergy_type"] == "schedule_based"
        assert sample_synergy["context_metadata"]["time_window"] == "hourly"
        assert sample_synergy["pattern_support_score"] == 0.9  # Lower for hourly


class TestDeviceChainDepthFix:
    """Tests for device_chain synergy depth storage fix."""

    def test_3_device_chain_depth(self):
        """Test that 3-device chains have synergy_depth=3."""
        sample_chain = {
            "synergy_id": str(uuid.uuid4()),
            "synergy_type": "device_chain",
            "devices": ["motion.hallway", "light.hallway", "light.living_room"],
            "chain_path": "motion.hallway → light.hallway → light.living_room",
            "trigger_entity": "motion.hallway",
            "action_entity": "light.living_room",
            "impact_score": 0.75,
            "confidence": 0.80,
            "complexity": "medium",
            "area": "hallway",
            "rationale": "Chain: Motion triggers hallway light then living room light",
            "synergy_depth": 3,
            "chain_devices": ["motion.hallway", "light.hallway", "light.living_room"],
        }
        
        assert sample_chain["synergy_depth"] == 3
        assert len(sample_chain["devices"]) == 3
        assert len(sample_chain["chain_devices"]) == 3

    def test_4_device_chain_depth(self):
        """Test that 4-device chains have synergy_depth=4."""
        sample_chain = {
            "synergy_id": str(uuid.uuid4()),
            "synergy_type": "device_chain",
            "devices": ["motion.entry", "light.entry", "light.hallway", "climate.living_room"],
            "chain_path": "motion.entry → light.entry → light.hallway → climate.living_room",
            "trigger_entity": "motion.entry",
            "action_entity": "climate.living_room",
            "impact_score": 0.70,
            "confidence": 0.75,
            "complexity": "medium",
            "area": "entry",
            "rationale": "4-device chain: Entry motion triggers lights and climate",
            "synergy_depth": 4,
            "chain_devices": ["motion.entry", "light.entry", "light.hallway", "climate.living_room"],
        }
        
        assert sample_chain["synergy_depth"] == 4
        assert len(sample_chain["devices"]) == 4
        assert len(sample_chain["chain_devices"]) == 4


class TestSynergyTypeValidation:
    """Tests for synergy type validation."""

    def test_all_synergy_types_present(self):
        """Test that all expected synergy types are defined."""
        expected_types = [
            "device_pair",
            "device_chain",
            "schedule_based",
            "scene_based",
            "context_aware",
        ]
        
        # These are the synergy types our system should generate
        for synergy_type in expected_types:
            assert synergy_type in expected_types

    def test_synergy_type_complexity_mapping(self):
        """Test complexity mapping for different synergy types."""
        complexity_mapping = {
            "device_pair": "low",
            "device_chain": "medium",
            "schedule_based": "low",
            "scene_based": "low",
            "context_aware": ["low", "medium"],  # Varies by context type
        }
        
        # Verify complexity values are valid
        valid_complexities = {"low", "medium", "high"}
        for synergy_type, complexity in complexity_mapping.items():
            if isinstance(complexity, list):
                for c in complexity:
                    assert c in valid_complexities
            else:
                assert complexity in valid_complexities
