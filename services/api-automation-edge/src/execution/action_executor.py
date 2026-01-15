"""
Action Executor

Execute single action via REST API
"""

import hashlib
import logging
import time
from typing import Any, Dict, Optional

from ..clients.ha_rest_client import HARestClient
from ..config import settings

from .confirmation_watcher import ConfirmationWatcher
from .retry_manager import RetryManager

logger = logging.getLogger(__name__)


class ActionExecutor:
    """
    Executes a single action via Home Assistant REST API.
    
    Features:
    - Execute via POST /api/services/<domain>/<service>
    - Handle idempotency, retry, confirmation
    - Emit structured telemetry
    """
    
    def __init__(
        self,
        rest_client: Optional[HARestClient] = None,
        retry_manager: Optional[RetryManager] = None,
        confirmation_watcher: Optional[ConfirmationWatcher] = None
    ):
        """
        Initialize action executor.
        
        Args:
            rest_client: Optional HARestClient instance
            retry_manager: Optional RetryManager instance
            confirmation_watcher: Optional ConfirmationWatcher instance
        """
        self.rest_client = rest_client or HARestClient()
        self.retry_manager = retry_manager or RetryManager()
        self.confirmation_watcher = confirmation_watcher
        
        # Idempotency store (entity_id -> {idempotency_key: timestamp})
        self.idempotency_store: Dict[str, Dict[str, float]] = {}
        self.idempotency_ttl = settings.idempotency_ttl
    
    def _generate_idempotency_key(
        self,
        action: Dict[str, Any],
        entity_id: str
    ) -> str:
        """
        Generate idempotency key for action.
        
        Args:
            action: Action dictionary
            entity_id: Entity ID
        
        Returns:
            Idempotency key string
        """
        # Create deterministic key from action
        key_data = {
            "capability": action.get("capability"),
            "entity_id": entity_id,
            "data": action.get("data", {})
        }
        key_str = str(sorted(key_data.items()))
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]
    
    def _is_duplicate(
        self,
        entity_id: str,
        idempotency_key: str
    ) -> bool:
        """
        Check if action is duplicate (idempotency).
        
        Args:
            entity_id: Entity ID
            idempotency_key: Idempotency key
        
        Returns:
            True if duplicate
        """
        now = time.time()
        
        # Clean up old entries
        if entity_id in self.idempotency_store:
            self.idempotency_store[entity_id] = {
                k: v for k, v in self.idempotency_store[entity_id].items()
                if (now - v) < self.idempotency_ttl
            }
        
        # Check if key exists
        if entity_id in self.idempotency_store:
            if idempotency_key in self.idempotency_store[entity_id]:
                return True
        
        return False
    
    def _record_idempotency(
        self,
        entity_id: str,
        idempotency_key: str
    ):
        """Record idempotency key"""
        if entity_id not in self.idempotency_store:
            self.idempotency_store[entity_id] = {}
        
        self.idempotency_store[entity_id][idempotency_key] = time.time()
    
    async def execute_action(
        self,
        action: Dict[str, Any],
        spec: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a single action.
        
        Args:
            action: Action dictionary with resolved_entity_ids
            spec: Optional spec dictionary (for confirmation)
        
        Returns:
            Execution result dictionary
        """
        action_id = action.get("id", "unknown")
        capability = action.get("capability", "")
        entity_ids = action.get("resolved_entity_ids", [])
        action_data = action.get("data", {})
        
        if not entity_ids:
            return {
                "success": False,
                "error": "No entities to execute action on",
                "action_id": action_id
            }
        
        # Parse capability to domain/service
        if "." not in capability:
            return {
                "success": False,
                "error": f"Invalid capability format: {capability}",
                "action_id": action_id
            }
        
        domain, service = capability.split(".", 1)
        
        # Execute for each entity
        results = []
        start_time = time.time()
        
        for entity_id in entity_ids:
            # Check idempotency
            idempotency_key = self._generate_idempotency_key(action, entity_id)
            if self._is_duplicate(entity_id, idempotency_key):
                logger.info(f"Skipping duplicate action {action_id} for {entity_id}")
                results.append({
                    "entity_id": entity_id,
                    "success": True,
                    "skipped": True,
                    "reason": "duplicate"
                })
                continue
            
            # Prepare service data
            service_data = action_data.copy()
            service_data["entity_id"] = entity_id
            
            try:
                # Execute with retry
                async def call_service():
                    return await self.rest_client.call_service(
                        domain, service, service_data
                    )
                
                response = await self.retry_manager.execute_with_retry(call_service)
                
                # Record idempotency
                self._record_idempotency(entity_id, idempotency_key)
                
                # Wait for confirmation if needed
                confirmed = True
                confirmation_error = None
                
                if self.confirmation_watcher and spec:
                    confirmed, confirmation_error = await self.confirmation_watcher.watch_action_confirmation(
                        action, spec
                    )
                
                results.append({
                    "entity_id": entity_id,
                    "success": True,
                    "response": response,
                    "confirmed": confirmed,
                    "confirmation_error": confirmation_error
                })
                
                logger.info(f"Action {action_id} executed for {entity_id}")
                
            except Exception as e:
                logger.error(f"Action {action_id} failed for {entity_id}: {e}")
                results.append({
                    "entity_id": entity_id,
                    "success": False,
                    "error": str(e)
                })
        
        execution_time = time.time() - start_time
        success_count = sum(1 for r in results if r.get("success"))
        
        return {
            "action_id": action_id,
            "capability": capability,
            "success": success_count == len(results),
            "success_count": success_count,
            "total_count": len(results),
            "execution_time": execution_time,
            "results": results
        }
