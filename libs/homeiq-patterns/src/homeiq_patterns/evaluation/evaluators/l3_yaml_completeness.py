"""
L3 YAML Completeness Evaluator — HA automation structure validation.

Story 3.2: Deterministic checks for required keys, list formats,
and unresolved placeholders in generated YAML.
"""

from __future__ import annotations

import yaml

from ..base_evaluator import DetailsEvaluator
from ..models import EvaluationResult, SessionTrace

# Templates known to require a condition block for correct behavior.
# Kept at module level so evaluator subclasses can reference or extend it.
CONDITION_EXPECTED_TEMPLATES: frozenset[str] = frozenset({
    "tmpl_thermostat",
    "tmpl_presence",
    "tmpl_time_range",
    "tmpl_energy_saving",
    "tmpl_night_mode",
})


class YAMLCompletenessEvaluator(DetailsEvaluator):
    """L3 — Verify generated YAML has all required HA automation structure.

    Scoring (1.0 total):
      - trigger present: 0.2
      - action present:  0.2
      - alias present:   0.2
      - trigger is list: 0.1  (HA 2024.x+ compliance)
      - action is list:  0.1  (HA 2024.x+ compliance)
      - no unresolved placeholders: 0.2
      - condition present (bonus when template expects it): 0.1
    """

    name = "yaml_completeness"

    async def evaluate(self, session: SessionTrace) -> EvaluationResult:
        yaml_str = session.metadata.get("generated_yaml", "")
        if not yaml_str:
            if session.metadata.get("execution_mode") == "preview":
                return self._result(
                    0.5, "N/A",
                    "No YAML generated (preview may not compile)",
                )
            return self._result(0.0, "Missing", "No generated YAML in metadata")

        try:
            parsed = yaml.safe_load(yaml_str)
        except yaml.YAMLError as exc:
            return self._result(0.0, "Invalid", f"YAML parse error: {exc}")

        if not isinstance(parsed, dict):
            return self._result(
                0.0, "Invalid",
                f"YAML root is {type(parsed).__name__}, expected dict",
            )

        checks: list[str] = []
        score_parts: list[float] = []

        # Required keys (0.2 each)
        for key in ("trigger", "action", "alias"):
            if key in parsed:
                score_parts.append(0.2)
                checks.append(f"{key}: present")
            else:
                checks.append(f"{key}: MISSING")

        # Trigger/action must be lists (0.1 each) — HA 2024.x+ compliance
        trigger = parsed.get("trigger")
        if isinstance(trigger, list):
            score_parts.append(0.1)
            checks.append("trigger: is list")
        elif trigger is not None:
            checks.append("trigger: NOT a list (HA 2024.x+ requires list)")

        action = parsed.get("action")
        if isinstance(action, list):
            score_parts.append(0.1)
            checks.append("action: is list")
        elif action is not None:
            checks.append("action: NOT a list (HA 2024.x+ requires list)")

        # No unresolved placeholders (0.2)
        placeholders = session.metadata.get("unresolved_placeholders", [])
        if not placeholders:
            score_parts.append(0.2)
            checks.append("No unresolved placeholders")
        else:
            checks.append(f"Unresolved: {placeholders}")

        # Condition block check (0.1 bonus, capped at 1.0).
        # When the session's template is known to require a condition, note
        # its absence explicitly; otherwise treat it as a generic bonus.
        template_id = session.metadata.get("template_id", "")
        condition_expected = (
            session.metadata.get("condition_expected")
            or template_id in CONDITION_EXPECTED_TEMPLATES
        )
        has_condition = "condition" in parsed and parsed["condition"]

        if has_condition:
            score_parts.append(0.1)
            checks.append("condition: present (bonus)")
        elif condition_expected:
            checks.append(
                f"condition: MISSING (expected for template '{template_id}')"
            )

        score = min(sum(score_parts), 1.0)
        label = "Complete" if score >= 0.8 else "Incomplete"
        return self._result(score, label, "; ".join(checks))
