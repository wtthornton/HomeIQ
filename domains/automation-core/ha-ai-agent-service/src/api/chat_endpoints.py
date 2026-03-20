"""
Chat API Endpoints
Epic AI-20 Story AI20.4: Chat API Endpoints

POST /api/v1/chat endpoint for interacting with the HA AI Agent.

Epic 60: Refactored — tool execution extracted to tool_execution.py,
OpenAI loop extracted to _run_openai_loop().
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field

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
    get_llm_router,
    get_memory_extractor,
    get_openai_client,
    get_prompt_assembly_service,
    get_settings,
    get_tool_service,
)
from .models import ChatRequest, ChatResponse
from .tool_execution import execute_tool_calls, safe_parse_tool_arguments

# Backward-compatible alias for tests that import the old private name
_safe_parse_tool_arguments = safe_parse_tool_arguments

# Agent Evaluation Framework: SessionTracer wiring (E3.S4)
try:
    from homeiq_patterns.evaluation.session_tracer import PersistentSink, trace_session

    _eval_sink = PersistentSink()
    _TRACING_AVAILABLE = True
except ImportError:
    _TRACING_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])


class SimpleRateLimiter:
    """Simple in-memory rate limiter (100 requests/minute per IP)."""

    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self._requests: dict[str, list] = {}

    def check_rate_limit(self, ip: str) -> bool:
        now = time.time()
        if ip not in self._requests:
            self._requests[ip] = []

        self._requests[ip] = [
            req_time for req_time in self._requests[ip] if now - req_time < 60
        ]

        # Clean stale IPs to prevent unbounded memory growth
        if len(self._requests) > 10_000:
            stale_ips = [
                k
                for k, v in self._requests.items()
                if not v or (now - max(v)) > 300
            ]
            for ip_key in stale_ips:
                del self._requests[ip_key]

        if len(self._requests[ip]) >= self.requests_per_minute:
            return False

        self._requests[ip].append(now)
        return True


_rate_limiter = SimpleRateLimiter(requests_per_minute=100)


async def _extract_memories_background(
    memory_extractor,
    message: str,
    conversation_id: str,
) -> None:
    """Fire-and-forget memory extraction (Story 30.1)."""
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


@dataclass
class LoopResult:
    """Return value from _run_openai_loop."""

    assistant_content: str = ""
    tool_calls: list = field(default_factory=list)
    total_tokens: int = 0
    iterations: int = 0
    openai_call_ids: list = field(default_factory=list)
    tool_execution_ids: list = field(default_factory=list)


async def _run_openai_loop(
    *,
    conversation_id: str,
    request_message: str,
    prompt_assembly_service,
    openai_client,
    tool_service,
    conversation_service,
    tools: list,
    max_iterations: int = 10,
) -> LoopResult:
    """
    Run the iterative OpenAI tool-call loop (Responses API pattern).

    Each iteration: call OpenAI -> if tool calls, execute them -> repeat.
    Stops when OpenAI returns no tool calls or max_iterations is reached.
    """
    result = LoopResult()
    tool_results: list[dict] = []
    previous_function_calls: list = []
    base_messages: list | None = None

    while result.iterations < max_iterations:
        result.iterations += 1
        logger.info(
            "[Chat Loop] Conversation %s: Iteration %d/%d",
            conversation_id,
            result.iterations,
            max_iterations,
        )

        # Build messages array
        if result.iterations == 1:
            base_messages = await prompt_assembly_service.assemble_messages(
                conversation_id, request_message,
                refresh_context=False, skip_add_message=True,
            )
            messages = base_messages.copy()
        else:
            messages = base_messages.copy() if base_messages else []

            # Remove trailing assistant messages to avoid duplication
            while messages and messages[-1].get("role") == "assistant":
                messages.pop()

            for fc_item in previous_function_calls:
                messages.append({"role": "tool_call", "_function_call": fc_item})

            for tr_item in tool_results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tr_item.get("call_id", ""),
                    "content": tr_item.get("output", ""),
                })

        # Call OpenAI API
        openai_call_id = start_tracking("openai_api_call", {
            "iteration": result.iterations,
            "message_count": len(messages),
            "tool_count": len(tools) if tools else 0,
        })
        result.openai_call_ids.append(openai_call_id)

        try:
            response = await openai_client.chat_completion(
                messages=messages, tools=tools, tool_choice="auto",
            )
        except OpenAIRateLimitError as e:
            logger.error("OpenAI rate limit error: %s", e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI API rate limit exceeded. Please try again later.",
            ) from e
        except OpenAITokenBudgetExceededError as e:
            logger.error("Token budget exceeded: %s", e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message too long. Please shorten your message or start a new conversation.",
            ) from e
        except OpenAIError as e:
            logger.error("OpenAI API error: %s", e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI API error. Please try again later.",
            ) from e

        # Extract response content and function calls
        result.assistant_content = response.output_text or ""
        function_call_items = [
            item for item in response.output
            if getattr(item, "type", None) == "function_call"
        ]

        # Token tracking
        input_tokens = getattr(response.usage, "input_tokens", 0) if response.usage else 0
        output_tokens = getattr(response.usage, "output_tokens", 0) if response.usage else 0
        tokens_used = input_tokens + output_tokens
        result.total_tokens += tokens_used

        end_tracking(openai_call_id, {
            "tokens_used": tokens_used,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "has_tool_calls": bool(function_call_items),
            "tool_calls_count": len(function_call_items),
        })

        previous_function_calls = function_call_items

        # Validate response
        if is_generic_welcome_message(result.assistant_content):
            logger.warning(
                "[Response Validation] Conversation %s: GENERIC WELCOME MESSAGE DETECTED",
                conversation_id,
            )

        # Add assistant message to conversation
        if result.assistant_content or not function_call_items:
            tc_dicts = None
            if not function_call_items and result.tool_calls:
                tc_dicts = [
                    {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                    for tc in result.tool_calls
                ]
            await conversation_service.add_message(
                conversation_id, "assistant",
                result.assistant_content or "[Processing...]",
                tool_calls=tc_dicts,
            )

        # Execute tool calls if any
        if function_call_items:
            tool_results = await execute_tool_calls(
                function_call_items,
                conversation_id,
                result.iterations,
                tool_service,
                conversation_service,
                result.tool_calls,
                result.tool_execution_ids,
            )
            continue

        # No tool calls — final response
        break

    if result.iterations >= max_iterations:
        logger.warning(
            "[Chat Loop] Conversation %s: Reached max iterations (%d)",
            conversation_id,
            max_iterations,
        )

    return result


async def _run_anthropic_loop(
    *,
    conversation_id: str,
    request_message: str,
    system_prompt: str,
    messages: list[dict],
    llm_router,
    tool_service,
    conversation_service,
    tools: list,
    entity_context: str | None = None,
    max_iterations: int = 10,
) -> LoopResult:
    """Run the iterative LLM tool-call loop via the Anthropic provider.

    Epic 97: Mirrors _run_openai_loop() but routes through LLMRouter
    which handles Anthropic API calls with prompt caching.
    """
    result = LoopResult()
    # Conversation messages (skip system — passed separately to LLMRouter)
    conv_messages = [m for m in messages if m.get("role") != "system"]

    while result.iterations < max_iterations:
        result.iterations += 1
        logger.info(
            "[Anthropic Loop] Conversation %s: Iteration %d/%d",
            conversation_id,
            result.iterations,
            max_iterations,
        )

        api_call_id = start_tracking("anthropic_api_call", {
            "iteration": result.iterations,
            "message_count": len(conv_messages),
        })
        result.openai_call_ids.append(api_call_id)

        try:
            llm_response = await llm_router.chat_completion(
                system_prompt=system_prompt,
                messages=conv_messages,
                tools=tools,
                max_tokens=4096,
                temperature=0.7,
                enable_caching=True,
                entity_context=entity_context,
                user_message=request_message,
            )
        except Exception as e:
            logger.error("Anthropic API error: %s", e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM API error. Please try again later.",
            ) from e

        result.assistant_content = llm_response.content or ""
        tokens_used = llm_response.usage.total_tokens
        result.total_tokens += tokens_used

        end_tracking(api_call_id, {
            "tokens_used": tokens_used,
            "input_tokens": llm_response.usage.input_tokens,
            "output_tokens": llm_response.usage.output_tokens,
            "cached_tokens": llm_response.cached_tokens,
            "has_tool_calls": bool(llm_response.tool_calls),
            "tool_calls_count": len(llm_response.tool_calls) if llm_response.tool_calls else 0,
        })

        # Add assistant message to conversation
        if result.assistant_content or not llm_response.tool_calls:
            await conversation_service.add_message(
                conversation_id, "assistant",
                result.assistant_content or "[Processing...]",
            )

        # Execute tool calls if any
        if llm_response.tool_calls:
            # Build function_call-like items for execute_tool_calls
            # The existing execute_tool_calls expects items with .name, .arguments, .call_id
            from types import SimpleNamespace

            fc_items = [
                SimpleNamespace(
                    name=tc.name,
                    arguments=tc.arguments,
                    call_id=tc.id,
                )
                for tc in llm_response.tool_calls
            ]

            tool_results = await execute_tool_calls(
                fc_items,
                conversation_id,
                result.iterations,
                tool_service,
                conversation_service,
                result.tool_calls,
                result.tool_execution_ids,
            )

            # Build tool result messages for the next iteration
            # Append assistant message with tool_use blocks
            assistant_msg: dict = {"role": "assistant", "content": result.assistant_content}
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "function": {"name": tc.name, "arguments": tc.arguments},
                }
                for tc in llm_response.tool_calls
            ]
            conv_messages.append(assistant_msg)

            # Append tool results
            for tr in tool_results:
                conv_messages.append({
                    "role": "tool",
                    "tool_call_id": tr.get("call_id", ""),
                    "content": tr.get("output", ""),
                })
            continue

        # No tool calls — final response
        break

    if result.iterations >= max_iterations:
        logger.warning(
            "[Anthropic Loop] Conversation %s: Reached max iterations (%d)",
            conversation_id,
            max_iterations,
        )

    return result


@router.post("/chat", response_model=ChatResponse)
@(
    trace_session(agent_name="ha-ai-agent", sink=_eval_sink, model="gpt-4o")
    if _TRACING_AVAILABLE
    else lambda f: f
)
async def chat(
    request: ChatRequest,
    http_request: Request,
    settings=Depends(get_settings),  # noqa: B008
    conversation_service=Depends(get_conversation_service),  # noqa: B008
    prompt_assembly_service=Depends(get_prompt_assembly_service),  # noqa: B008
    openai_client=Depends(get_openai_client),  # noqa: B008
    tool_service=Depends(get_tool_service),  # noqa: B008
    memory_extractor=Depends(get_memory_extractor),  # noqa: B008
    llm_router=Depends(get_llm_router),  # noqa: B008
):
    """
    Chat endpoint for interacting with the HA AI Agent.

    Sends a message to the agent and receives a response with optional tool calls.

    **Rate Limit:** 100 requests per minute per IP address
    """
    start_time = time.time()
    operation_id = f"chat_request_{int(time.time() * 1000)}"
    rate_limit_id = start_tracking("rate_limit_check")

    # Rate limiting
    client_ip = http_request.client.host if http_request.client else "unknown"
    if not _rate_limiter.check_rate_limit(client_ip):
        end_tracking(rate_limit_id, {"exceeded": True})
        logger.warning("Rate limit exceeded for IP: %s", client_ip)
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
            "is_new": not conversation_id,
        })

        if not conversation_id:
            title = request.title
            if not title:
                msg_text = request.message.strip()
                title = msg_text[:47] + "..." if len(msg_text) > 50 else msg_text

            conversation = await conversation_service.create_conversation(
                title=title, source=request.source or "user",
            )
            conversation_id = conversation.conversation_id
            logger.info(
                "[Chat Request] Created conversation %s (source=%s)",
                conversation_id,
                request.source or "user",
            )
        else:
            conversation = await conversation_service.get_conversation(conversation_id)
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Conversation {conversation_id} not found",
                )

        # Check for approval/rejection commands
        pending_preview_id = start_tracking("pending_preview_check")
        pending_preview = await conversation_service.get_pending_preview(conversation_id)
        if pending_preview:
            if is_approval_command(request.message):
                request.message = (
                    f"[USER APPROVED] {request.message}\n\n"
                    "Execute the pending automation preview that was previously generated."
                )
            elif is_rejection_command(request.message):
                await conversation_service.clear_pending_preview(conversation_id)
                request.message = (
                    f"[USER REJECTED] {request.message}\n\n"
                    "The user has rejected the pending automation preview. "
                    "Acknowledge and do not create the automation."
                )
        end_tracking(pending_preview_id, {"has_pending": bool(pending_preview)})

        # Story 30.1: Extract memories (fire-and-forget)
        if memory_extractor and settings.enable_memory_extraction:
            asyncio.create_task(
                _extract_memories_background(
                    memory_extractor, request.message, conversation_id,
                )
            )

        # Assemble messages with context
        message_assembly_id = start_tracking("message_assembly", {
            "refresh_context": request.refresh_context,
            "message_length": len(request.message),
            "has_hidden_context": request.hidden_context is not None,
        })
        messages = await prompt_assembly_service.assemble_messages(
            conversation_id,
            request.message,
            refresh_context=request.refresh_context,
            hidden_context=request.hidden_context,
        )
        end_tracking(message_assembly_id, {
            "message_count": len(messages),
            "system_message_length": len(messages[0].get("content", "")) if messages else 0,
        })

        # Verify messages
        if not messages:
            raise ValueError("No messages assembled for OpenAI API call")

        system_msg = messages[0]
        if not system_msg or system_msg.get("role") != "system":
            raise ValueError("System message is required as first message")

        # Get tool schemas and run the loop
        tools = get_tool_schemas()
        use_anthropic = (
            settings.llm_provider == "anthropic" and llm_router is not None
        )

        if use_anthropic:
            # Epic 97: Anthropic provider path with prompt caching
            model_name = settings.anthropic_model
            logger.info(
                "[Chat] Conversation %s: Using provider=anthropic, model=%s",
                conversation_id,
                model_name,
            )
            system_prompt = system_msg.get("content", "")
            loop_result = await _run_anthropic_loop(
                conversation_id=conversation_id,
                request_message=request.message,
                system_prompt=system_prompt,
                messages=messages,
                llm_router=llm_router,
                tool_service=tool_service,
                conversation_service=conversation_service,
                tools=tools,
            )
        else:
            model_name = settings.openai_model
            logger.info(
                "[Chat] Conversation %s: Using provider=openai, model=%s",
                conversation_id,
                model_name,
            )
            loop_result = await _run_openai_loop(
                conversation_id=conversation_id,
                request_message=request.message,
                prompt_assembly_service=prompt_assembly_service,
                openai_client=openai_client,
                tool_service=tool_service,
                conversation_service=conversation_service,
                tools=tools,
            )

        # Build response
        final_content = loop_result.assistant_content or ""
        response_time_ms = int((time.time() - start_time) * 1000)

        token_counts_id = start_tracking("token_count_retrieval")
        token_counts = await prompt_assembly_service.get_token_count(conversation_id)
        end_tracking(token_counts_id)

        response = ChatResponse(
            message=final_content,
            conversation_id=conversation_id,
            tool_calls=loop_result.tool_calls,
            metadata={
                "provider": "anthropic" if use_anthropic else "openai",
                "model": model_name,
                "reasoning_effort": getattr(openai_client, "reasoning_effort", None),
                "tokens_used": loop_result.total_tokens,
                "response_time_ms": response_time_ms,
                "token_breakdown": token_counts,
                "iterations": loop_result.iterations,
            },
        )

        # Performance report
        all_metric_ids = [
            rate_limit_id,
            conversation_management_id,
            pending_preview_id,
            message_assembly_id,
            token_counts_id,
        ] + loop_result.openai_call_ids + loop_result.tool_execution_ids

        create_report(operation_id, all_metric_ids, {
            "conversation_id": conversation_id,
            "total_tokens": loop_result.total_tokens,
            "iterations": loop_result.iterations,
            "tool_calls_count": len(loop_result.tool_calls),
            "response_length": len(final_content),
            "message_length": len(request.message),
        })

        logger.info(
            "[Chat Complete] Conversation %s: tokens=%d time=%dms iterations=%d tools=%d",
            conversation_id,
            loop_result.total_tokens,
            response_time_ms,
            loop_result.iterations,
            len(loop_result.tool_calls),
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
