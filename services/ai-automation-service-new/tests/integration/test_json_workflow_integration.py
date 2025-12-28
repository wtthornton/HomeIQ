"""
Integration tests for HomeIQ JSON Automation workflow.

Tests the complete flow:
1. JSON generation from LLM
2. JSON validation
3. JSON to AutomationSpec conversion
4. AutomationSpec to YAML rendering
5. Version-aware rendering
6. JSON query and combination
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from shared.homeiq_automation.converter import HomeIQToAutomationSpecConverter
from shared.homeiq_automation.schema import HomeIQAutomation
from shared.homeiq_automation.validator import HomeIQAutomationSchemaValidator
from shared.yaml_validation_service.version_aware_renderer import VersionAwareAutomationRenderer

from ...src.clients.data_api_client import DataAPIClient
from ...src.clients.openai_client import OpenAIClient
from ...src.services.automation_combiner import AutomationCombiner
from ...src.services.json_query_service import JSONQueryService
from ...src.services.json_rebuilder import JSONRebuilder
from ...src.services.json_verification_service import JSONVerificationService
from ...src.services.yaml_generation_service import YAMLGenerationService


@pytest.fixture
def sample_homeiq_json():
    """Sample HomeIQ JSON Automation for testing."""
    return {
        "schema_version": "1.0.0",
        "metadata": {
            "alias": "Test Automation",
            "description": "Test automation for integration testing",
            "created_at": "2025-01-01T00:00:00Z",
            "created_by": "test",
            "use_case": "comfort",
            "complexity": "low"
        },
        "pattern_context": None,
        "device_context": {
            "devices": [
                {
                    "device_id": "test_device_1",
                    "entity_ids": ["light.test_1", "sensor.motion_1"],
                    "area_id": "living_room"
                }
            ],
            "entity_ids": ["light.test_1", "sensor.motion_1"]
        },
        "safety_checks": {
            "critical_warnings": [],
            "recommendations": [],
            "requires_confirmation": False
        },
        "energy_impact": {
            "estimated_watts": 10.0,
            "estimated_daily_kwh": 0.24,
            "peak_power_time": "evening"
        },
        "ha_automation_spec": {
            "alias": "Test Automation",
            "description": "Test automation",
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": "sensor.motion_1",
                    "to": "on"
                }
            ],
            "condition": [],
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "entity_id": "light.test_1"
                    }
                }
            ],
            "mode": "single",
            "initial_state": True
        },
        "extra": {}
    }


@pytest.fixture
def mock_data_api_client():
    """Mock DataAPIClient for testing."""
    client = MagicMock(spec=DataAPIClient)
    client.fetch_entities = AsyncMock(return_value=[
        {"entity_id": "light.test_1"},
        {"entity_id": "sensor.motion_1"},
        {"entity_id": "light.test_2"}
    ])
    return client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAIClient for testing."""
    client = MagicMock(spec=OpenAIClient)
    return client


@pytest.mark.asyncio
@pytest.mark.integration
async def test_json_generation_workflow(mock_openai_client, sample_homeiq_json):
    """Test complete JSON generation workflow."""
    # Mock OpenAI response
    mock_openai_client.generate_homeiq_automation_json = AsyncMock(
        return_value=sample_homeiq_json
    )
    
    # Create YAML generation service
    yaml_service = YAMLGenerationService(
        openai_client=mock_openai_client,
        data_api_client=MagicMock(),
        yaml_validation_client=None
    )
    
    # Generate JSON
    result = await yaml_service.generate_homeiq_json(
        suggestion={"title": "Test", "description": "Turn on light when motion detected"},
        home_context={}
    )
    
    assert result is not None
    assert result["metadata"]["alias"] == "Test Automation"
    assert "ha_automation_spec" in result


