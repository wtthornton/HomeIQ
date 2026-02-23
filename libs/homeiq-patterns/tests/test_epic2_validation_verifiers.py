"""
Tests for Epic 2: High-Value Domain Extensions — Validation Routers & Verifiers

Tests for BlueprintValidationRouter, SetupValidationRouter,
BlueprintDeployVerifier, and SetupVerifier.
"""

import pytest
from pathlib import Path
import sys
from unittest.mock import AsyncMock

_project_root = str(Path(__file__).resolve().parents[3])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from shared.patterns import (
    UnifiedValidationRouter,
    ValidationRequest,
    ValidationResponse,
    PostActionVerifier,
    VerificationResult,
    VerificationWarning,
)


# ================================================================== #
# Blueprint Validation Router Tests (inline implementation)
# ================================================================== #

class _BlueprintValidationRouter(UnifiedValidationRouter):
    """Test-friendly inline version of BlueprintValidationRouter."""

    domain = "blueprint"
    error_categories = {
        "entity": ("entity", "Entity", "entity_id"),
        "service": ("service", "Service"),
        "device": ("device", "Device", "device_class"),
    }

    async def run_validation(self, request, **kwargs):
        import yaml as yaml_lib

        errors = []
        warnings = []

        try:
            data = yaml_lib.safe_load(request.content)
        except yaml_lib.YAMLError as e:
            return ValidationResponse(valid=False, errors=[f"Invalid YAML: {e}"])

        if not isinstance(data, dict):
            return ValidationResponse(valid=False, errors=["Must be a mapping"])

        bp = data.get("blueprint")
        if not bp:
            errors.append("Missing 'blueprint' section")
        else:
            if not bp.get("name"):
                errors.append("Blueprint missing required 'name' field")
            if not bp.get("domain"):
                errors.append("Blueprint missing required 'domain' field")

        score = max(0.0, 100.0 - len(errors) * 15 - len(warnings) * 5)
        return self.build_response(
            {"valid": len(errors) == 0, "errors": errors, "warnings": warnings, "score": score},
            request,
        )


class TestBlueprintValidationRouter:
    @pytest.mark.asyncio
    async def test_valid_blueprint(self):
        router = _BlueprintValidationRouter()
        req = ValidationRequest(
            content="blueprint:\n  name: Test\n  domain: automation\n  input: {}\n",
        )
        resp = await router.run_validation(req)
        assert resp.valid is True
        assert len(resp.errors) == 0

    @pytest.mark.asyncio
    async def test_missing_blueprint_section(self):
        router = _BlueprintValidationRouter()
        req = ValidationRequest(content="alias: test\n")
        resp = await router.run_validation(req)
        assert resp.valid is False
        assert any("Missing 'blueprint'" in e for e in resp.errors)

    @pytest.mark.asyncio
    async def test_missing_name(self):
        router = _BlueprintValidationRouter()
        req = ValidationRequest(content="blueprint:\n  domain: automation\n")
        resp = await router.run_validation(req)
        assert resp.valid is False
        assert any("name" in e for e in resp.errors)

    @pytest.mark.asyncio
    async def test_missing_domain(self):
        router = _BlueprintValidationRouter()
        req = ValidationRequest(content="blueprint:\n  name: Test\n")
        resp = await router.run_validation(req)
        assert resp.valid is False
        assert any("domain" in e for e in resp.errors)

    @pytest.mark.asyncio
    async def test_invalid_yaml(self):
        router = _BlueprintValidationRouter()
        req = ValidationRequest(content="{{invalid yaml")
        resp = await router.run_validation(req)
        assert resp.valid is False

    @pytest.mark.asyncio
    async def test_score_decreases_with_errors(self):
        router = _BlueprintValidationRouter()
        req_valid = ValidationRequest(
            content="blueprint:\n  name: Test\n  domain: automation\n"
        )
        req_invalid = ValidationRequest(content="alias: test\n")
        resp_valid = await router.run_validation(req_valid)
        resp_invalid = await router.run_validation(req_invalid)
        assert resp_valid.score > resp_invalid.score

    @pytest.mark.asyncio
    async def test_error_categorization(self):
        router = _BlueprintValidationRouter()
        resp = router.build_response(
            {
                "valid": False,
                "errors": [
                    "Entity not found: light.missing",
                    "Invalid service: bad.service",
                    "Device class mismatch",
                ],
                "warnings": [],
                "score": 50.0,
            }
        )
        assert "entity_validation" in resp.subsections
        assert "service_validation" in resp.subsections
        assert "device_validation" in resp.subsections
        assert not resp.subsections["entity_validation"].passed


# ================================================================== #
# Setup Validation Router Tests (inline implementation)
# ================================================================== #

