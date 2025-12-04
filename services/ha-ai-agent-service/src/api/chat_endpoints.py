"""
Chat API Endpoints
Epic AI-20 Story AI20.4: Chat API Endpoints

POST /api/v1/chat endpoint for interacting with the HA AI Agent.
"""

import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..services.openai_client import (
    OpenAIError,
    OpenAIRateLimitError,
    OpenAITokenBudgetExceededError,
)
from ..services.conversation_service import is_generic_welcome_message
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

    # Rate limiting
    client_ip = http_request.client.host if http_request.client else "unknown"
    if not _rate_limiter.check_rate_limit(client_ip):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )

    try:
        # Get or create conversation
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation = await conversation_service.create_conversation()
            conversation_id = conversation.conversation_id
            logger.info(
                f"[Chat Request] Created new conversation {conversation_id} for user message: "
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

        # Assemble messages with context
        logger.info(
            f"[Chat Request] Conversation {conversation_id}: "
            f"Assembling messages with refresh_context={request.refresh_context}"
        )
        messages = await prompt_assembly_service.assemble_messages(
            conversation_id, request.message, refresh_context=request.refresh_context
        )
        
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

        while iteration < max_iterations:
            iteration += 1
            logger.info(
                f"[Chat Loop] Conversation {conversation_id}: "
                f"Iteration {iteration}/{max_iterations}"
            )

            # Build messages array following 2025 OpenAI tool calling pattern
            if iteration == 1:
                # First iteration: get base messages from conversation history
                base_messages = await prompt_assembly_service.assemble_messages(
                    conversation_id, request.message, refresh_context=False
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
            total_tokens += completion.usage.total_tokens if completion.usage else 0
            
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
                
                for tool_call in assistant_message.tool_calls:
                    logger.debug(
                        f"[Tool Call] Conversation {conversation_id}: "
                        f"Executing {tool_call.function.name} with args: {tool_call.function.arguments}"
                    )
                    
                    # Execute tool call
                    tool_result = await tool_service.execute_tool_call(tool_call.model_dump())

                    # Format tool result for OpenAI (must include tool_call_id)
                    tool_result_str = str(tool_result.get("result", ""))
                    
                    # Store tool result for next OpenAI call
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "content": tool_result_str
                    })

                    # Format tool call for response
                    tool_calls.append(
                        ToolCall(
                            id=tool_call.id,
                            name=tool_call.function.name,
                            arguments=tool_call.function.arguments
                            if isinstance(tool_call.function.arguments, dict)
                            else {},
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
        token_counts = await prompt_assembly_service.get_token_count(conversation_id)

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

