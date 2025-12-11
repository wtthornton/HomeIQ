"""
Event rate router for websocket-ingestion service.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request

from ...api.models import EventRateResponse
from ...utils.logger import logger

router = APIRouter(prefix="/api/v1", tags=["metrics"])


@router.get("/event-rate", response_model=EventRateResponse)
async def get_event_rate(request: Request):
    """
    Get standardized event rate metrics.
    
    Returns event processing statistics including events per second and per hour.
    """
    service = request.app.state.service
    try:
        # Get processing statistics from async event processor
        processing_stats = {}
        if service.async_event_processor:
            processing_stats = service.async_event_processor.get_processing_statistics()

        # Get connection statistics
        connection_stats = {}
        if service.connection_manager and hasattr(service.connection_manager, 'event_subscription'):
            event_subscription = service.connection_manager.event_subscription
            if event_subscription:
                sub_status = event_subscription.get_subscription_status()
                connection_stats = {
                    "is_connected": getattr(service.connection_manager, 'is_running', False),
                    "is_subscribed": sub_status.get("is_subscribed", False),
                    "total_events_received": sub_status.get("total_events_received", 0),
                    "events_by_type": sub_status.get("events_by_type", {}),
                    "last_event_time": sub_status.get("last_event_time")
                }

        # Calculate event rate per second
        events_per_second = processing_stats.get("processing_rate_per_second", 0)

        # Calculate events per hour
        events_per_hour = events_per_second * 3600

        # Get uptime
        uptime_seconds = (datetime.now(timezone.utc) - service.start_time).total_seconds()

        # Build response
        response_data = {
            "service": "websocket-ingestion",
            "events_per_second": round(events_per_second, 2),
            "events_per_hour": round(events_per_hour, 2),
            "total_events_processed": processing_stats.get("processed_events", 0),
            "uptime_seconds": round(uptime_seconds, 2),
            "processing_stats": processing_stats,
            "connection_stats": connection_stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        return response_data

    except Exception as e:
        logger.error(f"Error getting event rate: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "service": "websocket-ingestion",
                "error": str(e),
                "events_per_second": 0,
                "events_per_hour": 0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

