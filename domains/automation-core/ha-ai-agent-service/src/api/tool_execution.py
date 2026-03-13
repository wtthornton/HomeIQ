"""
Tool Execution Helpers for Chat Endpoint

Epic 60 Story 60.1: Extracted from chat_endpoints.py to reduce cyclomatic complexity.
Handles tool call parsing, execution (parallel/sequential), and result processing.
"""

import asyncio
import json
import logging
from typing import Any

from ..utils.performance_tracker import end_tracking, start_tracking
from .models import ToolCall

# Agent Evaluation Framework: SessionTracer wiring (E3.S4)
try:
    from homeiq_patterns.evaluation.session_tracer import get_tracer_context

    _TRACING_AVAILABLE = True
except ImportError:
    _TRACING_AVAILABLE = False

logger = logging.getLogger(__name__)


def safe_parse_tool_arguments(arguments: Any) -> dict[str, Any]:
    """
    Safely parse tool call arguments from OpenAI format.

    OpenAI may return arguments as either:
    - dict: Already parsed arguments
    - str: JSON string that needs parsing

    Returns:
        Parsed arguments as dict, or empty dict if parsing fails
    """
    if isinstance(arguments, dict):
        return arguments

    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
            if isinstance(parsed, dict):
                return parsed
            logger.warning(
                "Parsed tool arguments are not a dict, got %s: %s",
                type(parsed),
                parsed,
            )
            return {}
        except json.JSONDecodeError as e:
            truncated = arguments[:200] if len(arguments) > 200 else arguments
            logger.warning(
                "Failed to parse tool arguments as JSON: %s, arguments: %s",
                e,
                truncated,
            )
            return {}

    logger.warning(
        "Unexpected tool arguments type %s, expected dict or str",
        type(arguments),
    )
    return {}


async def process_tool_result(
    tool_call,
    tool_result: dict,
    conversation_id: str,
    conversation_service,
    tool_calls: list,
    tool_results: list,
) -> None:
    """
    Process a single tool call result: handle preview/create workflow,
    format the result for OpenAI Responses API, and append to tracking lists.
    """
    tc_name = tool_call.name
    tc_arguments = tool_call.arguments
    tc_call_id = tool_call.call_id

    # Handle preview tool: store pending preview
    result_data = tool_result.get("result", {})
    if (
        tc_name == "preview_automation_from_prompt"
        and isinstance(result_data, dict)
        and result_data.get("success")
        and result_data.get("preview")
    ):
        await conversation_service.set_pending_preview(conversation_id, result_data)
        logger.info(
            "[Preview] Conversation %s: Stored pending preview for automation '%s'",
            conversation_id,
            result_data.get("alias", "unknown"),
        )

    # Handle create tool: clear pending preview after execution
    if (
        tc_name == "create_automation_from_prompt"
        and isinstance(result_data, dict)
        and result_data.get("success")
    ):
        await conversation_service.clear_pending_preview(conversation_id)
        logger.info(
            "[Execution] Conversation %s: Cleared pending preview after successful creation",
            conversation_id,
        )

    # Format tool result for OpenAI Responses API (function_call_output)
    tool_result_str = str(tool_result.get("result", ""))

    tool_results.append({
        "type": "function_call_output",
        "call_id": tc_call_id,
        "output": tool_result_str,
    })

    parsed_arguments = safe_parse_tool_arguments(tc_arguments)
    tool_calls.append(
        ToolCall(
            id=tc_call_id,
            name=tc_name,
            arguments=parsed_arguments,
        )
    )

    # Record tool call in SessionTracer (E3.S4)
    if _TRACING_AVAILABLE:
        ctx = get_tracer_context()
        if ctx is not None:
            ctx.record_tool_call(
                tool_name=tc_name,
                parameters=parsed_arguments,
                result=tool_result.get("result"),
            )

    logger.debug(
        "[Tool Call] Conversation %s: Completed %s. Result length: %d",
        conversation_id,
        tc_name,
        len(tool_result_str),
    )


async def execute_tool_calls(
    function_call_items: list,
    conversation_id: str,
    iteration: int,
    tool_service,
    conversation_service,
    tool_calls: list,
    tool_execution_ids: list,
) -> list[dict]:
    """
    Execute tool calls (parallel if multiple, sequential if single).

    Returns:
        List of tool result dicts (function_call_output items) for the next OpenAI call.
    """
    tool_results: list[dict] = []

    logger.info(
        "[Tool Calls] Conversation %s: Iteration %d: Processing %d tool call(s). Tools: %s",
        conversation_id,
        iteration,
        len(function_call_items),
        [item.name for item in function_call_items],
    )

    if len(function_call_items) > 1:
        # Execute independent tool calls in parallel
        logger.debug(
            "[Tool Calls] Conversation %s: Executing %d tool calls in parallel",
            conversation_id,
            len(function_call_items),
        )

        async def _execute_single(fc_item, _iteration=iteration):
            tool_exec_id = start_tracking(
                "tool_execution",
                {"tool_name": fc_item.name, "iteration": _iteration},
            )
            tool_execution_ids.append(tool_exec_id)
            try:
                tc_dict = {
                    "type": "function_call",
                    "name": fc_item.name,
                    "arguments": fc_item.arguments,
                    "call_id": fc_item.call_id,
                }
                result = await tool_service.execute_tool_call(tc_dict)
                end_tracking(tool_exec_id, {
                    "success": result.get("success", False),
                    "result_length": len(str(result.get("result", ""))),
                })
                return fc_item, result
            except Exception as e:
                end_tracking(tool_exec_id, {"success": False, "error": str(e)})
                raise

        parallel_results = await asyncio.gather(
            *[_execute_single(fc) for fc in function_call_items],
            return_exceptions=True,
        )

        for result in parallel_results:
            if isinstance(result, Exception):
                logger.error("Tool execution failed: %s", result, exc_info=True)
                tool_results.append({
                    "type": "function_call_output",
                    "call_id": "error",
                    "output": f"Tool execution failed: {result!s}",
                })
            else:
                fc_item, tr = result
                await process_tool_result(
                    fc_item, tr, conversation_id,
                    conversation_service, tool_calls, tool_results,
                )
    else:
        # Single tool call - execute directly
        fc_item = function_call_items[0]
        logger.debug(
            "[Tool Call] Conversation %s: Executing %s with args: %s",
            conversation_id,
            fc_item.name,
            fc_item.arguments,
        )

        tool_exec_id = start_tracking(
            "tool_execution",
            {"tool_name": fc_item.name, "iteration": iteration},
        )
        tool_execution_ids.append(tool_exec_id)
        tc_dict = {
            "type": "function_call",
            "name": fc_item.name,
            "arguments": fc_item.arguments,
            "call_id": fc_item.call_id,
        }
        tool_result = await tool_service.execute_tool_call(tc_dict)
        end_tracking(tool_exec_id, {
            "success": tool_result.get("success", False),
            "result_length": len(str(tool_result.get("result", ""))),
        })

        await process_tool_result(
            fc_item, tool_result, conversation_id,
            conversation_service, tool_calls, tool_results,
        )

    return tool_results
