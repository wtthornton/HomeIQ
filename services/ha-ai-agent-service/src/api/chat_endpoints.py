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

from ..utils.performance_tracker import (
    start_tracking,
    end_tracking,
    create_report,
)

from ..services.openai_client import (
    OpenAIError,
    OpenAIRateLimitError,
    OpenAITokenBudgetExceededError,
)
from ..services.conversation_service import is_generic_welcome_message
from ..services.approval_recognizer import is_approval_command, is_rejection_command
from ..tools.tool_schemas import get_tool_schemas
from .dependencies import (
    get_conversation_service,
    get_openai_client,
    get_prompt_assembly_service,
    get_settings,
    get_tool_service,
)
from .models import ChatRequest, ChatResponse, ToolCall

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

        # Check if limit exceeded
        if len(self._requests[ip]) >= self.requests_per_minute:
            return False

        # Add current request
        self._requests[ip].append(now)
        return True


# Global rate limiter instance
_rate_limiter = SimpleRateLimiter(requests_per_minute=100)


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
            else:
                logger.warning(f"Parsed tool arguments are not a dict, got {type(parsed)}: {parsed}")
                return {}
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse tool arguments as JSON: {e}, arguments: {arguments[:200] if len(str(arguments)) > 200 else arguments}")
            return {}
    
    # If it's neither dict nor str, log and return empty dict
    logger.warning(f"Unexpected tool arguments type {type(arguments)}, expected dict or str")
    return {}


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_request: Request,
    settings=Depends(get_settings),
    conversation_service=Depends(get_conversation_service),
    prompt_assembly_service=Depends(get_prompt_assembly_service),
    openai_client=Depends(get_openai_client),
    tool_service=Depends(get_tool_service),
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
                if len(msg_text) > 50:
                    title = msg_text[:47] + "..."
                else:
                    title = msg_text
            
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

        # Loop to handle multiple rounds of tool calls
        # OpenAI function calling requires looping until agent stops making tool calls
        # 2025 Pattern: Rebuild messages array each iteration with base history + tool context
        max_iterations = 10  # Safety limit to prevent infinite loops
        iteration = 0
        tool_calls = []
        total_tokens = 0
        assistant_content = ""
        final_assistant_message = None
        tool_results = []  # Store tool results in memory for this conversation round
        previous_assistant_message = None  # Store assistant message with tool_calls from previous iteration
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

            # Build messages array following 2025 OpenAI tool calling pattern
            if iteration == 1:
                # First iteration: get base messages from conversation history
                # Skip adding message since it was already added in the first assemble_messages call above
                base_messages = await prompt_assembly_service.assemble_messages(
                    conversation_id, request.message, refresh_context=False, skip_add_message=True
                )
                messages = base_messages.copy()  # Start with base conversation history
            else:
                # Subsequent iterations: rebuild messages from base + tool context
                # 2025 Pattern: Always include full conversation history
                messages = base_messages.copy() if base_messages else []
                
                # Remove last assistant message if present (we'll add it with tool_calls)
                # This prevents duplication if assistant message was persisted with content
                while messages and messages[-1].get("role") == "assistant":
                    removed = messages.pop()
                    logger.debug(
                        f"[Chat Loop] Conversation {conversation_id}: "
                        f"Iteration {iteration}: Removed assistant message from base to avoid duplication: "
                        f"{removed.get('content', '')[:50]}..."
                    )
                
                # Add assistant message with tool_calls from previous iteration
                if previous_assistant_message:
                    assistant_msg_dict = {
                        "role": "assistant",
                        "content": previous_assistant_message.content or "",
                    }
                    # Add tool_calls if present (OpenAI format)
                    if previous_assistant_message.tool_calls:
                        assistant_msg_dict["tool_calls"] = [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments if isinstance(tc.function.arguments, str) else json.dumps(tc.function.arguments)
                                }
                            }
                            for tc in previous_assistant_message.tool_calls
                        ]
                    messages.append(assistant_msg_dict)
                    
                    # Add tool results immediately after assistant message with tool_calls
                    for tool_result in tool_results:
                        messages.append({
                            "role": "tool",
                            "content": tool_result["content"],
                            "tool_call_id": tool_result["tool_call_id"]
                        })
                
                logger.debug(
                    f"[Chat Loop] Conversation {conversation_id}: "
                    f"Iteration {iteration}: Rebuilt messages array. "
                    f"Base messages: {len(base_messages) if base_messages else 0}, "
                    f"Total messages: {len(messages)}, "
                    f"Tool results: {len(tool_results)}"
                )

            # Call OpenAI API
            openai_call_id = start_tracking("openai_api_call", {
                "iteration": iteration,
                "message_count": len(messages),
                "tool_count": len(tools) if tools else 0
            })
            openai_call_ids.append(openai_call_id)
            try:
                completion = await openai_client.chat_completion(
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

            # Extract assistant message
            assistant_message = completion.choices[0].message
            assistant_content = assistant_message.content or ""
            tokens_used = completion.usage.total_tokens if completion.usage else 0
            total_tokens += tokens_used
            
            end_tracking(openai_call_id, {
                "tokens_used": tokens_used,
                "prompt_tokens": completion.usage.prompt_tokens if completion.usage else 0,
                "completion_tokens": completion.usage.completion_tokens if completion.usage else 0,
                "has_tool_calls": bool(assistant_message.tool_calls),
                "tool_calls_count": len(assistant_message.tool_calls) if assistant_message.tool_calls else 0
            })
            
            # Store assistant message for next iteration (needed for tool_calls)
            previous_assistant_message = assistant_message

            # Validate response - check if it's a generic welcome message
            if is_generic_welcome_message(assistant_content):
                logger.warning(
                    f"[Response Validation] Conversation {conversation_id}: "
                    f"⚠️ GENERIC WELCOME MESSAGE DETECTED in response! "
                    f"This indicates the prompt fixes may not be working. "
                    f"User message: {request.message[:100]}... "
                    f"Response: {assistant_content[:200]}... "
                    f"Tool calls: {len(assistant_message.tool_calls) if assistant_message.tool_calls else 0}"
                )

            # Add assistant message to conversation (only if there's content or it's the final response)
            if assistant_content or not assistant_message.tool_calls:
                await conversation_service.add_message(
                    conversation_id, "assistant", assistant_content or "[Processing...]"
                )

            # Process tool calls if any
            if assistant_message.tool_calls:
                logger.info(
                    f"[Tool Calls] Conversation {conversation_id}: "
                    f"Iteration {iteration}: Processing {len(assistant_message.tool_calls)} tool call(s). "
                    f"Tools: {[tc.function.name for tc in assistant_message.tool_calls]}"
                )
                
                # Clear tool results from previous iteration
                tool_results = []
                
                # P2: 2025 Optimization - Execute independent tool calls in parallel
                # Tools are typically independent (e.g., preview_automation, suggest_enhancements)
                # Use asyncio.gather() for parallel execution when multiple tool calls exist
                if len(assistant_message.tool_calls) > 1:
                    # Execute all tool calls in parallel
                    logger.debug(
                        f"[Tool Calls] Conversation {conversation_id}: "
                        f"Executing {len(assistant_message.tool_calls)} tool calls in parallel"
                    )
                    
                    async def execute_single_tool(tool_call):
                        """Execute a single tool call with tracking"""
                        tool_exec_id = start_tracking("tool_execution", {
                            "tool_name": tool_call.function.name,
                            "iteration": iteration
                        })
                        tool_execution_ids.append(tool_exec_id)
                        try:
                            tool_result = await tool_service.execute_tool_call(tool_call.model_dump())
                            end_tracking(tool_exec_id, {
                                "success": tool_result.get("success", False),
                                "result_length": len(str(tool_result.get("result", "")))
                            })
                            return tool_call, tool_result
                        except Exception as e:
                            end_tracking(tool_exec_id, {
                                "success": False,
                                "error": str(e)
                            })
                            raise
                    
                    # Execute all tools in parallel
                    parallel_results = await asyncio.gather(
                        *[execute_single_tool(tc) for tc in assistant_message.tool_calls],
                        return_exceptions=True
                    )
                    
                    # Process results in order
                    for result in parallel_results:
                        if isinstance(result, Exception):
                            logger.error(f"Tool execution failed: {result}", exc_info=True)
                            # Create error result
                            tool_results.append({
                                "tool_call_id": "error",
                                "content": f"Tool execution failed: {str(result)}"
                            })
                        else:
                            tool_call, tool_result = result
                            
                            # Handle preview tool: store pending preview (2025 Preview-and-Approval Workflow)
                            if tool_call.function.name == "preview_automation_from_prompt":
                                if tool_result.get("result", {}).get("success") and tool_result.get("result", {}).get("preview"):
                                    preview_data = tool_result.get("result", {})
                                    await conversation_service.set_pending_preview(conversation_id, preview_data)
                                    logger.info(
                                        f"[Preview] Conversation {conversation_id}: "
                                        f"Stored pending preview for automation '{preview_data.get('alias', 'unknown')}'"
                                    )
                            
                            # Handle create tool: clear pending preview after execution (2025 Preview-and-Approval Workflow)
                            if tool_call.function.name == "create_automation_from_prompt":
                                if tool_result.get("result", {}).get("success"):
                                    await conversation_service.clear_pending_preview(conversation_id)
                                    logger.info(
                                        f"[Execution] Conversation {conversation_id}: "
                                        f"Cleared pending preview after successful automation creation"
                                    )
                            
                            # Format tool result for OpenAI
                            tool_result_str = str(tool_result.get("result", ""))
                            
                            # Store tool result for next OpenAI call
                            tool_results.append({
                                "tool_call_id": tool_call.id,
                                "content": tool_result_str
                            })
                            
                            # Format tool call for response
                            parsed_arguments = _safe_parse_tool_arguments(tool_call.function.arguments)
                            tool_calls.append(
                                ToolCall(
                                    id=tool_call.id,
                                    name=tool_call.function.name,
                                    arguments=parsed_arguments,
                                )
                            )
                            
                            logger.debug(
                                f"[Tool Call] Conversation {conversation_id}: "
                                f"Completed {tool_call.function.name}. "
                                f"Result length: {len(tool_result_str)}"
                            )
                else:
                    # Single tool call - execute sequentially (no benefit from parallelization)
                    tool_call = assistant_message.tool_calls[0]
                    logger.debug(
                        f"[Tool Call] Conversation {conversation_id}: "
                        f"Executing {tool_call.function.name} with args: {tool_call.function.arguments}"
                    )
                    
                    # Execute tool call
                    tool_exec_id = start_tracking("tool_execution", {
                        "tool_name": tool_call.function.name,
                        "iteration": iteration
                    })
                    tool_execution_ids.append(tool_exec_id)
                    tool_result = await tool_service.execute_tool_call(tool_call.model_dump())
                    end_tracking(tool_exec_id, {
                        "success": tool_result.get("success", False),
                        "result_length": len(str(tool_result.get("result", "")))
                    })

                    # Handle preview tool: store pending preview (2025 Preview-and-Approval Workflow)
                    if tool_call.function.name == "preview_automation_from_prompt":
                        if tool_result.get("result", {}).get("success") and tool_result.get("result", {}).get("preview"):
                            preview_data = tool_result.get("result", {})
                            await conversation_service.set_pending_preview(conversation_id, preview_data)
                            logger.info(
                                f"[Preview] Conversation {conversation_id}: "
                                f"Stored pending preview for automation '{preview_data.get('alias', 'unknown')}'"
                            )
                    
                    # Handle create tool: clear pending preview after execution (2025 Preview-and-Approval Workflow)
                    if tool_call.function.name == "create_automation_from_prompt":
                        if tool_result.get("result", {}).get("success"):
                            await conversation_service.clear_pending_preview(conversation_id)
                            logger.info(
                                f"[Execution] Conversation {conversation_id}: "
                                f"Cleared pending preview after successful automation creation"
                            )

                    # Format tool result for OpenAI (must include tool_call_id)
                    tool_result_str = str(tool_result.get("result", ""))
                    
                    # Store tool result for next OpenAI call
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "content": tool_result_str
                    })

                    # Format tool call for response
                    parsed_arguments = _safe_parse_tool_arguments(tool_call.function.arguments)
                    tool_calls.append(
                        ToolCall(
                            id=tool_call.id,
                            name=tool_call.function.name,
                            arguments=parsed_arguments,
                        )
                    )
                    
                    logger.debug(
                        f"[Tool Call] Conversation {conversation_id}: "
                        f"Completed {tool_call.function.name}. "
                        f"Result length: {len(tool_result_str)}"
                    )
                
                # Continue loop to process tool results
                continue
            else:
                # No more tool calls - this is the final response
                logger.debug(
                    f"[Tool Calls] Conversation {conversation_id}: "
                    f"Iteration {iteration}: No tool calls - final response. "
                    f"User requested: {request.message[:50]}..."
                )
                final_assistant_message = assistant_message
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
                "model": settings.openai_model,
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
            detail=f"Internal server error: {str(e)}",
        ) from e

