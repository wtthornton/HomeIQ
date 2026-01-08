"""
Home Assistant Event Subscriber

Subscribes to Home Assistant events to track automation executions.
Monitors automation_triggered and automation_error events.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class HAEvent:
    """Represents a Home Assistant event."""
    
    event_type: str
    data: dict[str, Any]
    origin: str
    time_fired: datetime
    context: dict[str, Any]


class HAEventSubscriber:
    """
    Subscribes to Home Assistant WebSocket events.
    
    Monitors:
    - automation_triggered: When an automation starts
    - call_service_executed: When a service call completes
    - automation_error: When an automation fails (custom event)
    
    Uses Home Assistant WebSocket API for real-time event streaming.
    """
    
    def __init__(
        self,
        ha_url: str,
        ha_token: str,
        on_execution: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ):
        """
        Initialize event subscriber.
        
        Args:
            ha_url: Home Assistant WebSocket URL (ws://host:8123/api/websocket)
            ha_token: Long-lived access token
            on_execution: Callback for execution events
        """
        self.ha_url = ha_url.replace("http://", "ws://").replace("https://", "wss://")
        if not self.ha_url.endswith("/api/websocket"):
            self.ha_url = f"{self.ha_url}/api/websocket"
        
        self.ha_token = ha_token
        self.on_execution = on_execution
        
        self._ws = None
        self._running = False
        self._message_id = 0
        self._pending_automations: dict[str, dict[str, Any]] = {}  # context_id -> start info
        
        logger.info(f"HAEventSubscriber initialized for {self.ha_url}")
    
    async def start(self) -> None:
        """Start listening for events."""
        if self._running:
            logger.warning("Event subscriber already running")
            return
        
        self._running = True
        
        try:
            await self._connect()
        except Exception as e:
            logger.error(f"Failed to start event subscriber: {e}")
            self._running = False
            raise
    
    async def stop(self) -> None:
        """Stop listening for events."""
        self._running = False
        
        if self._ws:
            await self._ws.close()
            self._ws = None
        
        logger.info("Event subscriber stopped")
    
    async def _connect(self) -> None:
        """Connect to Home Assistant WebSocket."""
        try:
            import websockets
        except ImportError:
            logger.error("websockets package not installed. Install with: pip install websockets")
            return
        
        logger.info(f"Connecting to Home Assistant WebSocket: {self.ha_url}")
        
        # Connect without context manager to manage lifecycle manually
        ws = await websockets.connect(self.ha_url)
        self._ws = ws
        
        try:
            # Wait for auth_required message
            auth_required = await ws.recv()
            auth_msg = json.loads(auth_required)
            
            if auth_msg.get("type") != "auth_required":
                raise Exception(f"Unexpected message: {auth_msg}")
            
            # Send auth
            await ws.send(json.dumps({
                "type": "auth",
                "access_token": self.ha_token,
            }))
            
            # Wait for auth_ok
            auth_result = await ws.recv()
            auth_result_msg = json.loads(auth_result)
            
            if auth_result_msg.get("type") != "auth_ok":
                raise Exception(f"Authentication failed: {auth_result_msg}")
            
            logger.info("Connected to Home Assistant WebSocket")
            
            # Subscribe to events
            await self._subscribe_to_events(ws)
            
            # Listen for events
            while self._running:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=30.0)
                    await self._handle_message(json.loads(message))
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    self._message_id += 1
                    await ws.send(json.dumps({
                        "id": self._message_id,
                        "type": "ping",
                    }))
                except Exception as e:
                    logger.error(f"Error receiving message: {e}")
                    if not self._running:
                        break
        except Exception as e:
            # Close websocket on error
            if ws:
                await ws.close()
            self._ws = None
            raise
    
    async def _subscribe_to_events(self, ws) -> None:
        """Subscribe to automation events."""
        # Subscribe to automation_triggered
        self._message_id += 1
        await ws.send(json.dumps({
            "id": self._message_id,
            "type": "subscribe_events",
            "event_type": "automation_triggered",
        }))
        
        # Subscribe to call_service events (to track action completion)
        self._message_id += 1
        await ws.send(json.dumps({
            "id": self._message_id,
            "type": "subscribe_events",
            "event_type": "call_service",
        }))
        
        # Subscribe to state_changed for automation entities
        self._message_id += 1
        await ws.send(json.dumps({
            "id": self._message_id,
            "type": "subscribe_events",
            "event_type": "state_changed",
        }))
        
        logger.info("Subscribed to automation events")
    
    async def _handle_message(self, message: dict[str, Any]) -> None:
        """Handle incoming WebSocket message."""
        msg_type = message.get("type")
        
        if msg_type == "event":
            event_data = message.get("event", {})
            event_type = event_data.get("event_type")
            
            if event_type == "automation_triggered":
                await self._handle_automation_triggered(event_data)
            elif event_type == "call_service":
                await self._handle_call_service(event_data)
            elif event_type == "state_changed":
                await self._handle_state_changed(event_data)
        elif msg_type == "result":
            # Handle subscription confirmations
            pass
        elif msg_type == "pong":
            # Ping response
            pass
    
    async def _handle_automation_triggered(self, event_data: dict[str, Any]) -> None:
        """Handle automation_triggered event."""
        data = event_data.get("data", {})
        context = event_data.get("context", {})
        
        automation_id = data.get("entity_id", "")
        context_id = context.get("id", "")
        
        # Store start time for this automation execution
        self._pending_automations[context_id] = {
            "automation_id": automation_id,
            "started_at": datetime.now(timezone.utc),
            "trigger": data.get("trigger", {}),
            "context": context,
        }
        
        logger.debug(f"Automation triggered: {automation_id} (context: {context_id})")
    
    async def _handle_call_service(self, event_data: dict[str, Any]) -> None:
        """Handle call_service event (action completion)."""
        data = event_data.get("data", {})
        context = event_data.get("context", {})
        
        # Check if this is part of a pending automation
        parent_id = context.get("parent_id")
        if parent_id and parent_id in self._pending_automations:
            # This service call is part of an automation
            pending = self._pending_automations[parent_id]
            
            # Track action
            if "actions" not in pending:
                pending["actions"] = []
            pending["actions"].append({
                "domain": data.get("domain"),
                "service": data.get("service"),
                "success": True,  # If we get the event, it succeeded
            })
    
    async def _handle_state_changed(self, event_data: dict[str, Any]) -> None:
        """Handle state_changed event for automation entities."""
        data = event_data.get("data", {})
        entity_id = data.get("entity_id", "")
        
        # Only care about automation entities
        if not entity_id.startswith("automation."):
            return
        
        new_state = data.get("new_state", {})
        old_state = data.get("old_state", {})
        
        # Check for state change indicating completion
        new_state_value = new_state.get("state")
        old_state_value = old_state.get("state") if old_state else None
        
        # Find matching pending automation
        for context_id, pending in list(self._pending_automations.items()):
            if pending["automation_id"] == entity_id:
                # Calculate execution time
                started_at = pending["started_at"]
                completed_at = datetime.now(timezone.utc)
                execution_time_ms = int((completed_at - started_at).total_seconds() * 1000)
                
                # Determine success (no error state)
                success = new_state_value != "unavailable"
                
                # Build execution record
                actions = pending.get("actions", [])
                execution_data = {
                    "automation_id": entity_id,
                    "execution_id": context_id,
                    "triggered_at": started_at.isoformat(),
                    "completed_at": completed_at.isoformat(),
                    "execution_time_ms": execution_time_ms,
                    "success": success,
                    "trigger_type": pending.get("trigger", {}).get("platform"),
                    "trigger_entity": pending.get("trigger", {}).get("entity_id"),
                    "actions_total": len(actions),
                    "actions_succeeded": sum(1 for a in actions if a.get("success")),
                    "actions_failed": sum(1 for a in actions if not a.get("success")),
                }
                
                # Notify callback
                if self.on_execution:
                    try:
                        await self.on_execution(execution_data)
                    except Exception as e:
                        logger.error(f"Error in execution callback: {e}")
                
                # Clean up pending
                del self._pending_automations[context_id]
                
                logger.debug(
                    f"Automation completed: {entity_id}, "
                    f"success={success}, time={execution_time_ms}ms"
                )
                break
    
    def get_pending_count(self) -> int:
        """Get number of pending automation executions."""
        return len(self._pending_automations)
    
    def cleanup_stale_pending(self, max_age_seconds: int = 300) -> int:
        """
        Clean up stale pending automations.
        
        Args:
            max_age_seconds: Maximum age before considering stale
            
        Returns:
            Number of stale entries removed
        """
        cutoff = datetime.now(timezone.utc)
        stale = []
        
        for context_id, pending in self._pending_automations.items():
            age = (cutoff - pending["started_at"]).total_seconds()
            if age > max_age_seconds:
                stale.append(context_id)
        
        for context_id in stale:
            del self._pending_automations[context_id]
        
        if stale:
            logger.warning(f"Cleaned up {len(stale)} stale pending automations")
        
        return len(stale)
