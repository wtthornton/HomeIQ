"""
Config schema validation tests for the auto-fix pipeline.

Validates that config YAML files conform to config-schema.json.
References: auto-fix-pipeline/config/schema/README.md, config-schema.json
"""

import json
from pathlib import Path

import pytest
import yaml

# Paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AUTO_FIX_DIR = PROJECT_ROOT / "auto-fix-pipeline"
CONFIG_SCHEMA_PATH = AUTO_FIX_DIR / "config" / "schema" / "config-schema.json"
HOMEIQ_DEFAULT_PATH = AUTO_FIX_DIR / "config" / "example" / "homeiq-default.yaml"


def _load_schema() -> dict:
    """Load config schema from JSON."""
    with open(CONFIG_SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _load_yaml(path: Path) -> dict:
    """Load YAML config."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _validate_against_schema(data: dict, schema: dict) -> list[str]:
    """
    Validate data against JSON schema. Returns list of validation errors.
    Uses jsonschema if available; otherwise performs basic structural checks.
    """
    try:
        import jsonschema
    except ImportError:
        # Fallback: basic structural validation without jsonschema
        return _basic_validate(data, schema)
    try:
        jsonschema.validate(instance=data, schema=schema)
        return []
    except Exception as e:
        return [str(e)]


def _basic_validate(data: dict, schema: dict) -> list[str]:
    """Basic validation when jsonschema is not installed."""
    errors: list[str] = []
    if "properties" not in schema:
        return errors
    for key, prop_spec in schema["properties"].items():
        if key not in data:
            continue
        val = data[key]
        if "type" in prop_spec:
            expected = prop_spec["type"]
            if expected == "object" and not isinstance(val, dict):
                errors.append(f"{key}: expected object, got {type(val).__name__}")
            elif expected == "array" and not isinstance(val, list):
                errors.append(f"{key}: expected array, got {type(val).__name__}")
            elif expected == "string" and not isinstance(val, str):
                errors.append(f"{key}: expected string, got {type(val).__name__}")
            elif expected == "integer" and not isinstance(val, int):
                errors.append(f"{key}: expected integer, got {type(val).__name__}")
            elif expected == "number" and not isinstance(val, (int, float)):
                errors.append(f"{key}: expected number, got {type(val).__name__}")
            elif expected == "boolean" and not isinstance(val, bool):
                errors.append(f"{key}: expected boolean, got {type(val).__name__}")
    return errors


class TestConfigSchema:
    """Config schema validation tests."""

    def test_schema_file_exists(self) -> None:
        """Config schema JSON file exists."""
        assert CONFIG_SCHEMA_PATH.exists(), f"Schema not found: {CONFIG_SCHEMA_PATH}"

    def test_schema_is_valid_json(self) -> None:
        """Config schema is valid JSON."""
        schema = _load_schema()
        assert isinstance(schema, dict)
        assert "properties" in schema or "type" in schema

    def test_homeiq_default_exists(self) -> None:
        """HomeIQ default config exists."""
        assert HOMEIQ_DEFAULT_PATH.exists(), f"Config not found: {HOMEIQ_DEFAULT_PATH}"

    def test_homeiq_default_valid_yaml(self) -> None:
        """HomeIQ default config is valid YAML."""
        data = _load_yaml(HOMEIQ_DEFAULT_PATH)
        assert isinstance(data, dict)

    def test_homeiq_default_has_version(self) -> None:
        """HomeIQ default config has version."""
        data = _load_yaml(HOMEIQ_DEFAULT_PATH)
        assert "version" in data
        assert data["version"] == 1

    def test_homeiq_default_has_required_sections(self) -> None:
        """HomeIQ default config has expected sections for auto-bugfix.ps1."""
        data = _load_yaml(HOMEIQ_DEFAULT_PATH)
        expected = ["project", "runner", "scan", "fix", "mcp", "paths", "prompts"]
        for section in expected:
            assert section in data, f"Missing section: {section}"

    def test_homeiq_default_output_format_markers(self) -> None:
        """Scan output_format.markers has exactly 2 entries."""
        data = _load_yaml(HOMEIQ_DEFAULT_PATH)
        markers = data.get("scan", {}).get("output_format", {}).get("markers", [])
        assert len(markers) == 2, f"Expected 2 markers, got {len(markers)}"
        assert "<<<BUGS>>>" in markers
        assert "<<<END_BUGS>>>" in markers

    def test_homeiq_default_budget_allocation_sums_to_one(self) -> None:
        """Budget allocation ratios sum to 1.0."""
        data = _load_yaml(HOMEIQ_DEFAULT_PATH)
        ba = data.get("runner", {}).get("budget_allocation", {})
        total = sum(ba.get(k, 0) for k in ["scan", "fix", "chain", "feedback"])
        assert abs(total - 1.0) < 0.001, f"Budget allocation should sum to 1.0, got {total}"

    def test_homeiq_default_validate_against_schema(self) -> None:
        """HomeIQ default config validates against config-schema.json."""
        schema = _load_schema()
        data = _load_yaml(HOMEIQ_DEFAULT_PATH)
        errors = _validate_against_schema(data, schema)
        assert not errors, f"Schema validation failed: {errors}"
