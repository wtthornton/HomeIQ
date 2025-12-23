"""
Unit tests for BlueprintInputFiller service.
"""

import pytest

from src.services.blueprints.filler import BlueprintInputFiller


@pytest.fixture
def filler():
    """Create BlueprintInputFiller instance."""
    return BlueprintInputFiller()


@pytest.fixture
def sample_blueprint():
    """Sample blueprint with various input types."""
    return {
        "metadata": {
            "_blueprint_variables": {
                "motion_sensor": {
                    "domain": "binary_sensor",
                    "device_class": "motion",
                    "selector": {
                        "entity": {
                            "domain": "binary_sensor",
                            "device_class": "motion"
                        }
                    }
                },
                "target_light": {
                    "domain": "light",
                    "selector": {
                        "entity": {
                            "domain": "light"
                        }
                    }
                },
                "brightness": {
                    "selector": {
                        "number": {
                            "min": 1,
                            "max": 100,
                            "default": 75
                        }
                    }
                },
                "enable_notification": {
                    "selector": {
                        "boolean": {
                            "default": False
                        }
                    }
                }
            }
        }
    }


@pytest.mark.asyncio
async def test_fill_entity_inputs(filler, sample_blueprint):
    """Test filling entity selector inputs."""
    suggestion = {
        "description": "Turn on office light when motion detected"
    }
    validated_entities = {
        "Office Motion": "binary_sensor.office_motion",
        "Office Light": "light.office"
    }

    inputs = await filler.fill_blueprint_inputs(
        blueprint=sample_blueprint,
        suggestion=suggestion,
        validated_entities=validated_entities
    )

    assert "motion_sensor" in inputs
    assert "target_light" in inputs
    assert inputs["motion_sensor"] in validated_entities.values()
    assert inputs["target_light"] in validated_entities.values()


@pytest.mark.asyncio
async def test_fill_number_input(filler, sample_blueprint):
    """Test filling number selector inputs."""
    suggestion = {
        "description": "Turn on light at 50% brightness"
    }
    validated_entities = {"Light": "light.office"}

    inputs = await filler.fill_blueprint_inputs(
        blueprint=sample_blueprint,
        suggestion=suggestion,
        validated_entities=validated_entities
    )

    assert "brightness" in inputs
    assert inputs["brightness"] == 50


@pytest.mark.asyncio
async def test_fill_boolean_input(filler, sample_blueprint):
    """Test filling boolean selector inputs."""
    suggestion = {
        "description": "Turn on light and enable notification"
    }
    validated_entities = {"Light": "light.office"}

    inputs = await filler.fill_blueprint_inputs(
        blueprint=sample_blueprint,
        suggestion=suggestion,
        validated_entities=validated_entities
    )

    assert "enable_notification" in inputs
    assert isinstance(inputs["enable_notification"], bool)


@pytest.mark.asyncio
async def test_fill_with_defaults(filler, sample_blueprint):
    """Test that defaults are used when values not found."""
    suggestion = {
        "description": "Turn on light"
    }
    validated_entities = {"Light": "light.office"}

    inputs = await filler.fill_blueprint_inputs(
        blueprint=sample_blueprint,
        suggestion=suggestion,
        validated_entities=validated_entities
    )

    # Brightness should use default (75)
    assert "brightness" in inputs
    assert inputs["brightness"] == 75

    # Boolean should use default (False)
    assert "enable_notification" in inputs
    assert inputs["enable_notification"] is False


def test_extract_number_value(filler):
    """Test number extraction from text."""
    # Test percentage
    value = filler._extract_number_value(
        "brightness",
        {"selector": {"number": {"min": 1, "max": 100}}},
        "Turn on light at 50% brightness"
    )
    assert value == 50

    # Test seconds
    value = filler._extract_number_value(
        "timeout",
        {"selector": {"number": {"min": 1, "max": 300}}},
        "Wait 30 seconds before turning off"
    )
    assert value == 30


def test_extract_boolean_value(filler):
    """Test boolean extraction from text."""
    # Test positive - keyword "enable" in text, input name is "enable"
    value = filler._extract_boolean_value(
        "enable_notification",
        {"selector": {"boolean": {"default": False}}},
        "Enable notifications for this automation"
    )
    assert value is True, f"Expected True for 'enable' in text with 'enable_notification' input, got {value}"

    # Test negative - keyword "disable" in text, input name contains "enable"
    value = filler._extract_boolean_value(
        "enable_notification",
        {"selector": {"boolean": {"default": True}}},
        "Disable notifications for this automation"
    )
    assert value is False, f"Expected False for 'disable' in text with 'enable_notification' input, got {value}"

