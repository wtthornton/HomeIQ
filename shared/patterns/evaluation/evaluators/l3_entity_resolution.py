"""
L3 Entity Resolution Evaluator — HA entity/area resolution scoring.

Story 3.3: Score how well the pipeline resolved abstract references
(room names, device types) into concrete HA entity IDs and area IDs.
"""

from __future__ import annotations

from ..base_evaluator import DetailsEvaluator
from ..models import EvaluationResult, SessionTrace


class EntityResolutionEvaluator(DetailsEvaluator):
    """L3 — Score entity resolution quality.

    Scoring:
      - 70% weight on resolution ratio (resolved / total entities)
      - 30% bonus if YAML validates successfully
      - 0.8 default if no entities to resolve (simple template)
    """

    name = "entity_resolution"

    async def evaluate(self, session: SessionTrace) -> EvaluationResult:
        resolved = session.metadata.get("resolved_context", {})
        placeholders = session.metadata.get("unresolved_placeholders", [])
        yaml_valid = session.metadata.get("yaml_valid", False)

        total = len(resolved) + len(placeholders)
        if total == 0:
            return self._result(
                0.8, "N/A",
                "No entities to resolve (simple template)",
            )

        resolved_ratio = len(resolved) / total if total else 0
        score = resolved_ratio * 0.7  # 70% weight on resolution
        if yaml_valid:
            score += 0.3  # 30% bonus if YAML validates

        if score >= 0.8:
            label = "Resolved"
        elif score >= 0.4:
            label = "Partial"
        else:
            label = "Unresolved"

        details = f"{len(resolved)}/{total} resolved, yaml_valid={yaml_valid}"
        return self._result(min(score, 1.0), label, details)
