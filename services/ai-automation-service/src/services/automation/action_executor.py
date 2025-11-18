"""
Action Execution Engine

Executes automation actions directly via Home Assistant REST API
without creating temporary automations. Provides queuing, retry logic,
and parallel execution support.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from ..clients.ha_client import HomeAssistantClient
from .action_parser import ActionParser
from .action_models import ActionItem, ActionExecutionResult, ActionExecutionSummary
from .action_state_machine import ActionExecutionState, ActionExecutionStateMachine
from .action_exceptions import (
    ActionExecutionError,
    ServiceCallError,
    RetryExhaustedError,
    InvalidActionError
)

logger = logging.getLogger(__name__)


class ActionExecutor:
    """
    Action execution engine with queuing and retry logic.
    
    Executes automation actions directly via Home Assistant REST API
    without creating temporary automations. Supports:
    - Action queuing with asyncio.Queue
    - Worker tasks for parallel execution
    - Exponential backoff retry logic
    - Template rendering for dynamic values
    - State machine tracking
    """
    
    def __init__(
        self,
        ha_client: HomeAssistantClient,
        template_engine: Optional[Any] = None,
        num_workers: int = 2,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize action executor.
        
        Args:
            ha_client: Home Assistant client for service calls
            template_engine: Optional template engine for rendering dynamic values
            num_workers: Number of worker tasks (default: 2)
            max_retries: Maximum retry attempts (default: 3)
            retry_delay: Initial retry delay in seconds (default: 1.0)
        """
        self.ha_client = ha_client
        self.template_engine = template_engine
        self.num_workers = num_workers
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Action queue
        self._queue: asyncio.Queue = asyncio.Queue()
        
        # Worker tasks
        self._workers: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        self._running = False
        
        # Execution tracking
        self._executions: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"ActionExecutor initialized with {num_workers} workers")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.shutdown()
    
    async def start(self):
        """Start worker tasks"""
        if self._running:
            logger.warning("ActionExecutor already running")
            return
        
        self._running = True
        self._shutdown_event.clear()
        
        # Start worker tasks
        for i in range(self.num_workers):
            worker = asyncio.create_task(self._execute_worker(f"worker-{i}"))
            self._workers.append(worker)
            logger.info(f"Started worker {i+1}/{self.num_workers}")
        
        logger.info("ActionExecutor started")
    
    async def shutdown(self):
        """Gracefully shutdown workers"""
        if not self._running:
            return
        
        logger.info("Shutting down ActionExecutor...")
        self._running = False
        self._shutdown_event.set()
        
        # Wait for workers to finish
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
            self._workers.clear()
        
        logger.info("ActionExecutor shutdown complete")
    
    async def queue_action(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any],
        retry_on_failure: bool = True,
        execution_id: Optional[str] = None
    ) -> str:
        """
        Queue an action for execution.
        
        Args:
            action: Parsed action dictionary
            context: Test context (query_id, suggestion_id, etc.)
            retry_on_failure: Whether to retry on failure
            execution_id: Optional execution ID (generated if not provided)
            
        Returns:
            Execution ID for tracking
        """
        if not execution_id:
            execution_id = str(uuid.uuid4())
        
        action_item = ActionItem(
            action=action,
            context=context,
            retry_on_failure=retry_on_failure,
            execution_id=execution_id
        )
        
        await self._queue.put(action_item)
        logger.debug(f"Queued action {execution_id}: {action.get('type', 'unknown')}")
        
        return execution_id
    
    async def execute_actions(
        self,
        actions: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> ActionExecutionSummary:
        """
        Execute a list of actions and return summary.
        
        Convenience method that queues all actions and waits for completion.
        
        Args:
            actions: List of parsed action dictionaries
            context: Test context
            
        Returns:
            ActionExecutionSummary with results
        """
        execution_id = str(uuid.uuid4())
        context['execution_id'] = execution_id
        
        # Track execution
        self._executions[execution_id] = {
            'start_time': time.time(),
            'actions': [],
            'results': []
        }
        
        # Queue all actions
        action_ids = []
        for action in actions:
            action_id = await self.queue_action(
                action=action,
                context=context,
                execution_id=f"{execution_id}-{len(action_ids)}"
            )
            action_ids.append(action_id)
            self._executions[execution_id]['actions'].append(action_id)
        
        # Wait for all actions to complete
        # Note: In a real implementation, we'd track completion via callbacks
        # For now, we'll use a simple wait with timeout
        await asyncio.sleep(0.1)  # Small delay to let workers start
        
        # Collect results (simplified - in production would use proper tracking)
        summary = ActionExecutionSummary(
            total_actions=len(actions),
            successful=0,
            failed=0,
            total_time_ms=0.0
        )
        
        # Execute actions sequentially for now (can be parallelized later)
        for action in actions:
            try:
                result = await self._execute_single_action(action, context)
                summary.results.append(result)
                if result.success:
                    summary.successful += 1
                else:
                    summary.failed += 1
                    if result.error:
                        summary.errors.append(result.error)
                summary.total_time_ms += result.execution_time_ms
            except Exception as e:
                logger.error(f"Error executing action: {e}", exc_info=True)
                summary.failed += 1
                summary.errors.append(str(e))
        
        summary.total_time_ms = (time.time() - self._executions[execution_id]['start_time']) * 1000
        
        return summary
    
    async def _execute_worker(self, worker_name: str):
        """Background worker that processes actions from queue"""
        logger.info(f"Worker {worker_name} started")
        
        while self._running or not self._queue.empty():
            try:
                # Get action from queue with timeout
                try:
                    action_item = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Execute action
                try:
                    await self._execute_action_with_retry(action_item)
                except Exception as e:
                    logger.error(f"Worker {worker_name} error executing action: {e}", exc_info=True)
                finally:
                    self._queue.task_done()
                    
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}", exc_info=True)
                await asyncio.sleep(0.1)
        
        logger.info(f"Worker {worker_name} stopped")
    
    async def _execute_action_with_retry(self, action_item: ActionItem) -> bool:
        """
        Execute action with retry logic.
        
        Args:
            action_item: Action item to execute
            
        Returns:
            True if successful, False otherwise
        """
        state_machine = ActionExecutionStateMachine(ActionExecutionState.QUEUED)
        
        for attempt in range(self.max_retries + 1):
            action_item.attempts = attempt + 1
            
            try:
                if attempt > 0:
                    state_machine.transition(ActionExecutionState.RETRYING)
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    logger.info(f"Retrying action {action_item.execution_id} (attempt {attempt + 1}/{self.max_retries + 1}) after {delay:.1f}s")
                    await asyncio.sleep(delay)
                
                state_machine.transition(ActionExecutionState.EXECUTING)
                
                # Execute action based on type
                if action_item.action.get('type') == 'delay':
                    await asyncio.sleep(action_item.action.get('delay', 0))
                    state_machine.transition(ActionExecutionState.SUCCESS)
                    return True
                elif action_item.action.get('type') == 'service_call':
                    success = await self._execute_service_call(action_item)
                    if success:
                        state_machine.transition(ActionExecutionState.SUCCESS)
                        return True
                    else:
                        if attempt < self.max_retries and action_item.retry_on_failure:
                            state_machine.transition(ActionExecutionState.RETRYING)
                            continue
                        else:
                            state_machine.transition(ActionExecutionState.FAILED)
                            return False
                elif action_item.action.get('type') == 'sequence':
                    return await self._execute_sequence(action_item)
                elif action_item.action.get('type') == 'parallel':
                    return await self._execute_parallel(action_item)
                else:
                    logger.warning(f"Unknown action type: {action_item.action.get('type')}")
                    state_machine.transition(ActionExecutionState.FAILED)
                    return False
                    
            except Exception as e:
                logger.error(f"Error executing action {action_item.execution_id}: {e}", exc_info=True)
                if attempt < self.max_retries and action_item.retry_on_failure:
                    state_machine.transition(ActionExecutionState.RETRYING)
                    continue
                else:
                    state_machine.transition(ActionExecutionState.FAILED)
                    raise RetryExhaustedError(
                        f"Action execution failed after {attempt + 1} attempts",
                        attempts=attempt + 1,
                        last_error=e
                    )
        
        state_machine.transition(ActionExecutionState.FAILED)
        return False
    
    async def _execute_single_action(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any]
    ) -> ActionExecutionResult:
        """
        Execute a single action and return result.
        
        Args:
            action: Action dictionary
            context: Execution context
            
        Returns:
            ActionExecutionResult
        """
        start_time = time.time()
        action_id = action.get('action', 'unknown')
        
        try:
            if action.get('type') == 'delay':
                delay = action.get('delay', 0)
                await asyncio.sleep(delay)
                return ActionExecutionResult(
                    success=True,
                    action_id=action_id,
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            elif action.get('type') == 'service_call':
                # Create temporary action item for execution
                action_item = ActionItem(
                    action=action,
                    context=context,
                    execution_id=str(uuid.uuid4())
                )
                success = await self._execute_service_call(action_item)
                return ActionExecutionResult(
                    success=success,
                    action_id=action_id,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    error=None if success else "Service call failed"
                )
            else:
                return ActionExecutionResult(
                    success=False,
                    action_id=action_id,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    error=f"Unknown action type: {action.get('type')}"
                )
        except Exception as e:
            return ActionExecutionResult(
                success=False,
                action_id=action_id,
                execution_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
    
    async def _execute_service_call(self, action_item: ActionItem) -> bool:
        """
        Execute a service call action.
        
        Args:
            action_item: Action item with service call action
            
        Returns:
            True if successful, False otherwise
        """
        action = action_item.action
        domain = action.get('domain')
        service = action.get('service')
        
        if not domain or not service:
            raise InvalidActionError(f"Missing domain or service in action: {action}")
        
        # Build service data
        service_data = {}
        
        # Add target entity_id
        if 'target' in action:
            target = action['target']
            if isinstance(target, dict):
                if 'entity_id' in target:
                    entity_id = target['entity_id']
                    if isinstance(entity_id, list):
                        service_data['entity_id'] = entity_id
                    else:
                        service_data['entity_id'] = entity_id
                # Merge other target fields
                for key, value in target.items():
                    if key != 'entity_id':
                        service_data[key] = value
        
        # Add service data
        if 'data' in action:
            data = action['data']
            # Render templates if template engine available
            if self.template_engine and isinstance(data, dict):
                rendered_data = {}
                for key, value in data.items():
                    if isinstance(value, str) and '{{' in value:
                        try:
                            rendered_value = await self.template_engine.render(value, action_item.context)
                            rendered_data[key] = rendered_value
                        except Exception as e:
                            logger.warning(f"Template rendering failed for {key}: {e}")
                            rendered_data[key] = value
                    else:
                        rendered_data[key] = value
                service_data.update(rendered_data)
            else:
                service_data.update(data)
        
        # Make HTTP call to Home Assistant
        endpoint = f"/api/services/{domain}/{service}"
        
        try:
            result = await self.ha_client._retry_request(
                method='POST',
                endpoint=endpoint,
                json=service_data,
                return_json=False
            )
            
            if result and isinstance(result, dict):
                status = result.get('status', 0)
                if 200 <= status < 300:
                    logger.debug(f"Service call successful: {domain}.{service}")
                    return True
                else:
                    logger.warning(f"Service call failed: {domain}.{service} (status: {status})")
                    return False
            else:
                logger.warning(f"Service call returned unexpected result: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Service call error: {domain}.{service}: {e}")
            raise ServiceCallError(
                f"Service call failed: {domain}.{service}",
                response_data={'error': str(e)}
            )
    
    async def _execute_sequence(self, action_item: ActionItem) -> bool:
        """Execute sequence of actions"""
        actions = action_item.action.get('actions', [])
        for seq_action in actions:
            seq_item = ActionItem(
                action=seq_action,
                context=action_item.context,
                retry_on_failure=action_item.retry_on_failure,
                parent_action_id=action_item.execution_id
            )
            success = await self._execute_action_with_retry(seq_item)
            if not success:
                return False
        return True
    
    async def _execute_parallel(self, action_item: ActionItem) -> bool:
        """Execute actions in parallel"""
        actions = action_item.action.get('actions', [])
        tasks = []
        for par_action in actions:
            par_item = ActionItem(
                action=par_action,
                context=action_item.context,
                retry_on_failure=action_item.retry_on_failure,
                parent_action_id=action_item.execution_id
            )
            tasks.append(self._execute_action_with_retry(par_item))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return all(r is True for r in results)