@pytest.mark.asyncio
@pytest.mark.integration
async def test_json_validation_workflow(mock_data_api_client, sample_homeiq_json):
    """Test JSON validation workflow."""
    validator = HomeIQAutomationSchemaValidator(mock_data_api_client)
    
    # Validate JSON
    result = await validator.validate_homeiq_automation(sample_homeiq_json)
    
    assert result.is_valid is True
    assert len(result.errors) == 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_json_to_yaml_conversion_workflow(sample_homeiq_json):
    """Test JSON to YAML conversion workflow."""
    # Convert JSON to AutomationSpec
    # First convert dict to HomeIQAutomation model
    homeiq_automation = HomeIQAutomation(**sample_homeiq_json)
    converter = HomeIQToAutomationSpecConverter()
    automation_spec = converter.convert(homeiq_automation)
    
    assert automation_spec is not None
    assert automation_spec.alias == "Test Automation"
    assert len(automation_spec.trigger) == 1
    assert len(automation_spec.action) == 1
    
    # Render to YAML
    renderer = VersionAwareAutomationRenderer()
    yaml_content = renderer.render(automation_spec, ha_version="2025.10.3")
    
    assert yaml_content is not None
    assert "alias:" in yaml_content
    assert "Test Automation" in yaml_content
    assert "trigger:" in yaml_content
    assert "action:" in yaml_content


@pytest.mark.asyncio
@pytest.mark.integration
async def test_json_query_service(sample_homeiq_json):
    """Test JSON query service."""
    query_service = JSONQueryService()
    
    automations = [sample_homeiq_json]
    
    # Query by use_case
    results = query_service.query(automations, {"use_case": "comfort"})
    assert len(results) == 1
    
    # Query by complexity
    results = query_service.query(automations, {"complexity": "low"})
    assert len(results) == 1
    
    # Query by entity_id
    results = query_service.query(automations, {"entity_id": "light.test_1"})
    assert len(results) == 1
    
    # Query with no matches
    results = query_service.query(automations, {"use_case": "security"})
    assert len(results) == 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_automation_combiner(sample_homeiq_json):
    """Test automation combination service."""
    combiner = AutomationCombiner()
    
    # Create second automation
    automation2 = sample_homeiq_json.copy()
    automation2["metadata"]["alias"] = "Test Automation 2"
    automation2["ha_automation_spec"]["alias"] = "Test Automation 2"
    automation2["ha_automation_spec"]["trigger"][0]["entity_id"] = "sensor.motion_2"
    automation2["ha_automation_spec"]["action"][0]["target"]["entity_id"] = "light.test_2"
    
    # Combine automations
    combined = combiner.combine(
        automations=[sample_homeiq_json, automation2],
        alias="Combined Automation",
        description="Combined test automations"
    )
    
    assert combined is not None
    assert isinstance(combined, HomeIQAutomation)
    assert combined.metadata.alias == "Combined Automation"
    # Should have triggers and actions from both
    assert len(combined.ha_automation_spec.trigger) >= 1
    assert len(combined.ha_automation_spec.action) >= 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_json_rebuilder_from_yaml(mock_openai_client, sample_homeiq_json):
    """Test JSON rebuilder from YAML."""
    # Mock OpenAI response
    mock_openai_client.generate_homeiq_automation_json = AsyncMock(
        return_value=sample_homeiq_json
    )
    
    rebuilder = JSONRebuilder(mock_openai_client)
    
    # Sample YAML
    yaml_content = """
alias: Test Automation
trigger:
  - platform: state
    entity_id: sensor.motion_1
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.test_1
"""
    
    # Rebuild from YAML
    result = await rebuilder.rebuild_from_yaml(
        yaml_content=yaml_content,
        suggestion_id=1,
        pattern_id=None
    )
    
    assert result is not None
    assert "metadata" in result
    assert "ha_automation_spec" in result


@pytest.mark.asyncio
@pytest.mark.integration
async def test_json_rebuilder_from_description(mock_openai_client, sample_homeiq_json):
    """Test JSON rebuilder from description."""
    # Mock OpenAI response
    mock_openai_client.generate_homeiq_automation_json = AsyncMock(
        return_value=sample_homeiq_json
    )
    
    rebuilder = JSONRebuilder(mock_openai_client)
    
    # Rebuild from description
    result = await rebuilder.rebuild_from_description(
        description="Turn on light when motion detected",
        title="Test Automation",
        suggestion_id=1,
        pattern_id=None
    )
    
    assert result is not None
    assert "metadata" in result
    assert "ha_automation_spec" in result


