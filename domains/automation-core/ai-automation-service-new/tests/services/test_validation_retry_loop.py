"""
Tests for Validation Retry Loop

Epic 67, Story 67.6: Integration tests for the validation retry loop.
Tests cover: pass-on-first-try, pass-on-second-try, all-retries-exhausted,
and graceful degradation when linter/validator are down.
"""

import pytest

from src.clients.linter_client import LintFinding, LintResult
from src.services.validation_retry_loop import (
    ValidationRetryLoop,
    ValidationRetryResult,
)


# ---------------------------------------------------------------------------
# Mocks
# ---------------------------------------------------------------------------


class MockOpenAIClient:
    """Mock OpenAI client that returns pre-configured YAML responses."""

    def __init__(self, responses: list[str] | None = None):
        self.responses = responses or []
        self._call_count = 0

    async def generate_yaml(self, prompt: str, **kwargs) -> str:
        if self._call_count < len(self.responses):
            result = self.responses[self._call_count]
            self._call_count += 1
            return result
        return "# no more responses"


class MockLinterClient:
    """Mock linter client that returns pre-configured results."""

    def __init__(self, results: list[LintResult] | None = None, raise_on_call: bool = False):
        self.results = results or []
        self._call_count = 0
        self._raise_on_call = raise_on_call

    async def lint(self, yaml_content: str) -> LintResult:
        if self._raise_on_call:
            raise ConnectionError("Linter unavailable")
        if self._call_count < len(self.results):
            result = self.results[self._call_count]
            self._call_count += 1
            return result
        return LintResult(passed=True)


class MockValidationClient:
    """Mock YAML validation client."""

    def __init__(self, results: list[dict] | None = None, raise_on_call: bool = False):
        self.results = results or []
        self._call_count = 0
        self._raise_on_call = raise_on_call

    async def validate_yaml(self, yaml_content: str, **kwargs) -> dict:
        if self._raise_on_call:
            raise ConnectionError("Validator unavailable")
        if self._call_count < len(self.results):
            result = self.results[self._call_count]
            self._call_count += 1
            return result
        return {"valid": True, "errors": [], "warnings": []}


# ---------------------------------------------------------------------------
# Test: Pass on first try (no retry overhead)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pass_on_first_try():
    """YAML passes validation on first attempt — no retries needed."""
    loop = ValidationRetryLoop(
        openai_client=MockOpenAIClient(),
        linter_client=MockLinterClient(results=[
            LintResult(passed=True, findings=[], error_count=0),
        ]),
        yaml_validation_client=MockValidationClient(results=[
            {"valid": True, "errors": [], "warnings": []},
        ]),
        max_retries=3,
    )

    result = await loop.generate_and_validate(
        yaml_content="alias: Test\ntrigger:\n  - platform: state\naction:\n  - service: light.turn_on\n",
        original_request="Turn on the lights when motion detected",
    )

    assert result.passed is True
    assert result.validated is True
    assert result.attempts == 1
    assert len(result.attempt_history) == 1
    assert loop.first_pass_rate == 100.0


# ---------------------------------------------------------------------------
# Test: Pass on second try (error feedback works)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pass_on_second_try():
    """YAML fails first validation, LLM corrects errors on second attempt."""
    corrected_yaml = "alias: Test Fixed\ntrigger:\n  - platform: state\naction:\n  - service: light.turn_on\n"

    loop = ValidationRetryLoop(
        openai_client=MockOpenAIClient(responses=[corrected_yaml]),
        linter_client=MockLinterClient(results=[
            # First attempt: fails with error
            LintResult(
                passed=False,
                findings=[LintFinding(rule_id="R001", severity="error", message="Missing trigger platform")],
                error_count=1,
            ),
            # Second attempt: passes
            LintResult(passed=True, findings=[], error_count=0),
        ]),
        yaml_validation_client=MockValidationClient(results=[
            {"valid": True, "errors": [], "warnings": []},
            {"valid": True, "errors": [], "warnings": []},
        ]),
        max_retries=3,
    )

    result = await loop.generate_and_validate(
        yaml_content="alias: Test\ntrigger:\n  - bad: data\n",
        original_request="Turn on lights",
    )

    assert result.passed is True
    assert result.attempts == 2
    assert result.yaml_content == corrected_yaml


# ---------------------------------------------------------------------------
# Test: All retries exhausted (returns best attempt)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_retries_exhausted():
    """All retry attempts fail — returns the best attempt with error context."""
    loop = ValidationRetryLoop(
        openai_client=MockOpenAIClient(responses=[
            "# still broken 1",
            "# still broken 2",
        ]),
        linter_client=MockLinterClient(results=[
            LintResult(
                passed=False,
                findings=[
                    LintFinding(rule_id="R001", severity="error", message="Error 1"),
                    LintFinding(rule_id="R002", severity="error", message="Error 2"),
                ],
                error_count=2,
            ),
            LintResult(
                passed=False,
                findings=[LintFinding(rule_id="R001", severity="error", message="Error 1")],
                error_count=1,
            ),
            LintResult(
                passed=False,
                findings=[LintFinding(rule_id="R001", severity="error", message="Error 1")],
                error_count=1,
            ),
        ]),
        yaml_validation_client=MockValidationClient(results=[
            {"valid": False, "errors": [], "warnings": []},
            {"valid": False, "errors": [], "warnings": []},
            {"valid": False, "errors": [], "warnings": []},
        ]),
        max_retries=3,
    )

    result = await loop.generate_and_validate(
        yaml_content="# broken yaml",
        original_request="Create automation",
    )

    assert result.passed is False
    assert result.validated is True
    assert result.attempts == 3
    # Best attempt should be attempt 2 or 3 (fewer errors)
    assert result.best_attempt >= 2


