"""
Health Check Handler for WebSocket Ingestion Service
"""

import logging
from typing import Optional
from aiohttp import web
from datetime import datetime

logger = logging.getLogger(__name__)


class HealthCheckHandler:
    """Handles health check requests"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.connection_manager: Optional[object] = None
    
    def set_connection_manager(self, connection_manager):
        """Set the connection manager for health checks"""
        self.connection_manager = connection_manager
    
    async def handle(self, request):
        """Handle health check request - optimized for fast response"""
        try:
            # Basic health check - service is running (fast response)
            health_data = {
                "status": "healthy",
                "service": "websocket-ingestion",
                "uptime": str(datetime.now() - self.start_time),
                "timestamp": datetime.now().isoformat()
            }
            
            # Add minimal connection status without blocking operations
            if self.connection_manager:
                # Only access simple attributes that won't block
                health_data["connection"] = {
                    "is_running": getattr(self.connection_manager, 'is_running', False),
                    "connection_attempts": getattr(self.connection_manager, 'connection_attempts', 0),
                    "successful_connections": getattr(self.connection_manager, 'successful_connections', 0),
                    "failed_connections": getattr(self.connection_manager, 'failed_connections', 0)
                }
                
                # Add subscription status
                event_subscription = getattr(self.connection_manager, 'event_subscription', None)
                if event_subscription:
                    sub_status = event_subscription.get_subscription_status()
                    health_data["subscription"] = {
                        "is_subscribed": sub_status.get("is_subscribed", False),
                        "active_subscriptions": sub_status.get("active_subscriptions", 0),
                        "total_events_received": sub_status.get("total_events_received", 0),
                        "events_by_type": sub_status.get("events_by_type", {}),
                        "last_event_time": sub_status.get("last_event_time")
                    }
                    
                    # Calculate event rate (events per minute)
                    if sub_status.get("last_event_time") and sub_status.get("subscription_start_time"):
                        try:
                            last_event = datetime.fromisoformat(sub_status["last_event_time"])
                            start_time = datetime.fromisoformat(sub_status["subscription_start_time"])
                            duration_minutes = (last_event - start_time).total_seconds() / 60
                            if duration_minutes > 0:
                                event_rate = sub_status.get("total_events_received", 0) / duration_minutes
                                health_data["subscription"]["event_rate_per_minute"] = round(event_rate, 2)
                        except Exception:
                            pass
                else:
                    health_data["subscription"] = {"status": "not_initialized"}
                
                # Enhanced health determination
                if not getattr(self.connection_manager, 'is_running', False):
                    health_data["status"] = "unhealthy"
                    health_data["reason"] = "Connection manager not running"
                elif getattr(self.connection_manager, 'failed_connections', 0) > 5:
                    health_data["status"] = "degraded"
                    health_data["reason"] = "Multiple connection failures"
                elif event_subscription and not event_subscription.is_subscribed:
                    health_data["status"] = "degraded"
                    health_data["reason"] = "Not subscribed to events"
                elif event_subscription and event_subscription.total_events_received == 0:
                    # Check if we've been subscribed for more than 60 seconds without events
                    if event_subscription.subscription_start_time:
                        time_since_subscription = (datetime.now() - event_subscription.subscription_start_time).total_seconds()
                        if time_since_subscription > 60:
                            health_data["status"] = "degraded"
                            health_data["reason"] = "No events received in 60+ seconds"
            else:
                health_data["connection"] = {"status": "not_initialized"}
                health_data["subscription"] = {"status": "not_initialized"}
                health_data["status"] = "degraded"
                health_data["reason"] = "Connection manager not initialized"
            
            # Always return 200 for health checks (even if degraded)
            # This ensures the service is considered "up" by load balancers
            return web.json_response(health_data, status=200)
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            # Return 200 even on error to avoid service being marked as down
            return web.json_response(
                {
                    "status": "unhealthy", 
                    "service": "websocket-ingestion",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }, 
                status=200
            )
