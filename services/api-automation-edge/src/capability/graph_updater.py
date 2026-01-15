"""
Capability Graph Updater

Epic B3: Subscribe to state_changed events for graph updates
"""

import logging
from typing import Any, Callable, Dict, Optional

from ..clients.ha_websocket_client import HAWebSocketClient
from .entity_inventory import EntityInventory

logger = logging.getLogger(__name__)


class GraphUpdater:
    """
    Incremental capability graph updater via WebSocket.
    
    Features:
    - Subscribe to state_changed via WebSocket
    - Update cache + derived signals (occupancy, daylight, etc.)
    - Maintain capability graph freshness
    """
    
    def __init__(
        self,
        entity_inventory: EntityInventory,
        websocket_client: Optional[HAWebSocketClient] = None
    ):
        """
        Initialize graph updater.
        
        Args:
            entity_inventory: EntityInventory instance
            websocket_client: Optional HAWebSocketClient instance
        """
        self.entity_inventory = entity_inventory
        self.websocket_client = websocket_client
        self._subscription_id: Optional[int] = None
        self._running: bool = False
    
    async def start(self, websocket_client: HAWebSocketClient):
        """
        Start listening to state_changed events.
        
        Args:
            websocket_client: HAWebSocketClient instance
        """
        if self._running:
            logger.warning("Graph updater already running")
            return
        
        self.websocket_client = websocket_client
        self._running = True
        
        # Subscribe to state_changed events
        self._subscription_id = await websocket_client.subscribe_events(
            event_type="state_changed",
            handler=self._handle_state_changed
        )
        
        logger.info(f"Graph updater started (subscription ID: {self._subscription_id})")
    
    async def stop(self):
        """Stop listening to events"""
        self._running = False
        self._subscription_id = None
        logger.info("Graph updater stopped")
    
    async def _handle_state_changed(self, event: Dict[str, Any]):
        """
        Handle state_changed event.
        
        Args:
            event: Event data from HA
        """
        try:
            entity_id = event.get("entity_id")
            new_state = event.get("new_state")
            
            if not entity_id or not new_state:
                return
            
            # Update entity in inventory
            self.entity_inventory.update_entity(entity_id, new_state)
            
            logger.debug(f"Updated entity from state_changed: {entity_id}")
            
        except Exception as e:
            logger.error(f"Error handling state_changed event: {e}")
