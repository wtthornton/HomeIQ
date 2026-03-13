"""
Chat API Endpoints
Epic AI-20 Story AI20.4: Chat API Endpoints

POST /api/v1/chat endpoint for interacting with the HA AI Agent.
"""

import asyncio
import json
import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..services.approval_recognizer import is_approval_command, is_rejection_command
from ..services.conversation_service import is_generic_welcome_message
from ..services.openai_client import (
    OpenAIError,
    OpenAIRateLimitError,
    OpenAITokenBudgetExceededError,
)
from ..tools.tool_schemas import get_tool_schemas
from ..utils.performance_tracker import (
    create_report,
    end_tracking,
    start_tracking,
)
from .dependencies import (
    get_conversation_service,
    get_memory_extractor,
    get_openai_client,
    get_prompt_assembly_service,
    get_settings,
    get_tool_service,
)
from .models import ChatRequest, ChatResponse, ToolCall

# Agent Evaluation Framework: SessionTracer wiring (E3.S4)
try:
    from homeiq_patterns.evaluation.session_tracer import PersistentSink, trace_session
    _eval_sink = PersistentSink()  # Persists traces to database (EVAL_STORE_PATH env var)
    _TRACING_AVAILABLE = True
except ImportError:
    _TRACING_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])


# Simple in-memory rate limiter (100 requests/minute per IP)
class SimpleRateLimiter:
    """Simple rate limiter for chat endpoint"""

    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self._requests: dict[str, list] = {}

    def check_rate_limit(self, ip: str) -> bool:
        """Check if IP is within rate limit"""
        now = time.time()
        if ip not in self._requests:
            self._requests[ip] = []

        # Remove requests older than 1 minute
        self._requests[ip] = [
            req_time for req_time in self._requests[ip] if now - req_time < 60
        ]

        # Clean stale IPs to prevent unbounded memory growth
        if len(self._requests) > 10_000:
            stale_ips = [
                k for k, v in self._requests.items()
                if not v or (now - max(v)) > 300  # 5 min stale
            ]
            for ip_key in stale_ips:
                del self._requests[ip_key]

        # Check if limit exceeded
        if len(self._requests[ip]) >= self.requests_per_minute:
            return False

        # Add current request
        self._requests[ip].append(now)
        return True


# Global rate limiter instance
_rate_limiter = SimpleRateLimiter(requests_per_minute=100)


async def _extract_memories_background(
    memory_extractor,
    message: str,
    conversation_id: str,
) -> None:
    """
    Extract memories in background (fire-and-forget).

    Story 30.1: Memory extraction runs asynchronously to not slow down
    the main chat response flow.
    """
    try:
        facts = await memory_extractor.extract_and_save(message, conversation_id)
        if facts:
            logger.debug(
                "[Memory] Conversation %s: Extracted %d memories",
                conversation_id,
                len(facts),
            )
    except Exception as e:
        logger.warning(
            "[Memory] Background extraction failed for %s: %s",
            conversation_id,
            e,
        )


