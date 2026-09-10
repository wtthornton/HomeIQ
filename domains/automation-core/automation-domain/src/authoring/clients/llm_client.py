"""Authoring's LLM slice, served by AgentForge (TAP-7275).

This module replaces ``clients/llm_client.py``. The four generation calls
the authoring services make are now AgentForge workflow runs; no OpenAI
credential reaches this process.

What stayed here and what moved:

* **Stayed** — every HomeIQ-specific input: the entity inventory that pins the
  automation to real ``entity_id``s (R2), the pattern/device/area context, and
  the parsing of the answer into the shapes the callers already expect. That is
  the data slice.
* **Moved** — the model call, its system prompt, its retries, and its
  credential. Those live in ``agentforge/projects/homeiq/workflows/``.

The entity inventory is passed as a workflow *input* rather than baked into a
prompt string here, so the gene's own instructions own the "use only these
entity ids" rule and this module owns only the inventory's contents.

``generate_structured_plan`` is deliberately served by the same
``automation-draft`` workflow as ``generate_yaml``: the gene answers with
Home Assistant YAML, and the plan-then-render path existed only to turn a JSON
plan into that same YAML. Both callers therefore reach one workflow, and the
plan shape is reconstructed from the gene's structured answer.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import yaml

from ..config import settings
from ...agentforge_client import AgentForgeClient, AgentForgeError

logger = logging.getLogger(__name__)

WORKFLOW_DRAFT = "automation-draft"
WORKFLOW_JSON = "automation-json"
WORKFLOW_DESCRIBE = "suggestion-describe"
WORKFLOW_INTENT_PLAN = "intent-plan"

#: Per-domain cap on the entity ids handed to a gene. Matches the limit the
#: OpenAI prompts used, so the inventory a gene sees is the same size it was.
ENTITY_SAMPLE_PER_DOMAIN = 30


class AutomationLLMError(Exception):
    """A generation call to AgentForge failed or answered unusably."""


def format_entity_context(entity_context: dict[str, Any] | None) -> str:
    """Render an entity context into the ``DOMAIN: id, id, ...`` inventory.

    Returns an empty string when there is no inventory, which the genes read as
    "no inventory supplied" — never as "there are no entities".
    """
    if not entity_context or not entity_context.get("entities"):
        return ""
    lines: list[str] = []
    for domain, entity_list in sorted(entity_context["entities"].items()):
        if not entity_list:
            continue
        ids = [
            e.get("entity_id", "")
            for e in entity_list[:ENTITY_SAMPLE_PER_DOMAIN]
            if e.get("entity_id")
        ]
        if not ids:
            continue
        line = f"{domain.upper()}: {', '.join(ids)}"
        if len(entity_list) > ENTITY_SAMPLE_PER_DOMAIN:
            line += f" (and {len(entity_list) - ENTITY_SAMPLE_PER_DOMAIN} more)"
        lines.append(line)
    return "\n".join(lines)


def plan_from_draft(draft: dict[str, Any]) -> dict[str, Any]:
    """Turn an ``automation-draft`` answer into a structured plan dict.

    ``PlanParser.parse_plan`` wants ``alias`` plus ``trigger``/``action``
    (and optionally ``condition``/``mode``). The gene answers with the
    automation YAML, which carries exactly those keys — modern HA spells them
    ``triggers``/``conditions``/``actions``, so both spellings are accepted and
    normalised to the singular keys the parser reads.
    """
    raw_yaml = draft.get("automation_yaml")
    if not raw_yaml:
        refused = draft.get("refused") or {}
        raise AutomationLLMError(
            f"AgentForge refused to draft this automation: "
            f"{refused.get('rule_id', 'unknown-rule')} — {refused.get('reason', 'no reason given')}"
        )
    parsed = yaml.safe_load(raw_yaml)
    if isinstance(parsed, list):
        parsed = parsed[0] if parsed else {}
    if not isinstance(parsed, dict):
        raise AutomationLLMError("automation_yaml did not parse into a mapping")

    plan: dict[str, Any] = {
        "alias": parsed.get("alias") or draft.get("alias") or "",
        "description": parsed.get("description", ""),
        "mode": parsed.get("mode", "single"),
    }
    for singular, plural in (
        ("trigger", "triggers"),
        ("condition", "conditions"),
        ("action", "actions"),
    ):
        value = parsed.get(singular, parsed.get(plural))
        if value is not None:
            plan[singular] = value if isinstance(value, list) else [value]
    return plan


class AutomationLLMClient:
    """AgentForge-backed replacement for the authoring ``AutomationLLMClient``.

    The method names and return types are unchanged so the authoring services
    did not have to be rewritten around a new shape; only the engine changed.
    """

    def __init__(self, agentforge: AgentForgeClient | None = None) -> None:
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
        # Workflow spend is metered by AgentForge, not by a token count this
        # process can see. `total_tokens_used` is kept at 0 rather than removed
        # so `get_usage_stats()`'s callers keep their shape; the honest number
        # lives in AgentForge's invocation log.
        self.total_tokens_used = 0
        self.total_cost_usd = 0.0
        self.workflow_runs = 0

    @property
    def configured(self) -> bool:
        return self.agentforge.configured

    async def _run(self, workflow: str, inputs: dict[str, Any]) -> dict[str, Any]:
        try:
            answer = await self.agentforge.run_workflow_json(workflow, inputs)
        except AgentForgeError as exc:
            logger.error("AgentForge workflow %s failed: %s", workflow, exc)
            raise AutomationLLMError(str(exc)) from exc
        self.workflow_runs += 1
        return answer

    async def generate_yaml(
        self,
        prompt: str,
        entity_context: dict[str, Any] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
    ) -> str:
        """Return Home Assistant automation YAML for ``prompt``.

        ``temperature``/``max_tokens`` are accepted and ignored: sampling and
        token budget are now properties of the gene definition in AgentForge,
        not of this call site. They stay in the signature because the callers
        pass them positionally in places.
        """
        draft = await self._run(
            WORKFLOW_DRAFT,
            {
                "behavior_requirement": prompt,
                "entity_inventory": format_entity_context(entity_context),
            },
        )
        automation_yaml = draft.get("automation_yaml")
        if not automation_yaml:
            refused = draft.get("refused") or {}
            raise AutomationLLMError(
                f"AgentForge refused to draft this automation: "
                f"{refused.get('rule_id', 'unknown-rule')} — "
                f"{refused.get('reason', 'no reason given')}"
            )
        return str(automation_yaml).strip()

    async def generate_structured_plan(
        self,
        prompt: str,
        entity_context: dict[str, Any] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        """Return a structured automation plan dict for ``prompt``."""
        draft = await self._run(
            WORKFLOW_DRAFT,
            {
                "behavior_requirement": prompt,
                "entity_inventory": format_entity_context(entity_context),
            },
        )
        return plan_from_draft(draft)

    async def generate_homeiq_automation_json(
        self,
        prompt: str,
        homeiq_context: dict[str, Any] | None = None,
        entity_context: dict[str, Any] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 3000,
    ) -> dict[str, Any]:
        """Return a HomeIQ JSON Automation object for ``prompt``."""
        answer = await self._run(
            WORKFLOW_JSON,
            {
                "behavior_requirement": prompt,
                "entity_inventory": format_entity_context(entity_context),
                "homeiq_context": json.dumps(homeiq_context or {}, default=str),
            },
        )
        automation = answer.get("automation")
        if not isinstance(automation, dict):
            raise AutomationLLMError("automation-json workflow returned no 'automation' object")
        return automation

    async def generate_suggestion_description(
        self,
        pattern_data: dict[str, Any],
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        """Return a short user-facing description of ``pattern_data``."""
        answer = await self._run(
            WORKFLOW_DESCRIBE,
            {"pattern_data": json.dumps(pattern_data, default=str)},
        )
        description = answer.get("description") or answer.get("answer") or ""
        return str(description).strip()

    async def plan_intent(
        self,
        user_text: str,
        template_catalog: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Select a template for ``user_text`` and fill its parameters.

        The catalogue is built by HomeIQ from its own template library and
        passed as an input, so the gene can only choose a template that
        actually exists here.
        """
        return await self._run(
            WORKFLOW_INTENT_PLAN,
            {
                "user_text": user_text,
                "template_catalog": template_catalog,
                "context": json.dumps(context or {}, default=str),
            },
        )

    def get_usage_stats(self) -> dict[str, Any]:
        return {
            "total_tokens": self.total_tokens_used,
            "total_cost_usd": self.total_cost_usd,
            "workflow_runs": self.workflow_runs,
            "engine": "agentforge",
        }

    def reset_usage_stats(self) -> None:
        self.total_tokens_used = 0
        self.total_cost_usd = 0.0
        self.workflow_runs = 0

    async def close(self) -> None:
        await self.agentforge.close()
