"""Tests for entity safety blacklist enforcement in Stage 5 — Epic 93 Story 93.3."""

import pytest

from yaml_validation_service.validator import ValidationPipeline


def _make_yaml(entity_id: str = "light.office", service: str = "light.turn_on") -> str:
    return f"""
alias: "Test Automation"
description: "Test"
initial_state: true
mode: single
trigger:
  - platform: state
    entity_id: {entity_id}
    to: "on"
condition: []
action:
  - service: {service}
    target:
      entity_id: {entity_id}
"""


class TestBlockedEntityRejection:
    """93.3 AC: YAML containing blocked entity_ids → validation fails."""

    @pytest.mark.asyncio
    async def test_lock_entity_rejected(self):
        pipeline = ValidationPipeline()
        result = await pipeline.validate(_make_yaml("lock.front_door", "lock.unlock"))
        assert result.valid is False
        assert any("BLOCKED" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_alarm_entity_rejected(self):
        pipeline = ValidationPipeline()
        result = await pipeline.validate(
            _make_yaml("alarm_control_panel.home", "alarm_control_panel.alarm_disarm")
        )
        assert result.valid is False
        assert any("BLOCKED" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_light_entity_passes(self):
        pipeline = ValidationPipeline()
        result = await pipeline.validate(_make_yaml("light.office", "light.turn_on"))
        assert result.valid is True
        assert not any("BLOCKED" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_switch_entity_passes(self):
        pipeline = ValidationPipeline()
        result = await pipeline.validate(_make_yaml("switch.kitchen", "switch.turn_on"))
        assert result.valid is True


class TestBlockedServiceRejection:
    """93.3 AC: YAML containing blocked service calls → validation fails."""

    @pytest.mark.asyncio
    async def test_lock_unlock_service_rejected(self):
        pipeline = ValidationPipeline()
        yaml_content = _make_yaml("sensor.motion", "lock.unlock")
        result = await pipeline.validate(yaml_content)
        assert result.valid is False
        assert any("lock.unlock" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_alarm_disarm_service_rejected(self):
        pipeline = ValidationPipeline()
        yaml_content = _make_yaml("sensor.motion", "alarm_control_panel.alarm_disarm")
        result = await pipeline.validate(yaml_content)
        assert result.valid is False
        assert any("alarm_control_panel.alarm_disarm" in e for e in result.errors)


class TestWarnDomainWarnings:
    """93.3 AC: YAML containing cover.* → passes with warning."""

    @pytest.mark.asyncio
    async def test_cover_passes_with_warning(self):
        pipeline = ValidationPipeline()
        result = await pipeline.validate(_make_yaml("cover.garage_door", "cover.open_cover"))
        assert result.valid is True
        assert any("CAUTION" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_siren_passes_with_warning(self):
        pipeline = ValidationPipeline()
        result = await pipeline.validate(_make_yaml("siren.alarm", "siren.turn_on"))
        assert result.valid is True
        assert any("CAUTION" in w for w in result.warnings)


class TestSafetyOverride:
    """93.3 AC: Safety override header bypasses the block."""

    @pytest.mark.asyncio
    async def test_override_converts_errors_to_warnings(self):
        pipeline = ValidationPipeline(safety_override=True)
        result = await pipeline.validate(_make_yaml("lock.front_door", "lock.unlock"))
        # Should not fail with override
        assert not any("BLOCKED" in e for e in result.errors)
        # Should still warn
        assert any("SAFETY OVERRIDE" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_no_override_rejects(self):
        pipeline = ValidationPipeline(safety_override=False)
        result = await pipeline.validate(_make_yaml("lock.front_door", "lock.unlock"))
        assert result.valid is False
