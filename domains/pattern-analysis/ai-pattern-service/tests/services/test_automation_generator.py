"""
Unit tests for AutomationGenerator service

Tests automation generation from synergies, validation, and deployment.
"""

import pytest
import yaml
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

import httpx

from src.services.automation_generator import AutomationGenerator


class TestAutomationGenerator:
    """Test suite for AutomationGenerator class."""
    
    @pytest.fixture
    def ha_url(self) -> str:
        """Home Assistant URL for testing."""
        return "http://localhost:8123"
    
    @pytest.fixture
    def ha_token(self) -> str:
        """Home Assistant token for testing."""
        return "test_token_12345"
    
    @pytest.fixture
    def generator(self, ha_url: str, ha_token: str) -> AutomationGenerator:
        """Create AutomationGenerator instance for testing."""
        return AutomationGenerator(
            ha_url=ha_url,
            ha_token=ha_token,
            ha_version="2025.1"
        )
    
    @pytest.fixture
    def sample_synergy(self) -> dict[str, Any]:
        """Sample synergy dictionary for testing."""
        return {
            'synergy_id': 'test-synergy-123',
            'synergy_type': 'device_pair',
            'devices': ['binary_sensor.motion', 'light.kitchen'],
            'trigger_entity': 'binary_sensor.motion',
            'action_entity': 'light.kitchen',
            'impact_score': 0.85,
            'confidence': 0.9,
            'area': 'kitchen',
            'rationale': 'Motion sensor triggers kitchen light'
        }
    
    @pytest.fixture
    def mock_ha_client(self) -> AsyncMock:
        """Mock Home Assistant HTTP client."""
        client = AsyncMock(spec=httpx.AsyncClient)
        return client
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_init(self, ha_url: str, ha_token: str):
        """Test AutomationGenerator initialization."""
        generator = AutomationGenerator(ha_url=ha_url, ha_token=ha_token)
        
        assert generator.ha_url == ha_url.rstrip('/')
        assert generator.ha_token == ha_token
        assert generator.ha_version == "2025.1"
        assert generator.yaml_transformer is not None
        assert generator.blueprint_library is not None
        assert generator.validator is not None
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_synergy_to_homeiq_automation(
        self,
        generator: AutomationGenerator,
        sample_synergy: dict[str, Any]
    ):
        """Test synergy to HomeIQAutomation conversion."""
        automation = generator._synergy_to_homeiq_automation(sample_synergy)
        
        assert automation is not None
        assert automation.alias is not None
        assert automation.description is not None
        assert len(automation.triggers) > 0
        assert len(automation.actions) > 0
        assert automation.homeiq_metadata is not None
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.services.automation_generator.YAMLTransformer')
    @patch('src.services.automation_generator.AutomationPreDeploymentValidator')
    async def test_generate_automation_success(
        self,
        mock_validator_class,
        mock_yaml_transformer_class,
        generator: AutomationGenerator,
        sample_synergy: dict[str, Any],
        mock_ha_client: AsyncMock
    ):
        """Test successful automation generation."""
        # Setup mocks - need to replace the actual instances
        mock_yaml_transformer = MagicMock()
        mock_yaml_transformer.transform_to_yaml = AsyncMock(
            return_value="alias: Test Automation\ntrigger:\n  - platform: state\n    entity_id: binary_sensor.motion\naction:\n  - service: light.turn_on\n    entity_id: light.kitchen"
        )
        mock_yaml_transformer_class.return_value = mock_yaml_transformer
        generator.yaml_transformer = mock_yaml_transformer
        
        mock_validator = MagicMock()
        mock_validator.validate_automation = AsyncMock(
            return_value={
                'valid': True,
                'errors': [],
                'warnings': [],
                'suggestions': [],
                'entity_validation': {'binary_sensor.motion': True, 'light.kitchen': True},
                'service_validation': {'light.turn_on': True}
            }
        )
        mock_validator_class.return_value = mock_validator
        generator.validator = mock_validator
        
        # Mock HA API response
        mock_ha_client.post = AsyncMock(
            return_value=MagicMock(
                status_code=200,
                json=MagicMock(return_value={'entity_id': 'automation.test_automation'})
            )
        )
        mock_ha_client.post.return_value.raise_for_status = MagicMock()
        
        # Mock blueprint library
        generator.blueprint_library.find_matching_blueprint = MagicMock(return_value=None)
        
        # Execute
        result = await generator.generate_automation_from_synergy(
            sample_synergy,
            mock_ha_client
        )
        
        # Verify
        assert result is not None
        assert 'automation_id' in result
        assert 'automation_yaml' in result
        assert 'deployment_status' in result
        assert result['deployment_status'] == 'deployed'
        assert result['estimated_impact'] == sample_synergy['impact_score']
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.services.automation_generator.YAMLTransformer')
    @patch('src.services.automation_generator.AutomationPreDeploymentValidator')
    async def test_generate_automation_validation_failure(
        self,
        mock_validator_class,
        mock_yaml_transformer_class,
        generator: AutomationGenerator,
        sample_synergy: dict[str, Any],
        mock_ha_client: AsyncMock
    ):
        """Test automation generation with validation failure."""
        # Setup mocks - need to replace the actual instances
        mock_yaml_transformer = MagicMock()
        mock_yaml_transformer.transform_to_yaml = AsyncMock(
            return_value="alias: Test Automation\ntrigger:\n  - platform: state\naction:\n  - service: light.turn_on"
        )
        mock_yaml_transformer_class.return_value = mock_yaml_transformer
        generator.yaml_transformer = mock_yaml_transformer
        
        mock_validator = MagicMock()
        mock_validator.validate_automation = AsyncMock(
            return_value={
                'valid': False,
                'errors': ['Entity binary_sensor.motion does not exist'],
                'warnings': [],
                'suggestions': [],
                'entity_validation': {'binary_sensor.motion': False},
                'service_validation': {}
            }
        )
        mock_validator_class.return_value = mock_validator
        generator.validator = mock_validator
        
        # Execute and verify exception
        with pytest.raises(ValueError, match="Automation validation failed"):
            await generator.generate_automation_from_synergy(
                sample_synergy,
                mock_ha_client
            )
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.services.automation_generator.YAMLTransformer')
    async def test_generate_automation_yaml_error(
        self,
        mock_yaml_transformer_class,
        generator: AutomationGenerator,
        sample_synergy: dict[str, Any],
        mock_ha_client: AsyncMock
    ):
        """Test automation generation with YAML transformation error."""
        # Setup mock to raise exception - replace the actual instance
        mock_yaml_transformer = MagicMock()
        mock_yaml_transformer.transform_to_yaml = AsyncMock(
            side_effect=Exception("YAML transformation failed")
        )
        mock_yaml_transformer_class.return_value = mock_yaml_transformer
        generator.yaml_transformer = mock_yaml_transformer
        
        # Execute and verify exception
        with pytest.raises(Exception, match="YAML transformation failed"):
            await generator.generate_automation_from_synergy(
                sample_synergy,
                mock_ha_client
            )
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_deploy_automation_success(
        self,
        generator: AutomationGenerator,
        mock_ha_client: AsyncMock
    ):
        """Test successful automation deployment."""
        yaml_content = "alias: Test Automation\ntrigger:\n  - platform: state\naction:\n  - service: light.turn_on"
        synergy_id = "test-synergy-123"
        
        # Mock HA API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={'entity_id': 'automation.test_automation'})
        mock_response.raise_for_status = MagicMock()
        
        mock_ha_client.post = AsyncMock(return_value=mock_response)
        
        # Execute
        automation_id = await generator._deploy_automation(
            mock_ha_client,
            yaml_content,
            synergy_id
        )
        
        # Verify
        assert automation_id == 'automation.test_automation'
        mock_ha_client.post.assert_called_once()
        call_args = mock_ha_client.post.call_args
        assert 'api/services/automation/create' in call_args[0][0]
        assert call_args[1]['headers']['Authorization'] == f"Bearer {generator.ha_token}"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_deploy_automation_api_error(
        self,
        generator: AutomationGenerator,
        mock_ha_client: AsyncMock
    ):
        """Test automation deployment with API error."""
        yaml_content = "alias: Test Automation"
        synergy_id = "test-synergy-123"
        
        # Mock HA API error response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError(
            "Bad Request",
            request=MagicMock(),
            response=mock_response
        ))
        
        mock_ha_client.post = AsyncMock(return_value=mock_response)
        
        # Execute and verify exception
        with pytest.raises(httpx.HTTPStatusError):
            await generator._deploy_automation(
                mock_ha_client,
                yaml_content,
                synergy_id
            )
