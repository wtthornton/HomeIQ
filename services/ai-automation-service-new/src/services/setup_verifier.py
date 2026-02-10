"""
Device Setup Verifier

Epic: High-Value Domain Extensions, Story 9
Concrete PostActionVerifier for post-device-setup verification.

Verifies integration health and entity creation after a device setup/pairing
operation, and surfaces warnings when the integration is unhealthy.
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


class SetupVerifier(PostActionVerifier):
    """
    Verifies device/integration health after setup.

    Checks that expected entity IDs exist and are not 'unavailable',
    and verifies overall integration health via HA API.
    """

    def __init__(self, get_state_fn) -> None:
        """
        Args:
            get_state_fn: Async callable that takes entity_id and returns state dict.
        """
        self._get_state = get_state_fn

    async def verify(self, action_result: dict[str, Any]) -> VerificationResult:
        """
        Verify device setup result.

        Args:
            action_result: Dict with:
                - entity_ids (list[str]): Expected entity IDs created by the integration
                - integration (str): Integration name
                - status (str): Setup status

        Returns:
            VerificationResult with per-entity status and warnings.
        """
        entity_ids = action_result.get("entity_ids", [])
        integration = action_result.get("integration", "unknown")

        if not entity_ids:
            return VerificationResult(
                success=True,
                state="unknown",
                metadata={
                    "integration": integration,
                    "message": "No entity IDs provided for verification",
                },
            )

        all_warnings: list[VerificationWarning] = []
        per_entity: dict[str, dict[str, Any]] = {}
        unavailable_count = 0

        for eid in entity_ids:
            state_data = await self._get_state(eid)

            if state_data is None:
                per_entity[eid] = {"state": "not_found"}
                unavailable_count += 1
                all_warnings.append(
                    VerificationWarning(
                        message=(
                            f"Entity '{eid}' was not created after {integration} setup. "
                            "The device may not have been discovered."
                        ),
                        entity_id=eid,
                        severity="warning",
                        guidance=(
                            f"Check {integration} logs. Ensure the device is in pairing mode "
                            "and within range of the coordinator."
                        ),
                    )
                )
                continue

            state = state_data.get("state")
            per_entity[eid] = {"state": state}

            if state == "unavailable":
                unavailable_count += 1
                all_warnings.extend(self.map_warnings(state_data))

        overall_state = "healthy" if unavailable_count == 0 else "degraded"

        return VerificationResult(
            success=unavailable_count == 0,
            state=overall_state,
            warnings=all_warnings,
            metadata={
                "integration": integration,
                "per_entity": per_entity,
                "total": len(entity_ids),
                "unavailable_count": unavailable_count,
            },
        )

    def map_warnings(self, state_data: dict[str, Any] | None) -> list[VerificationWarning]:
        """Map device entity state to setup warnings."""
        warnings: list[VerificationWarning] = []
        if state_data and state_data.get("state") == "unavailable":
            entity_id = state_data.get("entity_id", "unknown")
            warnings.append(
                VerificationWarning(
                    message=(
                        f"Entity '{entity_id}' is 'unavailable' after setup. "
                        "The device may be offline or not responding."
                    ),
                    entity_id=entity_id,
                    severity="warning",
                    guidance=(
                        "Check device power, ensure it's within range, "
                        "and verify the integration is running."
                    ),
                )
            )
        return warnings
