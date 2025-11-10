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

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
import os
import yaml

pytest.importorskip(
    "transformers",
    reason="transformers dependency not available in this environment"
)

from src.main import app
from src.llm.yaml_generator import YAMLGenerator, YAMLGenerationResult
from src.safety_validator import SafetyValidator, SafetyResult, SafetyIssue


# ============================================================================
# Integration Tests (Mocked)
# ============================================================================

@pytest.mark.asyncio
async def test_approve_and_generate_valid_yaml():
    """Test approval with successful YAML generation"""
    
    with patch('src.api.conversational_router.yaml_generator') as mock_yaml_gen, \
         patch('src.api.conversational_router.safety_validator') as mock_safety:
        
        # Mock YAML generation
        mock_yaml_gen.generate_yaml = AsyncMock(return_value=YAMLGenerationResult(
            yaml="""alias: Morning Kitchen Light
trigger:
  - platform: time
    at: '07:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: light.kitchen
    data:
      brightness_pct: 100""",
            alias="Morning Kitchen Light",
            services_used=["light.turn_on"],
            syntax_valid=True,
            confidence=0.98
        ))
        
        # Mock safety validation
        mock_safety.validate = AsyncMock(return_value=SafetyResult(
            passed=True,
            safety_score=95,
            issues=[],
            can_override=True,
            summary="No safety issues detected"
        ))
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/suggestions/1/approve",
                json={"final_description": "At 7:00 AM, turn on Kitchen Light to full brightness"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data['status'] == 'yaml_generated'
            assert 'automation_yaml' in data
            assert 'alias: Morning Kitchen Light' in data['automation_yaml']
            assert data['yaml_validation']['syntax_valid'] == True
            assert data['yaml_validation']['safety_score'] == 95
            assert data['ready_to_deploy'] == True


@pytest.mark.asyncio
async def test_approve_with_safety_failure():
    """Test approval when safety validation fails"""
    
    with patch('src.api.conversational_router.yaml_generator') as mock_yaml_gen, \
         patch('src.api.conversational_router.safety_validator') as mock_safety:
        
        # Mock YAML generation (valid syntax)
        mock_yaml_gen.generate_yaml = AsyncMock(return_value=YAMLGenerationResult(
            yaml="""alias: Disable All Security
action:
  - service: alarm_control_panel.disarm""",
            alias="Disable All Security",
            services_used=["alarm_control_panel.disarm"],
            syntax_valid=True,
            confidence=0.95
        ))
        
        # Mock safety validation (FAILS)
        mock_safety.validate = AsyncMock(return_value=SafetyResult(
            passed=False,
            safety_score=25,
            issues=[SafetyIssue(
                rule="security_disable",
                severity="critical",
                message="Never disable security systems automatically"
            )],
            can_override=False,
            summary="Critical safety violation: disabling security"
        ))
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/suggestions/1/approve",
                json={"final_description": "Disable all security systems"}
            )
            
            # Should return 400 (bad request)
            assert response.status_code == 400
            assert "Safety validation failed" in response.json()['detail']


@pytest.mark.asyncio
async def test_approve_with_invalid_yaml_syntax():
    """Test approval when YAML generation produces invalid syntax"""
    
    with patch('src.api.conversational_router.yaml_generator') as mock_yaml_gen:
        
        # Mock YAML generation with INVALID syntax
        mock_yaml_gen.generate_yaml = AsyncMock(return_value=YAMLGenerationResult(
            yaml="alias: Bad YAML\ntrigger\n  - missing colon",  # Invalid!
            alias="Bad YAML",
            services_used=[],
            syntax_valid=False,  # Marked as invalid
            confidence=0.5
        ))
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/suggestions/1/approve",
                json={"final_description": "Test description"}
            )
            
            # Should return 500 (server error)
            assert response.status_code == 500
            assert "syntax errors" in response.json()['detail'].lower()


