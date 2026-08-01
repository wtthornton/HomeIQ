"""Exceptions raised by the Home Assistant client."""

from __future__ import annotations

from typing import Any


class HAClientError(Exception):
    """Base class for every Home Assistant client failure."""


class HAAuthError(HAClientError):
    """The access token was rejected during the WebSocket handshake."""


class HAClientClosed(HAClientError):
    """The connection was closed while a command was outstanding."""


class HACommandError(HAClientError):
    """Home Assistant answered a WebSocket command with ``success: false``.

    Attributes:
        code: Home Assistant's machine-readable error code, e.g. ``not_found``.
        command: The command type that failed.
    """

    def __init__(self, command: str, code: str, message: str) -> None:
        super().__init__(f"{command} failed ({code}): {message}")
        self.command = command
        self.code = code


class HAFlowError(HAClientError):
    """A config flow ended in a step the caller cannot advance past."""

    def __init__(self, message: str, step: dict[str, Any]) -> None:
        super().__init__(message)
        self.step = step
        self.flow_type: str = str(step.get("type", ""))

    @property
    def flow_id(self) -> str | None:
        value = self.step.get("flow_id")
        return str(value) if value is not None else None


class HAHumanGateRequired(HAFlowError):
    """The flow needs a person.

    Raised for ``external`` and ``progress`` steps, which Home Assistant core
    refuses to let a client advance on its own. The agent surfaces the URL or
    device code from :attr:`step` and waits rather than failing silently.
    """

    @property
    def external_url(self) -> str | None:
        value = self.step.get("url")
        return str(value) if value is not None else None

    @property
    def placeholders(self) -> dict[str, Any]:
        """Machine-readable prompt data, e.g. HACS's GitHub device code."""
        return dict(self.step.get("description_placeholders") or {})
