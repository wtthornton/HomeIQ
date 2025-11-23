"""
Unit tests for BlueprintRenderer service.
"""

import pytest
import yaml

from src.services.blueprints.renderer import BlueprintRenderer


@pytest.fixture
def renderer():
    """Create BlueprintRenderer instance."""
    return BlueprintRenderer()


@pytest.fixture
def sample_blueprint_yaml():
    """Sample blueprint YAML."""
    return """
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
    brightness:
      name: Brightness
      selector:
        number:
          min: 1
          max: 100
          default: 75
trigger:
  - platform: state
    entity_id: !input motion_sensor
    to: 'on'
action:
  - service: light.turn_on
    target:
      entity_id: !input target_light
    data:
      brightness_pct: !input brightness
"""


@pytest.fixture
def sample_inputs():
    """Sample filled inputs."""
    return {
        "motion_sensor": "binary_sensor.office_motion",
        "target_light": "light.office",
        "brightness": 50
    }


@pytest.mark.asyncio
async def test_render_blueprint_success(renderer, sample_blueprint_yaml, sample_inputs):
    """Test successful blueprint rendering."""
    suggestion = {
        "description": "Turn on office light when motion detected",
        "title": "Office Motion Light"
    }

    yaml_str = await renderer.render_blueprint(
        blueprint_yaml=sample_blueprint_yaml,
        inputs=sample_inputs,
        suggestion=suggestion
    )

    assert yaml_str
    assert "binary_sensor.office_motion" in yaml_str
    assert "light.office" in yaml_str
    assert "50" in yaml_str or "brightness_pct: 50" in yaml_str

    # Should not contain blueprint section
    assert "blueprint:" not in yaml_str

    # Should contain 2025 HA standards
    parsed = yaml.safe_load(yaml_str)
    assert "id" in parsed
    assert "alias" in parsed
    assert "description" in parsed


@pytest.mark.asyncio
async def test_render_blueprint_missing_inputs(renderer, sample_blueprint_yaml):
    """Test rendering with missing inputs."""
    inputs = {
        "motion_sensor": "binary_sensor.office_motion"
        # Missing target_light and brightness
    }

    with pytest.raises(ValueError, match="No inputs provided"):
        await renderer.render_blueprint(
            blueprint_yaml=sample_blueprint_yaml,
            inputs={},
            suggestion={}
        )


@pytest.mark.asyncio
async def test_render_blueprint_invalid_yaml(renderer):
    """Test rendering with invalid YAML."""
    with pytest.raises(ValueError):
        await renderer.render_blueprint(
            blueprint_yaml="invalid: yaml: [",
            inputs={"test": "value"},
            suggestion={}
        )


@pytest.mark.asyncio
async def test_render_blueprint_adds_ha_2025_standards(renderer, sample_blueprint_yaml, sample_inputs):
    """Test that rendered YAML includes HA 2025 standards."""
    suggestion = {
        "description": "Test automation",
        "title": "Test"
    }

    yaml_str = await renderer.render_blueprint(
        blueprint_yaml=sample_blueprint_yaml,
        inputs=sample_inputs,
        suggestion=suggestion
    )

    parsed = yaml.safe_load(yaml_str)
    assert "id" in parsed
    assert isinstance(parsed["id"], str)
    assert len(parsed["id"]) > 0

    assert "alias" in parsed
    assert parsed["alias"] == "Test"

    assert "description" in parsed
    assert parsed["description"] == "Test automation"


def test_extract_automation_section(renderer):
    """Test extraction of automation section from blueprint."""
    blueprint_data = {
        "blueprint": {
            "name": "Test",
            "input": {}
        },
        "trigger": [{"platform": "state"}],
        "action": [{"service": "light.turn_on"}]
    }

    automation = renderer._extract_automation_section(blueprint_data)

    assert "blueprint" not in automation
    assert "trigger" in automation
    assert "action" in automation


def test_substitute_inputs(renderer):
    """Test input variable substitution."""
    yaml_str = """
trigger:
  - platform: state
    entity_id: !input motion_sensor
action:
  - service: light.turn_on
    target:
      entity_id: !input target_light
    data:
      brightness_pct: !input brightness
"""

    inputs = {
        "motion_sensor": "binary_sensor.office_motion",
        "target_light": "light.office",
        "brightness": 50
    }

    result = renderer._substitute_inputs(yaml_str, inputs)

    assert "!input" not in result
    assert "binary_sensor.office_motion" in result
    assert "light.office" in result
    assert "50" in result

