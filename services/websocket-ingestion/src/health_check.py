"""
Health Check Handler for WebSocket Ingestion Service
"""

import logging
from datetime import datetime, timezone

from aiohttp import web

logger = logging.getLogger(__name__)


class HealthCheckHandler:
    """Handles health check requests"""

    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.connection_manager: object | None = None
        self.historical_counter: object | None = None

    def set_connection_manager(self, connection_manager):
        """Set the connection manager for health checks"""
        self.connection_manager = connection_manager

    def set_historical_counter(self, historical_counter):
        """Set the historical counter for persistent totals"""
        self.historical_counter = historical_counter

    async def handle(self, request):
        """Handle health check request - optimized for fast response (aiohttp compatibility)"""
        try:
            # Basic health check - service is running (fast response)
            health_data = {
                "status": "healthy",
                "service": "websocket-ingestion",
                "uptime": str(datetime.now(timezone.utc) - self.start_time),
                "timestamp": datetime.now(timezone.utc).isoformat()
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

                    # Get current session totals
                    session_total = sub_status.get("total_events_received", 0)

                    # Get historical totals if available
                    historical_total = 0
                    if self.historical_counter and self.historical_counter.is_initialized():
                        historical_total = self.historical_counter.get_total_events_received()

                    # Calculate combined total (historical + current session)
                    combined_total = historical_total + session_total

                    health_data["subscription"] = {
                        "is_subscribed": sub_status.get("is_subscribed", False),
                        "active_subscriptions": sub_status.get("active_subscriptions", 0),
                        "total_events_received": combined_total,  # Historical + current session
                        "session_events_received": session_total,  # Current session only
                        "historical_events_received": historical_total,  # Historical only
                        "events_by_type": sub_status.get("events_by_type", {}),
                        "last_event_time": sub_status.get("last_event_time")
                    }

                    # Calculate event rate (events per minute)
                    # Use session events for rate calculation (current activity)
                    session_events = sub_status.get("total_events_received", 0)
                    event_rate = 0
                    
                    # Calculate rate based on session events and subscription duration
                    if sub_status.get("subscription_start_time"):
                        try:
                            start_time = datetime.fromisoformat(sub_status["subscription_start_time"])
                            # Use last event time if available, otherwise use current time
                            if sub_status.get("last_event_time"):
                                end_time = datetime.fromisoformat(sub_status["last_event_time"])
                            else:
                                # If no events yet, use current time to show 0 rate (correct behavior)
                                end_time = datetime.now(timezone.utc)
                            
                            duration_minutes = (end_time - start_time).total_seconds() / 60
                            if duration_minutes > 0:
                                event_rate = session_events / duration_minutes
                        except Exception:
                            pass
                    # Always set event_rate_per_minute, default to 0
                    health_data["subscription"]["event_rate_per_minute"] = round(event_rate, 2)
                else:
                    health_data["subscription"] = {
                        "status": "not_initialized",
                        "is_subscribed": False,
                        "total_events_received": 0,
                        "event_rate_per_minute": 0
                    }

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
                        time_since_subscription = (datetime.now(timezone.utc) - event_subscription.subscription_start_time).total_seconds()
                        if time_since_subscription > 60:
                            health_data["status"] = "degraded"
                            health_data["reason"] = "No events received in 60+ seconds"
            else:
                health_data["connection"] = {"status": "not_initialized"}
                health_data["subscription"] = {"status": "not_initialized"}
                health_data["status"] = "degraded"
                health_data["reason"] = "Connection manager not initialized"

            # Weather enrichment is now handled by standalone weather-api service (Epic 31)
            # No longer part of websocket-ingestion service

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
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                status=200
            )

    async def handle_fastapi(self):
        """Handle health check request for FastAPI - returns dict instead of web.Response"""
        try:
            # Basic health check - service is running (fast response)
            health_data = {
                "status": "healthy",
                "service": "websocket-ingestion",
                "uptime": str(datetime.now(timezone.utc) - self.start_time),
                "timestamp": datetime.now(timezone.utc).isoformat()
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

                    # Get current session totals
                    session_total = sub_status.get("total_events_received", 0)

                    # Get historical totals if available
                    historical_total = 0
                    if self.historical_counter and self.historical_counter.is_initialized():
                        historical_total = self.historical_counter.get_total_events_received()

                    # Calculate combined total (historical + current session)
                    combined_total = historical_total + session_total

                    health_data["subscription"] = {
                        "is_subscribed": sub_status.get("is_subscribed", False),
                        "active_subscriptions": sub_status.get("active_subscriptions", 0),
                        "total_events_received": combined_total,  # Historical + current session
                        "session_events_received": session_total,  # Current session only
                        "historical_events_received": historical_total,  # Historical only
                        "events_by_type": sub_status.get("events_by_type", {}),
                        "last_event_time": sub_status.get("last_event_time")
                    }

                    # Calculate event rate (events per minute)
                    # Use session events for rate calculation (current activity)
                    session_events = sub_status.get("total_events_received", 0)
                    event_rate = 0
                    
                    # Calculate rate based on session events and subscription duration
                    if sub_status.get("subscription_start_time"):
                        try:
                            start_time = datetime.fromisoformat(sub_status["subscription_start_time"])
                            # Use last event time if available, otherwise use current time
                            if sub_status.get("last_event_time"):
                                end_time = datetime.fromisoformat(sub_status["last_event_time"])
                            else:
                                # If no events yet, use current time to show 0 rate (correct behavior)
                                end_time = datetime.now(timezone.utc)
                            
                            duration_minutes = (end_time - start_time).total_seconds() / 60
                            if duration_minutes > 0:
                                event_rate = session_events / duration_minutes
                        except Exception:
                            pass
                    # Always set event_rate_per_minute, default to 0
                    health_data["subscription"]["event_rate_per_minute"] = round(event_rate, 2)
                else:
                    health_data["subscription"] = {
                        "status": "not_initialized",
                        "is_subscribed": False,
                        "total_events_received": 0,
                        "event_rate_per_minute": 0
                    }

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
                        time_since_subscription = (datetime.now(timezone.utc) - event_subscription.subscription_start_time).total_seconds()
                        if time_since_subscription > 60:
                            health_data["status"] = "degraded"
                            health_data["reason"] = "No events received in 60+ seconds"
            else:
                health_data["connection"] = {"status": "not_initialized"}
                health_data["subscription"] = {"status": "not_initialized"}
                health_data["status"] = "degraded"
                health_data["reason"] = "Connection manager not initialized"

            # Weather enrichment is now handled by standalone weather-api service (Epic 31)
            # No longer part of websocket-ingestion service

            return health_data

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            # Return dict even on error
            return {
                "status": "unhealthy",
                "service": "websocket-ingestion",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
