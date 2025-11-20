"""
Authentication Manager for HA Simulator

Handles Home Assistant WebSocket authentication flow simulation.
"""

import json
import logging
from typing import Any

from aiohttp.web_ws import WebSocketResponse

logger = logging.getLogger(__name__)

class AuthenticationManager:
    """Manages WebSocket authentication for HA Simulator"""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.authenticated_clients: dict[WebSocketResponse, dict[str, Any]] = {}

    async def send_auth_required(self, ws: WebSocketResponse):
        """Send auth_required message to client"""
        auth_required = {
            "type": "auth_required",
            "ha_version": self.config.get("simulator", {}).get("version", "2025.10.1")
        }
        try:
            await ws.send_str(json.dumps(auth_required))
            logger.info("Sent auth_required to client")
        except Exception as e:
            logger.error(f"Error sending auth_required: {e}")

    async def handle_auth(self, ws: WebSocketResponse, message: dict[str, Any]) -> bool:
        """Handle authentication message"""
        access_token = message.get("access_token")
        expected_token = self.config.get("authentication", {}).get("token")

        if not access_token:
            await self.send_auth_invalid(ws, "Missing access_token")
            return False

        if access_token != expected_token:
            await self.send_auth_invalid(ws, "Invalid access_token")
            return False

        # Authentication successful
        await self.send_auth_ok(ws)
        self.authenticated_clients[ws] = {
            "authenticated": True,
            "token": access_token,
            "authenticated_at": json.dumps({"timestamp": "now"})  # Simplified for demo
        }
        logger.info("Client authenticated successfully")
        return True

    async def send_auth_ok(self, ws: WebSocketResponse):
        """Send auth_ok message"""
        auth_ok = {
            "type": "auth_ok",
            "ha_version": self.config.get("simulator", {}).get("version", "2025.10.1")
        }
        try:
            await ws.send_str(json.dumps(auth_ok))
            logger.info("Sent auth_ok to client")
        except Exception as e:
            logger.error(f"Error sending auth_ok: {e}")

    async def send_auth_invalid(self, ws: WebSocketResponse, message: str):
        """Send auth_invalid message"""
        auth_invalid = {
            "type": "auth_invalid",
            "message": message
        }
        try:
            await ws.send_str(json.dumps(auth_invalid))
            logger.warning(f"Sent auth_invalid to client: {message}")
        except Exception as e:
            logger.error(f"Error sending auth_invalid: {e}")

    def is_authenticated(self, ws: WebSocketResponse) -> bool:
        """Check if client is authenticated"""
        return ws in self.authenticated_clients

    def remove_client(self, ws: WebSocketResponse):
        """Remove client from authenticated clients"""
        if ws in self.authenticated_clients:
            del self.authenticated_clients[ws]
            logger.info("Removed client from authenticated clients")

