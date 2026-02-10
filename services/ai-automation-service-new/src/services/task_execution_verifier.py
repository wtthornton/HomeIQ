"""
Task Execution Verifier

Epic: Platform-Wide Pattern Rollout, Story 8
Concrete PostActionVerifier for API Automation Edge post-execution verification.

Verifies task execution results and surfaces failures with retry recommendations.
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

# Errors that are likely transient and can be retried
TRANSIENT_ERRORS = (
    "timeout", "connection refused", "connection reset", "service unavailable",
    "rate limit", "502", "503", "504",
)


class TaskExecutionVerifier(PostActionVerifier):
    """
    Verifies task execution results after completion.

    Detects failed or partially failed executions from execution traces
    and surfaces actionable warnings with retry recommendations.
    """

    def __init__(self, get_state_fn) -> None:
        self._get_state = get_state_fn

    async def verify(self, action_result: dict[str, Any]) -> VerificationResult:
        """
        Verify task execution result.

        Args:
            action_result: Dict with:
                - task_id (str): Task identifier
                - status (str): Execution status (success, failed, partial)
                - entity_id (str): Optional target entity to verify state
                - expected_state (str): Optional expected entity state
                - error (str): Optional error message
                - trace (list): Optional execution trace entries
        """
        task_id = action_result.get("task_id", "unknown")
        status = action_result.get("status", "unknown")
        error = action_result.get("error", "")
        entity_id = action_result.get("entity_id")
        expected_state = action_result.get("expected_state")
        trace = action_result.get("trace", [])

        warnings: list[VerificationWarning] = []

        # Check explicit failure status
        if status == "failed":
            is_transient = any(t in str(error).lower() for t in TRANSIENT_ERRORS)
            warnings.append(
                VerificationWarning(
                    message=f"Task '{task_id}' failed: {error}",
                    entity_id=entity_id or task_id,
                    severity="error",
                    guidance=(
                        "This appears to be a transient error. Retry recommended."
                        if is_transient
                        else "Check automation configuration and entity availability."
                    ),
                )
            )
            return VerificationResult(
                success=False,
                state="failed",
                warnings=warnings,
                metadata={
                    "task_id": task_id,
                    "retryable": is_transient,
                    "error": error,
                },
            )

        # Check trace for errors
        trace_errors = [
            entry for entry in trace
            if isinstance(entry, dict) and entry.get("error")
        ]
        if trace_errors:
            for entry in trace_errors:
                warnings.append(
                    VerificationWarning(
                        message=f"Trace error in task '{task_id}': {entry.get('error')}",
                        entity_id=entity_id or task_id,
                        severity="warning",
                        guidance="Review execution trace for details.",
                    )
                )

        # Verify entity state if expected
        if entity_id and expected_state:
            state_data = await self._get_state(entity_id)
            if state_data is None:
                warnings.append(
                    VerificationWarning(
                        message=f"Target entity '{entity_id}' not found after task execution.",
                        entity_id=entity_id,
                        severity="warning",
                        guidance="Verify the entity exists and is available.",
                    )
                )
            elif state_data.get("state") != expected_state:
                actual = state_data.get("state")
                warnings.append(
                    VerificationWarning(
                        message=(
                            f"Entity '{entity_id}' is '{actual}' but expected '{expected_state}' "
                            f"after task execution."
                        ),
                        entity_id=entity_id,
                        severity="warning",
                        guidance="The action may not have taken effect. Check HA logs.",
                    )
                )

        success = len(warnings) == 0

        return VerificationResult(
            success=success,
            state=status if success else "partial",
            warnings=warnings,
            metadata={
                "task_id": task_id,
                "retryable": any(
                    any(t in w.message.lower() for t in TRANSIENT_ERRORS)
                    for w in warnings
                ),
            },
        )

    def map_warnings(self, state_data: dict[str, Any] | None) -> list[VerificationWarning]:
        warnings: list[VerificationWarning] = []
        if state_data and state_data.get("state") == "unavailable":
            entity_id = state_data.get("entity_id", "unknown")
            warnings.append(
                VerificationWarning(
                    message=f"Entity '{entity_id}' is unavailable after task execution.",
                    entity_id=entity_id,
                    severity="warning",
                    guidance="Check entity availability and HA logs.",
                )
            )
        return warnings