# ---------------------------------------------------------------------------
# Test: Linter down — graceful degradation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_linter_down_graceful_degradation():
    """When automation-linter is unreachable, skip lint and return raw YAML with validated=True."""
    loop = ValidationRetryLoop(
        openai_client=MockOpenAIClient(),
        linter_client=MockLinterClient(raise_on_call=True),
        yaml_validation_client=MockValidationClient(results=[
            {"valid": True, "errors": [], "warnings": []},
        ]),
        max_retries=3,
    )

    result = await loop.generate_and_validate(
        yaml_content="alias: Test\ntrigger:\n  - platform: state\naction:\n  - service: light.turn_on\n",
        original_request="Turn on lights",
    )

    # Should pass since validator says OK (linter was skipped)
    assert result.passed is True
    assert result.validated is True
    assert result.attempts == 1


# ---------------------------------------------------------------------------
# Test: Validator down — graceful degradation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validator_down_graceful_degradation():
    """When yaml-validation-service is unreachable, use only linter results."""
    loop = ValidationRetryLoop(
        openai_client=MockOpenAIClient(),
        linter_client=MockLinterClient(results=[
            LintResult(passed=True, findings=[], error_count=0),
        ]),
        yaml_validation_client=MockValidationClient(raise_on_call=True),
        max_retries=3,
    )

    result = await loop.generate_and_validate(
        yaml_content="alias: Test\ntrigger:\n  - platform: state\naction:\n  - service: light.turn_on\n",
        original_request="Turn on lights",
    )

    assert result.passed is True
    assert result.attempts == 1


# ---------------------------------------------------------------------------
# Test: Both validators down — pass-through
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_both_validators_down():
    """When both validation services are down, YAML passes through."""
    loop = ValidationRetryLoop(
        openai_client=MockOpenAIClient(),
        linter_client=MockLinterClient(raise_on_call=True),
        yaml_validation_client=MockValidationClient(raise_on_call=True),
        max_retries=3,
    )

    result = await loop.generate_and_validate(
        yaml_content="alias: Test\ntrigger:\n  - platform: state\naction:\n  - service: light.turn_on\n",
        original_request="Turn on lights",
    )

    # No validators available = no errors found = passes
    assert result.passed is True
    assert result.attempts == 1


# ---------------------------------------------------------------------------
# Test: No validation clients configured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_validation_clients():
    """When no linter or validator is configured, YAML passes through."""
    loop = ValidationRetryLoop(
        openai_client=MockOpenAIClient(),
        linter_client=None,
        yaml_validation_client=None,
        max_retries=3,
    )

    result = await loop.generate_and_validate(
        yaml_content="alias: Test\ntrigger:\n  - platform: state\naction:\n  - service: light.turn_on\n",
        original_request="Turn on lights",
    )

    assert result.passed is True
    assert result.validated is True
    assert result.attempts == 1


# ---------------------------------------------------------------------------
# Test: Metrics tracking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_tracking():
    """Verify metrics are correctly tracked across multiple generations."""
    loop = ValidationRetryLoop(
        openai_client=MockOpenAIClient(),
        linter_client=MockLinterClient(results=[
            LintResult(passed=True),
            LintResult(passed=True),
        ]),
        yaml_validation_client=None,
        max_retries=3,
    )

    # First generation: pass on first try
    await loop.generate_and_validate(
        yaml_content="alias: Test1\ntrigger:\n  - platform: state\naction:\n  - service: light.turn_on\n",
        original_request="Test 1",
    )

    # Second generation: also pass on first try
    await loop.generate_and_validate(
        yaml_content="alias: Test2\ntrigger:\n  - platform: state\naction:\n  - service: light.turn_on\n",
        original_request="Test 2",
    )

    metrics = loop.get_metrics()
    assert metrics["total_generations"] == 2
    assert metrics["first_pass_count"] == 2
    assert metrics["first_pass_rate"] == 100.0
    assert metrics["average_retries"] == 1.0


# ---------------------------------------------------------------------------
# Test: Error context prompt format
# ---------------------------------------------------------------------------


def test_error_details_formatting():
    """Verify error details are formatted correctly for LLM feedback."""
    from src.services.validation_retry_loop import ValidationFinding, ValidationRetryLoop

    findings = [
        ValidationFinding(source="linter", severity="error", message="Missing trigger", rule_id="R001", path="trigger[0]"),
        ValidationFinding(source="validator", severity="error", message="Invalid entity_id: light.fake"),
    ]

    formatted = ValidationRetryLoop._format_error_details(findings)
    assert "1. [linter] Rule R001:" in formatted
    assert "Missing trigger" in formatted
    assert "(at trigger[0])" in formatted
    assert "2. [validator]" in formatted
    assert "light.fake" in formatted
