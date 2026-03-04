"""Tests for Admin API response models."""

from src.models import APIResponse, ErrorResponse


class TestAPIResponse:
    """Tests for APIResponse model."""

    def test_success_response(self) -> None:
        resp = APIResponse(success=True, data={"key": "value"}, message="OK")
        assert resp.success is True
        assert resp.data == {"key": "value"}
        assert resp.message == "OK"
        assert resp.timestamp is not None

    def test_defaults(self) -> None:
        resp = APIResponse(success=True)
        assert resp.data is None
        assert resp.message is None
        assert resp.request_id is None
        assert resp.timestamp is not None

    def test_serialization(self) -> None:
        resp = APIResponse(success=True, message="test")
        dumped = resp.model_dump()
        assert dumped["success"] is True
        assert "timestamp" in dumped


class TestErrorResponse:
    """Tests for ErrorResponse model."""

    def test_error_response(self) -> None:
        resp = ErrorResponse(error="Not found", error_code="HTTP_404")
        assert resp.success is False
        assert resp.error == "Not found"
        assert resp.error_code == "HTTP_404"

    def test_defaults(self) -> None:
        resp = ErrorResponse(error="fail")
        assert resp.success is False
        assert resp.error_code is None
        assert resp.request_id is None
        assert resp.timestamp is not None
