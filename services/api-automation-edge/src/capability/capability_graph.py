"""
Capability Graph Service

Main service that coordinates inventory, updates, and drift detection
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ..clients.ha_rest_client import HARestClient
from ..clients.ha_websocket_client import HAWebSocketClient
from ..config import settings

from .drift_detector import DriftDetector
from .entity_inventory import EntityInventory
from .graph_updater import GraphUpdater
from .service_inventory import ServiceInventory

logger = logging.getLogger(__name__)


class CapabilityGraph:
    """
    Main capability graph service.
    
    Coordinates:
    - Entity inventory
    - Service inventory
    - Incremental updates
    - Drift detection
    
    Provides query interface:
    - get_entities_by_area()
    - get_services_by_domain()
    - etc.
    """
    
    def __init__(
        self,
        rest_client: Optional[HARestClient] = None,
        websocket_client: Optional[HAWebSocketClient] = None
    ):
        """
        Initialize capability graph.
        
        Args:
            rest_client: Optional HARestClient instance
            websocket_client: Optional HAWebSocketClient instance
        """
        self.rest_client = rest_client or HARestClient()
        self.websocket_client = websocket_client
        
        # Initialize components
        self.entity_inventory = EntityInventory(self.rest_client)
        self.service_inventory = ServiceInventory(self.rest_client)
        self.graph_updater = GraphUpdater(self.entity_inventory)
        self.drift_detector = DriftDetector(
            self.entity_inventory,
            self.service_inventory
        )
        
        # Background task
        self._refresh_task: Optional[asyncio.Task] = None
        self._running: bool = False
    
    async def initialize(self):
        """Initialize capability graph (boot snapshot)"""
        logger.info("Initializing capability graph")
        
        # Refresh entity and service inventories
        await self.entity_inventory.refresh()
        await self.service_inventory.refresh()
        
        logger.info("Capability graph initialized")
    
    async def start(self, websocket_client: HAWebSocketClient):
        """
        Start capability graph (with WebSocket updates).
        
        Args:
            websocket_client: HAWebSocketClient instance
        """
        if self._running:
            logger.warning("Capability graph already running")
            return
        
        self.websocket_client = websocket_client
        self._running = True
        
        # Start graph updater
        await self.graph_updater.start(websocket_client)
        
        # Start periodic refresh task
        self._refresh_task = asyncio.create_task(self._periodic_refresh())
        
        logger.info("Capability graph started")
    
    async def stop(self):
        """Stop capability graph"""
        self._running = False
        
        await self.graph_updater.stop()
        
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Capability graph stopped")
    
    async def _periodic_refresh(self):
        """Background task for periodic refresh and drift detection"""
        try:
            while self._running:
                await asyncio.sleep(settings.capability_graph_refresh_interval)
                
                if not self._running:
                    break
                
                logger.info("Running periodic capability graph refresh")
                
                # Refresh inventories
                await self.entity_inventory.refresh()
                await self.service_inventory.refresh()
                
                # Detect drift
                current_entities = set(self.entity_inventory.entities.keys())
                entity_drift = self.drift_detector.detect_entity_drift(current_entities)
                
                current_services = set(self.service_inventory.services.keys())
                service_drift = self.drift_detector.detect_service_drift(current_services)
                
                if entity_drift["has_drift"] or service_drift["has_drift"]:
                    # Get affected specs
                    affected = self.drift_detector.get_affected_specs(
                        entity_drift["removed_entities"],
                        service_drift["removed_services"]
                    )
                    
                    if affected:
                        logger.warning(f"Drift affects {len(affected)} specs: {affected}")
                
        except asyncio.CancelledError:
            logger.info("Periodic refresh cancelled")
        except Exception as e:
            logger.error(f"Error in periodic refresh: {e}")
    
    # Query interface methods
    
    def get_entities_by_area(self, area_id: str) -> List[Dict[str, Any]]:
        """Get all entities in an area"""
        return self.entity_inventory.get_entities_by_area(area_id)
    
    def get_entities_by_device(self, device_id: str) -> List[Dict[str, Any]]:
        """Get all entities for a device"""
        return self.entity_inventory.get_entities_by_device(device_id)
    
    def get_entities_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """Get all entities for a domain"""
        return self.entity_inventory.get_entities_by_domain(domain)
    
    def get_entities_by_device_class(self, device_class: str) -> List[Dict[str, Any]]:
        """Get all entities with a specific device class"""
        return self.entity_inventory.get_entities_by_device_class(device_class)
    
    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID"""
        return self.entity_inventory.get_entity(entity_id)
    
    def get_service(self, domain: str, service: str) -> Optional[Dict[str, Any]]:
        """Get service by domain and service name"""
        return self.service_inventory.get_service(domain, service)
    
    def get_service_schema(self, domain: str, service: str) -> Optional[Dict[str, Any]]:
        """Get service schema"""
        return self.service_inventory.get_service_schema(domain, service)
    
    def get_capability_service(self, capability: str) -> Optional[tuple[str, str]]:
        """Get domain/service for a capability"""
        return self.service_inventory.get_capability_service(capability)
    
    def is_service_available(self, domain: str, service: str) -> bool:
        """Check if service is available"""
        return self.service_inventory.is_service_available(domain, service)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get capability graph statistics"""
        return {
            "entity_count": len(self.entity_inventory.entities),
            "service_count": len(self.service_inventory.services),
            "area_count": len(self.entity_inventory.area_to_entities),
            "device_count": len(self.entity_inventory.device_to_entities),
            "capability_count": len(self.service_inventory.capability_to_service),
            "running": self._running
        }