class _SetupValidationRouter(UnifiedValidationRouter):
    """Test-friendly inline version of SetupValidationRouter."""

    domain = "setup"
    error_categories = {
        "entity": ("entity", "Entity"),
        "connectivity": ("connect", "unreachable", "timeout"),
        "health": ("health", "Health", "unhealthy"),
    }

    async def run_validation(self, request, **kwargs):
        import yaml as yaml_lib

        errors = []
        warnings = []
        integration_type = kwargs.get("integration_type", "")
        step = kwargs.get("step", "config")

        if step in ("config", "all") and request.content.strip():
            try:
                data = yaml_lib.safe_load(request.content)
                if not isinstance(data, dict):
                    errors.append("Configuration must be a YAML mapping")
                elif integration_type == "mqtt":
                    if "host" not in data:
                        errors.append("Missing required field 'host' for mqtt")
                    if "port" not in data:
                        errors.append("Missing required field 'port' for mqtt")
            except yaml_lib.YAMLError as e:
                errors.append(f"Invalid YAML: {e}")

        score = max(0.0, 100.0 - len(errors) * 20 - len(warnings) * 5)
        return self.build_response(
            {"valid": len(errors) == 0, "errors": errors, "warnings": warnings, "score": score},
            request,
        )


class TestSetupValidationRouter:
    @pytest.mark.asyncio
    async def test_valid_mqtt_config(self):
        router = _SetupValidationRouter()
        req = ValidationRequest(content="host: localhost\nport: 1883\n")
        resp = await router.run_validation(req, integration_type="mqtt", step="config")
        assert resp.valid is True

    @pytest.mark.asyncio
    async def test_missing_mqtt_host(self):
        router = _SetupValidationRouter()
        req = ValidationRequest(content="port: 1883\n")
        resp = await router.run_validation(req, integration_type="mqtt", step="config")
        assert resp.valid is False
        assert any("host" in e for e in resp.errors)

    @pytest.mark.asyncio
    async def test_invalid_yaml(self):
        router = _SetupValidationRouter()
        req = ValidationRequest(content="{{bad yaml")
        resp = await router.run_validation(req, integration_type="mqtt", step="config")
        assert resp.valid is False

    @pytest.mark.asyncio
    async def test_empty_content_skips_config_check(self):
        router = _SetupValidationRouter()
        req = ValidationRequest(content="")
        resp = await router.run_validation(req, integration_type="mqtt", step="config")
        assert resp.valid is True

    @pytest.mark.asyncio
    async def test_error_categorization(self):
        router = _SetupValidationRouter()
        resp = router.build_response(
            {
                "valid": False,
                "errors": [
                    "Entity not found",
                    "Connection timeout",
                    "Health check failed: unhealthy",
                ],
                "warnings": [],
                "score": 40.0,
            }
        )
        assert not resp.subsections["entity_validation"].passed
        assert not resp.subsections["connectivity_validation"].passed
        assert not resp.subsections["health_validation"].passed


# ================================================================== #
# Blueprint Deploy Verifier Tests
# ================================================================== #

class _BlueprintDeployVerifier(PostActionVerifier):
    """Test-friendly inline BlueprintDeployVerifier."""

    def __init__(self, get_state_fn):
        self._get_state = get_state_fn

    async def verify(self, action_result):
        automation_ids = action_result.get("automation_ids", [])
        if not automation_ids:
            single = action_result.get("automation_id")
            if single:
                automation_ids = [single]
        if not automation_ids:
            return VerificationResult(success=True, state="unknown")

        all_warnings = []
        any_unavailable = False

        for aid in automation_ids:
            eid = aid if aid.startswith("automation.") else f"automation.{aid}"
            state_data = await self._get_state(eid)
            if state_data and state_data.get("state") == "unavailable":
                any_unavailable = True
                all_warnings.extend(self.map_warnings(state_data))

        return VerificationResult(
            success=not any_unavailable,
            state="partial" if any_unavailable else "on",
            warnings=all_warnings,
        )


