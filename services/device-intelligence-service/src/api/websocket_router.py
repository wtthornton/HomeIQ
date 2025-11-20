"""
Device Intelligence Service - WebSocket API

WebSocket endpoints for real-time device monitoring.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from ..core.device_state_tracker import device_state_tracker
from ..core.performance_collector import performance_collector
from ..core.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time device monitoring."""
    client_id = f"client_{datetime.now().timestamp()}"

    try:
        await websocket_manager.connect(websocket, client_id)

        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                await websocket_manager.handle_client_message(websocket, message)
            except json.JSONDecodeError:
                await websocket_manager._send_to_client(websocket, {
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await websocket_manager._send_to_client(websocket, {
                    "type": "error",
                    "message": f"Internal error: {str(e)}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.info(f"WebSocket client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)


@router.get("/test", response_class=HTMLResponse)
async def websocket_test_page():
    """Simple WebSocket test page."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Device Intelligence WebSocket Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .connected { background-color: #d4edda; color: #155724; }
            .disconnected { background-color: #f8d7da; color: #721c24; }
            .messages { height: 300px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; }
            .message { margin: 5px 0; padding: 5px; background-color: #f8f9fa; }
            .controls { margin: 10px 0; }
            button { margin: 5px; padding: 5px 10px; }
            input { margin: 5px; padding: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Device Intelligence WebSocket Test</h1>
            
            <div id="status" class="status disconnected">Disconnected</div>
            
            <div class="controls">
                <button onclick="connect()">Connect</button>
                <button onclick="disconnect()">Disconnect</button>
                <button onclick="ping()">Ping</button>
                <button onclick="getStats()">Get Stats</button>
            </div>
            
            <div class="controls">
                <input type="text" id="deviceId" placeholder="Device ID" value="test-device">
                <button onclick="subscribeDevice()">Subscribe to Device</button>
                <button onclick="unsubscribeDevice()">Unsubscribe from Device</button>
            </div>
            
            <div class="controls">
                <button onclick="simulateDeviceUpdate()">Simulate Device Update</button>
                <button onclick="clearMessages()">Clear Messages</button>
            </div>
            
            <h3>Messages:</h3>
            <div id="messages" class="messages"></div>
        </div>

        <script>
            let ws = null;
            let messageCount = 0;

            function connect() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws/`;
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function(event) {
                    updateStatus('Connected', 'connected');
                    addMessage('Connected to WebSocket server');
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    addMessage(`Received: ${JSON.stringify(data, null, 2)}`);
                };
                
                ws.onclose = function(event) {
                    updateStatus('Disconnected', 'disconnected');
                    addMessage('Disconnected from WebSocket server');
                };
                
                ws.onerror = function(error) {
                    addMessage(`Error: ${error}`);
                };
            }

            function disconnect() {
                if (ws) {
                    ws.close();
                    ws = null;
                }
            }

            function ping() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({type: 'ping'}));
                    addMessage('Sent ping');
                }
            }

            function getStats() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({type: 'get_stats'}));
                    addMessage('Requested connection stats');
                }
            }

            function subscribeDevice() {
                const deviceId = document.getElementById('deviceId').value;
                if (ws && ws.readyState === WebSocket.OPEN && deviceId) {
                    ws.send(JSON.stringify({type: 'subscribe_device', device_id: deviceId}));
                    addMessage(`Subscribed to device: ${deviceId}`);
                }
            }

            function unsubscribeDevice() {
                const deviceId = document.getElementById('deviceId').value;
                if (ws && ws.readyState === WebSocket.OPEN && deviceId) {
                    ws.send(JSON.stringify({type: 'unsubscribe_device', device_id: deviceId}));
                    addMessage(`Unsubscribed from device: ${deviceId}`);
                }
            }

            function simulateDeviceUpdate() {
                const deviceId = document.getElementById('deviceId').value;
                if (deviceId) {
                    // This would normally be sent by the server, but for testing we'll simulate it
                    addMessage(`Simulated device update for: ${deviceId}`);
                }
            }

            function updateStatus(text, className) {
                const status = document.getElementById('status');
                status.textContent = text;
                status.className = `status ${className}`;
            }

            function addMessage(text) {
                const messages = document.getElementById('messages');
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message';
                messageDiv.innerHTML = `<strong>${++messageCount}:</strong> ${text}`;
                messages.appendChild(messageDiv);
                messages.scrollTop = messages.scrollHeight;
            }

            function clearMessages() {
                document.getElementById('messages').innerHTML = '';
                messageCount = 0;
            }

            // Auto-connect on page load
            window.onload = function() {
                connect();
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.get("/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    return {
        "websocket_manager": websocket_manager.get_connection_stats(),
        "device_state_tracker": device_state_tracker.get_stats(),
        "performance_collector": performance_collector.get_stats(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/broadcast/test")
async def broadcast_test_message(message: dict[str, Any]):
    """Broadcast test message to all connected clients."""
    await websocket_manager.broadcast_to_all({
        "type": "test_message",
        "data": message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    return {
        "status": "success",
        "message": "Test message broadcasted",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/device/{device_id}/simulate")
async def simulate_device_update(device_id: str, update_data: dict[str, Any] = None):
    """Simulate device update for testing."""
    if update_data is None:
        update_data = {
            "response_time": 150,
            "error_rate": 0.02,
            "battery_level": 85,
            "signal_strength": -65,
            "cpu_usage": 25,
            "memory_usage": 40,
            "temperature": 35,
            "uptime": 86400
        }

    # Update device state
    await device_state_tracker.update_device_state(device_id, update_data)

    # Collect performance metrics
    await performance_collector.collect_device_metrics(device_id, update_data)

    return {
        "status": "success",
        "message": f"Simulated update for device {device_id}",
        "device_id": device_id,
        "update_data": update_data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
