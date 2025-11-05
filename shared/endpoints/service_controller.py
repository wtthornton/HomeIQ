"""
Service Controller - Health-based service management
Shared service controller for admin-api and data-api.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ServiceController:
    """Health-based service controller using HTTP health checks"""
    
    def __init__(self):
        """
        Initialize service controller with health check endpoints
        """
        self.service_ports = {
            "websocket-ingestion": 8001,
            "admin-api": 8004,  # Internal port
            "data-retention": 8080,
            "health-dashboard": 80,  # Internal port
            "influxdb": 8086,
            # Optional services that may not be running
            "carbon-intensity": 8010,
            "electricity-pricing": 8011,
            "air-quality": 8012,
            "calendar": 8013,
            "smart-meter": 8014,
        }
    
    async def _check_health_endpoint(self, service: str, port: int) -> Dict[str, any]:
        """
        Check health endpoint for a service using aiohttp best practices
        
        Args:
            service: Service name
            port: Service port
            
        Returns:
            Dictionary with health status
        """
        # Build URL based on service type - use container names for internal communication
        if service == "admin-api":
            url = "http://localhost:8004/health"
        elif service == "health-dashboard":
            url = "http://health-dashboard:80"
        elif service == "websocket-ingestion":
            url = "http://websocket-ingestion:8001/health"
        elif service == "data-retention":
            url = "http://data-retention:8080/health"
        elif service == "influxdb":
            url = "http://influxdb:8086/health"
        else:
            url = f"http://localhost:{port}/health"
        
        # Configure timeout for health checks
        timeout = aiohttp.ClientTimeout(total=3, connect=2)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    # Use raise_for_status for proper error handling
                    response.raise_for_status()
                    
                    return {
                        "service": service,
                        "running": True,
                        "status": "running",
                        "timestamp": datetime.now().isoformat(),
                        "port": port,
                        "health_status": response.status
                    }
        
        except Exception as e:
            # Handle all aiohttp exceptions and other errors
            error_type = type(e).__name__
            error_message = str(e)
            
            if "timeout" in error_message.lower():
                status = "error"
                error_msg = "Connection timeout"
            elif "connection" in error_message.lower():
                status = "stopped"
                error_msg = f"Connection refused: {error_message}"
            elif hasattr(e, 'status'):
                status = "error"
                error_msg = f"HTTP {e.status}: {error_message}"
            else:
                status = "error"
                error_msg = f"Unexpected error: {error_message}"
            
            logger.error(f"Error checking {service}: {error_type}: {error_message}")
            return {
                "service": service,
                "running": False,
                "status": status,
                "error": error_msg,
                "timestamp": datetime.now().isoformat(),
                "port": port
            }

    def get_service_status(self, service: str) -> Dict[str, any]:
        """
        Get status of a service using health check
        
        Args:
            service: Service name
            
        Returns:
            Dictionary with status information
        """
        if service not in self.service_ports:
            return {
                "service": service,
                "running": False,
                "status": "error",
                "error": f"Unknown service: {service}",
                "timestamp": datetime.now().isoformat()
            }
        
        port = self.service_ports[service]
        
        # Run async health check
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._check_health_endpoint(service, port))
    
    def list_services(self) -> List[Dict[str, any]]:
        """
        List core services with their status (only services that should be running)
        
        Returns:
            List of service status dictionaries
        """
        # Only check core services that are expected to be running
        core_services = [
            "websocket-ingestion", 
            "data-retention",
            "admin-api",
            "health-dashboard",
            "influxdb"
        ]
        
        return [self.get_service_status(service) for service in core_services]
    
    def restart_service(self, service: str) -> Dict[str, any]:
        """
        Restart a service (placeholder - requires external docker management)
        
        Args:
            service: Service name
            
        Returns:
            Dictionary with operation result
        """
        logger.info(f"Restart requested for service: {service}")
        
        # Since we can't restart services from within the container,
        # we provide instructions for manual restart
        return {
            "success": False,
            "service": service,
            "message": f"Service restart not available from within container",
            "instruction": f"To restart {service}, run: docker restart homeiq-{service.replace('-', '')}",
            "timestamp": datetime.now().isoformat()
        }
    
    
    def restart_all_services(self) -> Dict[str, any]:
        """
        Restart all services (placeholder - requires external docker management)
        
        Returns:
            Dictionary with operation results
        """
        logger.info("Restart all services requested")
        
        return {
            "success": False,
            "message": "Service restart not available from within container",
            "instruction": "To restart all services, run: docker-compose restart",
            "timestamp": datetime.now().isoformat()
        }


# Global instance
service_controller = ServiceController()

