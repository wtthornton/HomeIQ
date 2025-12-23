"""
Unit tests for BlueprintMatcher service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.blueprints.matcher import BlueprintMatcher
from src.utils.miner_integration import MinerIntegration


@pytest.fixture
def mock_miner():
    """Create a mock MinerIntegration instance."""
    miner = MagicMock(spec=MinerIntegration)
    miner.search_blueprints = AsyncMock(return_value=[])
    return miner


@pytest.fixture
def sample_blueprint():
    """Sample blueprint data structure."""
    return {
        "id": 1,
        "title": "Motion-Activated Light",
        "description": "Turn on lights when motion detected",
        "yaml": """
blueprint:
  name: Motion-Activated Light
  description: Turn on lights when motion detected
  domain: automation
  input:
    motion_sensor:
      name: Motion Sensor
      selector:
        entity:
          domain: binary_sensor
          device_class: motion
    target_light:
      name: Light to Control
      selector:
        entity:
          domain: light
trigger:
  - platform: state
    entity_id: !input motion_sensor
    to: 'on'
action:
  - service: light.turn_on
    target:
      entity_id: !input target_light
""",
        "metadata": {
            "_blueprint_metadata": {
                "name": "Motion-Activated Light",
                "description": "Turn on lights when motion detected",
                "domain": "automation"
            },
            "_blueprint_variables": {
                "motion_sensor": {
                    "domain": "binary_sensor",
                    "device_class": "motion",
                    "name": "Motion Sensor"
                },
                "target_light": {
                    "domain": "light",
                    "name": "Light to Control"
                }
            },
            "_blueprint_devices": ["binary_sensor", "light"]
        },
        "use_case": "comfort",
        "quality_score": 0.85
    }


@pytest.mark.asyncio
async def test_find_best_match_success(mock_miner, sample_blueprint):
    """Test successful blueprint matching."""
    mock_miner.search_blueprints.return_value = [sample_blueprint]

    matcher = BlueprintMatcher(mock_miner)
    suggestion = {
        "description": "Turn on office light when motion detected",
        "devices_involved": ["light", "binary_sensor"]
    }
    validated_entities = {
        "Office Light": "light.office",
        "Motion Sensor": "binary_sensor.office_motion"
    }

    result = await matcher.find_best_match(
        suggestion=suggestion,
        validated_entities=validated_entities,
        devices_involved=["light", "binary_sensor"]
    )

    assert result is not None
    assert result["fit_score"] > 0
    assert result["blueprint"]["id"] == 1


@pytest.mark.asyncio
async def test_find_best_match_no_devices(mock_miner):
    """Test matching with no devices involved."""
    matcher = BlueprintMatcher(mock_miner)
    suggestion = {
        "description": "Some automation",
        "devices_involved": []
    }

    result = await matcher.find_best_match(
        suggestion=suggestion,
        validated_entities={},
        devices_involved=[]
    )

    assert result is None


@pytest.mark.asyncio
async def test_find_best_match_no_blueprints(mock_miner):
    """Test matching when no blueprints are found."""
    mock_miner.search_blueprints.return_value = []

    matcher = BlueprintMatcher(mock_miner)
    suggestion = {
        "description": "Turn on light",
        "devices_involved": ["light"]
    }
    validated_entities = {"Light": "light.office"}

    result = await matcher.find_best_match(
        suggestion=suggestion,
        validated_entities=validated_entities,
        devices_involved=["light"]
    )

    assert result is None


def test_calculate_device_match():
    """Test device matching score calculation."""
    miner = MagicMock(spec=MinerIntegration)
    matcher = BlueprintMatcher(miner)

    blueprint = {
        "metadata": {
            "_blueprint_devices": ["binary_sensor", "light"],
            "_blueprint_variables": {
                "motion_sensor": {"domain": "binary_sensor"},
                "target_light": {"domain": "light"}
            }
        }
    }

    score = matcher._calculate_device_match(
        blueprint_devices=["binary_sensor", "light"],
        devices_involved=["light", "binary_sensor"],
        blueprint_vars=blueprint["metadata"]["_blueprint_variables"],
        validated_entities={
            "Motion": "binary_sensor.office_motion",
            "Light": "light.office"
        }
    )

    assert 0.0 <= score <= 1.0
    assert score > 0.5  # Should have good match


def test_extract_use_case():
    """Test use case extraction from description."""
    miner = MagicMock(spec=MinerIntegration)
    matcher = BlueprintMatcher(miner)

    # Test security use case
    use_case = matcher._extract_use_case("Turn on alarm when door opens")
    assert use_case == "security"

    # Test energy use case
    use_case = matcher._extract_use_case("Save energy by turning off lights")
    assert use_case == "energy"

    # Test comfort use case
    use_case = matcher._extract_use_case("Adjust temperature for comfort")
    assert use_case == "comfort"

    # Test no use case
    use_case = matcher._extract_use_case("Some random automation")
    assert use_case is None

