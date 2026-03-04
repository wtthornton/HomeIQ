"""House status aggregation module.

Maintains in-memory state from Home Assistant events and serves
it via REST + WebSocket for real-time frontend consumption.
"""

from __future__ import annotations

from .aggregator import HouseStatusAggregator
from .models import HouseStatusResponse
from .websocket_publisher import StatusWebSocketPublisher

__all__ = [
    "HouseStatusAggregator",
    "HouseStatusResponse",
    "StatusWebSocketPublisher",
]
