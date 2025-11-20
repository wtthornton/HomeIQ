"""
WebSocket Server for HA Simulator

Implements Home Assistant WebSocket API compatibility for development and testing.
"""

import json
import logging
from typing import Any

from aiohttp import WSMsgType, web
from aiohttp.web_ws import WebSocketResponse
from authentication import AuthenticationManager
from subscription_manager import SubscriptionManager

logger = logging.getLogger(__name__)

class HASimulatorWebSocketServer:
    """WebSocket server that simulates Home Assistant API"""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.clients: set[WebSocketResponse] = set()
        self.auth_manager = AuthenticationManager(config)
        self.subscription_manager = SubscriptionManager()
        self.app = None
        self.runner = None
        self.site = None

    async def websocket_handler(self, request):
        """Handle WebSocket connections"""
        ws = WebSocketResponse()
        await ws.prepare(request)

        self.clients.add(ws)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")

        # Send auth_required immediately
        await self.auth_manager.send_auth_required(ws)

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self.handle_message(ws, msg.data)
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
                elif msg.type == WSMsgType.CLOSE:
                    logger.info("Client closed connection")
                    break
        except Exception as e:
            logger.error(f"Error in WebSocket handler: {e}")
        finally:
            self.clients.remove(ws)
            self.subscription_manager.remove_client(ws)
            logger.info(f"Client disconnected. Total clients: {len(self.clients)}")

    async def handle_message(self, ws: WebSocketResponse, data: str):
        """Handle incoming WebSocket messages"""
        try:
            message = json.loads(data)
            message_type = message.get("type")

            logger.debug(f"Received message: {message_type}")

            if message_type == "auth":
                await self.auth_manager.handle_auth(ws, message)
            elif message_type == "subscribe_events":
                if self.auth_manager.is_authenticated(ws):
                    await self.subscription_manager.handle_subscribe_events(ws, message)
                else:
                    await self.send_error(ws, "Authentication required")
            else:
                logger.warning(f"Unknown message type: {message_type}")
                await self.send_error(ws, f"Unknown message type: {message_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON message: {e}")
            await self.send_error(ws, "Invalid JSON")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self.send_error(ws, "Internal error")

    async def send_error(self, ws: WebSocketResponse, message: str):
        """Send error message to client"""
        error_msg = {
            "type": "result",
            "success": False,
            "error": {
                "code": "unknown_error",
                "message": message
            }
        }
        try:
            await ws.send_str(json.dumps(error_msg))
        except Exception as e:
            logger.error(f"Error sending error message: {e}")

    async def broadcast_event(self, event: dict[str, Any]):
        """Broadcast event to all authenticated and subscribed clients"""
        if not event:
            return

        disconnected_clients = set()

        for client in self.clients:
            try:
                if (self.auth_manager.is_authenticated(client) and
                    self.subscription_manager.has_subscriptions(client)):
                    await client.send_str(json.dumps(event))
            except Exception as e:
                logger.error(f"Error sending event to client: {e}")
                disconnected_clients.add(client)

        # Remove disconnected clients
        for client in disconnected_clients:
            self.clients.remove(client)
            self.subscription_manager.remove_client(client)

    async def health_check(self, request):
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "service": "ha-simulator",
            "version": self.config["simulator"]["version"],
            "clients": len(self.clients),
            "authenticated_clients": len([
                c for c in self.clients
                if self.auth_manager.is_authenticated(c)
            ]),
            "subscribed_clients": len([
                c for c in self.clients
                if self.subscription_manager.has_subscriptions(c)
            ])
        })

    async def start_server(self):
        """Start the WebSocket server"""
        self.app = web.Application()
        self.app.router.add_get('/api/websocket', self.websocket_handler)
        self.app.router.add_get('/health', self.health_check)

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        port = self.config["simulator"]["port"]
        self.site = web.TCPSite(self.runner, '0.0.0.0', port)
        await self.site.start()

        logger.info(f"HA Simulator WebSocket server started on port {port}")

    async def stop_server(self):
        """Stop the WebSocket server"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("HA Simulator WebSocket server stopped")

