"""
Automation Deploy Verifier

Epic: Reusable Pattern Framework, Story 4
Concrete PostActionVerifier for automation deployment verification.

Verifies automation state after deployment and surfaces warnings
when HA fails to load the automation.
"""

import logging
import sys
from pathlib import Path
from typing import Any

# Ensure shared modules are importable
try:
    _project_root = str(Path(__file__).resolve().parents[4])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
except IndexError:
    pass  # Docker: PYTHONPATH already includes /app

from shared.patterns import PostActionVerifier, VerificationResult, VerificationWarning

logger = logging.getLogger(__name__)


class AutomationDeployVerifier(PostActionVerifier):
    """
    Verifies automation state after deployment to Home Assistant.

    Checks if the automation entity is available and warns if HA
    failed to load it (state = 'unavailable').
    """

    def __init__(self, get_state_fn) -> None:
        """
        Args:
            get_state_fn: Async callable that takes entity_id and returns state dict.
                          Typically ha_client.get_state.
        """
        self._get_state = get_state_fn

    async def verify(self, action_result: dict[str, Any]) -> VerificationResult:
        """
        Verify automation deployment result.

        Args:
            action_result: Dict with at least 'automation_id' and 'status'

        Returns:
            VerificationResult with state and any warnings
        """
        automation_id = action_result.get("automation_id", "")
        entity_id = (
            automation_id
            if str(automation_id).startswith("automation.")
            else f"automation.{automation_id}"
        )

        expected = action_result.get("expected_state")

        state_data = await self._get_state(entity_id)
        if not state_data:
            return VerificationResult(
                success=True,
                state=None,
                metadata={"entity_id": entity_id},
                expected_state=expected,
            )

        warnings = self.map_warnings(state_data)
        state = state_data.get("state")

        # Attribute-aware verification when expected state is provided
        verified_attributes: dict = {}
        if expected and isinstance(expected, dict):
            attr_warnings = self.verify_state_match(state_data, expected, entity_id)
            warnings.extend(attr_warnings)
            verified_attributes = state_data.get("attributes", {})

        return VerificationResult(
            success=state != "unavailable",
            state=state,
            warnings=warnings,
            metadata={
                "entity_id": entity_id,
                "attributes": state_data.get("attributes", {}),
            },
            verified_attributes=verified_attributes,
            expected_state=expected,
        )

    def map_warnings(self, state_data: dict[str, Any] | None) -> list[VerificationWarning]:
        """Map automation state to deployment warnings."""
        warnings: list[VerificationWarning] = []
        if state_data and state_data.get("state") == "unavailable":
            entity_id = state_data.get("entity_id", "unknown")
            warnings.append(
                VerificationWarning(
                    message=(
                        "Automation was deployed but state is 'unavailable'. "
                        "Home Assistant may have failed to load it. Check HA logs for errors."
                    ),
                    entity_id=entity_id,
                    severity="warning",
                    guidance="Check Home Assistant logs for YAML configuration errors.",
                )
            )
        return warnings
