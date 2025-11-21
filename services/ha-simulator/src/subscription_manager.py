"""
Subscription Manager for HA Simulator

Handles WebSocket event subscriptions for HA Simulator.
"""

import json
import logging
from typing import Any

from aiohttp.web_ws import WebSocketResponse

logger = logging.getLogger(__name__)

class SubscriptionManager:
    """Manages WebSocket event subscriptions for HA Simulator"""

    def __init__(self):
        self.subscriptions: dict[WebSocketResponse, set[int]] = {}
        self.subscription_counter = 0

    async def handle_subscribe_events(self, ws: WebSocketResponse, message: dict[str, Any]):
        """Handle subscribe_events message"""
        subscription_id = message.get("id")
        if subscription_id is None:
            await self.send_subscription_error(ws, "Missing subscription ID")
            return

        # Add subscription
        if ws not in self.subscriptions:
            self.subscriptions[ws] = set()
        self.subscriptions[ws].add(subscription_id)

        # Send confirmation
        await self.send_subscription_result(ws, subscription_id, True)
        logger.info(f"Client subscribed to events with ID: {subscription_id}")

    async def send_subscription_result(self, ws: WebSocketResponse, subscription_id: int, success: bool):
        """Send subscription result"""
        result = {
            "id": subscription_id,
            "type": "result",
            "success": success,
            "result": None,
        }
        try:
            await ws.send_str(json.dumps(result))
            logger.debug(f"Sent subscription result: {subscription_id}, success: {success}")
        except Exception as e:
            logger.exception(f"Error sending subscription result: {e}")

    async def send_subscription_error(self, ws: WebSocketResponse, message: str):
        """Send subscription error"""
        error = {
            "type": "result",
            "success": False,
            "error": {
                "code": "invalid_format",
                "message": message,
            },
        }
        try:
            await ws.send_str(json.dumps(error))
            logger.warning(f"Sent subscription error: {message}")
        except Exception as e:
            logger.exception(f"Error sending subscription error: {e}")

    def has_subscriptions(self, ws: WebSocketResponse) -> bool:
        """Check if client has active subscriptions"""
        return ws in self.subscriptions and len(self.subscriptions[ws]) > 0

    def get_subscriptions(self, ws: WebSocketResponse) -> set[int]:
        """Get client's subscription IDs"""
        return self.subscriptions.get(ws, set())

    def remove_client(self, ws: WebSocketResponse):
        """Remove client and all subscriptions"""
        if ws in self.subscriptions:
            del self.subscriptions[ws]
            logger.info("Removed client subscriptions")

