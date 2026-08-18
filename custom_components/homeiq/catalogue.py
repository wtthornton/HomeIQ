"""Derive typed tool definitions from the HomeIQ MCP tool catalogue (TAP-5308).

The catalogue at ``docs/mcp/homeiq-mcp-tools.schema.json`` is the machine-readable
source of truth for the HomeIQ MCP server's tool contract. This module reads a
copy of that file shipped inside the integration and turns every non-deferred
entry into a :class:`ToolSpec` — no tool is ever hand-written here, so the
integration cannot drift from the server it talks to.

JSON Schema is converted to voluptuous with ``voluptuous_openapi``, which Home
Assistant already depends on and which round-trips the same dialect Home
Assistant uses to describe tools to a model. Two catalogue keywords the
converter does not model are handled here: ``default`` (attached to the
voluptuous marker so it reaches both validation and the model-facing schema) and
``dependentRequired`` (enforced by :meth:`ToolSpec.validate_arguments`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import voluptuous as vol
from voluptuous_openapi import convert_to_voluptuous

from .const import CATALOGUE_FILENAME

STATUS_DEFERRED = "deferred"


class Rfc3339(vol.Datetime):
    """Accept any RFC 3339 timestamp.

    ``voluptuous.Datetime`` matches one ``strptime`` pattern that insists on
    fractional seconds and a literal ``Z``, so it rejects timestamps the
    catalogue's ``format: date-time`` fields allow. Subclassing keeps the
    ``vol.Datetime`` identity that ``voluptuous_openapi.convert`` relies on to
    describe the field to a model as ``format: date-time``.
    """

    def __call__(self, value: Any) -> Any:
        """Return the value when it parses as an RFC 3339 date-time."""
        # A bare date parses but is not a date-time, which is what the
        # catalogue declares and what the upstream API expects.
        if not isinstance(value, str) or not any(sep in value for sep in "Tt "):
            raise vol.DatetimeInvalid(self.msg or "value is not an RFC 3339 timestamp")
        try:
            datetime.fromisoformat(value)
        except ValueError:
            raise vol.DatetimeInvalid(self.msg or "value is not an RFC 3339 timestamp") from None
        return value


@dataclass(frozen=True, kw_only=True)
class ToolSpec:
    """A single MCP tool, as declared by the catalogue."""

    name: str
    description: str
    parameters: vol.Schema
    read_only: bool
    max_response_bytes: int
    dependent_required: dict[str, list[str]] = field(default_factory=dict)

    def validate_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Validate and normalise arguments for a call to this tool.

        Applies catalogue defaults and raises :exc:`voluptuous.Invalid` when the
        arguments do not satisfy the declared schema.
        """
        validated: dict[str, Any] = self.parameters(arguments)
        for trigger, requires in self.dependent_required.items():
            if trigger not in validated:
                continue
            missing = [key for key in requires if key not in validated]
            if missing:
                raise vol.Invalid(f"{trigger} requires {', '.join(missing)}", path=[trigger])
        return validated


def _value_schema(spec: dict[str, Any]) -> Any:
    """Convert one property's JSON Schema into a voluptuous validator."""
    if spec.get("type") == "string" and spec.get("format") == "date-time":
        return Rfc3339()
    return convert_to_voluptuous(spec)


def _object_schema(input_schema: dict[str, Any]) -> vol.Schema:
    """Convert a catalogue ``input_schema`` object into a voluptuous schema."""
    required = set(input_schema.get("required", ()))
    properties: dict[Any, Any] = {}

    for key, spec in input_schema.get("properties", {}).items():
        marker_kwargs: dict[str, Any] = {"description": spec.get("description")}
        if key in required:
            marker: vol.Marker = vol.Required(key, **marker_kwargs)
        else:
            if "default" in spec:
                marker_kwargs["default"] = spec["default"]
            marker = vol.Optional(key, **marker_kwargs)
        properties[marker] = _value_schema(spec)

    extra = vol.ALLOW_EXTRA if input_schema.get("additionalProperties") else vol.PREVENT_EXTRA
    return vol.Schema(properties, extra=extra)


def tool_spec_from_entry(entry: dict[str, Any]) -> ToolSpec:
    """Build a :class:`ToolSpec` from one catalogue entry."""
    return ToolSpec(
        name=entry["name"],
        description=entry["description"],
        parameters=_object_schema(entry["input_schema"]),
        read_only=bool(entry.get("annotations", {}).get("readOnlyHint", False)),
        max_response_bytes=entry["max_response_bytes"],
        dependent_required=dict(entry["input_schema"].get("dependentRequired", {})),
    )


def load_catalogue(path: Path | None = None) -> tuple[str, list[ToolSpec]]:
    """Load the catalogue, returning its version and every available tool.

    Tools marked ``status: deferred`` are excluded: the catalogue declares them
    but the server has no live implementation behind them, so exposing them to a
    model would only produce failing calls.
    """
    source = path or Path(__file__).parent / CATALOGUE_FILENAME
    document = json.loads(source.read_text(encoding="utf-8"))
    specs = [
        tool_spec_from_entry(entry)
        for entry in document["tools"]
        if entry.get("status") != STATUS_DEFERRED
    ]
    return document["catalogue_version"], specs
