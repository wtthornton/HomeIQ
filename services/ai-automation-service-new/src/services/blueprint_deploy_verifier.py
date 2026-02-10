"""
Blueprint Deploy Verifier

Epic: High-Value Domain Extensions, Story 4
Concrete PostActionVerifier for blueprint deployment verification.

Verifies each automation entity created by a blueprint after deployment
and surfaces per-entity warnings when HA fails to load them.
"""

import logging
import sys
from pathlib import Path
from typing import Any

_project_root = str(Path(__file__).resolve().parents[4])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from shared.patterns import PostActionVerifier, VerificationResult, VerificationWarning

logger = logging.getLogger(__name__)


class BlueprintDeployVerifier(PostActionVerifier):
    """
    Verifies automation state(s) after deploying a blueprint to Home Assistant.

    Supports single and multi-automation blueprints. Returns aggregate
    verification result with per-entity warnings.
    """

    def __init__(self, get_state_fn) -> None:
        """
        Args:
            get_state_fn: Async callable that takes entity_id and returns state dict.
        """
        self._get_state = get_state_fn

    async def verify(self, action_result: dict[str, Any]) -> VerificationResult:
        """
        Verify blueprint deployment result.

        Args:
            action_result: Dict with 'automation_ids' (list) or 'automation_id' (str)
                           and 'status'.

        Returns:
            VerificationResult with aggregate success and per-entity warnings.
        """
        automation_ids = action_result.get("automation_ids", [])
        if not automation_ids:
            single = action_result.get("automation_id")
            if single:
                automation_ids = [single]

        if not automation_ids:
            return VerificationResult(
                success=True,
                state="unknown",
                metadata={"message": "No automation IDs provided for verification"},
            )

        all_warnings: list[VerificationWarning] = []
        per_entity: dict[str, dict[str, Any]] = {}
        any_unavailable = False

        for aid in automation_ids:
            entity_id = (
                aid if str(aid).startswith("automation.") else f"automation.{aid}"
            )
            state_data = await self._get_state(entity_id)

            if not state_data:
                per_entity[entity_id] = {"state": None, "last_triggered": None}
                continue

            state = state_data.get("state")
            attrs = state_data.get("attributes", {})
            last_triggered = attrs.get("last_triggered")
            per_entity[entity_id] = {
                "state": state,
                "last_triggered": last_triggered,
            }

            if state == "unavailable":
                any_unavailable = True
                all_warnings.extend(self.map_warnings(state_data))

        overall_state = "partial" if any_unavailable else "on"

        return VerificationResult(
            success=not any_unavailable,
            state=overall_state,
            warnings=all_warnings,
            metadata={
                "per_entity": per_entity,
                "total": len(automation_ids),
                "unavailable_count": sum(
                    1 for v in per_entity.values() if v.get("state") == "unavailable"
                ),
            },
        )

    def map_warnings(self, state_data: dict[str, Any] | None) -> list[VerificationWarning]:
        """Map blueprint automation state to deployment warnings."""
        warnings: list[VerificationWarning] = []
        if state_data and state_data.get("state") == "unavailable":
            entity_id = state_data.get("entity_id", "unknown")
            warnings.append(
                VerificationWarning(
                    message=(
                        f"Blueprint automation '{entity_id}' state is 'unavailable'. "
                        "Home Assistant may have failed to load it. Check HA logs."
                    ),
                    entity_id=entity_id,
                    severity="warning",
                    guidance=(
                        "Check Home Assistant logs for YAML configuration errors. "
                        "Verify all blueprint inputs are valid."
                    ),
                )
            )
        return warnings
