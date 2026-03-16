"""
Delegate Service (Epic 70, Story 70.5).

Dispatches multi-area requests to parallel subagents, collects results,
and synthesizes a unified response.

Spawns up to MAX_SUBAGENTS parallel child loops with:
- Area-filtered context
- Restricted toolset (no delegate_task, no save_automation_skill)
- Per-subagent token budget
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .subagent_runner import SubagentResult, SubagentRunner

logger = logging.getLogger(__name__)

MAX_SUBAGENTS = 3
SUBAGENT_MAX_TOKENS = 8000
SUBAGENT_MAX_ITERATIONS = 15

# Tools that subagents cannot use
RESTRICTED_TOOLS = frozenset({"delegate_task", "save_automation_skill", "recall_skills"})


class DelegateService:
    """Dispatches tasks to parallel subagents with area-scoped context."""

    def __init__(
        self,
        openai_client: Any,
        tool_service: Any,
        conversation_service: Any,
        context_builder: Any,
        max_subagents: int = MAX_SUBAGENTS,
        subagent_max_tokens: int = SUBAGENT_MAX_TOKENS,
    ):
        self.openai_client = openai_client
        self.tool_service = tool_service
        self.conversation_service = conversation_service
        self.context_builder = context_builder
        self.max_subagents = max_subagents
        self.subagent_max_tokens = subagent_max_tokens

    async def delegate(
        self,
        tasks: list[dict[str, str]],
        conversation_id: str,
        tools: list[dict[str, Any]],
    ) -> list[SubagentResult]:
        """Dispatch tasks to parallel subagents.

        Args:
            tasks: List of {goal, area, context} dicts.
            conversation_id: Parent conversation ID.
            tools: Full tool list (will be filtered for subagents).

        Returns:
            List of SubagentResults, one per task.
        """
        # Limit to max subagents
        active_tasks = tasks[:self.max_subagents]

        # Filter restricted tools
        safe_tools = [
            t for t in tools
            if t.get("name") not in RESTRICTED_TOOLS
        ]

        # Spawn subagents in parallel
        runners = []
        for task in active_tasks:
            runner = SubagentRunner(
                openai_client=self.openai_client,
                tool_service=self.tool_service,
                conversation_service=self.conversation_service,
                max_iterations=SUBAGENT_MAX_ITERATIONS,
                max_tokens=self.subagent_max_tokens,
            )
            runners.append(
                runner.run(
                    goal=task.get("goal", ""),
                    context=task.get("context", ""),
                    area=task.get("area", "unknown"),
                    tools=safe_tools,
                    conversation_id=conversation_id,
                )
            )

        logger.info(
            "Delegating %d tasks to parallel subagents for conversation %s",
            len(runners), conversation_id,
        )

        results = await asyncio.gather(*runners, return_exceptions=True)

        # Convert exceptions to failed results
        processed: list[SubagentResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed.append(SubagentResult(
                    area=active_tasks[i].get("area", "unknown"),
                    status="failed",
                    error=str(result),
                ))
            else:
                processed.append(result)

        # Log summary
        completed = sum(1 for r in processed if r.status == "completed")
        total_tokens = sum(r.tokens_used for r in processed)
        logger.info(
            "Delegation complete: %d/%d tasks completed, %d total tokens",
            completed, len(processed), total_tokens,
        )

        return processed

    @staticmethod
    def synthesize_results(results: list[SubagentResult]) -> str:
        """Synthesize subagent results into a unified response."""
        if not results:
            return "No subtasks were executed."

        lines = []
        for result in results:
            status_icon = "✓" if result.status == "completed" else "⚠"
            lines.append(f"{status_icon} **{result.area}**: {result.summary[:300]}")
            if result.error:
                lines.append(f"  Error: {result.error}")

        return "\n\n".join(lines)
