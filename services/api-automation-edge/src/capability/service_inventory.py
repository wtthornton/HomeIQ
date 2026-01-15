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
            services_data = await self.rest_client.get_services()
            
            # Clear existing data
            self.services.clear()
            self.service_schemas.clear()
            self.capability_to_service.clear()
            
            # Handle different response formats from Home Assistant API
            # Format 1: Dict format {"light": {"turn_on": {...}, "turn_off": {...}}, ...}
            # Format 2: List format [{"domain": "light", "services": {...}}, ...]
            if isinstance(services_data, list):
                # Convert list format to dict format
                logger.debug(f"Converting services from list format ({len(services_data)} items) to dict format")
                services_dict: Dict[str, Dict[str, Any]] = {}
                for item in services_data:
                    if isinstance(item, dict) and "domain" in item and "services" in item:
                        domain = item["domain"]
                        services = item["services"]
                        if isinstance(services, dict):
                            services_dict[domain] = services
                services_data = services_dict
                logger.info(f"Converted {len(services_dict)} service domains from list format")
            elif not isinstance(services_data, dict):
                logger.error(f"Services data is neither dict nor list, got {type(services_data)}")
                raise ValueError(f"Unexpected services data format: {type(services_data)}")
            
            # Process services (now guaranteed to be dict format)
            for domain, domain_services in services_data.items():
                if not isinstance(domain_services, dict):
                    logger.warning(f"Skipping domain '{domain}' - services is not a dict")
                    continue
                
                for service_name, service_data in domain_services.items():
                    if not isinstance(service_data, dict):
                        logger.warning(f"Skipping service '{domain}.{service_name}' - service_data is not a dict")
                        continue
                    
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
