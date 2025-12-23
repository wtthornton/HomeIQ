"""
Integration tests for blueprint integration with YAML generation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.automation.yaml_generation_service import generate_automation_yaml
from src.llm.openai_client import OpenAIClient


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    client = MagicMock(spec=OpenAIClient)
    client.client = MagicMock()
    client.client.chat = MagicMock()
    client.client.chat.completions = MagicMock()
    
    # Mock response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = """
id: 'test-123'
alias: Test Automation
description: Test
trigger:
  - platform: state
    entity_id: light.office
    to: 'on'
action:
  - service: light.turn_on
    target:
      entity_id: light.office
"""
    mock_response.usage = MagicMock()
    mock_response.usage.total_tokens = 100
    
    client.client.chat.completions.create = AsyncMock(return_value=mock_response)
    return client


@pytest.fixture
def sample_suggestion():
    """Sample suggestion for testing."""
    return {
        "description": "Turn on office light when motion detected",
        "trigger_summary": "Motion sensor detects motion",
        "action_summary": "Turn on office light",
        "devices_involved": ["light", "binary_sensor"],
        "validated_entities": {
            "Office Light": "light.office",
            "Motion Sensor": "binary_sensor.office_motion"
        },
        "enriched_entity_context": "{}"
    }


@pytest.mark.asyncio
async def test_blueprint_integration_with_match(mock_openai_client, sample_suggestion):
    """Test blueprint integration when a match is found."""
    from src.utils.miner_integration import MinerIntegration
    
    # Mock blueprint data
    mock_blueprint = {
        "id": 1,
        "yaml": """
blueprint:
  name: Motion-Activated Light
  input:
    motion_sensor:
      selector:
        entity:
          domain: binary_sensor
          device_class: motion
    target_light:
      selector:
        entity:
          domain: light
trigger:
  - platform: state
    entity_id: !input motion_sensor
    to: 'on'
action:
  - service: light.turn_on
    target:
      entity_id: !input target_light
""",
        "metadata": {
            "_blueprint_metadata": {
                "name": "Motion-Activated Light",
                "description": "Turn on lights when motion detected"
            },
            "_blueprint_variables": {
                "motion_sensor": {
                    "domain": "binary_sensor",
                    "device_class": "motion"
                },
                "target_light": {
                    "domain": "light"
                }
            },
            "_blueprint_devices": ["binary_sensor", "light"]
        },
        "use_case": "comfort",
        "quality_score": 0.85
    }
    
    # Mock miner integration
    with patch('src.services.automation.yaml_generation_service.get_miner_integration') as mock_get_miner:
        mock_miner = MagicMock(spec=MinerIntegration)
        mock_miner.search_blueprints = AsyncMock(return_value=[mock_blueprint])
        mock_get_miner.return_value = mock_miner
        
        # Mock matcher to return high fit score
        with patch('src.services.blueprints.matcher.BlueprintMatcher.find_best_match') as mock_match:
            mock_match.return_value = {
                "blueprint": mock_blueprint,
                "fit_score": 0.9,
                "blueprint_yaml": mock_blueprint["yaml"],
                "metadata": mock_blueprint["metadata"]
            }
            
            # Mock filler
            with patch('src.services.blueprints.filler.BlueprintInputFiller.fill_blueprint_inputs') as mock_fill:
                mock_fill.return_value = {
                    "motion_sensor": "binary_sensor.office_motion",
                    "target_light": "light.office"
                }
                
                # Mock renderer
                with patch('src.services.blueprints.renderer.BlueprintRenderer.render_blueprint') as mock_render:
                    mock_render.return_value = """
id: 'blueprint-123'
alias: Motion-Activated Light
description: Turn on lights when motion detected
trigger:
  - platform: state
    entity_id: binary_sensor.office_motion
    to: 'on'
action:
  - service: light.turn_on
    target:
      entity_id: light.office
