"""
Health Check Handler for Weather API Service
Epic 31, Story 31.1
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .main import WeatherService

logger = logging.getLogger(__name__)


class HealthCheckHandler:
    """Handles health check requests with component status"""
    
    def __init__(self, service_name: str, version: str):
        """Initialize health check handler"""
        self.service_name = service_name
        self.version = version
        self.start_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        self.last_check_time: Optional[datetime] = None
    
    async def handle(self, service: Optional["WeatherService"]) -> Dict[str, Any]:
        """
        Handle health check request
        
        Returns:
            Dict with service health status
        """
        try:
            now = datetime.utcnow().replace(tzinfo=timezone.utc)
            self.last_check_time = now
            uptime = now - self.start_time
            
            health_data = {
                "status": self._resolve_status(service),
                "service": self.service_name,
                "version": self.version,
                "uptime": str(uptime),
                "uptime_seconds": int(uptime.total_seconds()),
                "timestamp": now.isoformat(),
                "components": self._component_status(service),
                "metrics": self._metrics(service, now)
            }
            
            return health_data
            
        except Exception as e:
            logger.exception("Health check failed")
            return {
                "status": "unhealthy",
                "service": self.service_name,
                "version": self.version,
                "error": str(e),
                "timestamp": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
            }
    
    def get_uptime_seconds(self) -> int:
        """Get service uptime in seconds"""
        uptime = datetime.utcnow().replace(tzinfo=timezone.utc) - self.start_time
        return int(uptime.total_seconds())
    
    def _resolve_status(self, service: Optional["WeatherService"]) -> str:
        if not service:
            return "initializing"
        if service.background_task and service.background_task.done():
            return "degraded"
        return "healthy"
    
    def _component_status(self, service: Optional["WeatherService"]) -> Dict[str, str]:
        if not service:
            return {
                "api": "initializing",
                "weather_client": "initializing",
                "cache": "initializing",
                "influxdb": "initializing",
                "background_task": "not_started"
            }
        
        session_state = "healthy" if service.session and not service.session.closed else "not_initialized"
        cache_state = "healthy" if service.cached_weather else "empty"
        influx_state = "healthy" if service.influxdb_client else "not_initialized"
        if not service.background_task:
            task_state = "not_started"
        elif service.background_task.cancelled():
            task_state = "cancelled"
        elif service.background_task.done():
            task_state = "stopped"
        else:
            task_state = "running"
        
        if service.last_background_error:
            task_state = "error"
        
        return {
            "api": "healthy",
            "weather_client": session_state,
            "cache": cache_state,
            "influxdb": influx_state,
            "background_task": task_state
        }
    
    def _metrics(self, service: Optional["WeatherService"], now: datetime) -> Dict[str, Any]:
        if not service:
            return {}
        
        cache_age = None
        if service.cache_time:
            cache_age = (now - service.cache_time).total_seconds()
        
        return {
            "cache_hits": service.cache_hits,
            "cache_misses": service.cache_misses,
            "fetch_count": service.fetch_count,
            "cache_ttl_seconds": service.cache_ttl,
            "cache_age_seconds": cache_age,
            "last_successful_fetch": service.last_successful_fetch.isoformat() if service.last_successful_fetch else None,
            "last_influx_write": service.last_influx_write.isoformat() if service.last_influx_write else None,
            "last_background_error": service.last_background_error
        }