class TestBlueprintDeployVerifier:
    @pytest.mark.asyncio
    async def test_all_automations_healthy(self):
        get_state = AsyncMock(
            return_value={"state": "on", "entity_id": "automation.test", "attributes": {}}
        )
        verifier = _BlueprintDeployVerifier(get_state)
        result = await verifier.verify({
            "automation_ids": ["automation.test1", "automation.test2"],
        })
        assert result.success is True
        assert result.state == "on"
        assert not result.has_warnings

    @pytest.mark.asyncio
    async def test_one_unavailable(self):
        async def mock_state(eid):
            if eid == "automation.test2":
                return {"state": "unavailable", "entity_id": eid, "attributes": {}}
            return {"state": "on", "entity_id": eid, "attributes": {}}

        verifier = _BlueprintDeployVerifier(mock_state)
        result = await verifier.verify({
            "automation_ids": ["automation.test1", "automation.test2"],
        })
        assert result.success is False
        assert result.state == "partial"
        assert result.has_warnings
        assert "test2" in result.verification_warning

    @pytest.mark.asyncio
    async def test_single_automation_id(self):
        get_state = AsyncMock(
            return_value={"state": "on", "entity_id": "automation.single", "attributes": {}}
        )
        verifier = _BlueprintDeployVerifier(get_state)
        result = await verifier.verify({"automation_id": "single"})
        assert result.success is True
        get_state.assert_called_once_with("automation.single")

    @pytest.mark.asyncio
    async def test_no_automation_ids(self):
        get_state = AsyncMock()
        verifier = _BlueprintDeployVerifier(get_state)
        result = await verifier.verify({"status": "deployed"})
        assert result.success is True
        assert result.state == "unknown"

    @pytest.mark.asyncio
    async def test_state_not_found(self):
        get_state = AsyncMock(return_value=None)
        verifier = _BlueprintDeployVerifier(get_state)
        result = await verifier.verify({"automation_ids": ["automation.missing"]})
        assert result.success is True  # Not found != unavailable


# ================================================================== #
# Setup Verifier Tests
# ================================================================== #

class _SetupVerifier(PostActionVerifier):
    """Test-friendly inline SetupVerifier."""

    def __init__(self, get_state_fn):
        self._get_state = get_state_fn

    async def verify(self, action_result):
        entity_ids = action_result.get("entity_ids", [])
        integration = action_result.get("integration", "unknown")

        if not entity_ids:
            return VerificationResult(success=True, state="unknown")

        all_warnings = []
        unavailable_count = 0

        for eid in entity_ids:
            state_data = await self._get_state(eid)
            if state_data is None:
                unavailable_count += 1
                all_warnings.append(
                    VerificationWarning(
                        message=f"Entity '{eid}' not created after {integration} setup.",
                        entity_id=eid,
                        severity="warning",
                    )
                )
            elif state_data.get("state") == "unavailable":
                unavailable_count += 1
                all_warnings.extend(self.map_warnings(state_data))

        return VerificationResult(
            success=unavailable_count == 0,
            state="healthy" if unavailable_count == 0 else "degraded",
            warnings=all_warnings,
        )


class TestSetupVerifier:
    @pytest.mark.asyncio
    async def test_all_entities_healthy(self):
        get_state = AsyncMock(return_value={"state": "on", "entity_id": "light.test"})
        verifier = _SetupVerifier(get_state)
        result = await verifier.verify({
            "entity_ids": ["light.test1", "light.test2"],
            "integration": "hue",
        })
        assert result.success is True
        assert result.state == "healthy"
        assert not result.has_warnings

    @pytest.mark.asyncio
    async def test_entity_not_found(self):
        get_state = AsyncMock(return_value=None)
        verifier = _SetupVerifier(get_state)
        result = await verifier.verify({
            "entity_ids": ["binary_sensor.missing"],
            "integration": "zigbee2mqtt",
        })
        assert result.success is False
        assert result.state == "degraded"
        assert result.has_warnings
        assert "not created" in result.verification_warning

    @pytest.mark.asyncio
    async def test_entity_unavailable(self):
        get_state = AsyncMock(
            return_value={"state": "unavailable", "entity_id": "sensor.offline"}
        )
        verifier = _SetupVerifier(get_state)
        result = await verifier.verify({
            "entity_ids": ["sensor.offline"],
            "integration": "zwave",
        })
        assert result.success is False
        assert result.state == "degraded"

    @pytest.mark.asyncio
    async def test_no_entity_ids(self):
        get_state = AsyncMock()
        verifier = _SetupVerifier(get_state)
        result = await verifier.verify({"integration": "mqtt"})
        assert result.success is True
        assert result.state == "unknown"

    @pytest.mark.asyncio
    async def test_mixed_healthy_and_unavailable(self):
        async def mock_state(eid):
            if eid == "sensor.bad":
                return {"state": "unavailable", "entity_id": eid}
            return {"state": "on", "entity_id": eid}

        verifier = _SetupVerifier(mock_state)
        result = await verifier.verify({
            "entity_ids": ["light.good", "sensor.bad"],
            "integration": "zigbee",
        })
        assert result.success is False
        assert result.state == "degraded"
        assert len(result.warnings) == 1

    @pytest.mark.asyncio
    async def test_verification_warning_backward_compat(self):
        get_state = AsyncMock(return_value=None)
        verifier = _SetupVerifier(get_state)
        result = await verifier.verify({
            "entity_ids": ["light.missing"],
            "integration": "hue",
        })
        # verification_warning property returns first warning message
        assert result.verification_warning is not None
        assert "missing" in result.verification_warning