"""
                    
                    # Test YAML generation
                    yaml_str = await generate_automation_yaml(
                        suggestion=sample_suggestion,
                        original_query="Turn on office light when motion detected",
                        openai_client=mock_openai_client,
                        entities=[],
                        db_session=None,
                        ha_client=None
                    )
                    
                    # Should use blueprint (not AI)
                    assert yaml_str
                    assert "binary_sensor.office_motion" in yaml_str
                    assert "light.office" in yaml_str
                    # Should not call OpenAI
                    mock_openai_client.client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_blueprint_integration_no_match_fallback_to_ai(mock_openai_client, sample_suggestion):
    """Test that AI generation is used when no blueprint match is found."""
    from src.utils.miner_integration import MinerIntegration
    
    # Mock miner integration returning no blueprints
    with patch('src.services.automation.yaml_generation_service.get_miner_integration') as mock_get_miner:
        mock_miner = MagicMock(spec=MinerIntegration)
        mock_miner.search_blueprints = AsyncMock(return_value=[])
        mock_get_miner.return_value = mock_miner
        
        # Mock matcher to return None (no match)
        with patch('src.services.blueprints.matcher.BlueprintMatcher.find_best_match') as mock_match:
            mock_match.return_value = None
            
            # Test YAML generation
            yaml_str = await generate_automation_yaml(
                suggestion=sample_suggestion,
                original_query="Turn on office light when motion detected",
                openai_client=mock_openai_client,
                entities=[],
                db_session=None,
                ha_client=None
            )
            
            # Should fallback to AI
            assert yaml_str
            # OpenAI should have been called
            mock_openai_client.client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_blueprint_integration_low_score_fallback_to_ai(mock_openai_client, sample_suggestion):
    """Test that AI generation is used when blueprint match score is too low."""
    from src.utils.miner_integration import MinerIntegration
    
    # Mock blueprint with low fit score
    mock_blueprint = {
        "id": 1,
        "yaml": "blueprint:\n  name: Test",
        "metadata": {
            "_blueprint_metadata": {"name": "Test"},
            "_blueprint_variables": {},
            "_blueprint_devices": []
        }
    }
    
    with patch('src.services.automation.yaml_generation_service.get_miner_integration') as mock_get_miner:
        mock_miner = MagicMock(spec=MinerIntegration)
        mock_miner.search_blueprints = AsyncMock(return_value=[mock_blueprint])
        mock_get_miner.return_value = mock_miner
        
        # Mock matcher to return low fit score (< 0.8 threshold)
        with patch('src.services.blueprints.matcher.BlueprintMatcher.find_best_match') as mock_match:
            mock_match.return_value = {
                "blueprint": mock_blueprint,
                "fit_score": 0.5,  # Below 0.8 threshold
                "blueprint_yaml": mock_blueprint["yaml"],
                "metadata": mock_blueprint["metadata"]
            }
            
            # Test YAML generation
            yaml_str = await generate_automation_yaml(
                suggestion=sample_suggestion,
                original_query="Turn on office light when motion detected",
                openai_client=mock_openai_client,
                entities=[],
                db_session=None,
                ha_client=None
            )
            
            # Should fallback to AI
            assert yaml_str
            # OpenAI should have been called
            mock_openai_client.client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_blueprint_integration_error_fallback_to_ai(mock_openai_client, sample_suggestion):
    """Test that AI generation is used when blueprint matching fails."""
    from src.utils.miner_integration import MinerIntegration
    
    with patch('src.services.automation.yaml_generation_service.get_miner_integration') as mock_get_miner:
        mock_miner = MagicMock(spec=MinerIntegration)
        mock_miner.search_blueprints = AsyncMock(side_effect=Exception("Miner unavailable"))
        mock_get_miner.return_value = mock_miner
        
        # Test YAML generation (should handle error gracefully)
        yaml_str = await generate_automation_yaml(
            suggestion=sample_suggestion,
            original_query="Turn on office light when motion detected",
            openai_client=mock_openai_client,
            entities=[],
            db_session=None,
            ha_client=None
        )
        
        # Should fallback to AI
        assert yaml_str
        # OpenAI should have been called
        mock_openai_client.client.chat.completions.create.assert_called_once()

