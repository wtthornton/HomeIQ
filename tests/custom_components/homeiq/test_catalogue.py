"""Tests for deriving typed tools from the MCP catalogue (TAP-5308)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import voluptuous as vol
from voluptuous_openapi import convert

from custom_components.homeiq.catalogue import (
    Rfc3339,
    load_catalogue,
    tool_spec_from_entry,
)
from custom_components.homeiq.const import CATALOGUE_FILENAME

PACKAGED = Path("custom_components/homeiq") / CATALOGUE_FILENAME
CANONICAL = Path("docs/mcp/homeiq-mcp-tools.schema.json")


def spec_named(name: str):
    """Return the loaded spec for one tool."""
    _, specs = load_catalogue()
    return next(spec for spec in specs if spec.name == name)


def test_packaged_catalogue_matches_the_canonical_one() -> None:
    """The shipped copy must be byte-identical to docs/mcp."""
    assert PACKAGED.read_bytes() == CANONICAL.read_bytes()


def test_every_non_deferred_tool_is_derived() -> None:
    """Loading yields the catalogue version and one spec per live tool."""
    document = json.loads(CANONICAL.read_text())
    expected = [tool["name"] for tool in document["tools"] if tool.get("status") != "deferred"]

    version, specs = load_catalogue()

    assert version == document["catalogue_version"]
    assert [spec.name for spec in specs] == expected


def test_deferred_tools_are_skipped() -> None:
    """A tool the server has no implementation for is never exposed."""
    document = json.loads(CANONICAL.read_text())
    deferred = [tool["name"] for tool in document["tools"] if tool.get("status") == "deferred"]

    _, specs = load_catalogue()

    assert deferred, "the catalogue is expected to carry deferred tools"
    assert not {spec.name for spec in specs} & set(deferred)


def test_read_only_hint_and_budget_are_carried() -> None:
    """Annotations and byte budgets survive the conversion."""
    spec = spec_named("get_entity_history")

    assert spec.read_only is True
    assert spec.max_response_bytes == 65536


def test_v1_catalogue_is_entirely_read_only() -> None:
    """Nothing exposed in v1 mutates the home."""
    _, specs = load_catalogue()

    assert all(spec.read_only for spec in specs)


def test_defaults_are_applied_on_validation() -> None:
    """Catalogue defaults reach the call, not just the schema."""
    validated = spec_named("get_entity_history").validate_arguments(
        {"entity_id": "sensor.total_power"}
    )

    assert validated == {
        "entity_id": "sensor.total_power",
        "hours": 24,
        "downsample_minutes": 0,
        "limit": 500,
    }


def test_required_argument_is_enforced() -> None:
    """A missing required argument is rejected."""
    with pytest.raises(vol.Invalid):
        spec_named("get_entity_history").validate_arguments({})


def test_additional_properties_false_rejects_extras() -> None:
    """additionalProperties: false becomes PREVENT_EXTRA."""
    with pytest.raises(vol.Invalid, match="extra keys not allowed"):
        spec_named("get_entity_state").validate_arguments(
            {"entity_id": "light.kitchen", "bogus": 1}
        )


@pytest.mark.parametrize("hours", [0, 721])
def test_integer_bounds_are_enforced(hours: int) -> None:
    """minimum/maximum become a vol.Range."""
    with pytest.raises(vol.Invalid):
        spec_named("get_entity_history").validate_arguments(
            {"entity_id": "sensor.x", "hours": hours}
        )


def test_enum_is_enforced_and_described() -> None:
    """enum becomes vol.In and still reaches the model as an enum."""
    spec = spec_named("detect_anomalies")

    with pytest.raises(vol.Invalid):
        spec.validate_arguments({"kind": "nonsense"})
    assert spec.validate_arguments({"kind": "power"})["kind"] == "power"
    assert convert(spec.parameters)["properties"]["kind"]["enum"] == [
        "power",
        "failure_risk",
        "all",
    ]


def test_string_pattern_is_enforced() -> None:
    """A pattern on an id that reaches an upstream URL path is applied."""
    spec = spec_named("get_entity_state")

    with pytest.raises(vol.Invalid):
        spec.validate_arguments({"entity_id": "light kitchen/../etc"})


def test_string_length_bounds_are_enforced() -> None:
    """minLength/maxLength become a vol.Length."""
    spec = spec_named("search_events")

    with pytest.raises(vol.Invalid):
        spec.validate_arguments({"query": ""})
    with pytest.raises(vol.Invalid):
        spec.validate_arguments({"query": "x" * 201})


def test_dependent_required_is_enforced() -> None:
    """start_time without end_time is rejected, together they are accepted."""
    spec = spec_named("get_entity_history")

    with pytest.raises(vol.Invalid, match="start_time requires end_time"):
        spec.validate_arguments({"entity_id": "sensor.x", "start_time": "2026-08-17T00:00:00Z"})

    validated = spec.validate_arguments(
        {
            "entity_id": "sensor.x",
            "start_time": "2026-08-17T00:00:00Z",
            "end_time": "2026-08-18T00:00:00Z",
        }
    )
    assert validated["end_time"] == "2026-08-18T00:00:00Z"


@pytest.mark.parametrize(
    "value",
    ["2026-08-17T00:00:00Z", "2026-08-17T00:00:00+02:00", "2026-08-17T00:00:00.123456Z"],
)
def test_rfc3339_accepts_real_timestamps(value: str) -> None:
    """Every RFC 3339 spelling the catalogue allows is accepted."""
    assert Rfc3339()(value) == value


@pytest.mark.parametrize("value", ["yesterday", "2026-08-17", 17])
def test_rfc3339_rejects_non_timestamps(value: object) -> None:
    """Anything that is not a timestamp is rejected."""
    with pytest.raises(vol.Invalid):
        Rfc3339()(value)


def test_datetime_field_still_advertises_its_format() -> None:
    """The model-facing schema keeps format: date-time."""
    schema = convert(spec_named("get_entity_history").parameters)

    assert schema["properties"]["start_time"]["format"] == "date-time"


def test_additional_properties_true_allows_extras() -> None:
    """A catalogue entry that allows extras converts to ALLOW_EXTRA."""
    spec = tool_spec_from_entry(
        {
            "name": "permissive",
            "description": "accepts anything extra",
            "annotations": {"readOnlyHint": True},
            "max_response_bytes": 1024,
            "input_schema": {
                "type": "object",
                "additionalProperties": True,
                "properties": {"limit": {"type": "integer", "minimum": 1}},
            },
        }
    )

    assert spec.validate_arguments({"limit": 5, "extra": "kept"}) == {
        "limit": 5,
        "extra": "kept",
    }