@pytest.mark.asyncio
@pytest.mark.integration
async def test_json_verification_service(mock_data_api_client, sample_homeiq_json):
    """Test JSON verification service."""
    verification_service = JSONVerificationService(mock_data_api_client)
    
    # Verify valid JSON
    result = await verification_service.verify(sample_homeiq_json)
    assert result.is_valid is True
    
    # Test invalid entity
    invalid_json = sample_homeiq_json.copy()
    invalid_json["ha_automation_spec"]["trigger"][0]["entity_id"] = "invalid.entity"
    
    result = await verification_service.verify(invalid_json)
    # Should fail entity validation
    assert result.is_valid is False


@pytest.mark.asyncio
@pytest.mark.integration
async def test_version_aware_rendering(sample_homeiq_json):
    """Test version-aware YAML rendering."""
    # First convert dict to HomeIQAutomation model
    homeiq_automation_model = HomeIQAutomation(**sample_homeiq_json)
    converter = HomeIQToAutomationSpecConverter()
    automation_spec = converter.convert(homeiq_automation_model)
    
    renderer = VersionAwareAutomationRenderer()
    
    # Render for different versions
    yaml_2025_10 = renderer.render(automation_spec, ha_version="2025.10.3")
    yaml_2024_12 = renderer.render(automation_spec, ha_version="2024.12.0")
    yaml_latest = renderer.render(automation_spec, ha_version=None)
    
    # All should produce valid YAML
    assert yaml_2025_10 is not None
    assert yaml_2024_12 is not None
    assert yaml_latest is not None
    
    # All should contain basic structure
    for yaml_content in [yaml_2025_10, yaml_2024_12, yaml_latest]:
        assert "alias:" in yaml_content
        assert "trigger:" in yaml_content
        assert "action:" in yaml_content


@pytest.mark.asyncio
@pytest.mark.integration
async def test_end_to_end_json_workflow(mock_openai_client, mock_data_api_client, sample_homeiq_json):
    """Test complete end-to-end JSON workflow."""
    # Mock OpenAI response
    mock_openai_client.generate_homeiq_automation_json = AsyncMock(
        return_value=sample_homeiq_json
    )
    
    # Step 1: Generate JSON
    yaml_service = YAMLGenerationService(
        openai_client=mock_openai_client,
        data_api_client=mock_data_api_client,
        yaml_validation_client=None
    )
    
    homeiq_json = await yaml_service.generate_homeiq_json(
        suggestion={"title": "Test", "description": "Test automation"},
        home_context={}
    )
    
    # Step 2: Validate JSON
    validator = HomeIQAutomationSchemaValidator(mock_data_api_client)
    validation_result = await validator.validate_homeiq_automation(homeiq_json)
    assert validation_result.is_valid is True
    
    # Step 3: Convert to AutomationSpec
    # First convert dict to HomeIQAutomation model
    homeiq_automation_model = HomeIQAutomation(**homeiq_json)
    converter = HomeIQToAutomationSpecConverter()
    automation_spec = converter.convert(homeiq_automation_model)
    assert automation_spec is not None
    
    # Step 4: Render to YAML
    renderer = VersionAwareAutomationRenderer()
    yaml_content = renderer.render(automation_spec, ha_version="2025.10.3")
    assert yaml_content is not None
    assert "alias:" in yaml_content
    
    # Step 5: Query JSON
    query_service = JSONQueryService()
    results = query_service.query([homeiq_json], {"use_case": "comfort"})
    assert len(results) == 1
    
    # Step 6: Verify complete workflow
    verification_service = JSONVerificationService(mock_data_api_client)
    verify_result = await verification_service.verify(homeiq_json)
    assert verify_result.is_valid is True

