"""
Immediate Action Router v2

Handles immediate action execution (turn on lights, etc.).
Uses function calling to execute HA services directly.

Created: Phase 3 - New API Routers
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends

from src.services.service_container import ServiceContainer, get_service_container

from .models import ActionRequest, ActionResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/actions", tags=["Immediate Actions"])


@router.post("/execute", response_model=ActionResult)
async def execute_immediate_action(
    request: ActionRequest,
    container: ServiceContainer = Depends(get_service_container),
) -> ActionResult:
    """
    Execute immediate actions like 'turn on office lights'.

    Uses function calling to execute HA services directly.
    """
    start_time = datetime.utcnow()

    try:
        # Extract entities and intent
        entity_extractor = container.entity_extractor
        entities = await entity_extractor.extract(request.query)

        intent_matcher = container.intent_matcher
        intent = intent_matcher.match_intent(request.query)

        if intent.value != "action":
            return ActionResult(
                success=False,
                action_type="not_an_action",
                entity_id=None,
                result={},
                message="Query does not appear to be an immediate action. Use /api/v2/conversations for automation creation.",
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
            )

        # Resolve entities
        if entities:
            # Extract entity IDs from entities
            entity_ids = [e.get("entity_id") for e in entities if e.get("entity_id")]

            if entity_ids:
                # Determine action type and function
                query_lower = request.query.lower()
                function_name = None
                params = {"entity_id": entity_ids[0]}

                if "turn on" in query_lower or "switch on" in query_lower:
                    if entity_ids[0].startswith("light."):
                        function_name = "turn_on_light"
                    elif entity_ids[0].startswith("switch."):
                        function_name = "turn_on_switch"
                elif "turn off" in query_lower or "switch off" in query_lower:
                    if entity_ids[0].startswith("light."):
                        function_name = "turn_off_light"
                    elif entity_ids[0].startswith("switch."):
                        function_name = "turn_off_switch"
                elif "brightness" in query_lower or "dim" in query_lower:
                    # Extract brightness value
                    import re
                    brightness_match = re.search(r"(\d+)%", request.query)
                    if brightness_match:
                        brightness = int((int(brightness_match.group(1)) / 100) * 255)
                        params["brightness"] = brightness
                        function_name = "set_light_brightness"

                if function_name:
                    # Execute function
                    function_registry = container.function_registry
                    result = await function_registry.call_function(function_name, params)

                    execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

                    return ActionResult(
                        success=result.get("success", False),
                        action_type=function_name,
                        entity_id=entity_ids[0],
                        result=result.get("result", {}),
                        message=f"Action executed: {function_name}" if result.get("success") else f"Action failed: {result.get('error', 'Unknown error')}",
                        execution_time_ms=execution_time,
                    )

        # Fallback: couldn't determine action
        return ActionResult(
            success=False,
            action_type="unknown",
            entity_id=None,
            result={},
            message="Could not determine action to execute. Please be more specific.",
            execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
        )

    except Exception as e:
        logger.error(f"Action execution failed: {e}", exc_info=True)
        error_recovery = container.error_recovery
        error_response = await error_recovery.handle_processing_error(e, request.query)

        return ActionResult(
            success=False,
            action_type="error",
            entity_id=None,
            result={"error": error_response.message, "recovery_actions": error_response.recovery_actions},
            message=error_response.message,
            execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
        )

