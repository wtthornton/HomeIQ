"""Loader for the normative tool catalogue (`docs/mcp/homeiq-mcp-tools.schema.json`).

The JSON file is the contract; this module only reads it. Tools flagged
`status: deferred` are loaded (so contract tests can see them) but never
registered.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

_REPO_RELATIVE = (
    Path(__file__).resolve().parents[4] / "docs" / "mcp" / "homeiq-mcp-tools.schema.json"
)
_IMAGE_PATH = Path("/app/catalogue/homeiq-mcp-tools.schema.json")


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    max_response_bytes: int
    read_only: bool
    status: str = "active"
    input_validator: Draft202012Validator = field(repr=False, compare=False, default=None)  # type: ignore[assignment]
    output_validator: Draft202012Validator = field(repr=False, compare=False, default=None)  # type: ignore[assignment]

    @property
    def deferred(self) -> bool:
        return self.status == "deferred"


@dataclass(frozen=True)
class Catalogue:
    version: str
    tools: dict[str, ToolSpec]
    source: Path

    def active(self) -> list[ToolSpec]:
        return [t for t in self.tools.values() if not t.deferred]


def resolve_catalogue_path(explicit: str = "") -> Path:
    for candidate in (explicit, os.environ.get("HOMEIQ_MCP_CATALOGUE_PATH", "")):
        if candidate:
            return Path(candidate)
    if _REPO_RELATIVE.exists():
        return _REPO_RELATIVE
    return _IMAGE_PATH


def load_catalogue(path: str | Path = "") -> Catalogue:
    source = Path(path) if path else resolve_catalogue_path()
    if not source.exists():
        raise FileNotFoundError(f"tool catalogue not found at {source}")
    raw = json.loads(source.read_text(encoding="utf-8"))
    tools: dict[str, ToolSpec] = {}
    for entry in raw["tools"]:
        Draft202012Validator.check_schema(entry["input_schema"])
        Draft202012Validator.check_schema(entry["output_schema"])
        spec = ToolSpec(
            name=entry["name"],
            description=entry["description"],
            input_schema=entry["input_schema"],
            output_schema=entry["output_schema"],
            max_response_bytes=int(entry["max_response_bytes"]),
            read_only=bool(entry.get("annotations", {}).get("readOnlyHint", False)),
            status=entry.get("status", "active"),
            input_validator=Draft202012Validator(entry["input_schema"]),
            output_validator=Draft202012Validator(entry["output_schema"]),
        )
        tools[spec.name] = spec
    return Catalogue(version=str(raw["catalogue_version"]), tools=tools, source=source)
