"""
Integration Tests for Phase 4 - YAML Generation on Approval
============================================================

Story AI1.23 Phase 4: Conversational Suggestion Refinement

Tests the complete approval and YAML generation flow:
1. User approves refined description
2. System generates Home Assistant YAML
3. YAML syntax validation
4. Safety validation
5. Store in database
6. Rollback on failure

These tests require:
- OpenAI API key set (or mocked)
- SafetyValidator configured
- Database initialized with suggestions
"""

import os
from unittest.mock import AsyncMock, patch

import pytest
import yaml
from httpx import AsyncClient

pytest.importorskip(
    "transformers",
    reason="transformers dependency not available in this environment",
)

from src.main import app
from src.safety_validator import SafetyIssue, SafetyResult

# ============================================================================
# Integration Tests (Mocked)
# ============================================================================

@pytest.mark.asyncio
async def test_approve_and_generate_valid_yaml():
    """Test approval with successful YAML generation"""

    with patch("src.api.ask_ai_router.generate_automation_yaml") as mock_generate_yaml, \
         patch("src.api.conversational_router.safety_validator") as mock_safety:

        # Mock YAML generation
        mock_generate_yaml.return_value = """alias: Morning Kitchen Light
triggers:
  - trigger: time
    at: '07:00:00'
actions:
  - action: light.turn_on
    target:
      entity_id: light.kitchen
    data:
      brightness_pct: 100"""

        # Mock safety validation
        mock_safety.validate = AsyncMock(return_value=SafetyResult(
            passed=True,
            safety_score=95,
            issues=[],
            can_override=True,
            summary="No safety issues detected",
        ))

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/suggestions/1/approve",
                json={"final_description": "At 7:00 AM, turn on Kitchen Light to full brightness"},
            )

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "yaml_generated"
            assert "automation_yaml" in data
            assert "alias: Morning Kitchen Light" in data["automation_yaml"]
            assert data["yaml_validation"]["syntax_valid"]
            assert data["yaml_validation"]["safety_score"] == 95
            assert data["ready_to_deploy"]


@pytest.mark.asyncio
async def test_approve_with_safety_failure():
    """Test approval when safety validation fails"""

    with patch("src.api.ask_ai_router.generate_automation_yaml") as mock_generate_yaml, \
         patch("src.api.conversational_router.safety_validator") as mock_safety:

        # Mock YAML generation (valid syntax)
        mock_generate_yaml.return_value = """alias: Disable All Security
actions:
  - action: alarm_control_panel.disarm"""

        # Mock safety validation (FAILS)
        mock_safety.validate = AsyncMock(return_value=SafetyResult(
            passed=False,
            safety_score=25,
            issues=[SafetyIssue(
                rule="security_disable",
                severity="critical",
                message="Never disable security systems automatically",
            )],
            can_override=False,
            summary="Critical safety violation: disabling security",
        ))

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/suggestions/1/approve",
                json={"final_description": "Disable all security systems"},
            )

            # Should return 400 (bad request)
            assert response.status_code == 400
            assert "Safety validation failed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_approve_with_invalid_yaml_syntax():
    """Test approval when YAML generation produces invalid syntax"""

    with patch("src.api.ask_ai_router.generate_automation_yaml") as mock_generate_yaml:

        # Mock YAML generation with INVALID syntax (will raise ValueError)
        mock_generate_yaml.side_effect = ValueError("Generated YAML syntax is invalid: missing colon")

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/suggestions/1/approve",
                json={"final_description": "Test description"},
            )

            # Should return 500 (server error)
            assert response.status_code == 500
            assert "syntax errors" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_rollback_on_yaml_failure():
    """Test that suggestion status rolls back to 'refining' on YAML failure"""

    with patch("src.api.ask_ai_router.generate_automation_yaml") as mock_generate_yaml:

        # Mock YAML generation that raises exception
        mock_generate_yaml.side_effect = Exception("OpenAI timeout")

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Attempt approval (will fail)
            response = await client.post(
                "/api/v1/suggestions/1/approve",
                json={"final_description": "Test"},
            )

            # Should return 500
            assert response.status_code == 500

            # TODO: Verify suggestion status was rolled back to 'refining'
            # (Would need database access in test)


# ============================================================================
# End-to-End Flow Test
# ============================================================================

