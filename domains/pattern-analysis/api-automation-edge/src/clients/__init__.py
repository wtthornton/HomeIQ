"""
Home Assistant API Clients

The WebSocket client is the shared homeiq_ha implementation (TAP-5440);
`make_ha_websocket_client` carries this service's settings-driven
construction (URL normalization, auto-reconnect tuning).
"""

from homeiq_ha.client import HAWebSocketClient

from ..config import settings
from .ha_metadata_client import HAMetadataClient
from .ha_rest_client import HARestClient

__all__ = [
    "HARestClient",
    "HAWebSocketClient",
    "HAMetadataClient",
    "make_ha_websocket_client",
]


def make_ha_websocket_client() -> HAWebSocketClient:
    """Build the shared WebSocket client from this service's settings."""
    url = settings.ha_ws_url or settings.ha_url or ""
    if url.startswith("http://"):
        url = url.replace("http://", "ws://", 1)
    elif url.startswith("https://"):
        url = url.replace("https://", "wss://", 1)
    if not url.endswith("/api/websocket"):
        url = url.rstrip("/") + "/api/websocket"
    return HAWebSocketClient(
        url,
        settings.ha_token or "",
        auto_reconnect=True,
        reconnect_delay=settings.ws_reconnect_delay,
        max_reconnect_attempts=settings.ws_max_reconnect_attempts,
    )
