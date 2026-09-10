"""The agent slice's LLM calls, served by AgentForge (TAP-7275).

Replaces ``services/openai_client.py`` and ``services/llm_router.py``. There is
no provider choice left to route between: every model call this slice makes is
a workflow run on AgentForge, and the model, the sampling settings and the
credential are properties of the gene definition, not of this process.

The chat turn is the substantive change. It used to be an iterative
tool-calling loop run here -- call the model, execute whatever Home Assistant
tools it asked for, feed the results back, repeat. That loop now lives inside
the ``assistant-chat`` workflow, whose gene reaches the same Home Assistant
data through the ``homeiq`` MCP read tools. What stays here is the
conversation: assembling the prompt from HomeIQ's own context, persisting the
turn, and reporting what the run did.

``/api/v1/tools`` and ``/api/v1/tools/execute`` are unaffected. Those are
deterministic Home Assistant tool dispatch with no model in the path, so they
stay in this process -- they are data slice, not LLM slice.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ...agentforge_client import (
    AgentForgeClient,
    AgentForgeError,
)

logger = logging.getLogger(__name__)

WORKFLOW_CHAT = "assistant-chat"
WORKFLOW_MEMORY_EXTRACT = "memory-extract"
WORKFLOW_AUTOMATION_DRAFT = "automation-draft"


class AgentChatError(Exception):
    """A chat turn could not be answered by AgentForge."""


class AgentChatClient:
    """AgentForge-backed replacement for the agent slice's ``OpenAIClient``."""

    def __init__(self, settings: Any, agentforge: AgentForgeClient | None = None) -> None:
        self.settings = settings
        self.agentforge = agentforge or AgentForgeClient(
            base_url=settings.agentforge_url,
            api_key=(
                settings.agentforge_api_key.get_secret_value()
                if settings.agentforge_api_key
                else None
            ),
            project_slug=settings.agentforge_project_slug,
            timeout=settings.agentforge_timeout,
        )
        self.total_requests = 0
        self.total_errors = 0

    @property
    def configured(self) -> bool:
        return self.agentforge.configured

    async def close(self) -> None:
        await self.agentforge.close()

    async def _run(self, workflow: str, inputs: dict[str, Any]) -> dict[str, Any]:
        self.total_requests += 1
        try:
            return await self.agentforge.run_workflow_json(workflow, inputs)
        except AgentForgeError as exc:
            self.total_errors += 1
            logger.error("AgentForge workflow %s failed: %s", workflow, exc)
            raise AgentChatError(str(exc)) from exc

    async def chat_turn(
        self,
        *,
        system_prompt: str,
        conversation: list[dict[str, str]],
        message: str,
    ) -> dict[str, Any]:
        """Answer one conversation turn.

        ``conversation`` is the prior turns (roles ``user``/``assistant``),
        already trimmed to the token budget by ``PromptAssemblyService``. The
        gene sees HomeIQ's assembled system prompt as ``house_context`` so the
        answer stays grounded in this home rather than in the gene's own idea
        of one.
        """
        return await self._run(
            WORKFLOW_CHAT,
            {
                "message": message,
                "house_context": system_prompt,
                "conversation": json.dumps(conversation, default=str),
            },
        )

    async def extract_json(self, text: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Return an instance of ``schema`` transcribed from ``text``.

        Backed by ``hiq-extract``, whose contract is that a field the source
        does not state comes back ``null`` and listed in ``unsourced_fields``
        rather than guessed. That is exactly the property memory extraction
        needs: a fact the user never said must not become a stored memory.
        """
        answer = await self._run(
            WORKFLOW_MEMORY_EXTRACT,
            {"text": text, "target_schema": json.dumps(schema)},
        )
        instance = answer.get("instance")
        return instance if isinstance(instance, dict) else {}

    async def draft_automation(
        self,
        requirement: str,
        entity_inventory: str = "",
    ) -> dict[str, Any]:
        """Draft a Home Assistant automation from a plain-text requirement."""
        return await self._run(
            WORKFLOW_AUTOMATION_DRAFT,
            {
                "behavior_requirement": requirement,
                "entity_inventory": entity_inventory,
            },
        )

    def get_token_stats(self) -> dict[str, Any]:
        """Report what this process can honestly see about spend.

        Token counts are no longer visible here: the model call happens inside
        AgentForge, which meters it in its own invocation log. Reporting a
        fabricated zero-token count under the old key names would read as "this
        turn was free", so the keys name what they are.
        """
        return {
            "engine": "agentforge",
            "workflow_runs": self.total_requests,
            "workflow_errors": self.total_errors,
        }

    def reset_stats(self) -> None:
        self.total_requests = 0
        self.total_errors = 0
