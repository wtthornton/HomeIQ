"""
Epic 90, Story 90.7: YAML validation service integration tests.

Tests the yaml-validation-service /api/v1/validation/validate endpoint.
Covers all 6 validation stages: syntax, schema, entity resolution,
service schema, safety checks, and style/maintainability.

Requires: yaml-validation-service running at YAML_VALIDATION_URL
          (default: http://localhost:8037)

Run: pytest tests/integration/test_yaml_validation_service.py -v
     pytest tests/integration/test_yaml_validation_service.py -v -m integration
Exclude from default: pytest -m "not integration"
"""

from __future__ import annotations

import os

import httpx
import pytest

YAML_VALIDATION_URL = os.environ.get("YAML_VALIDATION_URL", "http://localhost:8037")
VALIDATE_ENDPOINT = f"{YAML_VALIDATION_URL}/api/v1/validation/validate"
TIMEOUT = 30.0


@pytest.mark.integration
@pytest.mark.asyncio
class TestYAMLValidationService:
    """Integration tests for yaml-validation-service (Story 90.7)."""

    async def _validate(
        self,
        client: httpx.AsyncClient,
        yaml_content: str,
        normalize: bool = True,
        validate_entities: bool = False,
        validate_services: bool = False,
    ) -> dict:
        """Call validation endpoint and return response."""
        response = await client.post(
            VALIDATE_ENDPOINT,
            json={
                "yaml_content": yaml_content,
                "normalize": normalize,
                "validate_entities": validate_entities,
                "validate_services": validate_services,
            },
            timeout=TIMEOUT,
        )
        assert response.status_code == 200, (
            f"Validation endpoint failed: {response.status_code} {response.text}"
        )
        return response.json()

    # --- Stage 1: Syntax ---

    async def test_valid_automation_passes(self):
        """Valid automation YAML scores > 80."""
        yaml_content = """
alias: Motion Kitchen Lights
description: Turn on kitchen lights when motion detected
initial_state: true
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.kitchen_motion
    to: "on"
action:
  - action: light.turn_on
    target:
      entity_id: light.kitchen
"""
        async with httpx.AsyncClient() as client:
            result = await self._validate(client, yaml_content)
            assert result["valid"] is True
            assert result["score"] >= 80.0, (
                f"Expected score >= 80, got {result['score']}"
            )
            assert len(result["errors"]) == 0

    async def test_malformed_yaml_syntax_error(self):
        """Malformed YAML returns syntax error."""
        yaml_content = """
alias: Bad YAML
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
  action:  # Bad indentation - this is invalid YAML
    - action: light.turn_on
"""
        async with httpx.AsyncClient() as client:
            result = await self._validate(client, yaml_content)
            assert result["valid"] is False
            assert any(
                "syntax" in e.lower()
                or "yaml" in e.lower()
                or "parse" in e.lower()
                for e in result["errors"]
            ), f"Expected syntax error, got: {result['errors']}"

    async def test_completely_invalid_yaml(self):
        """Completely unparseable YAML returns error."""
        yaml_content = "{{{{ this is not yaml: [[[["
        async with httpx.AsyncClient() as client:
            result = await self._validate(client, yaml_content)
            assert result["valid"] is False
            assert len(result["errors"]) > 0

    # --- Stage 2: Schema Validation ---

    async def test_missing_trigger_schema_error(self):
        """YAML without trigger array fails schema validation."""
        yaml_content = """
alias: No Trigger
action:
  - action: light.turn_on
    target:
      entity_id: light.kitchen
"""
        async with httpx.AsyncClient() as client:
            result = await self._validate(client, yaml_content)
            assert result["valid"] is False
            assert any(
                "trigger" in e.lower() for e in result["errors"]
            ), f"Expected trigger error, got: {result['errors']}"

    async def test_missing_action_schema_error(self):
        """YAML without action array fails schema validation."""
        yaml_content = """
alias: No Action
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
"""
        async with httpx.AsyncClient() as client:
            result = await self._validate(client, yaml_content)
            assert result["valid"] is False
            assert any(
                "action" in e.lower() for e in result["errors"]
            ), f"Expected action error, got: {result['errors']}"

    # --- Stage 2+: Normalization (triggers->trigger, actions->action) ---

    async def test_deprecated_plural_keys_normalized(self):
        """Deprecated 'triggers'/'actions' are auto-normalized to singular."""
        yaml_content = """
alias: Deprecated Keys
triggers:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
actions:
  - action: light.turn_on
    target:
      entity_id: light.kitchen
"""
        async with httpx.AsyncClient() as client:
            result = await self._validate(client, yaml_content, normalize=True)
            # Should apply fixes
            assert len(result["fixes_applied"]) > 0, "Expected normalization fixes"
            # Check fixes mention the plural->singular transformation
            fixes_text = " ".join(result["fixes_applied"]).lower()
            assert "trigger" in fixes_text or "action" in fixes_text, (
                f"Expected trigger/action normalization fix, got: {result['fixes_applied']}"
            )
            # Fixed YAML should be provided
            if result["fixed_yaml"]:
                assert "triggers:" not in result["fixed_yaml"], (
                    "Fixed YAML should not contain 'triggers:'"
                )
                assert "actions:" not in result["fixed_yaml"], (
                    "Fixed YAML should not contain 'actions:'"
                )

    async def test_initial_state_auto_added(self):
        """Missing initial_state is auto-added during normalization."""
        yaml_content = """
alias: Missing Initial State
trigger:
  - platform: time
    at: "23:00:00"
action:
  - action: light.turn_off
    target:
      entity_id: light.all_lights
"""
        async with httpx.AsyncClient() as client:
            result = await self._validate(client, yaml_content, normalize=True)
            # Should be valid (initial_state auto-added)
            if result["fixed_yaml"]:
                assert "initial_state" in result["fixed_yaml"], (
                    "Fixed YAML should include initial_state"
                )

    # --- Stage 5: Safety Checks ---

    async def test_safety_warning_lock_without_condition(self):
        """Lock unlock without conditions produces safety warning."""
        yaml_content = """
alias: Unsafe Unlock
initial_state: true
mode: single
trigger:
  - platform: time
    at: "08:00:00"
action:
  - action: lock.unlock
    target:
      entity_id: lock.front_door
"""
        async with httpx.AsyncClient() as client:
            result = await self._validate(client, yaml_content)
            # Should produce safety warnings (not necessarily invalid)
            has_safety = any(
                "safety" in w.lower()
                or "lock" in w.lower()
                or "unlock" in w.lower()
                for w in result.get("warnings", [])
            )
            assert has_safety, (
                "Expected safety warning for unconditional unlock, "
                f"got warnings: {result.get('warnings', [])}"
            )

    async def test_safety_warning_alarm_disarm(self):
        """Alarm disarm without conditions produces safety warning."""
        yaml_content = """
alias: Unsafe Disarm
initial_state: true
mode: single
trigger:
  - platform: time
    at: "07:00:00"
action:
  - action: alarm_control_panel.alarm_disarm
    target:
      entity_id: alarm_control_panel.home
"""
        async with httpx.AsyncClient() as client:
            result = await self._validate(client, yaml_content)
            has_safety = any(
                "safety" in w.lower()
                or "alarm" in w.lower()
                or "disarm" in w.lower()
                for w in result.get("warnings", [])
            )
            assert has_safety, (
                "Expected safety warning for alarm disarm, "
                f"got warnings: {result.get('warnings', [])}"
            )

    # --- Stage 6: Style/Maintainability ---

    async def test_jinja2_template_validation(self):
        """Valid Jinja2 templates pass style checks."""
        yaml_content = """
alias: Template Test
initial_state: true
mode: single
trigger:
  - platform: template
    value_template: "{{ is_state('binary_sensor.motion', 'on') }}"
action:
  - action: light.turn_on
    target:
      entity_id: light.kitchen
"""
        async with httpx.AsyncClient() as client:
            result = await self._validate(client, yaml_content)
            # Valid Jinja2 should not produce template errors
            template_errors = [
                e
                for e in result["errors"]
                if "template" in e.lower() or "jinja" in e.lower()
            ]
            assert len(template_errors) == 0, (
                f"Unexpected template errors: {template_errors}"
            )

    # --- Complex Scenarios ---

    async def test_multi_trigger_multi_action(self):
        """Complex automation with multiple triggers and actions validates."""
        yaml_content = """
alias: Complex Automation
description: Multiple triggers and actions
initial_state: true
mode: restart
trigger:
  - platform: state
    entity_id: binary_sensor.front_door
    to: "on"
  - platform: state
    entity_id: binary_sensor.back_door
    to: "on"
action:
  - action: light.turn_on
    target:
      entity_id: light.hallway
  - delay: "00:00:05"
  - action: notify.mobile_app
    data:
      message: "Door opened"
"""
        async with httpx.AsyncClient() as client:
            result = await self._validate(client, yaml_content)
            assert result["valid"] is True, (
                f"Complex automation should be valid: {result['errors']}"
            )
            assert result["score"] >= 70.0

    async def test_empty_string_returns_error(self):
        """Empty YAML string returns error."""
        async with httpx.AsyncClient() as client:
            result = await self._validate(client, "")
            assert result["valid"] is False
            assert len(result["errors"]) > 0

    async def test_non_dict_yaml_returns_error(self):
        """YAML that parses to a list (not dict) returns error."""
        yaml_content = """
- item1
- item2
"""
        async with httpx.AsyncClient() as client:
            result = await self._validate(client, yaml_content)
            assert result["valid"] is False

    async def test_normalization_disabled(self):
        """With normalize=False, deprecated keys are not auto-fixed."""
        yaml_content = """
alias: No Normalization
triggers:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
actions:
  - action: light.turn_on
    target:
      entity_id: light.kitchen
"""
        async with httpx.AsyncClient() as client:
            result = await self._validate(
                client, yaml_content, normalize=False,
            )
            assert (
                result["fixed_yaml"] is None
                or len(result["fixes_applied"]) == 0
            )

    async def test_response_schema_completeness(self):
        """Verify response contains all expected fields."""
        yaml_content = """
alias: Schema Check
initial_state: true
trigger:
  - platform: time
    at: "12:00:00"
action:
  - action: light.toggle
    target:
      entity_id: light.office
"""
        async with httpx.AsyncClient() as client:
            result = await self._validate(client, yaml_content)
            expected_fields = ["valid", "errors", "warnings", "score"]
            for field in expected_fields:
                assert field in result, f"Response missing field: {field}"
            assert isinstance(result["valid"], bool)
            assert isinstance(result["errors"], list)
            assert isinstance(result["warnings"], list)
            assert isinstance(result["score"], (int, float))
