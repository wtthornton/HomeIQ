"""
Subagent Runner (Epic 70, Story 70.5).

Lightweight wrapper around _run_openai_loop() with area-scoped context
and per-subagent token budget enforcement.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SubagentResult:
    """Result from a subagent execution."""

    area: str
    status: str  # completed, budget_exceeded, failed
    summary: str = ""
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
    tokens_used: int = 0
    duration_seconds: float = 0.0
    error: str | None = None


class SubagentRunner:
    """Runs a scoped child agent loop for a specific area/task."""

    def __init__(
        self,
        openai_client: Any,
        tool_service: Any,
        conversation_service: Any,
        max_iterations: int = 15,
        max_tokens: int = 8000,
    ):
        self.openai_client = openai_client
        self.tool_service = tool_service
        self.conversation_service = conversation_service
        self.max_iterations = max_iterations
        self.max_tokens = max_tokens

    async def run(
        self,
        goal: str,
        context: str,
        area: str,
        tools: list[dict[str, Any]],
        conversation_id: str,
    ) -> SubagentResult:
        """Run a subagent for a specific area-scoped task.

        Args:
            goal: What the subagent should accomplish.
            context: Area-scoped context (entities, devices in this area only).
            area: Area name (for logging and result tracking).
            tools: Restricted toolset (no delegate_task, no save_automation_skill).
            conversation_id: Parent conversation ID.

        Returns:
            SubagentResult with status, summary, and metrics.
        """
        start = time.monotonic()
        tokens_used = 0

        try:
            # Build scoped system prompt
            system_prompt = (
                f"You are handling the '{area}' portion of a multi-area request. "
                f"Focus ONLY on entities and devices in {area}.\n\n"
                f"Goal: {goal}\n\n"
                f"Available context for {area}:\n{context[:4000]}"
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": goal},
            ]

            assistant_content = ""
            tool_trace: list[dict[str, Any]] = []

            for iteration in range(1, self.max_iterations + 1):
                # Budget check
                if tokens_used >= self.max_tokens:
                    logger.warning(
                        "Subagent '%s' exceeded token budget (%d/%d) at iteration %d",
                        area, tokens_used, self.max_tokens, iteration,
                    )
                    return SubagentResult(
                        area=area,
                        status="budget_exceeded",
                        summary=assistant_content or "Budget exceeded before completion",
                        tool_trace=tool_trace,
                        tokens_used=tokens_used,
                        duration_seconds=time.monotonic() - start,
                    )

                # Call OpenAI
                response = await self.openai_client.chat_completion(
                    messages=messages, tools=tools, tool_choice="auto",
                )

                # Track tokens
                if response.usage:
                    tokens_used += (
                        getattr(response.usage, "input_tokens", 0)
                        + getattr(response.usage, "output_tokens", 0)
                    )

                assistant_content = response.output_text or ""
                function_calls = [
                    item for item in response.output
                    if getattr(item, "type", None) == "function_call"
                ]

                if not function_calls:
                    break  # Done — final response

                # Execute tool calls
                for fc in function_calls:
                    tool_trace.append({
                        "name": fc.name,
                        "arguments": fc.arguments,
                        "iteration": iteration,
                    })

                    # Execute via tool service
                    try:
                        result = await self.tool_service.execute_tool(
                            fc.name, fc.arguments, conversation_id,
                        )
                        messages.append({"role": "tool_call", "_function_call": fc})
                        messages.append({
                            "role": "tool",
                            "tool_call_id": fc.call_id,
                            "content": str(result)[:2000],
                        })
                    except Exception as e:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": fc.call_id,
                            "content": f"Error: {e}",
                        })

            return SubagentResult(
                area=area,
                status="completed",
                summary=assistant_content,
                tool_trace=tool_trace,
                tokens_used=tokens_used,
                duration_seconds=time.monotonic() - start,
            )

        except Exception as e:
            logger.error("Subagent '%s' failed: %s", area, e, exc_info=True)
            return SubagentResult(
                area=area,
                status="failed",
                error=str(e),
                duration_seconds=time.monotonic() - start,
            )
