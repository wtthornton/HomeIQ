"""
L2 Template Match Evaluator — Verify correct template selection.

Story 3.1: Deterministic keyword-based intent-to-template matching with
LLM fallback for unrecognised intents.
"""

from __future__ import annotations

import re

from ..base_evaluator import PathEvaluator
from ..llm_judge import JudgeRubric, LLMJudge
from ..models import EvaluationResult, SessionTrace


class TemplateAppropriatenessEvaluator(PathEvaluator):
    """L2 — Verify the LLM selected the right template for the user's intent.

    Uses deterministic keyword matching first, falling back to LLM judge
    only for prompts that don't match any known intent pattern.
    """

    name = "template_appropriateness"

    # Intent keywords -> acceptable template IDs.
    # First matching group wins, so order matters.
    INTENT_TEMPLATE_MAP: dict[tuple[str, ...], list[str]] = {
        ("turn on", "switch on", "light on"): [
            "room_entry_light_on",
            "state_based_automation",
        ],
        ("schedule", "every", "hourly", "daily", "cron"): [
            "scheduled_task",
        ],
        ("time", "at midnight", "at noon", "at 7"): [
            "time_based_light_on",
            "scheduled_task",
        ],
        ("motion", "presence", "enter", "entry"): [
            "room_entry_light_on",
            "motion_dim_off",
        ],
        ("temperature", "thermostat", "hvac", "degrees"): [
            "temperature_control",
        ],
        ("leave", "away", "depart"): [
            "state_based_automation",
        ],
        ("turn off", "switch off"): [
            "state_based_automation",
            "time_based_light_on",
        ],
        ("scene", "movie", "party", "relax"): [
            "scene_activation",
        ],
        ("notify", "alert", "message"): [
            "notification_on_event",
        ],
    }

    def __init__(self, llm_judge: LLMJudge | None = None):
        self._judge = llm_judge or LLMJudge()

    async def evaluate(self, session: SessionTrace) -> EvaluationResult:
        prompt = (
            session.user_messages[0].content.lower()
            if session.user_messages
            else ""
        )
        template_id = session.metadata.get("template_id", "")

        if not template_id:
            return self._result(0.0, "Missing", "No template_id in metadata")

        # Deterministic keyword matching
        for keywords, valid_templates in self.INTENT_TEMPLATE_MAP.items():
            if any(re.search(rf'\b{re.escape(kw)}\b', prompt) for kw in keywords):
                if template_id in valid_templates:
                    return self._result(
                        1.0,
                        "Match",
                        f"Template '{template_id}' matches intent",
                    )
                return self._result(
                    0.0,
                    "Mismatch",
                    f"Expected one of {valid_templates} for intent, "
                    f"got '{template_id}'",
                )

        # No deterministic match — fall back to LLM judge
        return await self._llm_fallback(session, template_id)

    async def _llm_fallback(
        self, session: SessionTrace, template_id: str
    ) -> EvaluationResult:
        rubric = JudgeRubric(
            name="template_appropriateness",
            prompt_template=(
                "Does the selected template match the user's "
                "automation intent?\n\n"
                "User request: {{ user_input }}\n"
                f"Selected template: {template_id}\n\n"
                "Is this template appropriate for the request?"
            ),
            output_labels=["Yes", "Partial", "No"],
            score_mapping={"Yes": 1.0, "Partial": 0.5, "No": 0.0},
        )
        result = await self._judge.judge(session, rubric)
        return self._result(result.score, result.label, result.explanation)
