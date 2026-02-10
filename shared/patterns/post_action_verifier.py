"""
PostActionVerifier - Reusable Pattern C: Post-Action Verification

Epic: Reusable Pattern Framework, Story 4
Abstract base class for post-action verification: verify results after
deploy/apply and surface warnings to users.

Pattern: After performing an action (deploy, apply, configure), verify
the result and map failures to user-facing warnings.

Usage:
    class BlueprintDeployVerifier(PostActionVerifier):
        async def verify(self, action_result):
            state = await self.ha_client.get_state(action_result["entity_id"])
            return VerificationResult(
                success=state.get("state") != "unavailable",
                state=state.get("state"),
                warnings=self.map_warnings(state),
            )
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VerificationWarning:
    """A single verification warning with actionable guidance."""
    message: str
    entity_id: str | None = None
    severity: str = "warning"  # "warning" | "error" | "info"
    guidance: str | None = None


@dataclass
class VerificationResult:
    """
    Result of post-action verification.

    Attributes:
        success: True if the action completed successfully
        state: Current state of the target entity/resource
        warnings: List of warnings to surface to the user
        metadata: Additional data from the verification check
    """
    success: bool
    state: str | None = None
    warnings: list[VerificationWarning] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def verification_warning(self) -> str | None:
        """
        Backward-compatible single warning string.

        Returns the first warning message, or None if no warnings.
        This maintains compatibility with the existing deploy response shape.
        """
        if self.warnings:
            return self.warnings[0].message
        return None

    @property
    def has_warnings(self) -> bool:
        """True if any warnings exist."""
        return len(self.warnings) > 0


class PostActionVerifier(ABC):
    """
    Abstract base class for post-action verification.

    Subclasses implement verify() to check the result of an action
    and return a VerificationResult with any warnings.
    """

    @abstractmethod
    async def verify(self, action_result: dict[str, Any]) -> VerificationResult:
        """
        Verify the result of an action.

        Args:
            action_result: Dict containing action output
                (e.g. automation_id, entity_id, status, data)

        Returns:
            VerificationResult with success status and warnings
        """
        ...

    def map_warnings(self, state_data: dict[str, Any] | None) -> list[VerificationWarning]:
        """
        Map verification state data to user-facing warnings.

        Override in subclass for domain-specific warning logic.
        Default implementation checks for 'unavailable' state.

        Args:
            state_data: State dict from HA API or similar

        Returns:
            List of warnings (empty if verification passed)
        """
        warnings: list[VerificationWarning] = []
        if state_data and state_data.get("state") == "unavailable":
            entity_id = state_data.get("entity_id", "unknown")
            warnings.append(
                VerificationWarning(
                    message=(
                        f"Entity {entity_id} state is 'unavailable'. "
                        "The system may have failed to load it. Check logs for errors."
                    ),
                    entity_id=entity_id,
                    severity="warning",
                    guidance="Check Home Assistant logs for configuration errors.",
                )
            )
        return warnings
