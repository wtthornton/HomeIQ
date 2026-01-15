"""
Service Inventory

Epic B2: Discover and cache service schemas
"""

import logging
import time
from typing import Any, Dict, Optional

from ..clients.ha_rest_client import HARestClient

logger = logging.getLogger(__name__)


class ServiceInventory:
    """
    Service inventory builder from Home Assistant.
    
    Features:
    - Discover services via /api/services
    - Cache service schemas with TTL
    - Reconcile changes on HA restart
    - Map capabilities to domain/service pairs
    """
    
    def __init__(
        self,
        rest_client: Optional[HARestClient] = None,
        ttl: int = 3600
    ):
        """
        Initialize service inventory.
        
        Args:
            rest_client: Optional HARestClient instance
            ttl: Cache TTL in seconds
        """
        self.rest_client = rest_client or HARestClient()
        self.ttl = ttl
        self.services: Dict[str, Dict[str, Any]] = {}
        self.service_schemas: Dict[str, Dict[str, Any]] = {}
        self.capability_to_service: Dict[str, tuple[str, str]] = {}  # capability -> (domain, service)
        self.last_refresh: Optional[float] = None
    
    async def refresh(self) -> Dict[str, Any]:
        """
        Refresh service inventory from HA.
        
        Returns:
            Dictionary with refresh statistics
        """
        logger.info("Refreshing service inventory from HA")
        
        try:
            # Get services
            services = await self.rest_client.get_services()
            
            # Clear existing data
            self.services.clear()
            self.service_schemas.clear()
            self.capability_to_service.clear()
            
            # Process services
            for domain, domain_services in services.items():
                if not isinstance(domain_services, dict):
                    continue
                
                for service_name, service_data in domain_services.items():
                    service_key = f"{domain}.{service_name}"
                    
                    # Normalize service data
                    service = {
                        "domain": domain,
                        "service": service_name,
                        "service_key": service_key,
                        "fields": service_data.get("fields", {}),
                        "target": service_data.get("target", {}),
                    }
                    
                    self.services[service_key] = service
                    
                    # Extract schema
                    schema = {
                        "domain": domain,
                        "service": service_name,
                        "fields": service_data.get("fields", {}),
                        "target": service_data.get("target", {}),
                    }
                    self.service_schemas[service_key] = schema
                    
                    # Map capability (domain.service format)
                    capability = service_key
                    self.capability_to_service[capability] = (domain, service_name)
            
            self.last_refresh = time.time()
            
            logger.info(
                f"Refreshed service inventory: {len(self.services)} services, "
                f"{len(self.capability_to_service)} capabilities"
            )
            
            return {
                "service_count": len(self.services),
                "capability_count": len(self.capability_to_service)
            }
            
        except Exception as e:
            logger.error(f"Failed to refresh service inventory: {e}")
            raise
    
    def get_service(self, domain: str, service: str) -> Optional[Dict[str, Any]]:
        """Get service by domain and service name"""
        service_key = f"{domain}.{service}"
        return self.services.get(service_key)
    
    def get_service_schema(self, domain: str, service: str) -> Optional[Dict[str, Any]]:
        """Get service schema"""
        service_key = f"{domain}.{service}"
        return self.service_schemas.get(service_key)
    
    def get_capability_service(self, capability: str) -> Optional[tuple[str, str]]:
        """
        Get domain/service for a capability.
        
        Args:
            capability: Capability string (e.g., "light.turn_on")
        
        Returns:
            Tuple of (domain, service) or None
        """
        return self.capability_to_service.get(capability)
    
    def is_service_available(self, domain: str, service: str) -> bool:
        """Check if service is available"""
        service_key = f"{domain}.{service}"
        return service_key in self.services
    
    def is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if self.last_refresh is None:
            return False
        return (time.time() - self.last_refresh) < self.ttl
    
    async def ensure_fresh(self):
        """Ensure cache is fresh (refresh if needed)"""
        if not self.is_cache_valid():
            await self.refresh()
