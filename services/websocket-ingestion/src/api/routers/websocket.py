"""
WebSocket router for websocket-ingestion service.
Epic 50 Story 50.2: Added security hardening (message validation, rate limiting)
"""

import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Annotated

from shared.logging_config import (
    generate_correlation_id,
    get_correlation_id,
    log_error_with_context,
    log_with_context,
    set_correlation_id,
)
from src.security import (
    get_rate_limiter,
    validate_message_json,
    validate_message_size,
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

        # Epic 50 Story 50.2: Initialize rate limiter for this connection
        rate_limiter = get_rate_limiter()
        connection_id = f"{corr_id}_{websocket.client.host if websocket.client else 'unknown'}"
        
        # Keep connection alive and handle messages
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            # Epic 50 Story 50.2: Validate message size
            size_valid, size_error = validate_message_size(data)
            if not size_valid:
                log_error_with_context(
                    logger, "WebSocket message size validation failed", None,
                    operation="websocket_message_validation",
                    correlation_id=corr_id,
                    error=size_error,
                    message_size=len(data.encode('utf-8'))
                )
                await websocket.send_json({
                    "type": "error",
                    "message": size_error,
                    "correlation_id": corr_id
                })
                continue
            
            # Epic 50 Story 50.2: Check rate limit
            rate_allowed, rate_error = rate_limiter.check_rate_limit(connection_id)
            if not rate_allowed:
                log_error_with_context(
                    logger, "WebSocket rate limit exceeded", None,
                    operation="websocket_rate_limit",
                    correlation_id=corr_id,
                    error=rate_error,
                    connection_id=connection_id
                )
                await websocket.send_json({
                    "type": "error",
                    "message": rate_error,
                    "correlation_id": corr_id
                })
                continue
            
            try:
                # Epic 50 Story 50.2: Validate JSON structure
                json_valid, message_data, json_error = validate_message_json(data)
                if not json_valid:
                    log_error_with_context(
                        logger, "WebSocket message JSON validation failed", None,
                        operation="websocket_message_validation",
                        correlation_id=corr_id,
                        error=json_error,
                        message_data=data[:100]  # First 100 chars for debugging
                    )
                    await websocket.send_json({
                        "type": "error",
                        "message": json_error,
                        "correlation_id": corr_id
                    })
                    continue
                
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
                        "timestamp": datetime.now(timezone.utc).isoformat(),
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
        # Epic 50 Story 50.2: Reset rate limiter on disconnect
        rate_limiter.reset(connection_id)
    except Exception as e:
        log_error_with_context(
            logger, "WebSocket handler error", e,
            operation="websocket_handler",
            correlation_id=corr_id
        )

