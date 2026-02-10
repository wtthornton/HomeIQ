"""Tests for UnifiedValidationRouter and related models."""

import pytest
from typing import Any

import sys
from pathlib import Path
_project_root = str(Path(__file__).resolve().parents[3])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from shared.patterns import (
    UnifiedValidationRouter,
    ValidationBackend,
    ValidationRequest,
    ValidationResponse,
    ValidationSubsection,
    categorize_errors,
)


# --- Test fixtures ---

class MockValidationBackend(ValidationBackend):
    name = "mock_backend"

    def __init__(self, result: dict):
        self._result = result

    async def validate(self, content: str, **kwargs) -> dict[str, Any]:
        return self._result


class MockValidationRouter(UnifiedValidationRouter):
    domain = "test"
    error_categories = {
        "entity": ("entity", "Entity", "entity_id"),
        "service": ("service", "Service"),
    }

    def __init__(self, backend_result: dict):
        self._backend_result = backend_result

    async def run_validation(self, request: ValidationRequest, **kwargs) -> ValidationResponse:
        return self.build_response(self._backend_result, request)


# --- categorize_errors Tests ---

class TestCategorizeErrors:
    def test_entity_errors_categorized(self):
        errors = ["Unknown entity light.missing", "Invalid entity_id sensor.bad"]
        result = categorize_errors(errors, {
            "entity": ("entity", "Entity", "entity_id"),
            "service": ("service", "Service"),
        })
        assert len(result["entity"]) == 2
        assert len(result["service"]) == 0
        assert len(result["other"]) == 0

    def test_service_errors_categorized(self):
        errors = ["Invalid service call light.invalid_action"]
        result = categorize_errors(errors, {
            "entity": ("entity",),
            "service": ("service", "Service"),
        })
        assert len(result["service"]) == 1
        assert len(result["entity"]) == 0

    def test_mixed_errors(self):
        errors = [
            "Unknown entity light.missing",
            "Invalid service call",
            "YAML syntax error at line 5",
        ]
        result = categorize_errors(errors, {
            "entity": ("entity",),
            "service": ("service",),
        })
        assert len(result["entity"]) == 1
        assert len(result["service"]) == 1
        assert len(result["other"]) == 1
        assert "YAML syntax error" in result["other"][0]

    def test_empty_errors(self):
        result = categorize_errors([], {"entity": ("entity",), "service": ("service",)})
        assert result == {"entity": [], "service": [], "other": []}


# --- ValidationRequest Tests ---

class TestValidationRequest:
    def test_defaults(self):
        req = ValidationRequest(content="test yaml")
        assert req.normalize is True
        assert req.validate_entities is True
        assert req.validate_services is True

    def test_custom_flags(self):
        req = ValidationRequest(
            content="test",
            normalize=False,
            validate_entities=False,
            validate_services=False,
        )
        assert req.normalize is False


# --- ValidationResponse Tests ---

class TestValidationResponse:
    def test_valid_response(self):
        resp = ValidationResponse(valid=True, score=95.0)
        assert resp.valid is True
        assert resp.errors == []
        assert resp.subsections == {}

    def test_response_with_subsections(self):
        resp = ValidationResponse(
            valid=False,
            errors=["bad entity"],
            subsections={
                "entity_validation": ValidationSubsection(
                    performed=True, passed=False, errors=["bad entity"]
                )
            },
        )
        assert resp.subsections["entity_validation"].passed is False


# --- UnifiedValidationRouter Tests ---

class TestUnifiedValidationRouter:
    @pytest.mark.asyncio
    async def test_valid_result(self):
        router = MockValidationRouter({
            "valid": True,
            "errors": [],
            "warnings": [],
            "score": 95.0,
            "fixed_yaml": None,
            "fixes_applied": [],
        })
        request = ValidationRequest(content="good yaml")
        response = await router.run_validation(request)
        assert response.valid is True
        assert response.score == 95.0
        assert "entity_validation" in response.subsections
        assert response.subsections["entity_validation"].passed is True

    @pytest.mark.asyncio
    async def test_invalid_with_entity_errors(self):
        router = MockValidationRouter({
            "valid": False,
            "errors": ["Unknown entity light.missing", "YAML syntax error"],
            "warnings": ["Consider adding description"],
            "score": 30.0,
        })
        request = ValidationRequest(content="bad yaml")
        response = await router.run_validation(request)
        assert response.valid is False
        assert len(response.errors) == 2
        entity_sub = response.subsections["entity_validation"]
        assert entity_sub.passed is False
        assert len(entity_sub.errors) == 1

    @pytest.mark.asyncio
    async def test_performed_flags_from_request(self):
        router = MockValidationRouter({
            "valid": True,
            "errors": [],
            "warnings": [],
            "score": 100.0,
        })
        request = ValidationRequest(
            content="yaml",
            validate_entities=False,
            validate_services=False,
        )
        response = await router.run_validation(request)
        assert response.subsections["entity_validation"].performed is False
        assert response.subsections["service_validation"].performed is False

    @pytest.mark.asyncio
    async def test_fixed_content_passthrough(self):
        router = MockValidationRouter({
            "valid": True,
            "errors": [],
            "warnings": [],
            "score": 90.0,
            "fixed_yaml": "normalized: yaml",
            "fixes_applied": ["fixed triggers plural"],
        })
        request = ValidationRequest(content="yaml")
        response = await router.run_validation(request)
        assert response.fixed_content == "normalized: yaml"
        assert "fixed triggers plural" in response.fixes_applied


# --- ValidationBackend Tests ---

class TestValidationBackend:
    @pytest.mark.asyncio
    async def test_mock_backend(self):
        backend = MockValidationBackend({"valid": True, "errors": [], "warnings": []})
        result = await backend.validate("test content")
        assert result["valid"] is True