def _safe_parse_tool_arguments(arguments: Any) -> dict[str, Any]:
    """
    Safely parse tool call arguments from OpenAI format.

    OpenAI may return arguments as either:
    - dict: Already parsed arguments
    - str: JSON string that needs parsing

    Args:
        arguments: Tool call arguments (dict or str)

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
            logger.warning(f"Parsed tool arguments are not a dict, got {type(parsed)}: {parsed}")
            return {}
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse tool arguments as JSON: {e}, arguments: {arguments[:200] if len(str(arguments)) > 200 else arguments}")
            return {}

    # If it's neither dict nor str, log and return empty dict
    logger.warning(f"Unexpected tool arguments type {type(arguments)}, expected dict or str")
    return {}


async def _process_tool_result(
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

    Supports Responses API function_call items (with .name, .arguments, .call_id)
    """
    # Extract tool call attributes (Responses API format)
    tc_name = tool_call.name
    tc_arguments = tool_call.arguments
    tc_call_id = tool_call.call_id

    # Handle preview tool: store pending preview (Preview-and-Approval Workflow)
    if tc_name == "preview_automation_from_prompt" and tool_result.get("result", {}).get("success") and tool_result.get("result", {}).get("preview"):
        preview_data = tool_result.get("result", {})
        await conversation_service.set_pending_preview(conversation_id, preview_data)
        logger.info(
            f"[Preview] Conversation {conversation_id}: "
            f"Stored pending preview for automation '{preview_data.get('alias', 'unknown')}'"
        )

    # Handle create tool: clear pending preview after execution (Preview-and-Approval Workflow)
    if tc_name == "create_automation_from_prompt" and tool_result.get("result", {}).get("success"):
        await conversation_service.clear_pending_preview(conversation_id)
        logger.info(
            f"[Execution] Conversation {conversation_id}: "
            f"Cleared pending preview after successful automation creation"
        )

    # Format tool result for OpenAI Responses API (function_call_output)
    tool_result_str = str(tool_result.get("result", ""))

    # Store tool result for next OpenAI call (Responses API format)
    tool_results.append({
        "type": "function_call_output",
        "call_id": tc_call_id,
        "output": tool_result_str,
    })

    # Format tool call for response
    parsed_arguments = _safe_parse_tool_arguments(tc_arguments)
    tool_calls.append(
        ToolCall(
            id=tc_call_id,
            name=tc_name,
            arguments=parsed_arguments,
        )
    )

    # Record tool call in SessionTracer (E3.S4)
    if _TRACING_AVAILABLE:
        from homeiq_patterns.evaluation.session_tracer import get_tracer_context
        ctx = get_tracer_context()
        if ctx is not None:
            ctx.record_tool_call(
                tool_name=tc_name,
                parameters=parsed_arguments,
                result=tool_result.get("result"),
            )

    logger.debug(
        f"[Tool Call] Conversation {conversation_id}: "
        f"Completed {tool_call.function.name}. "
        f"Result length: {len(tool_result_str)}"
    )


