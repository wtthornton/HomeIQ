"""
Execution Router

Endpoints for executing automations
"""

from typing import Optional

from fastapi import APIRouter, HTTPException

from ..capability.capability_graph import CapabilityGraph
from ..clients.ha_rest_client import HARestClient
from ..execution.executor import Executor
from ..observability.explainer import Explainer
from ..observability.logger import StructuredLogger
from ..observability.metrics import MetricsCollector
from ..registry.spec_registry import SpecRegistry
from ..rollout.kill_switch import KillSwitch
from ..validation.validator import Validator
from ..config import settings

router = APIRouter(prefix="/api/execute", tags=["execution"])

# Initialize components
spec_registry = SpecRegistry(settings.database_url)
rest_client = HARestClient()
websocket_client = None  # Will be initialized on startup
capability_graph = CapabilityGraph(rest_client)
validator = Validator(capability_graph, rest_client)
executor = Executor(rest_client, websocket_client)
kill_switch = KillSwitch()
structured_logger = StructuredLogger()
metrics_collector = MetricsCollector()
explainer = Explainer()


@router.post("/{spec_id}")
async def execute_spec(
    spec_id: str,
    trigger_data: Optional[dict] = None,
    home_id: str = settings.home_id
):
    """Execute automation spec"""
    # Check kill switch
    spec = spec_registry.get_spec(spec_id, home_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")
    
    is_allowed, reason = kill_switch.is_allowed(spec, home_id)
    if not is_allowed:
        raise HTTPException(status_code=403, detail=reason)
    
    # Set correlation ID
    correlation_id = structured_logger.set_correlation_id()
    
    # Log trigger
    if trigger_data:
        structured_logger.log_trigger(
            trigger_data.get("type", "manual"),
            trigger_data,
            spec_id
        )
    
    # Validate
    validation_result = await validator.validate(spec, perform_preflight=False)
    
    if not validation_result["is_valid"]:
        structured_logger.log_validation(
            spec_id, False, validation_result["errors"]
        )
        raise HTTPException(
            status_code=400,
            detail={"errors": validation_result["errors"]}
        )
    
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
    
    # Execute
    execution_result = await executor.execute(
        validation_result["execution_plan"],
        spec,
        correlation_id
    )
    
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
        "success": True,
        "correlation_id": correlation_id,
        "execution_result": execution_result
    }
