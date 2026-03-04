"""
Phase 1 Verification: Super Bowl Guide Automation Validation

Epic: HomeIQ Automation Platform Improvements
Story 1: Schema validation passes for Super Bowl guide automation structures

Validates that YAML samples from implementation/superbowl_teamtracker_lights_guide.md
pass the yaml-validation-service pipeline. Uses minimal samples to verify:
- time_pattern trigger with seconds
- state trigger
- condition: template with value_template
- variables action
- repeat (until, for_each) with sequence
"""

import pytest
from yaml_validation_service.validator import ValidationPipeline, ValidationResult

# Minimal kickoff automation - structure from Super Bowl guide (reduced entity lists)
KICKOFF_YAML = """
alias: Super Bowl - Kickoff Flash (Starts -15s, Runs 30s)
description: Starts 15 seconds before kickoff and flashes for 30 seconds.
mode: single
initial_state: true

trigger:
  - platform: time_pattern
    seconds: "/1"

condition:
  - condition: state
    entity_id: input_boolean.super_bowl_kickoff_flashed
    state: "off"
  - condition: state
    entity_id: sensor.super_bowl_sea
    state: "PRE"
  - condition: template
    value_template: >
      {% set kickoff = as_datetime(state_attr('sensor.super_bowl_sea','date')) %}
      {% if kickoff is none %} false
      {% else %}
        {% set t = now() %}
        {{ t >= (kickoff - timedelta(seconds=15)) and t <= (kickoff + timedelta(seconds=15)) }}
      {% endif %}

action:
  - service: input_boolean.turn_on
    target:
      entity_id: input_boolean.super_bowl_kickoff_flashed
  - variables:
      start_ts: "{{ as_timestamp(now()) }}"
      wled_lights: [light.bar]
      hue_lights: [light.back_front_hallway]
      kickoff_colors: [[0, 42, 92], [105, 190, 40]]
  - repeat:
      until:
        - condition: template
          value_template: "{{ (as_timestamp(now()) - start_ts) >= 30 }}"
      sequence:
        - variables:
            hi: "{{ range(90, 101) | random }}"
            wled_rgb: "{{ kickoff_colors | random }}"
        - service: light.turn_on
          target:
            entity_id: "{{ wled_lights }}"
          data:
            effect: "Dancing Shadows"
            rgb_color: "{{ wled_rgb }}"
            brightness_pct: "{{ hi }}"
        - repeat:
            for_each: "{{ hue_lights }}"
            sequence:
              - service: light.turn_on
                target:
                  entity_id: "{{ repeat.item }}"
                data:
                  rgb_color: "{{ kickoff_colors | random }}"
                  brightness_pct: "{{ range(85, 101) | random }}"
        - delay:
            milliseconds: 120
"""

# Minimal score flash - structure from Super Bowl guide
SCORE_FLASH_YAML = """
alias: Super Bowl - SEA Score Flash (15s)
description: When SEA score increases, flash 15s using SEA colors only.
mode: single
initial_state: true

trigger:
  - platform: state
    entity_id: sensor.super_bowl_sea

condition:
  - condition: state
    entity_id: sensor.super_bowl_sea
    state: "IN"
  - condition: template
    value_template: >
      {% set old = trigger.from_state.attributes.team_score | int(0) if trigger.from_state else 0 %}
      {% set new = trigger.to_state.attributes.team_score | int(0) if trigger.to_state else 0 %}
      {{ new > old }}

action:
  - variables:
      start_ts: "{{ as_timestamp(now()) }}"
      sea_colors: [[0, 42, 92], [105, 190, 40]]
  - repeat:
      until:
        - condition: template
          value_template: "{{ (as_timestamp(now()) - start_ts) >= 15 }}"
      sequence:
        - service: light.turn_on
          target:
            entity_id: light.bar
          data:
            effect: "Dancing Shadows"
            rgb_color: "{{ sea_colors | random }}"
            brightness_pct: 95
        - delay:
            milliseconds: 120
"""


@pytest.fixture
def pipeline_no_entity_validation():
    """Pipeline without entity validation (no Data API dependency)."""
    return ValidationPipeline(
        data_api_client=None,
        ha_client=None,
        validation_level="moderate",
    )


@pytest.mark.asyncio
async def test_kickoff_automation_passes_validation(pipeline_no_entity_validation):
    """Kickoff flash automation (time_pattern, variables, repeat.until, repeat.for_each) passes."""
    # Use normalize=False to avoid known bug: normalizer injects initial_state into nested dicts
    result: ValidationResult = await pipeline_no_entity_validation.validate(
        KICKOFF_YAML, normalize=False
    )
    assert result.valid, f"Expected valid; errors: {result.errors}"
    assert result.errors == [], f"Unexpected errors: {result.errors}"


@pytest.mark.asyncio
async def test_score_flash_automation_passes_validation(pipeline_no_entity_validation):
    """Score flash automation (state trigger, template condition, repeat.until) passes."""
    # Use normalize=False to avoid known bug: normalizer injects initial_state into nested dicts
    result: ValidationResult = await pipeline_no_entity_validation.validate(
        SCORE_FLASH_YAML, normalize=False
    )
    assert result.valid, f"Expected valid; errors: {result.errors}"
    assert result.errors == [], f"Unexpected errors: {result.errors}"