@router.post("/chat", response_model=ChatResponse)
@(trace_session(agent_name="ha-ai-agent", sink=_eval_sink, model="gpt-4o") if _TRACING_AVAILABLE else lambda f: f)
async def chat(
    request: ChatRequest,
    http_request: Request,
    settings=Depends(get_settings),
    conversation_service=Depends(get_conversation_service),
    prompt_assembly_service=Depends(get_prompt_assembly_service),
    openai_client=Depends(get_openai_client),
    tool_service=Depends(get_tool_service),
    memory_extractor=Depends(get_memory_extractor),
):
    """
    Chat endpoint for interacting with the HA AI Agent.

    Sends a message to the agent and receives a response with optional tool calls.

    **Rate Limit:** 100 requests per minute per IP address
    """
    start_time = time.time()

    # Start performance tracking
    operation_id = f"chat_request_{int(time.time() * 1000)}"
    rate_limit_id = start_tracking("rate_limit_check")

    # Rate limiting
    client_ip = http_request.client.host if http_request.client else "unknown"
    if not _rate_limiter.check_rate_limit(client_ip):
        end_tracking(rate_limit_id, {"exceeded": True})
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )
    end_tracking(rate_limit_id, {"exceeded": False})

    try:
        # Get or create conversation
        conversation_id = request.conversation_id
        conversation_management_id = start_tracking("conversation_management", {
            "conversation_id": conversation_id or "new",
            "is_new": not conversation_id
        })
        if not conversation_id:
            # Epic AI-20.9: Auto-generate title from message if not provided
            title = request.title
            if not title:
                # Generate title from first 50 chars of user message
                msg_text = request.message.strip()
                title = msg_text[:47] + "..." if len(msg_text) > 50 else msg_text

            # Epic AI-20.9: Pass title and source for new conversations
            conversation = await conversation_service.create_conversation(
                title=title,
                source=request.source or "user",
            )
            conversation_id = conversation.conversation_id
            logger.info(
                f"[Chat Request] Created new conversation {conversation_id} "
                f"(source={request.source or 'user'}, title={title}) for user message: "
                f"{request.message[:100]}..."
            )
        else:
            conversation = await conversation_service.get_conversation(conversation_id)
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Conversation {conversation_id} not found",
                )
            logger.debug(
                f"[Chat Request] Using existing conversation {conversation_id}. "
                f"Message count: {conversation.message_count}, "
                f"User message: {request.message[:100]}..."
            )

        # Check for approval/rejection commands if pending preview exists (2025 Preview-and-Approval Workflow)
        pending_preview_id = start_tracking("pending_preview_check")
        pending_preview = await conversation_service.get_pending_preview(conversation_id)
        if pending_preview:
            if is_approval_command(request.message):
                logger.info(
                    f"[Approval] Conversation {conversation_id}: "
                    f"User approved pending preview. Message: {request.message[:100]}..."
                )
                # Inject instruction to execute the pending preview
                # The agent will see the pending preview and execute it
                request.message = f"[USER APPROVED] {request.message}\n\nExecute the pending automation preview that was previously generated."
            elif is_rejection_command(request.message):
                logger.info(
                    f"[Rejection] Conversation {conversation_id}: "
                    f"User rejected pending preview. Message: {request.message[:100]}..."
                )
                # Clear pending preview and acknowledge rejection
                await conversation_service.clear_pending_preview(conversation_id)
                request.message = f"[USER REJECTED] {request.message}\n\nThe user has rejected the pending automation preview. Acknowledge and do not create the automation."
        end_tracking(pending_preview_id, {"has_pending": bool(pending_preview)})

        # Story 30.1: Extract memories from user message (fire-and-forget)
        if memory_extractor and settings.enable_memory_extraction:
            asyncio.create_task(
                _extract_memories_background(
                    memory_extractor,
                    request.message,
                    conversation_id,
                )
            )

        # Assemble messages with context
        logger.info(
            f"[Chat Request] Conversation {conversation_id}: "
            f"Assembling messages with refresh_context={request.refresh_context}, "
            f"has_hidden_context={request.hidden_context is not None}"
        )
        message_assembly_id = start_tracking("message_assembly", {
            "refresh_context": request.refresh_context,
            "message_length": len(request.message),
            "has_hidden_context": request.hidden_context is not None
        })
        messages = await prompt_assembly_service.assemble_messages(
            conversation_id,
            request.message,
            refresh_context=request.refresh_context,
            hidden_context=request.hidden_context  # Pass proactive agent context
        )
        end_tracking(message_assembly_id, {
            "message_count": len(messages),
            "system_message_length": len(messages[0].get("content", "")) if messages else 0
        })

        # Verify messages are properly assembled
        if not messages:
            logger.error(
                f"[Chat Request] Conversation {conversation_id}: "
                f"❌ CRITICAL: No messages assembled!"
            )
            raise ValueError("No messages assembled for OpenAI API call")

        # Verify system message is present
        system_msg = messages[0] if messages else None
        if not system_msg or system_msg.get("role") != "system":
            logger.error(
                f"[Chat Request] Conversation {conversation_id}: "
                f"❌ CRITICAL: System message missing or incorrect! "
                f"First message: {system_msg}"
            )
            raise ValueError("System message is required as first message")

        system_content = system_msg.get("content", "")
        logger.info(
            f"[Chat Request] Conversation {conversation_id}: "
            f"✅ Assembled {len(messages)} messages for OpenAI API call. "
            f"System message: {len(system_content)} chars, "
            f"Contains 'CRITICAL': {'CRITICAL' in system_content}, "
            f"Contains 'HOME ASSISTANT CONTEXT': {'HOME ASSISTANT CONTEXT' in system_content}, "
            f"History messages: {len(messages) - 1}"
        )

        # Get tool schemas
        tools = get_tool_schemas()

        # Use model from settings (configured via OPENAI_MODEL env var)
        logger.info(
            f"[Chat] Conversation {conversation_id}: "
            f"Using model={settings.openai_model}"
        )

        # Loop to handle multiple rounds of tool calls (Responses API pattern)
        # Build cumulative input list, appending function_call + function_call_output items
        max_iterations = 10  # Safety limit to prevent infinite loops
        iteration = 0
        tool_calls = []
        total_tokens = 0
        assistant_content = ""
        tool_results = []  # Store tool results (function_call_output items)
        previous_function_calls = []  # Store function_call items from previous response
        base_messages = None  # Store base conversation history (system + user messages)

        # Track OpenAI API calls
        openai_call_ids = []
        tool_execution_ids = []

        while iteration < max_iterations:
            iteration += 1
            logger.info(
                f"[Chat Loop] Conversation {conversation_id}: "
                f"Iteration {iteration}/{max_iterations}"
            )

            # Build messages array for the OpenAI client
            if iteration == 1:
                # First iteration: get base messages from conversation history
                base_messages = await prompt_assembly_service.assemble_messages(
                    conversation_id, request.message, refresh_context=False, skip_add_message=True
                )
                messages = base_messages.copy()
            else:
                # Subsequent iterations: rebuild messages with tool context
                messages = base_messages.copy() if base_messages else []

                # Remove last assistant message if present (we'll add tool context)
                while messages and messages[-1].get("role") == "assistant":
                    removed = messages.pop()
                    logger.debug(
                        f"[Chat Loop] Conversation {conversation_id}: "
                        f"Iteration {iteration}: Removed assistant message from base to avoid duplication: "
                        f"{removed.get('content', '')[:50]}..."
                    )

                # Append function_call items from previous response output
                for fc_item in previous_function_calls:
                    messages.append({
                        "role": "tool_call",
                        "_function_call": fc_item,
                    })

                # Append function_call_output items (tool results)
                for tr_item in tool_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tr_item.get("call_id", ""),
                        "content": tr_item.get("output", ""),
                    })

                logger.debug(
                    f"[Chat Loop] Conversation {conversation_id}: "
                    f"Iteration {iteration}: Rebuilt messages array. "
                    f"Base messages: {len(base_messages) if base_messages else 0}, "
                    f"Total messages: {len(messages)}, "
                    f"Tool results: {len(tool_results)}"
                )

            # Call OpenAI API (via Responses API internally)
            openai_call_id = start_tracking("openai_api_call", {
                "iteration": iteration,
                "message_count": len(messages),
                "tool_count": len(tools) if tools else 0
            })
            openai_call_ids.append(openai_call_id)
            try:
                response = await openai_client.chat_completion(
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )
            except OpenAIRateLimitError as e:
                logger.error(f"OpenAI rate limit error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="OpenAI API rate limit exceeded. Please try again later.",
                ) from e
            except OpenAITokenBudgetExceededError as e:
                logger.error(f"Token budget exceeded: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Message too long. Please shorten your message or start a new conversation.",
                ) from e
            except OpenAIError as e:
                logger.error(f"OpenAI API error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="OpenAI API error. Please try again later.",
                ) from e

            # Extract response content and function calls from Responses API output
            assistant_content = response.output_text or ""
            function_call_items = [
                item for item in response.output
                if getattr(item, "type", None) == "function_call"
            ]

            # Token tracking
            input_tokens = getattr(response.usage, "input_tokens", 0) if response.usage else 0
            output_tokens = getattr(response.usage, "output_tokens", 0) if response.usage else 0
            tokens_used = input_tokens + output_tokens
            total_tokens += tokens_used

            end_tracking(openai_call_id, {
                "tokens_used": tokens_used,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "has_tool_calls": bool(function_call_items),
                "tool_calls_count": len(function_call_items)
            })

            # Store function call items for next iteration input
            previous_function_calls = function_call_items

            # Validate response - check if it's a generic welcome message
            if is_generic_welcome_message(assistant_content):
                logger.warning(
                    f"[Response Validation] Conversation {conversation_id}: "
                    f"GENERIC WELCOME MESSAGE DETECTED in response! "
                    f"This indicates the prompt fixes may not be working. "
                    f"User message: {request.message[:100]}... "
                    f"Response: {assistant_content[:200]}... "
                    f"Tool calls: {len(function_call_items)}"
                )

            # Add assistant message to conversation (only if there's content or it's the final response)
            if assistant_content or not function_call_items:
                # On the final message (no more tool calls), persist accumulated tool_calls
                tc_dicts = None
                if not function_call_items and tool_calls:
                    tc_dicts = [
                        {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                        for tc in tool_calls
                    ]
                await conversation_service.add_message(
                    conversation_id, "assistant", assistant_content or "[Processing...]",
                    tool_calls=tc_dicts,
                )

            # Process tool calls if any
            if function_call_items:
                logger.info(
                    f"[Tool Calls] Conversation {conversation_id}: "
                    f"Iteration {iteration}: Processing {len(function_call_items)} tool call(s). "
                    f"Tools: {[item.name for item in function_call_items]}"
                )

                # Clear tool results from previous iteration
                tool_results = []

                # Execute independent tool calls in parallel
                if len(function_call_items) > 1:
                    logger.debug(
                        f"[Tool Calls] Conversation {conversation_id}: "
                        f"Executing {len(function_call_items)} tool calls in parallel"
                    )

                    async def execute_single_tool(fc_item, _iteration=iteration):
                        """Execute a single tool call with tracking"""
                        tool_exec_id = start_tracking("tool_execution", {
                            "tool_name": fc_item.name,
                            "iteration": _iteration
                        })
                        tool_execution_ids.append(tool_exec_id)
                        try:
                            # Convert Responses API function_call to dict for tool_service
                            tc_dict = {
                                "type": "function_call",
                                "name": fc_item.name,
                                "arguments": fc_item.arguments,
                                "call_id": fc_item.call_id,
                            }
                            result = await tool_service.execute_tool_call(tc_dict)
                            end_tracking(tool_exec_id, {
                                "success": result.get("success", False),
                                "result_length": len(str(result.get("result", "")))
                            })
                            return fc_item, result
                        except Exception as e:
                            end_tracking(tool_exec_id, {
                                "success": False,
                                "error": str(e)
                            })
                            raise

                    parallel_results = await asyncio.gather(
                        *[execute_single_tool(fc) for fc in function_call_items],
                        return_exceptions=True
                    )

                    for result in parallel_results:
                        if isinstance(result, Exception):
                            logger.error(f"Tool execution failed: {result}", exc_info=True)
                            tool_results.append({
                                "type": "function_call_output",
                                "call_id": "error",
                                "output": f"Tool execution failed: {str(result)}",
                            })
                        else:
                            fc_item, tr = result
                            await _process_tool_result(
                                fc_item, tr, conversation_id,
                                conversation_service, tool_calls, tool_results,
                            )
                else:
                    # Single tool call - execute sequentially
                    fc_item = function_call_items[0]
                    logger.debug(
                        f"[Tool Call] Conversation {conversation_id}: "
                        f"Executing {fc_item.name} with args: {fc_item.arguments}"
                    )

                    tool_exec_id = start_tracking("tool_execution", {
                        "tool_name": fc_item.name,
                        "iteration": iteration
                    })
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
                        "result_length": len(str(tool_result.get("result", "")))
                    })

                    await _process_tool_result(
                        fc_item, tool_result, conversation_id,
                        conversation_service, tool_calls, tool_results,
                    )

                # Continue loop to process tool results
                continue
            # No more tool calls - this is the final response
            logger.debug(
                f"[Tool Calls] Conversation {conversation_id}: "
                f"Iteration {iteration}: No tool calls - final response. "
                f"User requested: {request.message[:50]}..."
            )
            break

        if iteration >= max_iterations:
            logger.warning(
                f"[Chat Loop] Conversation {conversation_id}: "
                f"⚠️ Reached max iterations ({max_iterations}). "
                f"This may indicate an infinite loop or complex automation request."
            )

        # Use final assistant content (from last iteration)
        final_content = assistant_content if assistant_content else ""

        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)

        # Get token counts
        token_counts_id = start_tracking("token_count_retrieval")
        token_counts = await prompt_assembly_service.get_token_count(conversation_id)
        end_tracking(token_counts_id)

        # Build response
        response = ChatResponse(
            message=final_content,
            conversation_id=conversation_id,
            tool_calls=tool_calls,
            metadata={
                "model": openai_client.model,
                "reasoning_effort": openai_client.reasoning_effort,
                "tokens_used": total_tokens,
                "response_time_ms": response_time_ms,
                "token_breakdown": token_counts,
                "iterations": iteration,
            },
        )

        # Create performance report
        all_metric_ids = [
            rate_limit_id,
            conversation_management_id,
            pending_preview_id,
            message_assembly_id,
            token_counts_id,
        ] + openai_call_ids + tool_execution_ids

        create_report(
            operation_id,
            all_metric_ids,
            {
                "conversation_id": conversation_id,
                "total_tokens": total_tokens,
                "iterations": iteration,
                "tool_calls_count": len(tool_calls),
                "response_length": len(final_content),
                "message_length": len(request.message)
            }
        )

        logger.info(
            f"[Chat Complete] Conversation {conversation_id}: "
            f"Request completed. "
            f"Tokens: {total_tokens}, "
            f"Time: {response_time_ms}ms, "
            f"Iterations: {iteration}, "
            f"Tool calls: {len(tool_calls)}, "
            f"Response length: {len(final_content)}, "
            f"Generic response detected: {is_generic_welcome_message(final_content)}"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in chat endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e

