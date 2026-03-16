"""
Validation Retry Loop for YAML Generation

Epic 67: Self-Healing Validation Loop
Stories 67.1-67.4: Integrates automation-linter + yaml-validation-service
into a retry loop around LLM YAML generation.

Flow:
1. Generate YAML via LLM (existing YAMLGenerationService)
2. Validate via automation-linter (POST /lint) + yaml-validation-service
3. If validation fails, feed errors back to LLM and retry (max N attempts)
4. Return first passing result, or best attempt with error context
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from homeiq_resilience import CircuitOpenError

from ..clients.linter_client import LinterClient, LintResult
from ..clients.openai_client import OpenAIClient
from ..clients.yaml_validation_client import YAMLValidationClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error Context Prompt Template (Story 67.3)
# ---------------------------------------------------------------------------

ERROR_FEEDBACK_PROMPT = """The YAML you generated has validation errors. Fix ONLY the errors listed below.
Do NOT change parts that are already valid.

ORIGINAL USER REQUEST:
{original_request}

YOUR PREVIOUS YAML OUTPUT:
```yaml
{failed_yaml}
```

VALIDATION ERRORS (fix these):
{error_details}

INSTRUCTIONS:
- Return ONLY the corrected YAML, no explanations or markdown code blocks
- Fix ONLY the specific errors listed above
- Keep all valid parts unchanged
- Ensure the output is valid Home Assistant automation YAML
"""


@dataclass
class ValidationFinding:
    """Unified finding from linter or validator."""

    source: str  # "linter" or "validator"
    severity: str  # "error", "warning", "info"
    message: str
    rule_id: str | None = None
    path: str | None = None


@dataclass
class RetryAttempt:
    """Record of a single generation attempt."""

    attempt: int
    yaml_content: str
    lint_passed: bool | None = None
    validation_passed: bool | None = None
    findings: list[ValidationFinding] = field(default_factory=list)
    duration_ms: float = 0.0


@dataclass
class ValidationRetryResult:
    """Final result from the validation retry loop."""

    yaml_content: str
    passed: bool
    validated: bool  # False if validation was skipped (services down)
    attempts: int
    total_duration_ms: float
    best_attempt: int
    findings: list[ValidationFinding] = field(default_factory=list)
    attempt_history: list[RetryAttempt] = field(default_factory=list)


class ValidationRetryLoop:
    """Wraps YAML generation with a validate-retry loop.

    Calls automation-linter and yaml-validation-service after each
    LLM generation attempt. On failure, feeds errors back to the LLM.
    """

    def __init__(
        self,
        openai_client: OpenAIClient,
        linter_client: LinterClient | None = None,
        yaml_validation_client: YAMLValidationClient | None = None,
        max_retries: int = 3,
    ):
        self.openai_client = openai_client
        self.linter_client = linter_client
        self.yaml_validation_client = yaml_validation_client
        self.max_retries = max_retries
        # Metrics counters (Story 67.5)
        self._first_pass_count = 0
        self._total_count = 0
        self._retry_counts: list[int] = []

    async def generate_and_validate(
        self,
        yaml_content: str,
        original_request: str,
        entity_context: dict[str, Any] | None = None,
    ) -> ValidationRetryResult:
        """Run the validation retry loop on already-generated YAML.

        Args:
            yaml_content: Initial YAML from the generation service.
            original_request: The original user request (for error feedback prompt).
            entity_context: Entity context for LLM re-generation.

        Returns:
            ValidationRetryResult with the best YAML and validation status.
        """
        start_time = time.monotonic()
        attempts: list[RetryAttempt] = []
        current_yaml = yaml_content
        best_attempt_idx = 0
        best_error_count = float("inf")

        self._total_count += 1

        for attempt_num in range(1, self.max_retries + 1):
            attempt_start = time.monotonic()

            # --- Validate current YAML ---
            lint_result, validation_findings = await self._validate(current_yaml)
            all_findings = self._merge_findings(lint_result, validation_findings)

            error_findings = [f for f in all_findings if f.severity == "error"]
            lint_passed = lint_result.passed if lint_result else None
            validation_passed = len(error_findings) == 0

            attempt = RetryAttempt(
                attempt=attempt_num,
                yaml_content=current_yaml,
                lint_passed=lint_passed,
                validation_passed=validation_passed,
                findings=all_findings,
                duration_ms=(time.monotonic() - attempt_start) * 1000,
            )
            attempts.append(attempt)

            # Track best attempt (fewest errors)
            if len(error_findings) < best_error_count:
                best_error_count = len(error_findings)
                best_attempt_idx = attempt_num - 1

            # --- Check if passed ---
            if validation_passed:
                if attempt_num == 1:
                    self._first_pass_count += 1
                self._retry_counts.append(attempt_num)

                logger.info(
                    "Validation passed on attempt %d/%d (%.0fms)",
                    attempt_num, self.max_retries,
                    (time.monotonic() - start_time) * 1000,
                )
                return ValidationRetryResult(
                    yaml_content=current_yaml,
                    passed=True,
                    validated=True,
                    attempts=attempt_num,
                    total_duration_ms=(time.monotonic() - start_time) * 1000,
                    best_attempt=attempt_num,
                    findings=all_findings,
                    attempt_history=attempts,
                )

            # --- Last attempt — don't retry ---
            if attempt_num >= self.max_retries:
                break

            # --- Build error feedback and retry ---
            logger.info(
                "Validation failed on attempt %d/%d (%d errors). Retrying with error context.",
                attempt_num, self.max_retries, len(error_findings),
            )
            current_yaml = await self._retry_with_error_feedback(
                original_request=original_request,
                failed_yaml=current_yaml,
                findings=error_findings,
                entity_context=entity_context,
            )

        # All retries exhausted — return best attempt
        self._retry_counts.append(self.max_retries)
        best = attempts[best_attempt_idx]

        logger.warning(
            "All %d validation attempts exhausted. Returning best attempt #%d (%d errors).",
            self.max_retries, best_attempt_idx + 1, int(best_error_count),
        )

        return ValidationRetryResult(
            yaml_content=best.yaml_content,
            passed=False,
            validated=True,
            attempts=len(attempts),
            total_duration_ms=(time.monotonic() - start_time) * 1000,
            best_attempt=best_attempt_idx + 1,
            findings=best.findings,
            attempt_history=attempts,
        )

    # ------------------------------------------------------------------
    # Validation (Story 67.1)
    # ------------------------------------------------------------------

    async def _validate(
        self, yaml_content: str
    ) -> tuple[LintResult | None, list[ValidationFinding]]:
        """Run both linter and validator. Graceful degradation if either is down."""
        lint_result = await self._run_linter(yaml_content)
        validation_findings = await self._run_validator(yaml_content)
        return lint_result, validation_findings

    async def _run_linter(self, yaml_content: str) -> LintResult | None:
        """Call automation-linter. Returns None if unavailable (Story 67.4)."""
        if not self.linter_client:
            return None
        try:
            return await self.linter_client.lint(yaml_content)
        except CircuitOpenError:
            logger.warning("AI FALLBACK: automation-linter circuit open — skipping lint")
            return None
        except Exception as e:
            logger.warning("AI FALLBACK: automation-linter unavailable: %s", e)
            return None

    async def _run_validator(self, yaml_content: str) -> list[ValidationFinding]:
        """Call yaml-validation-service. Returns empty list if unavailable (Story 67.4)."""
        if not self.yaml_validation_client:
            return []
        try:
            result = await self.yaml_validation_client.validate_yaml(
                yaml_content=yaml_content,
                normalize=False,
                validate_entities=True,
            )
            findings = []
            for error_msg in result.get("errors", []):
                findings.append(ValidationFinding(
                    source="validator",
                    severity="error",
                    message=error_msg,
                ))
            for warning_msg in result.get("warnings", []):
                findings.append(ValidationFinding(
                    source="validator",
                    severity="warning",
                    message=warning_msg,
                ))
            return findings
        except Exception as e:
            logger.warning("AI FALLBACK: yaml-validation-service unavailable: %s", e)
            return []

    # ------------------------------------------------------------------
    # Error Feedback (Story 67.3)
    # ------------------------------------------------------------------

    async def _retry_with_error_feedback(
        self,
        original_request: str,
        failed_yaml: str,
        findings: list[ValidationFinding],
        entity_context: dict[str, Any] | None = None,
    ) -> str:
        """Ask the LLM to fix validation errors."""
        error_details = self._format_error_details(findings)

        prompt = ERROR_FEEDBACK_PROMPT.format(
            original_request=original_request,
            failed_yaml=failed_yaml,
            error_details=error_details,
        )

        try:
            corrected = await self.openai_client.generate_yaml(
                prompt=prompt,
                entity_context=entity_context,
                temperature=0.05,  # Very low temp for corrections
                max_tokens=2000,
            )
            return corrected.strip()
        except Exception as e:
            logger.error("LLM retry failed: %s. Returning original YAML.", e)
            return failed_yaml

    @staticmethod
    def _format_error_details(findings: list[ValidationFinding]) -> str:
        """Format findings into a structured error list for the LLM."""
        lines = []
        for i, f in enumerate(findings, 1):
            parts = [f"  {i}. [{f.source}]"]
            if f.rule_id:
                parts.append(f"Rule {f.rule_id}:")
            parts.append(f.message)
            if f.path:
                parts.append(f"(at {f.path})")
            lines.append(" ".join(parts))
        return "\n".join(lines) if lines else "No specific errors available."

    # ------------------------------------------------------------------
    # Merge findings
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_findings(
        lint_result: LintResult | None,
        validation_findings: list[ValidationFinding],
    ) -> list[ValidationFinding]:
        """Merge linter and validator findings into a unified list."""
        merged: list[ValidationFinding] = []
        if lint_result:
            for f in lint_result.findings:
                merged.append(ValidationFinding(
                    source="linter",
                    severity=f.severity,
                    message=f.message,
                    rule_id=f.rule_id,
                    path=f.path,
                ))
        merged.extend(validation_findings)
        return merged

    # ------------------------------------------------------------------
    # Metrics (Story 67.5)
    # ------------------------------------------------------------------

    @property
    def first_pass_rate(self) -> float:
        """Percentage of generations that passed on first attempt."""
        if self._total_count == 0:
            return 0.0
        return (self._first_pass_count / self._total_count) * 100.0

    @property
    def average_retries(self) -> float:
        """Average number of retries needed."""
        if not self._retry_counts:
            return 0.0
        return sum(self._retry_counts) / len(self._retry_counts)

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics for observability."""
        return {
            "total_generations": self._total_count,
            "first_pass_count": self._first_pass_count,
            "first_pass_rate": round(self.first_pass_rate, 1),
            "average_retries": round(self.average_retries, 2),
            "max_retries_configured": self.max_retries,
        }

    def reset_metrics(self) -> None:
        """Reset metrics counters."""
        self._first_pass_count = 0
        self._total_count = 0
        self._retry_counts = []
