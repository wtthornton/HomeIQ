"""
Epic 90, Story 90.9: Hybrid Flow (Plan->Validate->Compile->Deploy) integration test.

Tests the ai-automation-service-new 4-step pipeline directly via HTTP.
Verifies: plan returns template_id, validate resolves entities,
compile produces deterministic YAML, compiled YAML passes validation service.

Requires: ai-automation-service-new at AUTOMATION_SERVICE_URL (default: http://localhost:8036)
          yaml-validation-service at YAML_VALIDATION_URL (default: http://localhost:8037)
          OpenAI API key configured (for plan step only)
"""

import os

import httpx
import pytest
import yaml

AUTOMATION_SERVICE_URL = os.environ.get(
    "AUTOMATION_SERVICE_URL", "http://localhost:8036"
)
YAML_VALIDATION_URL = os.environ.get(
    "YAML_VALIDATION_URL", "http://localhost:8037"
)
TIMEOUT = 60.0  # Plan step uses LLM


@pytest.mark.integration
@pytest.mark.asyncio
class TestHybridFlowPipeline:
    """Integration tests for Hybrid Flow pipeline (Story 90.9)."""

    async def _plan(
        self,
        client: httpx.AsyncClient,
        user_text: str,
        context: dict | None = None,
    ) -> dict:
        """Call plan endpoint."""
        response = await client.post(
            f"{AUTOMATION_SERVICE_URL}/automation/plan",
            json={
                "user_text": user_text,
                "context": context or {},
                "conversation_id": None,
            },
            timeout=TIMEOUT,
        )
        assert response.status_code == 200, (
            f"Plan failed: {response.status_code} {response.text}"
        )
        return response.json()

    async def _validate(
        self, client: httpx.AsyncClient, plan_data: dict
    ) -> dict:
        """Call validate endpoint using plan output."""
        response = await client.post(
            f"{AUTOMATION_SERVICE_URL}/automation/validate",
            json={
                "plan_id": plan_data["plan_id"],
                "template_id": plan_data["template_id"],
                "template_version": plan_data.get("template_version", 1),
                "parameters": plan_data["parameters"],
            },
            timeout=30.0,
        )
        assert response.status_code == 200, (
            f"Validate failed: {response.status_code} {response.text}"
        )
        return response.json()

    async def _compile(
        self,
        client: httpx.AsyncClient,
        plan_data: dict,
        validate_data: dict,
    ) -> dict:
        """Call compile endpoint using plan + validate output."""
        response = await client.post(
            f"{AUTOMATION_SERVICE_URL}/automation/compile",
            json={
                "plan_id": plan_data["plan_id"],
                "template_id": plan_data["template_id"],
                "template_version": plan_data.get("template_version", 1),
                "parameters": plan_data["parameters"],
                "resolved_context": validate_data["resolved_context"],
            },
            timeout=30.0,
        )
        assert response.status_code == 200, (
            f"Compile failed: {response.status_code} {response.text}"
        )
        return response.json()

    async def _cross_validate_yaml(
        self, client: httpx.AsyncClient, yaml_content: str
    ) -> dict:
        """Validate compiled YAML through yaml-validation-service."""
        response = await client.post(
            f"{YAML_VALIDATION_URL}/api/v1/validation/validate",
            json={
                "yaml_content": yaml_content,
                "normalize": True,
                "validate_entities": False,
                "validate_services": False,
            },
            timeout=30.0,
        )
        assert response.status_code == 200, (
            f"Cross-validation failed: {response.status_code} {response.text}"
        )
        return response.json()

    # --- Plan Step Tests ---

    async def test_plan_returns_template_and_parameters(self):
        """Plan endpoint returns template_id and parameters for automation request."""
        async with httpx.AsyncClient() as client:
            plan = await self._plan(
                client, "Turn on the hallway lights when motion is detected"
            )

            assert "plan_id" in plan, (
                f"Plan missing plan_id: {list(plan.keys())}"
            )
            assert plan["plan_id"].startswith("p_"), (
                f"plan_id should start with 'p_': {plan['plan_id']}"
            )
            assert "template_id" in plan, "Plan missing template_id"
            assert isinstance(plan["template_id"], str) and len(plan["template_id"]) > 0
            assert "parameters" in plan, "Plan missing parameters"
            assert isinstance(plan["parameters"], dict)
            assert "confidence" in plan, "Plan missing confidence"
            assert 0.0 <= plan["confidence"] <= 1.0
            assert "safety_class" in plan
            assert plan["safety_class"] in ("low", "medium", "high", "critical")

    # --- Validate Step Tests ---

    async def test_validate_resolves_entities(self):
        """Validate endpoint resolves entities successfully."""
        async with httpx.AsyncClient() as client:
            plan = await self._plan(
                client, "Turn on the hallway lights when motion is detected"
            )
            validate = await self._validate(client, plan)

            assert "valid" in validate
            assert "resolved_context" in validate, (
                "Validate missing resolved_context"
            )
            assert isinstance(validate["resolved_context"], dict)
            assert "safety" in validate, "Validate missing safety"

    # --- Compile Step Tests ---

    async def test_compile_produces_valid_yaml(self):
        """Compile endpoint produces valid YAML."""
        async with httpx.AsyncClient() as client:
            plan = await self._plan(
                client, "Turn on the hallway lights when motion is detected"
            )
            validate = await self._validate(client, plan)

            if not validate.get("valid", False):
                pytest.skip(
                    f"Validate failed: {validate.get('validation_errors', [])}"
                )

            compile_result = await self._compile(client, plan, validate)

            assert "compiled_id" in compile_result
            assert compile_result["compiled_id"].startswith("c_")
            assert "yaml" in compile_result, "Compile missing yaml"
            assert len(compile_result["yaml"]) > 0, "Compiled YAML is empty"
            assert "human_summary" in compile_result

            # Parse the YAML to verify it's valid
            parsed = yaml.safe_load(compile_result["yaml"])
            assert isinstance(parsed, dict), (
                f"Compiled YAML is not a dict: {type(parsed)}"
            )

            # Basic structure check
            has_trigger = "trigger" in parsed or "triggers" in parsed
            has_action = "action" in parsed or "actions" in parsed
            assert has_trigger, (
                f"Compiled YAML missing trigger: {list(parsed.keys())}"
            )
            assert has_action, (
                f"Compiled YAML missing action: {list(parsed.keys())}"
            )

    async def test_compile_is_deterministic(self):
        """Compile step is deterministic: 3 identical calls produce identical YAML."""
        async with httpx.AsyncClient() as client:
            plan = await self._plan(
                client, "Turn on the hallway lights when motion is detected"
            )
            validate = await self._validate(client, plan)

            if not validate.get("valid", False):
                pytest.skip(
                    f"Validate failed: {validate.get('validation_errors', [])}"
                )

            # Call compile 3 times with identical input
            results = []
            for _ in range(3):
                result = await self._compile(client, plan, validate)
                results.append(result["yaml"])

            # All 3 should produce identical YAML
            assert results[0] == results[1], (
                f"Compile call 1 != 2:\n--- Call 1 ---\n{results[0]}"
                f"\n--- Call 2 ---\n{results[1]}"
            )
            assert results[1] == results[2], (
                f"Compile call 2 != 3:\n--- Call 2 ---\n{results[1]}"
                f"\n--- Call 3 ---\n{results[2]}"
            )

    # --- Cross-Service Validation ---

    async def test_compiled_yaml_passes_validation_service(self):
        """Compiled YAML passes yaml-validation-service validation."""
        async with httpx.AsyncClient() as client:
            plan = await self._plan(
                client, "Turn on the hallway lights when motion is detected"
            )
            validate = await self._validate(client, plan)

            if not validate.get("valid", False):
                pytest.skip(
                    f"Validate failed: {validate.get('validation_errors', [])}"
                )

            compile_result = await self._compile(client, plan, validate)
            validation = await self._cross_validate_yaml(
                client, compile_result["yaml"]
            )

            assert validation["valid"] is True, (
                f"Compiled YAML failed validation: errors={validation['errors']}, "
                f"warnings={validation.get('warnings', [])}"
            )
            assert validation["score"] >= 70.0, (
                f"Compiled YAML score too low: {validation['score']}"
            )

    # --- Full Pipeline ---

    async def test_full_pipeline_completes(self):
        """Full pipeline (plan->validate->compile->cross-validate) completes successfully."""
        async with httpx.AsyncClient() as client:
            # Step 1: Plan
            plan = await self._plan(
                client, "Turn off all lights at midnight"
            )
            assert plan["template_id"], "Plan should select a template"

            # Step 2: Validate
            validate = await self._validate(client, plan)
            if not validate.get("valid", False):
                pytest.skip(
                    f"Validate step failed: {validate.get('validation_errors', [])}"
                )

            # Step 3: Compile
            compile_result = await self._compile(client, plan, validate)
            assert compile_result["yaml"], "Compile should produce YAML"

            # Step 4: Cross-validate
            validation = await self._cross_validate_yaml(
                client, compile_result["yaml"]
            )
            assert validation["valid"] is True, (
                f"Cross-validation failed: {validation['errors']}"
            )

    async def test_plan_response_schema(self):
        """Verify plan response contains all documented fields."""
        async with httpx.AsyncClient() as client:
            plan = await self._plan(
                client, "Dim the bedroom lights to 30% at 10pm"
            )

            expected_fields = [
                "plan_id",
                "template_id",
                "parameters",
                "confidence",
                "safety_class",
                "explanation",
            ]
            for field in expected_fields:
                assert field in plan, (
                    f"Plan response missing field: {field}"
                )
