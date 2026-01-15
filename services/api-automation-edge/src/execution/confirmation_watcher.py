"""
Confirmation Watcher

Epic E3: Observe state changes via WebSocket for confirmation
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, Optional

from ..clients.ha_websocket_client import HAWebSocketClient

logger = logging.getLogger(__name__)


class ConfirmationWatcher:
    """
    Watches for state changes to confirm action execution.
    
    Features:
    - Observe expected state change via WebSocket after service call
    - Timeout behavior per risk class
    - Optional confirmation (required for high-risk actions)
    """
    
    def __init__(
        self,
        websocket_client: Optional[HAWebSocketClient] = None,
        default_timeout: float = 10.0
    ):
        """
        Initialize confirmation watcher.
        
        Args:
            websocket_client: Optional HAWebSocketClient instance
            default_timeout: Default timeout in seconds
        """
        self.websocket_client = websocket_client
        self.default_timeout = default_timeout
        self._pending_confirmations: Dict[str, Dict[str, Any]] = {}
        self._confirmation_handlers: Dict[str, Callable] = {}
    
    async def wait_for_confirmation(
        self,
        entity_id: str,
        expected_state: Optional[str] = None,
        timeout: Optional[float] = None,
        risk_level: str = "low"
    ) -> tuple[bool, Optional[str]]:
        """
        Wait for state change confirmation.
        
        Args:
            entity_id: Entity ID to watch
            expected_state: Expected state value (optional)
            timeout: Timeout in seconds (default based on risk)
            risk_level: Risk level (affects timeout)
        
        Returns:
            Tuple of (confirmed, error_message)
        """
        if not self.websocket_client:
            logger.warning("No WebSocket client - skipping confirmation")
            return True, None
        
        # Determine timeout based on risk
        if timeout is None:
            if risk_level == "high":
                timeout = 30.0
            elif risk_level == "medium":
                timeout = 15.0
            else:
                timeout = self.default_timeout
        
        confirmation_id = f"{entity_id}_{time.time()}"
        
        # Set up confirmation handler
        confirmed = asyncio.Event()
        actual_state = [None]
        error_message = [None]
        
        async def handler(event: Dict[str, Any]):
            """Handle state_changed event"""
            event_entity_id = event.get("entity_id")
            if event_entity_id != entity_id:
                return
            
            new_state_data = event.get("new_state", {})
            new_state = new_state_data.get("state")
            actual_state[0] = new_state
            
            if expected_state is None:
                # Any state change confirms
                confirmed.set()
            elif new_state == expected_state:
                # Expected state reached
                confirmed.set()
            else:
                # State changed but not to expected
                error_message[0] = f"State changed to '{new_state}' but expected '{expected_state}'"
        
        # Subscribe to state_changed events
        sub_id = await self.websocket_client.subscribe_events(
            event_type="state_changed",
            handler=handler
        )
        
        try:
            # Wait for confirmation
            try:
                await asyncio.wait_for(confirmed.wait(), timeout=timeout)
                logger.info(f"Confirmation received for {entity_id}: {actual_state[0]}")
                return True, None
            except asyncio.TimeoutError:
                error_msg = error_message[0] or f"Confirmation timeout after {timeout}s"
                logger.warning(f"Confirmation timeout for {entity_id}: {error_msg}")
                return False, error_msg
        finally:
            # Clean up subscription (would need to unsubscribe - simplified for now)
            pass
    
    async def watch_action_confirmation(
        self,
        action: Dict[str, Any],
        spec: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Watch for confirmation of an action.
        
        Args:
            action: Action dictionary
            spec: Spec dictionary (for risk level)
        
        Returns:
            Tuple of (confirmed, error_message)
        """
        policy = spec.get("policy", {})
        risk_level = policy.get("risk", "low")
        require_confirmation = risk_level == "high"
        
        if not require_confirmation:
            # Low/medium risk - confirmation optional
            return True, None
        
        # Get entity IDs from action
        entity_ids = action.get("resolved_entity_ids", [])
        if not entity_ids:
            return True, None  # No entities to confirm
        
        # Watch first entity (could watch all)
        entity_id = entity_ids[0]
        
        # Determine expected state from capability
        capability = action.get("capability", "")
        expected_state = None
        
        if "turn_on" in capability:
            expected_state = "on"
        elif "turn_off" in capability:
            expected_state = "off"
        elif "close" in capability:
            expected_state = "closed"
        elif "open" in capability:
            expected_state = "open"
        
        return await self.wait_for_confirmation(
            entity_id,
            expected_state=expected_state,
            risk_level=risk_level
        )
