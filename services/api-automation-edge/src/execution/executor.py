"""
Main Executor

Epic E1: Deterministic executor with idempotency, sequential execution, bounded parallelism
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional

from ..clients.ha_rest_client import HARestClient
from ..clients.ha_websocket_client import HAWebSocketClient

from .action_executor import ActionExecutor
from .confirmation_watcher import ConfirmationWatcher
from .retry_manager import RetryManager

logger = logging.getLogger(__name__)


class Executor:
    """
    Main executor for automation specs.
    
    Features:
    - Idempotency keys per action (TTL store)
    - Sequential execution by default
    - Bounded parallelism option for independent actions
    - Action correlation IDs
    """
    
    def __init__(
        self,
        rest_client: Optional[HARestClient] = None,
        websocket_client: Optional[HAWebSocketClient] = None,
        max_parallel: int = 1
    ):
        """
        Initialize executor.
        
        Args:
            rest_client: Optional HARestClient instance
            websocket_client: Optional HAWebSocketClient instance
            max_parallel: Maximum parallel actions (1 = sequential)
        """
        self.rest_client = rest_client or HARestClient()
        self.websocket_client = websocket_client
        self.max_parallel = max_parallel
        
        # Initialize components
        retry_manager = RetryManager()
        confirmation_watcher = (
            ConfirmationWatcher(websocket_client) if websocket_client else None
        )
        self.action_executor = ActionExecutor(
            rest_client, retry_manager, confirmation_watcher
        )
    
    async def execute(
        self,
        execution_plan: Dict[str, Any],
        spec: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute automation spec.
        
        Args:
            execution_plan: Execution plan from validator
            spec: Automation spec dictionary
            correlation_id: Optional correlation ID
        
        Returns:
            Execution result dictionary
        """
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        spec_id = spec.get("id", "unknown")
        spec_version = spec.get("version", "unknown")
        
        logger.info(
            f"Executing spec {spec_id} v{spec_version} "
            f"(correlation_id: {correlation_id})"
        )
        
        actions = execution_plan.get("actions", [])
        if not actions:
            return {
                "success": False,
                "error": "No actions to execute",
                "correlation_id": correlation_id
            }
        
        start_time = asyncio.get_event_loop().time()
        
        # Execute actions
        if self.max_parallel > 1:
            # Parallel execution (bounded)
            results = await self._execute_parallel(actions, spec, correlation_id)
        else:
            # Sequential execution
            results = await self._execute_sequential(actions, spec, correlation_id)
        
        execution_time = asyncio.get_event_loop().time() - start_time
        
        # Aggregate results
        success_count = sum(1 for r in results if r.get("success"))
        total_count = len(results)
        
        return {
            "correlation_id": correlation_id,
            "spec_id": spec_id,
            "spec_version": spec_version,
            "success": success_count == total_count,
            "success_count": success_count,
            "total_count": total_count,
            "execution_time": execution_time,
            "action_results": results
        }
    
    async def _execute_sequential(
        self,
        actions: List[Dict[str, Any]],
        spec: Dict[str, Any],
        correlation_id: str
    ) -> List[Dict[str, Any]]:
        """Execute actions sequentially"""
        results = []
        
        for i, action in enumerate(actions):
            action_id = action.get("id", f"action_{i}")
            logger.info(
                f"Executing action {action_id} ({i+1}/{len(actions)}) "
                f"[correlation_id: {correlation_id}]"
            )
            
            result = await self.action_executor.execute_action(action, spec)
            result["correlation_id"] = correlation_id
            results.append(result)
            
            # Stop on error if needed (could be configurable)
            if not result.get("success") and spec.get("policy", {}).get("risk") == "high":
                logger.error("High-risk action failed - stopping execution")
                break
        
        return results
    
    async def _execute_parallel(
        self,
        actions: List[Dict[str, Any]],
        spec: Dict[str, Any],
        correlation_id: str
    ) -> List[Dict[str, Any]]:
        """Execute actions in parallel (bounded)"""
        semaphore = asyncio.Semaphore(self.max_parallel)
        results = []
        
        async def execute_with_semaphore(action: Dict[str, Any], index: int):
            async with semaphore:
                action_id = action.get("id", f"action_{index}")
                logger.info(
                    f"Executing action {action_id} ({index+1}/{len(actions)}) "
                    f"[correlation_id: {correlation_id}]"
                )
                
                result = await self.action_executor.execute_action(action, spec)
                result["correlation_id"] = correlation_id
                return result
        
        # Create tasks
        tasks = [
            execute_with_semaphore(action, i)
            for i, action in enumerate(actions)
        ]
        
        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Action {i} raised exception: {result}")
                processed_results.append({
                    "success": False,
                    "error": str(result),
                    "correlation_id": correlation_id
                })
            else:
                processed_results.append(result)
        
        return processed_results
