"""
Scene Creation Verifier

Epic: Platform-Wide Pattern Rollout, Story 7
Concrete PostActionVerifier for post-scene-creation verification.
"""

import logging
import sys
from pathlib import Path
from typing import Any

try:
    _project_root = str(Path(__file__).resolve().parents[4])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
except IndexError:
    pass  # Docker: PYTHONPATH already includes /app

from shared.patterns import PostActionVerifier, VerificationResult, VerificationWarning

logger = logging.getLogger(__name__)


class SceneVerifier(PostActionVerifier):
    """
    Verifies scene entity exists and is available after creation.
    """

    def __init__(self, get_state_fn) -> None:
        self._get_state = get_state_fn

    async def verify(self, action_result: dict[str, Any]) -> VerificationResult:
        scene_id = action_result.get("scene_id", "")
        entity_id = scene_id if scene_id.startswith("scene.") else f"scene.{scene_id}"

        state_data = await self._get_state(entity_id)
        if state_data is None:
            return VerificationResult(
                success=False,
                state="not_found",
                warnings=[
                    VerificationWarning(
                        message=f"Scene '{entity_id}' was not found after creation.",
                        entity_id=entity_id,
                        severity="warning",
                        guidance="Check Home Assistant logs for scene configuration errors.",
                    )
                ],
                metadata={"entity_id": entity_id},
            )

        warnings = self.map_warnings(state_data)
        state = state_data.get("state")

        # Verify individual entity states if expected_entities provided
        expected_entities = action_result.get("expected_entities")
        verified_attributes: dict = {}
        if expected_entities and isinstance(expected_entities, list):
            for expected in expected_entities:
                target_id = expected.get("entity_id")
                if not target_id:
                    continue
                target_state = await self._get_state(target_id)
                if target_state is None:
                    warnings.append(
                        VerificationWarning(
                            message=f"Scene target '{target_id}' not found after activation.",
                            entity_id=target_id,
                            severity="warning",
                            guidance="Verify the entity exists and is available.",
                        )
                    )
                    continue
                attr_warnings = self.verify_state_match(target_state, expected, target_id)
                warnings.extend(attr_warnings)
                verified_attributes[target_id] = target_state.get("attributes", {})

        return VerificationResult(
            success=state != "unavailable",
            state=state,
            warnings=warnings,
            metadata={"entity_id": entity_id},
            verified_attributes=verified_attributes,
            expected_state={"expected_entities": expected_entities} if expected_entities else None,
        )

    def map_warnings(self, state_data: dict[str, Any] | None) -> list[VerificationWarning]:
        warnings: list[VerificationWarning] = []
        if state_data and state_data.get("state") == "unavailable":
            entity_id = state_data.get("entity_id", "unknown")
            warnings.append(
                VerificationWarning(
                    message=f"Scene '{entity_id}' is 'unavailable'. HA may have rejected the definition.",
                    entity_id=entity_id,
                    severity="warning",
                    guidance="Check entity targets exist and have valid state values.",
                )
            )
        return warnings
