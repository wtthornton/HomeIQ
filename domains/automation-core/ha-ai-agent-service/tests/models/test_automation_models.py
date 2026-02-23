"""
Tests for automation_models.py
"""

from src.models.automation_models import (
    AutomationPreview,
    AutomationPreviewRequest,
    AutomationPreviewResponse,
    ValidationResult,
)


class TestValidationResult:
    """Test ValidationResult class."""

    def test_to_dict(self):
        """Test to_dict method."""
        result = ValidationResult(
            valid=True,
            errors=["error1"],
            warnings=["warning1"],
            score=85.0,
        )
        data = result.to_dict()
        assert data["valid"] is True
        assert data["errors"] == ["error1"]
        assert data["warnings"] == ["warning1"]
        assert data["score"] == 85.0

    def test_to_dict_with_fixed_yaml(self):
        """Test to_dict with fixed_yaml."""
        result = ValidationResult(
            valid=True,
            fixed_yaml="fixed: yaml",
            fixes_applied=["fix1"],
        )
        data = result.to_dict()
        assert "fixed_yaml" in data
        assert "fixes_applied" in data


class TestAutomationPreview:
    """Test AutomationPreview class."""

    def test_to_dict(self):
        """Test to_dict method."""
        preview = AutomationPreview(
            alias="Test Automation",
            trigger_description="Time trigger",
            action_description="Turn on light",
        )
        data = preview.to_dict()
        assert data["alias"] == "Test Automation"
        assert data["trigger_description"] == "Time trigger"
        assert data["action_description"] == "Turn on light"
        assert data["mode"] == "single"


class TestAutomationPreviewRequest:
    """Test AutomationPreviewRequest class."""

    def test_from_dict(self):
        """Test from_dict method."""
        data = {
            "user_prompt": "Turn on lights",
            "automation_yaml": "alias: test",
            "alias": "Test",
        }
        request = AutomationPreviewRequest.from_dict(data)
        assert request.user_prompt == "Turn on lights"
        assert request.automation_yaml == "alias: test"
        assert request.alias == "Test"

    def test_validate_success(self):
        """Test validate with valid data."""
        request = AutomationPreviewRequest(
            user_prompt="Turn on lights",
            automation_yaml="alias: test",
            alias="Test",
        )
        is_valid, error = request.validate()
        assert is_valid is True
        assert error is None

    def test_validate_empty_user_prompt(self):
        """Test validate with empty user_prompt."""
        request = AutomationPreviewRequest(
            user_prompt="",
            automation_yaml="alias: test",
            alias="Test",
        )
        is_valid, error = request.validate()
        assert is_valid is False
        assert "user_prompt" in error

    def test_validate_short_user_prompt(self):
        """Test validate with short user_prompt."""
        request = AutomationPreviewRequest(
            user_prompt="ab",
            automation_yaml="alias: test",
            alias="Test",
        )
        is_valid, error = request.validate()
        assert is_valid is False
        assert "at least 3 characters" in error

    def test_validate_long_alias(self):
        """Test validate with long alias."""
        request = AutomationPreviewRequest(
            user_prompt="Turn on lights",
            automation_yaml="alias: test",
            alias="a" * 101,
        )
        is_valid, error = request.validate()
        assert is_valid is False
        assert "100 characters" in error


class TestAutomationPreviewResponse:
    """Test AutomationPreviewResponse class."""

    def test_to_dict_success(self):
        """Test to_dict with success response."""
        preview = AutomationPreview(alias="Test")
        validation = ValidationResult(valid=True)
        response = AutomationPreviewResponse(
            success=True,
            preview=preview,
            validation=validation,
            entities_affected=["light.1"],
            message="Success",
        )
        data = response.to_dict()
        assert data["success"] is True
        assert data["preview"] is True
        assert data["entities_affected"] == ["light.1"]
        assert data["message"] == "Success"

    def test_error_response(self):
        """Test error_response class method."""
        response = AutomationPreviewResponse.error_response(
            error="Test error",
            user_prompt="test",
            alias="Test",
        )
        assert response.success is False
        assert response.error == "Test error"
        assert response.user_prompt == "test"
        assert response.alias == "Test"
