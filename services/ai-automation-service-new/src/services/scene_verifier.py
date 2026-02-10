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
        entity_id = (
            scene_id if scene_id.startswith("scene.") else f"scene.{scene_id}"
        )

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

        return VerificationResult(
            success=state != "unavailable",
            state=state,
            warnings=warnings,
            metadata={"entity_id": entity_id},
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
