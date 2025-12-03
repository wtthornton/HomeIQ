"""
Chat API Endpoints
Epic AI-20 Story AI20.4: Chat API Endpoints

POST /api/v1/chat endpoint for interacting with the HA AI Agent.
"""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..services.openai_client import (
    OpenAIError,
    OpenAIRateLimitError,
    OpenAITokenBudgetExceededError,
)
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
        else:
            conversation = await conversation_service.get_conversation(conversation_id)
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Conversation {conversation_id} not found",
                )

        # Assemble messages with context
        messages = await prompt_assembly_service.assemble_messages(
            conversation_id, request.message, refresh_context=request.refresh_context
        )

        # Get tool schemas
        tools = get_tool_schemas()

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

        # Add assistant message to conversation
        await conversation_service.add_message(
            conversation_id, "assistant", assistant_content
        )

        # Process tool calls if any
        tool_calls = []
        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                # Execute tool call
                tool_result = await tool_service.execute_tool_call(tool_call.model_dump())

                # Add tool result to conversation as assistant message
                tool_result_str = str(tool_result.get("result", ""))
                await conversation_service.add_message(
                    conversation_id, "assistant", f"Tool result: {tool_result_str}"
                )

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

        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)

        # Get token counts
        token_counts = await prompt_assembly_service.get_token_count(conversation_id)

        # Build response
        response = ChatResponse(
            message=assistant_content,
            conversation_id=conversation_id,
            tool_calls=tool_calls,
            metadata={
                "model": settings.openai_model,
                "tokens_used": completion.usage.total_tokens if completion.usage else 0,
                "response_time_ms": response_time_ms,
                "token_breakdown": token_counts,
            },
        )

        logger.info(
            f"Chat request completed: conversation={conversation_id}, "
            f"tokens={response.metadata.get('tokens_used')}, "
            f"time={response_time_ms}ms"
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

