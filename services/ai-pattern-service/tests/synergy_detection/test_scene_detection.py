"""
Integration tests for SceneDetector module.

Tests the scene detection functionality including:
- Area-based scene detection
- Domain-based scene detection
- Existing scene detection
"""

import pytest
import uuid

import sys
from pathlib import Path

# Add src/synergy_detection to path directly (avoid __init__.py import issues)
src_path = Path(__file__).parent.parent.parent / "src" / "synergy_detection"
sys.path.insert(0, str(src_path))

from scene_detection import (
    SceneDetector,
    ACTIONABLE_DOMAINS,
    MAX_SCENE_SYNERGIES,
    MIN_DEVICES_FOR_AREA_SCENE,
    MIN_DEVICES_FOR_DOMAIN_SCENE,
)


class TestSceneDetector:
    """Test SceneDetector class."""

    @pytest.fixture
    def detector(self):
        """Create a SceneDetector instance."""
        return SceneDetector()

    @pytest.fixture
    def entities_with_areas(self):
        """Create entities with area_id set."""
        return [
            {"entity_id": "light.living_room_1", "area_id": "living_room"},
            {"entity_id": "light.living_room_2", "area_id": "living_room"},
            {"entity_id": "light.living_room_3", "area_id": "living_room"},
            {"entity_id": "switch.living_room_fan", "area_id": "living_room"},
            {"entity_id": "light.bedroom_1", "area_id": "bedroom"},
            {"entity_id": "light.bedroom_2", "area_id": "bedroom"},
            {"entity_id": "climate.bedroom_ac", "area_id": "bedroom"},
            {"entity_id": "sensor.temperature", "area_id": "living_room"},  # Not actionable
        ]

    @pytest.fixture
    def entities_without_areas(self):
        """Create entities without area_id."""
        return [
            {"entity_id": "light.light_1", "area_id": None},
            {"entity_id": "light.light_2", "area_id": None},
            {"entity_id": "light.light_3", "area_id": None},
            {"entity_id": "light.light_4", "area_id": None},
            {"entity_id": "light.light_5", "area_id": None},
            {"entity_id": "switch.switch_1", "area_id": None},
            {"entity_id": "switch.switch_2", "area_id": None},
            {"entity_id": "switch.switch_3", "area_id": None},
            {"entity_id": "switch.switch_4", "area_id": None},
            {"entity_id": "switch.switch_5", "area_id": None},
        ]

    @pytest.fixture
    def entities_with_existing_scenes(self):
        """Create entities including existing scenes."""
        return [
            {"entity_id": "light.living_room_1", "area_id": "living_room"},
            {"entity_id": "light.living_room_2", "area_id": "living_room"},
            {"entity_id": "light.living_room_3", "area_id": "living_room"},
            {"entity_id": "scene.living_room_movie", "area_id": "living_room"},  # Existing scene
        ]

    def test_group_devices_by_area(self, detector, entities_with_areas):
        """Test grouping devices by area."""
        area_devices = detector._group_devices_by_area(entities_with_areas)
        
        assert "living_room" in area_devices
        assert "bedroom" in area_devices
        
        # Should have 4 actionable devices in living room (3 lights + 1 switch)
        assert len(area_devices["living_room"]) == 4
        
        # Should have 3 actionable devices in bedroom (2 lights + 1 climate)
        assert len(area_devices["bedroom"]) == 3
        
        # Sensor should not be included
        assert "sensor.temperature" not in area_devices["living_room"]

    def test_group_devices_by_domain(self, detector, entities_with_areas):
        """Test grouping devices by domain."""
        domain_devices = detector._group_devices_by_domain(entities_with_areas)
        
        assert "light" in domain_devices
        assert "switch" in domain_devices
        assert "climate" in domain_devices
        assert "sensor" not in domain_devices  # Not actionable
        
        # Should have 5 lights total
        assert len(domain_devices["light"]) == 5

    def test_find_existing_scenes(self, detector, entities_with_existing_scenes):
        """Test finding existing scenes."""
        scenes = detector._find_existing_scenes(entities_with_existing_scenes)
        
        assert len(scenes) == 1
        assert scenes[0]["entity_id"] == "scene.living_room_movie"

    def test_has_existing_area_scene(self, detector, entities_with_existing_scenes):
        """Test checking for existing area scene."""
        scenes = detector._find_existing_scenes(entities_with_existing_scenes)
        
        # living_room has a scene
        assert detector._has_existing_area_scene("living_room", scenes) is True
        
        # bedroom has no scene
        assert detector._has_existing_area_scene("bedroom", scenes) is False

    def test_has_existing_domain_scene(self, detector):
        """Test checking for existing domain scene."""
        scenes = [
            {"entity_id": "scene.all_lights"},
            {"entity_id": "scene.movie_time"},
        ]
        
        assert detector._has_existing_domain_scene("light", scenes) is True
        assert detector._has_existing_domain_scene("switch", scenes) is False

    def test_create_area_scene_synergy(self, detector):
        """Test creating area-based scene synergy."""
        devices = ["light.a", "light.b", "light.c", "switch.d"]
        synergy = detector._create_area_scene_synergy("living_room", devices)
        
        assert synergy["synergy_type"] == "scene_based"
        assert synergy["area"] == "living_room"
        assert synergy["trigger_entity"] == "scene.living_room_all"
        assert synergy["confidence"] == 0.80
        assert synergy["complexity"] == "low"
        assert synergy["context_metadata"]["scene_type"] == "area_based"
        assert synergy["context_metadata"]["device_count"] == 4
        assert "Living Room All" in synergy["context_metadata"]["suggested_scene_name"]

    def test_create_domain_scene_synergy(self, detector):
        """Test creating domain-based scene synergy."""
        devices = ["light.a", "light.b", "light.c", "light.d", "light.e"]
        synergy = detector._create_domain_scene_synergy("light", devices)
        
        assert synergy["synergy_type"] == "scene_based"
        assert synergy["area"] is None
        assert synergy["trigger_entity"] == "scene.all_lights"
        assert synergy["confidence"] == 0.70
        assert synergy["context_metadata"]["scene_type"] == "domain_based"
        assert synergy["context_metadata"]["domain"] == "light"
        assert "All Lights" in synergy["context_metadata"]["suggested_scene_name"]

    @pytest.mark.asyncio
    async def test_detect_scene_based_synergies_with_areas(self, detector, entities_with_areas):
        """Test detecting scene-based synergies with area data."""
        synergies = await detector.detect_scene_based_synergies(entities_with_areas)
        
        # Should find at least one area-based scene (living_room has 4 devices >= 3)
        assert len(synergies) >= 1
        
        # Check structure
        for synergy in synergies:
            assert synergy["synergy_type"] == "scene_based"
            assert "context_metadata" in synergy
            assert synergy["complexity"] == "low"

    @pytest.mark.asyncio
    async def test_detect_scene_based_synergies_without_areas(self, detector, entities_without_areas):
        """Test detecting scene-based synergies without area data."""
        synergies = await detector.detect_scene_based_synergies(entities_without_areas)
        
        # Should find domain-based scenes (5 lights, 5 switches)
        assert len(synergies) >= 1
        
        # All should be domain-based
        for synergy in synergies:
            assert synergy["context_metadata"]["scene_type"] == "domain_based"

    @pytest.mark.asyncio
    async def test_detect_scene_based_synergies_respects_existing(self, detector, entities_with_existing_scenes):
        """Test that existing scenes prevent duplicate suggestions."""
        synergies = await detector.detect_scene_based_synergies(entities_with_existing_scenes)
        
        # Should not suggest scene for living_room (already has one)
        for synergy in synergies:
            if synergy["context_metadata"]["scene_type"] == "area_based":
                assert synergy["area"] != "living_room"

    @pytest.mark.asyncio
    async def test_detect_scene_based_synergies_max_limit(self, detector):
        """Test that detection respects max synergies limit."""
        # Create many entities to trigger limit
        entities = []
        for i in range(100):
            area = f"area_{i}"
            for j in range(5):
                entities.append({
                    "entity_id": f"light.{area}_{j}",
                    "area_id": area
                })
        
        synergies = await detector.detect_scene_based_synergies(entities)
        
        assert len(synergies) <= MAX_SCENE_SYNERGIES


class TestSceneDetectorConstants:
    """Test configuration constants."""

    def test_actionable_domains(self):
        """Test actionable domains are correct."""
        assert "light" in ACTIONABLE_DOMAINS
        assert "switch" in ACTIONABLE_DOMAINS
        assert "climate" in ACTIONABLE_DOMAINS
        assert "cover" in ACTIONABLE_DOMAINS
        assert "fan" in ACTIONABLE_DOMAINS
        assert "media_player" in ACTIONABLE_DOMAINS
        assert "sensor" not in ACTIONABLE_DOMAINS

    def test_min_devices_thresholds(self):
        """Test minimum device thresholds."""
        assert MIN_DEVICES_FOR_AREA_SCENE == 3
        assert MIN_DEVICES_FOR_DOMAIN_SCENE == 5
        assert MIN_DEVICES_FOR_DOMAIN_SCENE > MIN_DEVICES_FOR_AREA_SCENE

    def test_max_synergies(self):
        """Test max synergies limit."""
        assert MAX_SCENE_SYNERGIES == 50
