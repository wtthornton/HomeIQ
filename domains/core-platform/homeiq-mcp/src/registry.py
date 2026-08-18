"""Tool registry: binds catalogue specs to handlers and enforces the contract.

Dispatch order for every call: input validation (`invalid_input`) → write grant
(design rule 1) → handler → budget enforcement (design rule 2) → output
validation (`contract_violation`).
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import mcp.types as types
from jsonschema import ValidationError

from .budget import enforce_budget, payload_size
from .errors import ToolError

if TYPE_CHECKING:
    from .catalogue import Catalogue, ToolSpec

logger = logging.getLogger("homeiq_mcp.registry")

Handler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


Recount = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class RegisteredTool:
    spec: ToolSpec
    handler: Handler
    narrow_hint: str | None
    recount: Recount | None


class ToolRegistry:
    def __init__(
        self, catalogue: Catalogue, *, allowed_write_tools: frozenset[str] = frozenset()
    ) -> None:
        self.catalogue = catalogue
        self.allowed_write_tools = allowed_write_tools
        self._tools: dict[str, RegisteredTool] = {}

    def register(
        self, name: str, *, narrow_hint: str | None = "limit", recount: Recount | None = None
    ) -> Callable[[Handler], Handler]:
        """Bind a handler. `narrow_hint` names the input the agent should narrow when the
        response is truncated (None for tools with no narrowing input); `recount` runs after
        budget truncation to fix derived counters the generic budget cannot know about."""
        spec = self.catalogue.tools.get(name)
        if spec is None:
            raise KeyError(f"{name!r} is not in catalogue v{self.catalogue.version}")
        if spec.deferred:
            raise ValueError(
                f"{name!r} is deferred in catalogue v{self.catalogue.version}; do not register it"
            )

        def decorator(fn: Handler) -> Handler:
            if name in self._tools:
                raise ValueError(f"tool {name!r} registered twice")
            self._tools[name] = RegisteredTool(
                spec=spec, handler=fn, narrow_hint=narrow_hint, recount=recount
            )
            return fn

        return decorator

    def names(self) -> list[str]:
        return sorted(self._tools)

    def unregistered_active(self) -> list[str]:
        """Catalogue tools that are active but have no handler yet (visible in /health)."""
        return sorted(t.name for t in self.catalogue.active() if t.name not in self._tools)

    def list_tools(self) -> list[types.Tool]:
        return [
            types.Tool(
                name=t.spec.name,
                description=t.spec.description,
                input_schema=t.spec.input_schema,
                output_schema=t.spec.output_schema,
                annotations=types.ToolAnnotations(read_only_hint=t.spec.read_only),
            )
            for t in (self._tools[n] for n in self.names())
        ]

    def _check_write_grant(self, spec: ToolSpec, scopes: frozenset[str]) -> None:
        if spec.read_only:
            return
        if "mutate" not in scopes:
            raise ToolError(
                "invalid_input",
                f"{spec.name} mutates state; the caller's token is read-only",
                tool=spec.name,
            )
        if spec.name not in self.allowed_write_tools:
            raise ToolError(
                "invalid_input",
                f"{spec.name} is not granted: set HOMEIQ_MCP_ALLOW_WRITES to include it",
                tool=spec.name,
            )

    async def call(
        self, name: str, arguments: dict[str, Any] | None, *, scopes: frozenset[str]
    ) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolError("not_found", f"unknown tool {name!r}", tool=name)
        spec = tool.spec
        args = dict(arguments or {})
        try:
            spec.input_validator.validate(args)
        except ValidationError as exc:
            path = "/".join(str(p) for p in exc.absolute_path) or "(root)"
            raise ToolError("invalid_input", f"{path}: {exc.message}", tool=name) from exc
        self._check_write_grant(spec, scopes)
        payload = await tool.handler(args)
        before = payload_size(payload)
        payload = enforce_budget(payload, spec.max_response_bytes, tool.narrow_hint)
        if tool.recount is not None and payload_size(payload) != before:
            tool.recount(payload)
        try:
            spec.output_validator.validate(payload)
        except ValidationError as exc:
            path = "/".join(str(p) for p in exc.absolute_path) or "(root)"
            logger.error("contract violation in %s at %s: %s", name, path, exc.message)
            raise ToolError(
                "contract_violation",
                f"{name} produced an off-contract response at {path}",
                tool=name,
            ) from exc
        return payload
