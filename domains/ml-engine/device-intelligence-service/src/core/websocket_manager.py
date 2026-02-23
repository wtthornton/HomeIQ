"""
Device Intelligence Service - WebSocket Manager

WebSocket server for real-time device monitoring and updates.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and real-time device updates."""

    MAX_CONNECTIONS = 100  # Connection limit to prevent DoS (HIGH-4)

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.device_subscribers: dict[str, set[WebSocket]] = defaultdict(set)
        self.connection_info: dict[WebSocket, dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, client_id: str = None) -> bool:
        """Accept WebSocket connection with connection limit (HIGH-4)."""
        if len(self.active_connections) >= self.MAX_CONNECTIONS:
            await websocket.close(code=1013, reason="Too many connections")
            logger.warning("WebSocket connection rejected: max connections (%d) reached", self.MAX_CONNECTIONS)
            return False

        await websocket.accept()
        self.active_connections.append(websocket)

        # Store connection info
        self.connection_info[websocket] = {
            "client_id": client_id or f"client_{len(self.active_connections)}",
            "connected_at": datetime.now(timezone.utc),
            "subscribed_devices": set()
        }

        logger.info(f"WebSocket client connected: {self.connection_info[websocket]['client_id']}")

        # Send welcome message
        await self._send_to_client(websocket, {
            "type": "connection_established",
            "client_id": self.connection_info[websocket]["client_id"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return True

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

            # Remove from device subscribers
            if websocket in self.connection_info:
                client_info = self.connection_info[websocket]
                for device_id in client_info["subscribed_devices"]:
                    self.device_subscribers[device_id].discard(websocket)

                logger.info(f"WebSocket client disconnected: {client_info['client_id']}")
                del self.connection_info[websocket]

    async def subscribe_to_device(self, websocket: WebSocket, device_id: str):
        """Subscribe to device updates."""
        if websocket not in self.active_connections:
            return False

        self.device_subscribers[device_id].add(websocket)

        if websocket in self.connection_info:
            self.connection_info[websocket]["subscribed_devices"].add(device_id)

        logger.debug(f"Client {self.connection_info.get(websocket, {}).get('client_id', 'unknown')} subscribed to device {device_id}")

        # Send confirmation
        await self._send_to_client(websocket, {
            "type": "subscription_confirmed",
            "device_id": device_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return True

    async def unsubscribe_from_device(self, websocket: WebSocket, device_id: str):
        """Unsubscribe from device updates."""
        if websocket in self.device_subscribers[device_id]:
            self.device_subscribers[device_id].discard(websocket)

        if websocket in self.connection_info:
            self.connection_info[websocket]["subscribed_devices"].discard(device_id)

        logger.debug(f"Client unsubscribed from device {device_id}")

        # Send confirmation
        await self._send_to_client(websocket, {
            "type": "unsubscription_confirmed",
            "device_id": device_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    async def broadcast_device_update(self, device_id: str, update_data: dict[str, Any]):
        """Broadcast device update to subscribers."""
        if device_id not in self.device_subscribers or not self.device_subscribers[device_id]:
            return

        message = {
            "type": "device_update",
            "device_id": device_id,
            "data": update_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Send to all subscribers of this device
        disconnected_clients = set()
        for websocket in self.device_subscribers[device_id]:
            try:
                await self._send_to_client(websocket, message)
            except Exception as e:
                logger.warning(f"Failed to send update to client: {e}")
                disconnected_clients.add(websocket)

        # Clean up disconnected clients
        for websocket in disconnected_clients:
            self.device_subscribers[device_id].discard(websocket)
            if websocket in self.connection_info:
                self.connection_info[websocket]["subscribed_devices"].discard(device_id)

    async def broadcast_to_all(self, message: dict[str, Any]):
        """Broadcast message to all connected clients."""
        disconnected_clients = set()

        for websocket in self.active_connections:
            try:
                await self._send_to_client(websocket, message)
            except Exception as e:
                logger.warning(f"Failed to broadcast to client: {e}")
                disconnected_clients.add(websocket)

        # Clean up disconnected clients
        for websocket in disconnected_clients:
            self.disconnect(websocket)

    async def broadcast_health_alert(self, device_id: str, alert_type: str, alert_data: dict[str, Any]):
        """Broadcast health alert to all clients."""
        alert_message = {
            "type": "health_alert",
            "device_id": device_id,
            "alert_type": alert_type,
            "data": alert_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        await self.broadcast_to_all(alert_message)

    async def broadcast_system_status(self, status_data: dict[str, Any]):
        """Broadcast system status update."""
        status_message = {
            "type": "system_status",
            "data": status_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        await self.broadcast_to_all(status_message)

    async def _send_to_client(self, websocket: WebSocket, message: dict[str, Any]):
        """Send message to specific client."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send message to client: {e}")
            raise

    def get_connection_stats(self) -> dict[str, Any]:
        """Get WebSocket connection statistics."""
        return {
            "total_connections": len(self.active_connections),
            "total_device_subscriptions": sum(len(subscribers) for subscribers in self.device_subscribers.values()),
            "devices_with_subscribers": len(self.device_subscribers),
            "connection_details": [
                {
                    "client_id": info["client_id"],
                    "connected_at": info["connected_at"].isoformat(),
                    "subscribed_devices": list(info["subscribed_devices"])
                }
                for info in self.connection_info.values()
            ]
        }

    async def handle_client_message(self, websocket: WebSocket, message: dict[str, Any]):
        """Handle incoming client messages."""
        message_type = message.get("type")

        if message_type == "subscribe_device":
            device_id = message.get("device_id")
            if device_id:
                await self.subscribe_to_device(websocket, device_id)
            else:
                await self._send_to_client(websocket, {
                    "type": "error",
                    "message": "Missing device_id for subscription",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

        elif message_type == "unsubscribe_device":
            device_id = message.get("device_id")
            if device_id:
                await self.unsubscribe_from_device(websocket, device_id)
            else:
                await self._send_to_client(websocket, {
                    "type": "error",
                    "message": "Missing device_id for unsubscription",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

        elif message_type == "ping":
            await self._send_to_client(websocket, {
                "type": "pong",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        elif message_type == "get_stats":
            stats = self.get_connection_stats()
            await self._send_to_client(websocket, {
                "type": "connection_stats",
                "data": stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        else:
            await self._send_to_client(websocket, {
                "type": "error",
                "message": f"Unknown message type: {message_type}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
