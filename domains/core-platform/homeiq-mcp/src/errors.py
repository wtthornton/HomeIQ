"""Tool-error contract for the homeiq MCP server.

Every tool failure is surfaced to the agent as MCP tool-error content carrying
one of the catalogue's fixed codes — never a raw upstream traceback
(catalogue "Server-level contract notes").
"""

from __future__ import annotations

from typing import Literal

ErrorCode = Literal[
    "backing_unavailable",
    "invalid_input",
    "not_found",
    "contract_violation",
]


class ToolError(Exception):
    """A tool failure with a catalogue error code and an agent-readable message."""

    def __init__(self, code: ErrorCode, message: str, *, tool: str | None = None) -> None:
        super().__init__(message)
        self.code: ErrorCode = code
        self.message = message
        self.tool = tool

    def to_payload(self) -> dict[str, str]:
        payload = {"code": self.code, "message": self.message}
        if self.tool:
            payload["tool"] = self.tool
        return payload