@pytest.mark.asyncio
async def test_complete_flow_generate_refine_approve():
    """
    Test complete flow from generation to approval.

    Flow:
    1. Generate description (Phase 2)
    2. Refine description (Phase 3)
    3. Approve and generate YAML (Phase 4)
    """

    with patch("src.api.conversational_router.description_generator") as mock_desc_gen, \
         patch("src.api.conversational_router.suggestion_refiner") as mock_refiner, \
         patch("src.api.ask_ai_router.generate_automation_yaml") as mock_generate_yaml, \
         patch("src.api.conversational_router.safety_validator") as mock_safety, \
         patch("src.api.conversational_router.data_api_client") as mock_data_api:

        # Mock capabilities
        mock_data_api.fetch_device_capabilities = AsyncMock(return_value={
            "entity_id": "light.kitchen",
            "friendly_name": "Kitchen Light",
            "domain": "light",
            "supported_features": {"brightness": True, "rgb_color": True},
            "friendly_capabilities": ["Adjust brightness", "Change color"],
        })

        # Mock description generation
        mock_desc_gen.generate_description = AsyncMock(
            return_value="At 7:00 AM, turn on the Kitchen Light to 50% brightness",
        )

        # Mock refinement
        from src.llm.suggestion_refiner import RefinementResult, ValidationResult
        mock_refiner.validate_feasibility = AsyncMock(return_value=ValidationResult(
            ok=True, messages=[], warnings=[], alternatives=[],
        ))
        mock_refiner.refine_description = AsyncMock(return_value=RefinementResult(
            updated_description="At 7:00 AM, turn on the Kitchen Light to blue at full brightness",
            changes_made=["Added color: blue"],
            validation=ValidationResult(ok=True, messages=[], warnings=[], alternatives=[]),
            history_entry={"user_input": "Make it blue", "updated_description": "..."},
        ))

        # Mock YAML generation
        mock_generate_yaml.return_value = """alias: Morning Kitchen Light
triggers:
  - trigger: time
    at: '07:00:00'
actions:
  - action: light.turn_on
    target:
      entity_id: light.kitchen
    data:
      rgb_color: [0, 0, 255]
      brightness_pct: 100"""

        # Mock safety validation
        mock_safety.validate = AsyncMock(return_value=SafetyResult(
            passed=True,
            safety_score=95,
            issues=[],
            can_override=True,
            summary="No issues",
        ))

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Step 1: Generate description
            gen_response = await client.post(
                "/api/v1/suggestions/generate",
                json={
                    "pattern_id": 1,
                    "pattern_type": "time_of_day",
                    "device_id": "light.kitchen",
                    "metadata": {"avg_time_decimal": 7.0},
                },
            )
            assert gen_response.status_code == 201

            # Step 2: Refine (would use real ID from step 1)
            # (Skipped for mock - would fetch suggestion_id from gen_response)

            # Step 3: Approve and generate YAML
            approve_response = await client.post(
                "/api/v1/suggestions/1/approve",
                json={"final_description": "At 7:00 AM, turn on the Kitchen Light to blue"},
            )

            assert approve_response.status_code == 200
            approval_data = approve_response.json()

            assert approval_data["status"] == "yaml_generated"
            assert "alias: Morning Kitchen Light" in approval_data["automation_yaml"]
            assert "rgb_color: [0, 0, 255]" in approval_data["automation_yaml"]
            assert approval_data["ready_to_deploy"]


# ============================================================================
# YAML Syntax Validation Tests
# ============================================================================

def test_valid_yaml_syntax():
    """Test YAML syntax validation with valid YAML"""
    import yaml

    valid_yaml = """alias: Test Automation
triggers:
  - trigger: time
    at: '07:00:00'
actions:
  - action: light.turn_on
    target:
      entity_id: light.kitchen"""

    # Should not raise exception
    parsed = yaml.safe_load(valid_yaml)
    assert parsed is not None
    assert "alias" in parsed


def test_invalid_yaml_syntax():
    """Test YAML syntax validation with invalid YAML"""
    import yaml

    invalid_yaml = """alias: Bad YAML
trigger
  - missing colon here
    at: '07:00:00'"""

    # Should raise YAMLError
    with pytest.raises(yaml.YAMLError):
        yaml.safe_load(invalid_yaml)


# ============================================================================
# Real OpenAI Integration Test (Optional, costs money)
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set - skipping real API tests",
)
@pytest.mark.asyncio
async def test_real_openai_yaml_generation():
    """
    Test real OpenAI YAML generation (COSTS MONEY - ~$0.0002).

    This is a real integration test that calls OpenAI API.
    Only run when you want to verify the actual integration works.

    Note: This test now uses generate_automation_yaml from ask_ai_router
    instead of the removed YAMLGenerator class.
    """
    from src.api.ask_ai_router import generate_automation_yaml
    from src.llm.openai_client import OpenAIClient

    # Initialize real client and patch the global openai_client in ask_ai_router
    openai_client = OpenAIClient(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o-mini")

    # Test YAML generation
    suggestion = {
        "description": "At 7:00 AM every weekday, turn on the Kitchen Light to blue at full brightness",
        "trigger_summary": "Time trigger at 7:00 AM on weekdays",
        "action_summary": "Turn on Kitchen Light to blue at full brightness",
        "devices_involved": ["Kitchen Light"],
        "validated_entities": {
            "Kitchen Light": "light.kitchen",
        },
    }

    # Patch the global openai_client in ask_ai_router module
    with patch("src.api.ask_ai_router.openai_client", openai_client):
        yaml_content = await generate_automation_yaml(
            suggestion=suggestion,
            original_query="Turn on kitchen light at 7am weekdays",
            entities=None,
            db_session=None,
            ha_client=None,
        )

    # Assertions
    assert yaml_content is not None
    assert len(yaml_content) > 0

    # Verify it's valid YAML
    parsed = yaml.safe_load(yaml_content)
    assert "alias" in parsed
    assert "triggers" in parsed or "trigger" in parsed
    assert "actions" in parsed or "action" in parsed

    print("\n✅ Real OpenAI YAML generation test passed!")
    print("\n   Generated YAML:")
    print("   " + yaml_content.replace("\n", "\n   "))


# ============================================================================
# Pytest Configuration
# ============================================================================

@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio for async tests"""
    return "asyncio"

