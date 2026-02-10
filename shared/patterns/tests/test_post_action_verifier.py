"""Tests for PostActionVerifier and related models."""

import pytest
from typing import Any

import sys
from pathlib import Path
_project_root = str(Path(__file__).resolve().parents[3])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from shared.patterns import PostActionVerifier, VerificationResult, VerificationWarning


# --- Test fixtures ---

class MockDeployVerifier(PostActionVerifier):
    """Mock verifier that checks state from a provided dict."""

    def __init__(self, state_data: dict[str, Any] | None):
        self._state_data = state_data

    async def verify(self, action_result: dict[str, Any]) -> VerificationResult:
        if not self._state_data:
            return VerificationResult(success=True, state=None)

        warnings = self.map_warnings(self._state_data)
        state = self._state_data.get("state")
        return VerificationResult(
            success=state != "unavailable",
            state=state,
            warnings=warnings,
            metadata={"entity_id": self._state_data.get("entity_id", "unknown")},
        )


# --- VerificationResult Tests ---

class TestVerificationResult:
    def test_success_no_warnings(self):
        result = VerificationResult(success=True, state="on")
        assert result.success is True
        assert result.has_warnings is False
        assert result.verification_warning is None

    def test_with_warnings(self):
        result = VerificationResult(
            success=False,
            state="unavailable",
            warnings=[
                VerificationWarning(
                    message="Entity unavailable",
                    entity_id="automation.test",
                    severity="warning",
                )
            ],
        )
        assert result.success is False
        assert result.has_warnings is True
        assert result.verification_warning == "Entity unavailable"

    def test_metadata(self):
        result = VerificationResult(
            success=True,
            state="on",
            metadata={"entity_id": "automation.test", "version": 2},
        )
        assert result.metadata["entity_id"] == "automation.test"


# --- VerificationWarning Tests ---

class TestVerificationWarning:
    def test_defaults(self):
        warning = VerificationWarning(message="Something went wrong")
        assert warning.severity == "warning"
        assert warning.entity_id is None
        assert warning.guidance is None

    def test_full_warning(self):
        warning = VerificationWarning(
            message="State unavailable",
            entity_id="automation.test",
            severity="error",
            guidance="Check HA logs",
        )
        assert warning.entity_id == "automation.test"
        assert warning.guidance == "Check HA logs"


# --- PostActionVerifier Tests ---

class TestPostActionVerifier:
    @pytest.mark.asyncio
    async def test_verify_success(self):
        verifier = MockDeployVerifier({"state": "on", "entity_id": "automation.test"})
        result = await verifier.verify({"automation_id": "test"})
        assert result.success is True
        assert result.state == "on"
        assert result.has_warnings is False

    @pytest.mark.asyncio
    async def test_verify_unavailable(self):
        verifier = MockDeployVerifier({
            "state": "unavailable",
            "entity_id": "automation.test",
        })
        result = await verifier.verify({"automation_id": "test"})
        assert result.success is False
        assert result.state == "unavailable"
        assert result.has_warnings is True
        assert "unavailable" in result.verification_warning

    @pytest.mark.asyncio
    async def test_verify_no_state(self):
        verifier = MockDeployVerifier(None)
        result = await verifier.verify({"automation_id": "test"})
        assert result.success is True
        assert result.state is None

    def test_map_warnings_unavailable(self):
        verifier = MockDeployVerifier(None)
        warnings = verifier.map_warnings({
            "state": "unavailable",
            "entity_id": "automation.broken",
        })
        assert len(warnings) == 1
        assert "unavailable" in warnings[0].message
        assert warnings[0].entity_id == "automation.broken"

    def test_map_warnings_ok(self):
        verifier = MockDeployVerifier(None)
        warnings = verifier.map_warnings({"state": "on", "entity_id": "automation.ok"})
        assert len(warnings) == 0

    def test_map_warnings_none(self):
        verifier = MockDeployVerifier(None)
        warnings = verifier.map_warnings(None)
        assert len(warnings) == 0
