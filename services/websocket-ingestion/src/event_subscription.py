"""
Event Subscription Manager for Home Assistant WebSocket
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import json

from .message_id_manager import get_message_id_manager

logger = logging.getLogger(__name__)


class EventSubscriptionManager:
    """Manages WebSocket event subscriptions with Home Assistant"""
    
    def __init__(self):
        self.subscriptions: Dict[int, Dict[str, Any]] = {}
        self.message_id_manager = get_message_id_manager()  # Use centralized manager
        self.is_subscribed = False
        self.subscription_handlers: Dict[str, Callable] = {}
        
        # Event statistics
        self.total_events_received = 0
        self.events_by_type: Dict[str, int] = {}
        self.last_event_time: Optional[datetime] = None
        self.subscription_start_time: Optional[datetime] = None
    
    async def subscribe_to_events(self, websocket_client, event_types: List[str] = None) -> bool:
        """
        Subscribe to Home Assistant events
        
        Args:
            websocket_client: The WebSocket client instance
            event_types: List of event types to subscribe to (default: ['state_changed'])
            
        Returns:
            True if subscription successful, False otherwise
        """
        if event_types is None:
            event_types = ['state_changed']
        
        try:
            logger.info("=" * 80)
            logger.info("📡 STARTING EVENT SUBSCRIPTION")
            logger.info("=" * 80)
            logger.info(f"📋 Event types to subscribe: {event_types}")
            logger.info(f"🔌 WebSocket client connected: {websocket_client.is_connected}")
            logger.info(f"🔐 WebSocket client authenticated: {websocket_client.is_authenticated}")
            
            # Pre-flight checks
            if not websocket_client.is_connected:
                logger.error("❌ Cannot subscribe: WebSocket not connected")
                return False
            
            if not websocket_client.is_authenticated:
                logger.error("❌ Cannot subscribe: WebSocket not authenticated")
                return False
            
            logger.info("✅ Pre-flight checks passed")
            
            # Create subscription message using centralized message ID manager
            subscription_id = await self.message_id_manager.get_next_id()
            
            subscription_message = {
                "id": subscription_id,
                "type": "subscribe_events",
                "event_type": event_types[0] if len(event_types) == 1 else None
            }
            
            logger.info(f"📤 Sending subscription message:")
            logger.info(f"   ID: {subscription_id}")
            logger.info(f"   Type: subscribe_events")
            logger.info(f"   Event Type: {event_types[0] if len(event_types) == 1 else 'all'}")
            logger.info(f"   Full message: {json.dumps(subscription_message, indent=2)}")
            
            # If subscribing to multiple event types, we need separate subscriptions
            if len(event_types) > 1:
                success = True
                for event_type in event_types:
                    sub_id = await self.message_id_manager.get_next_id()
                    
                    sub_message = {
                        "id": sub_id,
                        "type": "subscribe_events",
                        "event_type": event_type
                    }
                    
                    if not await websocket_client.send_message(sub_message):
                        logger.error(f"Failed to send subscription message for {event_type}")
                        success = False
                        break
                    
                    self.subscriptions[sub_id] = {
                        "event_type": event_type,
                        "subscribed_at": datetime.now(),
                        "status": "pending"
                    }
                
                if success:
                    self.is_subscribed = True
                    self.subscription_start_time = datetime.now()
                    logger.info(f"Successfully subscribed to {len(event_types)} event types")
                
                return success
            else:
                # Single event type subscription
                send_result = await websocket_client.send_message(subscription_message)
                logger.info(f"📨 Send result: {send_result}")
                
                if send_result:
                    self.subscriptions[subscription_id] = {
                        "event_type": event_types[0],
                        "subscribed_at": datetime.now(),
                        "status": "pending"
                    }
                    self.is_subscribed = True
                    self.subscription_start_time = datetime.now()
                    logger.info("=" * 80)
                    logger.info(f"✅ SUBSCRIPTION SUCCESSFUL: {event_types[0]} events")
                    logger.info(f"🆔 Subscription ID: {subscription_id}")
                    logger.info(f"⏰ Subscribed at: {datetime.now().isoformat()}")
                    logger.info("=" * 80)
                    return True
                else:
                    logger.error("=" * 80)
                    logger.error("❌ SUBSCRIPTION FAILED: Could not send message")
                    logger.error("=" * 80)
                    return False
                    
        except Exception as e:
            logger.error(f"Error subscribing to events: {e}")
            return False
    
    async def handle_subscription_result(self, message: Dict[str, Any]) -> bool:
        """
        Handle subscription result message from Home Assistant
        
        Args:
            message: The subscription result message
            
        Returns:
            True if subscription was successful, False otherwise
        """
        try:
            if message.get("type") == "result":
                subscription_id = message.get("id")
                success = message.get("success", False)
                
                logger.info("=" * 80)
                logger.info("📥 SUBSCRIPTION RESULT RECEIVED")
                logger.info(f"🆔 Subscription ID: {subscription_id}")
                logger.info(f"✅ Success: {success}")
                logger.info(f"📄 Full message: {json.dumps(message, indent=2)}")
                
                if subscription_id in self.subscriptions:
                    if success:
                        self.subscriptions[subscription_id]["status"] = "active"
                        logger.info(f"🎉 Subscription {subscription_id} CONFIRMED for {self.subscriptions[subscription_id]['event_type']}")
                        logger.info("=" * 80)
                    else:
                        self.subscriptions[subscription_id]["status"] = "failed"
                        error = message.get("error", {})
                        logger.error(f"❌ Subscription {subscription_id} FAILED: {error}")
                        logger.error("=" * 80)
                        return False
                else:
                    logger.warning(f"⚠️  Received result for unknown subscription {subscription_id}")
                    logger.warning("=" * 80)
                
                return success
            else:
                logger.debug(f"📨 Received non-result message: {message.get('type')}")
                return True
                
        except Exception as e:
            logger.error(f"Error handling subscription result: {e}")
            return False
    
    async def handle_event_message(self, message: Dict[str, Any]) -> bool:
        """
        Handle incoming event message from Home Assistant
        
        Args:
            message: The event message
            
        Returns:
            True if event was processed successfully, False otherwise
        """
        try:
            if message.get("type") == "event":
                event_data = message.get("event", {})
                event_type = event_data.get("event_type")
                
                if event_type:
                    # Update statistics
                    self.total_events_received += 1
                    self.events_by_type[event_type] = self.events_by_type.get(event_type, 0) + 1
                    self.last_event_time = datetime.now()
                    
                    # Log basic event information (every 10th event to avoid spam)
                    if self.total_events_received % 10 == 1:
                        logger.info(f"📨 Received event #{self.total_events_received}: {event_type} - {self._extract_event_summary(event_data)}")
                    else:
                        logger.debug(f"📨 Event #{self.total_events_received}: {event_type}")
                    
                    # Call event handler if registered
                    if event_type in self.subscription_handlers:
                        await self.subscription_handlers[event_type](event_data)
                    
                    return True
                else:
                    logger.warning("Received event without event_type")
                    return False
            else:
                logger.debug(f"Received non-event message: {message.get('type')}")
                return True
                
        except Exception as e:
            logger.error(f"Error handling event message: {e}")
            return False
    
    def _extract_event_summary(self, event_data: Dict[str, Any]) -> str:
        """
        Extract summary information from event data
        
        Args:
            event_data: The event data dictionary
            
        Returns:
            String summary of the event
        """
        try:
            if event_data.get("event_type") == "state_changed":
                old_state = event_data.get("old_state", {})
                new_state = event_data.get("new_state", {})
                
                entity_id = new_state.get("entity_id", old_state.get("entity_id", "unknown"))
                old_state_value = old_state.get("state", "unknown")
                new_state_value = new_state.get("state", "unknown")
                
                return f"entity_id={entity_id}, {old_state_value} -> {new_state_value}"
            else:
                return f"event_type={event_data.get('event_type', 'unknown')}"
                
        except Exception as e:
            logger.error(f"Error extracting event summary: {e}")
            return "error_extracting_summary"
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """
        Register a handler for a specific event type
        
        Args:
            event_type: The event type to handle
            handler: The handler function
        """
        self.subscription_handlers[event_type] = handler
        logger.info(f"Registered handler for {event_type} events")
    
    async def resubscribe_after_reconnection(self, websocket_client) -> bool:
        """
        Resubscribe to events after reconnection
        
        Args:
            websocket_client: The WebSocket client instance
            
        Returns:
            True if resubscription successful, False otherwise
        """
        if not self.subscriptions:
            logger.info("No previous subscriptions to restore")
            return True
        
        logger.info("Resubscribing to events after reconnection")
        
        # Get list of event types that were previously subscribed
        event_types = [sub["event_type"] for sub in self.subscriptions.values()]
        
        # Clear previous subscriptions
        self.subscriptions.clear()
        self.is_subscribed = False
        
        # Resubscribe
        return await self.subscribe_to_events(websocket_client, event_types)
    
    def get_subscription_status(self) -> Dict[str, Any]:
        """
        Get current subscription status
        
        Returns:
            Dictionary with subscription status information
        """
        active_subscriptions = sum(1 for sub in self.subscriptions.values() if sub["status"] == "active")
        pending_subscriptions = sum(1 for sub in self.subscriptions.values() if sub["status"] == "pending")
        failed_subscriptions = sum(1 for sub in self.subscriptions.values() if sub["status"] == "failed")
        
        return {
            "is_subscribed": self.is_subscribed,
            "total_subscriptions": len(self.subscriptions),
            "active_subscriptions": active_subscriptions,
            "pending_subscriptions": pending_subscriptions,
            "failed_subscriptions": failed_subscriptions,
            "subscription_start_time": self.subscription_start_time.isoformat() if self.subscription_start_time else None,
            "total_events_received": self.total_events_received,
            "events_by_type": self.events_by_type.copy(),
            "last_event_time": self.last_event_time.isoformat() if self.last_event_time else None,
            "registered_handlers": list(self.subscription_handlers.keys())
        }
    
    def reset_statistics(self):
        """Reset event statistics"""
        self.total_events_received = 0
        self.events_by_type.clear()
        self.last_event_time = None
        logger.info("Event statistics reset")
