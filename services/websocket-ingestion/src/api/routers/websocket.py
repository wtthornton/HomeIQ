"""
WebSocket router for websocket-ingestion service.
"""

import json
import logging
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Annotated

from shared.logging_config import (
    generate_correlation_id,
    get_correlation_id,
    log_error_with_context,
    log_with_context,
    set_correlation_id,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time data streaming.
    
    Handles WebSocket connections and message routing.
    """
    # Generate correlation ID for this WebSocket connection
    corr_id = generate_correlation_id()
    set_correlation_id(corr_id)

    await websocket.accept()

    log_with_context(
        logger, "INFO", "WebSocket client connected",
        operation="websocket_connection",
        correlation_id=corr_id,
        client_ip=websocket.client.host if websocket.client else "unknown",
    )

    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "message": "Connected to HA Ingestor WebSocket",
            "correlation_id": corr_id
        })

        # Keep connection alive and handle messages
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                log_with_context(
                    logger, "DEBUG", "Received WebSocket message",
                    operation="websocket_message",
                    correlation_id=corr_id,
                    message_type=message_data.get("type", "unknown"),
                    message_size=len(data)
                )

                # Handle different message types
                if message_data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat(),
                        "correlation_id": corr_id
                    })
                elif message_data.get("type") == "subscribe":
                    # Handle subscription requests
                    channels = message_data.get("channels", [])
                    await websocket.send_json({
                        "type": "subscription",
                        "status": "subscribed",
                        "channels": channels,
                        "correlation_id": corr_id
                    })
                    log_with_context(
                        logger, "INFO", "WebSocket client subscribed to channels",
                        operation="websocket_subscription",
                        correlation_id=corr_id,
                        channels=channels
                    )
                else:
                    # Echo back unknown messages
                    await websocket.send_json({
                        "type": "echo",
                        "original": message_data,
                        "correlation_id": corr_id
                    })

            except json.JSONDecodeError as e:
                log_error_with_context(
                    logger, "Invalid JSON in WebSocket message", e,
                    operation="websocket_message_parse",
                    correlation_id=corr_id,
                    message_data=data[:100]  # First 100 chars for debugging
                )
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "correlation_id": corr_id
                })

    except WebSocketDisconnect:
        log_with_context(
            logger, "INFO", "WebSocket client disconnected",
            operation="websocket_disconnection",
            correlation_id=corr_id
        )
    except Exception as e:
        log_error_with_context(
            logger, "WebSocket handler error", e,
            operation="websocket_handler",
            correlation_id=corr_id
        )

