"""
Execution Wrapper

Bridge between async Executor and sync Huey tasks.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from ..clients.ha_rest_client import HARestClient
from ..clients.ha_websocket_client import HAWebSocketClient
from ..execution.executor import Executor
from ..registry.spec_registry import SpecRegistry
from ..validation.validator import Validator
from ..capability.capability_graph import CapabilityGraph
from ..rollout.kill_switch import KillSwitch
from ..observability.logger import StructuredLogger
from ..observability.metrics import MetricsCollector
from ..observability.explainer import Explainer
from ..config import settings

logger = logging.getLogger(__name__)

# Global components (initialized on first use)
_executor: Optional[Executor] = None
_rest_client: Optional[HARestClient] = None
_websocket_client: Optional[HAWebSocketClient] = None
_spec_registry: Optional[SpecRegistry] = None
_validator: Optional[Validator] = None
_kill_switch: Optional[KillSwitch] = None
_structured_logger: Optional[StructuredLogger] = None
_metrics_collector: Optional[MetricsCollector] = None
_explainer: Optional[Explainer] = None
_capability_graph: Optional[CapabilityGraph] = None


def _get_components():
    """Initialize or return global components"""
    global _executor, _rest_client, _websocket_client, _spec_registry
    global _validator, _kill_switch, _structured_logger, _metrics_collector
    global _explainer, _capability_graph
    
    if _executor is None:
        _rest_client = HARestClient()
        _spec_registry = SpecRegistry(settings.database_url)
        _kill_switch = KillSwitch()
        _structured_logger = StructuredLogger()
        _metrics_collector = MetricsCollector()
        _explainer = Explainer()
        _capability_graph = CapabilityGraph(_rest_client)
        _validator = Validator(_capability_graph, _rest_client)
        _executor = Executor(_rest_client, _websocket_client)
    
    return {
        'executor': _executor,
        'rest_client': _rest_client,
        'websocket_client': _websocket_client,
        'spec_registry': _spec_registry,
        'validator': _validator,
        'kill_switch': _kill_switch,
        'structured_logger': _structured_logger,
        'metrics_collector': _metrics_collector,
        'explainer': _explainer,
        'capability_graph': _capability_graph
    }


def execute_automation_sync(
    spec_id: str,
    trigger_data: Optional[dict],
    home_id: str,
    correlation_id: str
) -> Dict[str, Any]:
    """
    Execute automation synchronously (for use in Huey tasks).
    
    This function wraps the async executor to work with sync Huey tasks.
    
    Args:
        spec_id: Automation spec ID
        trigger_data: Optional trigger data
        home_id: Home ID
        correlation_id: Correlation ID for tracking
    
    Returns:
        Execution result dictionary
    """
    components = _get_components()
    spec_registry = components['spec_registry']
    kill_switch = components['kill_switch']
    structured_logger = components['structured_logger']
    validator = components['validator']
    executor = components['executor']
    metrics_collector = components['metrics_collector']
    explainer = components['explainer']
    
    try:
        # Get spec
        spec = spec_registry.get_spec(spec_id, home_id)
        if not spec:
            logger.error(f"Spec {spec_id} not found for home {home_id}")
            return {
                "success": False,
                "error": f"Spec {spec_id} not found",
                "correlation_id": correlation_id
            }
        
        # Check kill switch
        is_allowed, reason = kill_switch.is_allowed(spec, home_id)
        if not is_allowed:
            logger.warning(f"Spec {spec_id} blocked by kill switch: {reason}")
            return {
                "success": False,
                "error": f"Blocked by kill switch: {reason}",
                "correlation_id": correlation_id
            }
        
        # Log trigger
        if trigger_data:
            structured_logger.log_trigger(
                trigger_data.get("type", "manual"),
                trigger_data,
                spec_id
            )
        
        # Validate (sync wrapper around async validator)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        validation_result = None
        try:
            validation_result = loop.run_until_complete(
                validator.validate(spec, perform_preflight=False)
            )
        finally:
            loop.close()
        
        if not validation_result or not validation_result.get("is_valid"):
            errors = validation_result.get("errors", []) if validation_result else ["Validation failed"]
            structured_logger.log_validation(
                spec_id, False, errors
            )
            return {
                "success": False,
                "error": f"Validation failed: {errors}",
                "correlation_id": correlation_id
            }
        
        structured_logger.log_validation(
            spec_id, True, [], validation_result["execution_plan"]
        )
        
        # Record decision factors
        explainer.record_decision_factors(
            correlation_id,
            spec_id,
            triggers_matched=[trigger_data] if trigger_data else [],
            conditions_applied=spec.get("conditions", []),
            targets_resolved={
                action.get("id"): action.get("resolved_entity_ids", [])
                for action in validation_result["execution_plan"]["actions"]
            },
            policy_checks={},
            execution_plan=validation_result["execution_plan"]
        )
        
        # Execute (sync wrapper around async executor)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        execution_result = None
        try:
            execution_result = loop.run_until_complete(
                executor.execute(
                    validation_result["execution_plan"],
                    spec,
                    correlation_id
                )
            )
        finally:
            loop.close()
        
        if execution_result:
            # Log execution
            structured_logger.log_execution(spec_id, execution_result)
            
            # Record metrics
            if execution_result.get("success"):
                metrics_collector.record_action_metric(
                    home_id,
                    spec_id,
                    spec.get("version", "unknown"),
                    "unknown",  # Would extract from actions
                    True,
                    execution_result.get("execution_time", 0.0),
                    correlation_id
                )
            
            return {
                "success": execution_result.get("success", False),
                "correlation_id": correlation_id,
                "execution_result": execution_result
            }
        else:
            # Execution failed or returned None
            return {
                "success": False,
                "error": "Execution returned no result",
                "correlation_id": correlation_id
            }
        
    except Exception as e:
        logger.error(f"Error executing automation {spec_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "correlation_id": correlation_id
        }
