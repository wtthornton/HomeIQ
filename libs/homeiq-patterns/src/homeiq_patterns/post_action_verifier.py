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
        verified_attributes: Attributes that were verified (actual values)
        expected_state: Expected state dict (for audit trail)
    """
    success: bool
    state: str | None = None
    warnings: list[VerificationWarning] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    verified_attributes: dict[str, Any] = field(default_factory=dict)
    expected_state: dict[str, Any] | None = None

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


class VerificationResultStore(ABC):
    """
    Abstract store for persisting verification results.

    Implementations write results to a backing store (InfluxDB, SQLite, etc.)
    and support querying recent failures/successes for feedback loops.
    """

    @abstractmethod
    async def store(
        self,
        result: "VerificationResult",
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Persist a verification result.

        Args:
            result: The verification result to store
            context: Optional context (entity_id, action_type, etc.)
        """
        ...

    @abstractmethod
    async def query_failures(
        self,
        entity_id: str,
        lookback_hours: int = 24,
    ) -> list[dict[str, Any]]:
        """
        Query recent verification failures for an entity.

        Args:
            entity_id: Entity to query failures for
            lookback_hours: How far back to look (default 24h)

        Returns:
            List of failure records
        """
        ...

    @abstractmethod
    async def query_successes(
        self,
        entity_ids: list[str],
        lookback_hours: int = 168,
    ) -> list[dict[str, Any]]:
        """
        Query recent verification successes for entities.

        Args:
            entity_ids: Entities to query successes for
            lookback_hours: How far back to look (default 7 days)

        Returns:
            List of success records
        """
        ...


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

    # Attributes to check for state-match verification
    STATE_ATTRIBUTES = ("brightness", "color_temp", "temperature", "hvac_mode", "fan_mode", "position")

    def verify_state_match(
        self,
        actual: dict[str, Any],
        expected: dict[str, Any],
        entity_id: str | None = None,
    ) -> list[VerificationWarning]:
        """
        Compare actual entity state against expected state and attributes.

        Args:
            actual: Actual state dict from HA (with "state" and "attributes" keys)
            expected: Expected state dict (with optional "state" and attribute keys)
            entity_id: Entity identifier for warning messages

        Returns:
            List of warnings for mismatches. State mismatches are "warning",
            attribute mismatches are "info".
        """
        warnings: list[VerificationWarning] = []
        eid = entity_id or actual.get("entity_id", "unknown")

        # Check main state field
        expected_state = expected.get("state")
        actual_state = actual.get("state")
        if expected_state is not None and actual_state != expected_state:
            warnings.append(
                VerificationWarning(
                    message=(
                        f"Entity '{eid}' is '{actual_state}' "
                        f"but expected '{expected_state}'."
                    ),
                    entity_id=eid,
                    severity="warning",
                    guidance="The action may not have taken effect. Check HA logs.",
                )
            )

        # Check attributes
        actual_attrs = actual.get("attributes", {})
        for attr in self.STATE_ATTRIBUTES:
            expected_val = expected.get(attr)
            if expected_val is None:
                continue
            actual_val = actual_attrs.get(attr)
            if actual_val is None:
                continue
            if actual_val != expected_val:
                warnings.append(
                    VerificationWarning(
                        message=(
                            f"Entity '{eid}' attribute '{attr}' is "
                            f"'{actual_val}' but expected '{expected_val}'."
                        ),
                        entity_id=eid,
                        severity="info",
                        guidance=f"The '{attr}' value did not match the requested value.",
                    )
                )

        return warnings

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
