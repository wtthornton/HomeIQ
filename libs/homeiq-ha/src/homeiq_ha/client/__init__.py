"""Shared Home Assistant client.

Registries (entity, device, area, floor, label, category) are WebSocket-only in
Home Assistant. Several HomeIQ services reach for them over REST and receive a
404, which is why every "apply a fix to Home Assistant" path in HomeIQ has been
inert. :class:`~homeiq_ha.client.ws.HAWebSocketClient` is the shared fix.

Typical use::

    from homeiq_ha.client import HAClient

    async with HAClient.from_env() as ha:
        entities = await ha.ws.list_entities()
        devices = await ha.ws.list_devices()
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .errors import (
    HAAuthError,
    HAClientClosed,
    HAClientError,
    HACommandError,
    HAFlowError,
    HAHumanGateRequired,
)
from .redaction import REDACTED, redact, redact_text
from .rest import HARestClient
from .ws import (
    DEFAULT_COMMAND_TIMEOUT,
    SUPERVISOR_INSTALL_TIMEOUT,
    HAWebSocketClient,
)

if TYPE_CHECKING:
    from types import TracebackType

__all__ = [
    "DEFAULT_COMMAND_TIMEOUT",
    "REDACTED",
    "SUPERVISOR_INSTALL_TIMEOUT",
    "HAAuthError",
    "HAClient",
    "HAClientClosed",
    "HAClientError",
    "HACommandError",
    "HAFlowError",
    "HAHumanGateRequired",
    "HARestClient",
    "HAWebSocketClient",
    "redact",
    "redact_text",
    "websocket_url",
]


def websocket_url(http_url: str) -> str:
    """Derive the WebSocket API URL from an HTTP base URL.

    Public because a consumer that needs a custom ``ssl_context`` has to build
    :class:`HAWebSocketClient` directly — :class:`HAClient` does not forward one —
    and would otherwise have to re-implement this mapping.
    """
    base = http_url.rstrip("/")
    if base.startswith("https://"):
        return "wss://" + base[len("https://") :] + "/api/websocket"
    if base.startswith("http://"):
        return "ws://" + base[len("http://") :] + "/api/websocket"
    raise ValueError(f"Cannot derive a WebSocket URL from {http_url!r}")


# Retained for internal callers predating the public name.
_websocket_url = websocket_url


class HAClient:
    """Facade pairing the WebSocket and REST surfaces against one instance."""

    def __init__(self, base_url: str, token: str, *, ws_url: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.ws = HAWebSocketClient(ws_url or _websocket_url(base_url), token)
        self.rest = HARestClient(self.base_url, token)

    @classmethod
    def from_env(cls) -> HAClient:
        """Build a client from the environment.

        Reads ``HOME_ASSISTANT_URL``/``HOME_ASSISTANT_TOKEN``, falling back to
        the shorter ``HA_URL``/``HA_TOKEN`` names other HomeIQ services use.
        """
        base_url = os.environ.get("HOME_ASSISTANT_URL") or os.environ.get("HA_URL")
        token = os.environ.get("HOME_ASSISTANT_TOKEN") or os.environ.get("HA_TOKEN")
        if not base_url or not token:
            raise HAClientError(
                "Set HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN "
                "(or HA_URL and HA_TOKEN) to build an HAClient"
            )
        return cls(base_url, token)

    async def __aenter__(self) -> HAClient:
        await self.ws.connect()
        await self.rest.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.ws.close()
        await self.rest.close()