@pytest.mark.asyncio
async def test_rollback_on_yaml_failure():
    """Test that suggestion status rolls back to 'refining' on YAML failure"""
    
    with patch('src.api.conversational_router.yaml_generator') as mock_yaml_gen:
        
        # Mock YAML generation that raises exception
        mock_yaml_gen.generate_yaml = AsyncMock(
            side_effect=Exception("OpenAI timeout")
        )
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Attempt approval (will fail)
            response = await client.post(
                f"/api/v1/suggestions/1/approve",
                json={"final_description": "Test"}
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
    
    with patch('src.api.conversational_router.description_generator') as mock_desc_gen, \
         patch('src.api.conversational_router.suggestion_refiner') as mock_refiner, \
         patch('src.api.conversational_router.yaml_generator') as mock_yaml_gen, \
         patch('src.api.conversational_router.safety_validator') as mock_safety, \
         patch('src.api.conversational_router.data_api_client') as mock_data_api:
        
        # Mock capabilities
        mock_data_api.fetch_device_capabilities = AsyncMock(return_value={
            "entity_id": "light.kitchen",
            "friendly_name": "Kitchen Light",
            "domain": "light",
            "supported_features": {"brightness": True, "rgb_color": True},
            "friendly_capabilities": ["Adjust brightness", "Change color"]
        })
        
        # Mock description generation
        mock_desc_gen.generate_description = AsyncMock(
            return_value="At 7:00 AM, turn on the Kitchen Light to 50% brightness"
        )
        
        # Mock refinement
        from src.llm.suggestion_refiner import RefinementResult, ValidationResult
        mock_refiner.validate_feasibility = AsyncMock(return_value=ValidationResult(
            ok=True, messages=[], warnings=[], alternatives=[]
        ))
        mock_refiner.refine_description = AsyncMock(return_value=RefinementResult(
            updated_description="At 7:00 AM, turn on the Kitchen Light to blue at full brightness",
            changes_made=["Added color: blue"],
            validation=ValidationResult(ok=True, messages=[], warnings=[], alternatives=[]),
            history_entry={"user_input": "Make it blue", "updated_description": "..."}
        ))
        
        # Mock YAML generation
        mock_yaml_gen.generate_yaml = AsyncMock(return_value=YAMLGenerationResult(
            yaml="""alias: Morning Kitchen Light
trigger:
  - platform: time
    at: '07:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: light.kitchen
    data:
      rgb_color: [0, 0, 255]
      brightness_pct: 100""",
            alias="Morning Kitchen Light",
            services_used=["light.turn_on"],
            syntax_valid=True,
            confidence=0.98
        ))
        
        # Mock safety validation
        mock_safety.validate = AsyncMock(return_value=SafetyResult(
            passed=True,
            safety_score=95,
            issues=[],
            can_override=True,
            summary="No issues"
        ))
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Step 1: Generate description
            gen_response = await client.post(
                "/api/v1/suggestions/generate",
                json={
                    "pattern_id": 1,
                    "pattern_type": "time_of_day",
                    "device_id": "light.kitchen",
                    "metadata": {"avg_time_decimal": 7.0}
                }
            )
            assert gen_response.status_code == 201
            
            # Step 2: Refine (would use real ID from step 1)
            # (Skipped for mock - would fetch suggestion_id from gen_response)
            
            # Step 3: Approve and generate YAML
            approve_response = await client.post(
                f"/api/v1/suggestions/1/approve",
                json={"final_description": "At 7:00 AM, turn on the Kitchen Light to blue"}
            )
            
            assert approve_response.status_code == 200
            approval_data = approve_response.json()
            
            assert approval_data['status'] == 'yaml_generated'
            assert 'alias: Morning Kitchen Light' in approval_data['automation_yaml']
            assert 'rgb_color: [0, 0, 255]' in approval_data['automation_yaml']
            assert approval_data['ready_to_deploy'] == True


# ============================================================================
# YAML Syntax Validation Tests
# ============================================================================

def test_valid_yaml_syntax():
    """Test YAML syntax validation with valid YAML"""
    from openai import AsyncOpenAI
    
    # Can use without actual client for syntax validation
    generator = YAMLGenerator(AsyncOpenAI(api_key="test"), model="gpt-4o-mini")
    
    valid_yaml = """alias: Test Automation
trigger:
  - platform: time
    at: '07:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: light.kitchen"""
    
    is_valid, error = generator.validate_yaml_syntax(valid_yaml)
    assert is_valid == True
    assert error is None


def test_invalid_yaml_syntax():
    """Test YAML syntax validation with invalid YAML"""
    from openai import AsyncOpenAI
    
    generator = YAMLGenerator(AsyncOpenAI(api_key="test"), model="gpt-4o-mini")
    
    invalid_yaml = """alias: Bad YAML
trigger
  - missing colon here
    at: '07:00:00'"""
    
    is_valid, error = generator.validate_yaml_syntax(invalid_yaml)
    assert is_valid == False
    assert error is not None


# ============================================================================
# Real OpenAI Integration Test (Optional, costs money)
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv('OPENAI_API_KEY'),
    reason="OPENAI_API_KEY not set - skipping real API tests"
)
@pytest.mark.asyncio
async def test_real_openai_yaml_generation():
    """
    Test real OpenAI YAML generation (COSTS MONEY - ~$0.0002).
    
    This is a real integration test that calls OpenAI API.
    Only run when you want to verify the actual integration works.
    """
    from openai import AsyncOpenAI
    
    # Initialize real client
    client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    generator = YAMLGenerator(client, model="gpt-4o-mini")
    
    # Test YAML generation
    result = await generator.generate_yaml(
        final_description="At 7:00 AM every weekday, turn on the Kitchen Light to blue at full brightness",
        devices_metadata={
            "entity_id": "light.kitchen",
            "friendly_name": "Kitchen Light",
            "domain": "light"
        },
        conversation_history=[
            {"user_input": "Make it blue", "updated_description": "...turn on light to blue"},
            {"user_input": "Only weekdays", "updated_description": "...on weekdays"}
        ]
    )
    
    # Assertions
    assert result.yaml is not None
    assert len(result.yaml) > 0
    assert result.syntax_valid == True
    assert result.alias is not None
    
    # Verify it's valid YAML
    parsed = yaml.safe_load(result.yaml)
    assert 'alias' in parsed
    assert 'trigger' in parsed
    assert 'action' in parsed
    
    # Check token usage
    stats = generator.get_usage_stats()
    assert stats['total_tokens'] > 0
    
    print(f"\n✅ Real OpenAI YAML generation test passed!")
    print(f"   Alias: {result.alias}")
    print(f"   Services: {result.services_used}")
    print(f"   Tokens: {stats['total_tokens']}")
    print(f"   Cost: ${stats['estimated_cost_usd']:.6f}")
    print(f"\n   Generated YAML:")
    print("   " + result.yaml.replace('\n', '\n   '))


# ============================================================================
# Pytest Configuration
# ============================================================================

@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio for async tests"""
    return "asyncio"

