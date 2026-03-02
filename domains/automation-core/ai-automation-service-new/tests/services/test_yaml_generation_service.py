"""
Tests for yaml_generation_service.py
"""

import pytest

from src.services.yaml_generation_service import (
    InvalidSuggestionError,
    YAMLGenerationError,
    YAMLGenerationService,
)


class TestYAMLGenerationError:
    """Test YAMLGenerationError class."""

    def test_init(self):
        """Test YAMLGenerationError is an Exception."""
        err = YAMLGenerationError("test error")
        assert str(err) == "test error"
        assert isinstance(err, Exception)


class TestInvalidSuggestionError:
    """Test InvalidSuggestionError class."""

    def test_init(self):
        """Test InvalidSuggestionError inherits from YAMLGenerationError."""
        err = InvalidSuggestionError("bad suggestion")
        assert str(err) == "bad suggestion"
        assert isinstance(err, YAMLGenerationError)


class TestYAMLGenerationServiceFormatEntityContext:
    """Test _format_entity_context_for_prompt method."""

    def _make_service(self):
        """Create a YAMLGenerationService with mock deps."""
        from unittest.mock import MagicMock

        return YAMLGenerationService(
            openai_client=MagicMock(),
            data_api_client=MagicMock(),
            yaml_validation_client=None,
        )

    def test_empty_context_returns_empty_string(self):
        """Test empty context returns empty string."""
        svc = self._make_service()
        result = svc._format_entity_context_for_prompt({})
        assert result == ""

    def test_none_context_returns_empty_string(self):
        """Test None context returns empty string."""
        svc = self._make_service()
        result = svc._format_entity_context_for_prompt(None)
        assert result == ""

    def test_formats_entities_by_domain(self):
        """Test entities are grouped and formatted by domain."""
        svc = self._make_service()
        context = {
            "entities": {
                "light": [
                    {"entity_id": "light.office", "friendly_name": "Office Light", "area_id": "office"},
                ],
                "switch": [
                    {"entity_id": "switch.fan", "friendly_name": "Fan", "area_id": None},
                ],
            }
        }

        result = svc._format_entity_context_for_prompt(context)

        assert "LIGHT entities:" in result
        assert "light.office" in result
        assert "(Office Light)" in result
        assert "[area: office]" in result
        assert "SWITCH entities:" in result
        assert "switch.fan" in result

    def test_truncates_over_50_entities(self):
        """Test entities per domain are capped at 50."""
        svc = self._make_service()
        many_entities = [
            {"entity_id": f"light.light_{i}", "friendly_name": f"Light {i}", "area_id": None}
            for i in range(60)
        ]
        context = {"entities": {"light": many_entities}}

        result = svc._format_entity_context_for_prompt(context)

        assert "... and 10 more light entities" in result


class TestYAMLGenerationServiceCleanYaml:
    """Test _clean_yaml_content method."""

    def _make_service(self):
        from unittest.mock import MagicMock

        return YAMLGenerationService(
            openai_client=MagicMock(),
            data_api_client=MagicMock(),
        )

    def test_strips_markdown_code_blocks(self):
        """Test markdown code blocks are removed."""
        svc = self._make_service()
        raw = "```yaml\nalias: Test\ntrigger:\n  - platform: state\n```"

        result = svc._clean_yaml_content(raw)

        assert not result.startswith("```")
        assert "alias: Test" in result
        assert result.endswith("- platform: state")

    def test_removes_document_separators(self):
        """Test --- document separators are removed."""
        svc = self._make_service()
        raw = "---\nalias: Test\ntrigger:\n  - platform: state"

        result = svc._clean_yaml_content(raw)

        assert "---" not in result
        assert "alias: Test" in result

    def test_passthrough_clean_yaml(self):
        """Test clean YAML passes through unchanged."""
        svc = self._make_service()
        clean = "alias: Test\ntrigger:\n  - platform: state"

        result = svc._clean_yaml_content(clean)

        assert result == clean


class TestYAMLGenerationServiceExtractEntityIds:
    """Test _extract_entity_ids method."""

    def _make_service(self):
        from unittest.mock import MagicMock

        return YAMLGenerationService(
            openai_client=MagicMock(),
            data_api_client=MagicMock(),
        )

    def test_extracts_entity_id_field(self):
        """Test extraction from entity_id field."""
        svc = self._make_service()
        data = {"action": [{"service": "light.turn_on", "entity_id": "light.office"}]}

        result = svc._extract_entity_ids(data)

        assert "light.office" in result

    def test_extracts_entity_id_list(self):
        """Test extraction from entity_id list."""
        svc = self._make_service()
        data = {"action": [{"entity_id": ["light.office", "light.kitchen"]}]}

        result = svc._extract_entity_ids(data)

        assert "light.office" in result
        assert "light.kitchen" in result

    def test_extracts_from_template_expressions(self):
        """Test extraction from Jinja2 template expressions."""
        svc = self._make_service()
        data = {"condition": "{{ states('sensor.temperature') }}"}

        result = svc._extract_entity_ids(data)

        assert "sensor.temperature" in result

    def test_extracts_snapshot_entities(self):
        """Test extraction from snapshot_entities."""
        svc = self._make_service()
        data = {"snapshot_entities": ["light.office", "switch.fan"]}

        result = svc._extract_entity_ids(data)

        assert "light.office" in result
        assert "switch.fan" in result

    def test_excludes_service_actions(self):
        """Test service actions like light.turn_on are excluded."""
        svc = self._make_service()
        data = {"service": "light.turn_on"}

        result = svc._extract_entity_ids(data)

        assert "light.turn_on" not in result

    def test_empty_data_returns_empty(self):
        """Test empty data returns empty list."""
        svc = self._make_service()

        result = svc._extract_entity_ids({})

        assert result == []
