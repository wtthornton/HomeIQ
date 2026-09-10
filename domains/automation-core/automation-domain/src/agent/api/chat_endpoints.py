"""
Chat API Endpoints
Epic AI-20 Story AI20.4: Chat API Endpoints

POST /api/v1/chat endpoint for interacting with the HA AI Agent.

Epic 60: Refactored — tool execution extracted to tool_execution.py.
TAP-7275: the provider tool-call loops were replaced by a single
`assistant-chat` AgentForge workflow run (see _run_agentforge_turn).
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..services.approval_recognizer import is_approval_command, is_rejection_command
from ..services.llm_client import AgentChatError
from ..utils.performance_tracker import (
    create_report,
    end_tracking,
    start_tracking,
)
from .dependencies import (
    get_chat_client,
    get_conversation_service,
    get_memory_extractor,
    get_prompt_assembly_service,
    get_settings,
    get_tool_service,
)
from .models import ChatRequest, ChatResponse
from .tool_execution import safe_parse_tool_arguments

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

        self._requests[ip] = [req_time for req_time in self._requests[ip] if now - req_time < 60]

        # Clean stale IPs to prevent unbounded memory growth
        if len(self._requests) > 10_000:
            stale_ips = [k for k, v in self._requests.items() if not v or (now - max(v)) > 300]
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
    """Return value from :func:`_run_agentforge_turn`.

    The field names are the ones the response builder and the performance
    report already used, so the turn's shape did not change when the tool loop
    moved into AgentForge. ``total_tokens`` is 0 because token accounting now
    lives in AgentForge's invocation log, not in this process -- the response
    metadata says so explicitly rather than letting a zero read as "free".
    """

    assistant_content: str = ""
    tool_calls: list = field(default_factory=list)
    iterations: int = 0
    llm_call_ids: list = field(default_factory=list)
    tool_execution_ids: list = field(default_factory=list)


async def _run_agentforge_turn(
    *,
    conversation_id: str,
    request_message: str,
    system_prompt: str,
    messages: list[dict],
    chat_client,
    conversation_service,
) -> LoopResult:
    """Answer one turn by running the ``assistant-chat`` workflow.

    This replaces the iterative provider loops that used to live here (one for
    OpenAI, one for Anthropic). The iteration -- ask the model, run whatever
    Home Assistant tools it named, feed the results back -- happens inside the
    workflow now, where the gene reaches the same house data through the
    ``homeiq`` MCP read tools. HomeIQ still owns the prompt it assembled and
    the persistence of the turn.
    """
    result = LoopResult()
    call_id = start_tracking(
        "agentforge_workflow_run",
        {"conversation_id": conversation_id, "workflow": "assistant-chat"},
    )
    result.llm_call_ids.append(call_id)

    # Prior turns only: the system message is passed separately as house
    # context, and re-sending it inside the transcript would duplicate it.
    conversation = [
        {"role": m.get("role", ""), "content": str(m.get("content", ""))}
        for m in messages
        if m.get("role") in ("user", "assistant")
    ]

    try:
        answer = await chat_client.chat_turn(
            system_prompt=system_prompt,
            conversation=conversation,
            message=request_message,
        )
    except AgentChatError as e:
        end_tracking(call_id, {"error": str(e)})
        logger.error("AgentForge chat turn failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The assistant is unavailable: AgentForge could not answer this turn.",
        ) from e

    content = answer.get("answer")
    if content is None:
        content = answer.get("response") or ""
    result.assistant_content = str(content)
    tool_calls = answer.get("tool_calls")
    result.tool_calls = tool_calls if isinstance(tool_calls, list) else []
    result.iterations = int(answer.get("iterations") or 1)
    end_tracking(
        call_id,
        {
            "response_length": len(result.assistant_content),
            "tool_calls": len(result.tool_calls),
        },
    )

    await conversation_service.add_message(
        conversation_id=conversation_id,
        role="user",
        content=request_message,
    )
    await conversation_service.add_message(
        conversation_id=conversation_id,
        role="assistant",
        content=result.assistant_content,
    )
    return result


@router.post("/chat", response_model=ChatResponse)
@(
    trace_session(agent_name="ha-ai-agent", sink=_eval_sink, model="agentforge:hiq-assistant")
    if _TRACING_AVAILABLE
    else lambda f: f
)
async def chat(
    request: ChatRequest,
    http_request: Request,
    settings=Depends(get_settings),  # noqa: B008
    conversation_service=Depends(get_conversation_service),  # noqa: B008
    prompt_assembly_service=Depends(get_prompt_assembly_service),  # noqa: B008
    chat_client=Depends(get_chat_client),  # noqa: B008
    tool_service=Depends(get_tool_service),  # noqa: B008
    memory_extractor=Depends(get_memory_extractor),  # noqa: B008
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
        conversation_management_id = start_tracking(
            "conversation_management",
            {
                "conversation_id": conversation_id or "new",
                "is_new": not conversation_id,
            },
        )

        if not conversation_id:
            title = request.title
            if not title:
                msg_text = request.message.strip()
                title = msg_text[:47] + "..." if len(msg_text) > 50 else msg_text

            conversation = await conversation_service.create_conversation(
                title=title,
                source=request.source or "user",
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
                    memory_extractor,
                    request.message,
                    conversation_id,
                )
            )

        # Assemble messages with context
        message_assembly_id = start_tracking(
            "message_assembly",
            {
                "refresh_context": request.refresh_context,
                "message_length": len(request.message),
                "has_hidden_context": request.hidden_context is not None,
            },
        )
        messages = await prompt_assembly_service.assemble_messages(
            conversation_id,
            request.message,
            refresh_context=request.refresh_context,
            hidden_context=request.hidden_context,
        )
        end_tracking(
            message_assembly_id,
            {
                "message_count": len(messages),
                "system_message_length": len(messages[0].get("content", "")) if messages else 0,
            },
        )

        # Verify messages
        if not messages:
            raise ValueError("No messages assembled for the chat turn")

        system_msg = messages[0]
        if not system_msg or system_msg.get("role") != "system":
            raise ValueError("System message is required as first message")

        # Run the turn on AgentForge. There is no provider branch left: the
        # tool-calling loop and the model choice both live in the workflow.
        logger.info(
            "[Chat] Conversation %s: running workflow assistant-chat",
            conversation_id,
        )
        loop_result = await _run_agentforge_turn(
            conversation_id=conversation_id,
            request_message=request.message,
            system_prompt=system_msg.get("content", ""),
            messages=messages,
            chat_client=chat_client,
            conversation_service=conversation_service,
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
                "provider": "agentforge",
                "workflow": "assistant-chat",
                # Token accounting moved to AgentForge's invocation log with
                # the model call; this process no longer sees a token count,
                # and reporting 0 under the old key would read as "free".
                "tokens_used": None,
                "response_time_ms": response_time_ms,
                "token_breakdown": token_counts,
                "iterations": loop_result.iterations,
            },
        )

        # Performance report
        all_metric_ids = (
            [
                rate_limit_id,
                conversation_management_id,
                pending_preview_id,
                message_assembly_id,
                token_counts_id,
            ]
            + loop_result.llm_call_ids
            + loop_result.tool_execution_ids
        )

        create_report(
            operation_id,
            all_metric_ids,
            {
                "conversation_id": conversation_id,
                "iterations": loop_result.iterations,
                "tool_calls_count": len(loop_result.tool_calls),
                "response_length": len(final_content),
                "message_length": len(request.message),
            },
        )

        logger.info(
            "[Chat Complete] Conversation %s: time=%dms iterations=%d tools=%d",
            conversation_id,
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
