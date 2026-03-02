"""
Tests for synergy_router.py — SynergyFeedback model
"""

from src.api.synergy_router import AutomationExecutionResult, SynergyFeedback


class TestSynergyFeedback:
    """Test SynergyFeedback Pydantic model."""

    def test_init_accepted(self):
        """Test creating accepted feedback."""
        fb = SynergyFeedback(accepted=True, feedback_text="Great suggestion", rating=5)
        assert fb.accepted is True
        assert fb.feedback_text == "Great suggestion"
        assert fb.rating == 5

    def test_init_rejected(self):
        """Test creating rejected feedback."""
        fb = SynergyFeedback(accepted=False, feedback_text="Not relevant")
        assert fb.accepted is False
        assert fb.feedback_text == "Not relevant"

    def test_defaults_none(self):
        """Test optional fields default to None."""
        fb = SynergyFeedback(accepted=True)
        assert fb.feedback_text is None
        assert fb.rating is None


class TestAutomationExecutionResult:
    """Test AutomationExecutionResult Pydantic model."""

    def test_success_result(self):
        """Test successful execution result."""
        result = AutomationExecutionResult(
            success=True, execution_time_ms=150, triggered_count=3
        )
        assert result.success is True
        assert result.error is None
        assert result.execution_time_ms == 150
        assert result.triggered_count == 3

    def test_failure_result(self):
        """Test failed execution result."""
        result = AutomationExecutionResult(success=False, error="Timeout")
        assert result.success is False
        assert result.error == "Timeout"

    def test_defaults(self):
        """Test default values."""
        result = AutomationExecutionResult(success=True)
        assert result.error is None
        assert result.execution_time_ms == 0
        assert result.triggered_count == 0
