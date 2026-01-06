"""
Unit tests for AutomationPreDeploymentValidator service

Tests automation validation before deployment, including entity and service validation.
"""

import pytest
import yaml
from unittest.mock import AsyncMock, MagicMock
from typing import Any

import httpx

from src.services.automation_pre_deployment_validator import AutomationPreDeploymentValidator


class TestAutomationPreDeploymentValidator:
    """Test suite for AutomationPreDeploymentValidator class."""
    
    @pytest.fixture
    def ha_url(self) -> str:
        """Home Assistant URL for testing."""
        return "http://localhost:8123"
    
    @pytest.fixture
    def ha_token(self) -> str:
        """Home Assistant token for testing."""
        return "test_token_12345"
    
    @pytest.fixture
    def validator(self, ha_url: str, ha_token: str) -> AutomationPreDeploymentValidator:
        """Create AutomationPreDeploymentValidator instance for testing."""
        return AutomationPreDeploymentValidator(ha_url=ha_url, ha_token=ha_token)
    
    @pytest.fixture
    def valid_automation_yaml(self) -> str:
        """Valid automation YAML for testing."""
        return """
alias: Test Automation
description: Test automation description
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
action:
  - service: light.turn_on
    entity_id: light.kitchen
"""
    
    @pytest.fixture
    def invalid_automation_yaml(self) -> str:
        """Invalid automation YAML for testing."""
        return """
alias: Invalid Automation
# Missing trigger and action
"""
    
    @pytest.fixture
    def mock_ha_client(self) -> AsyncMock:
        """Mock Home Assistant HTTP client."""
        client = AsyncMock(spec=httpx.AsyncClient)
        return client
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_init(self, ha_url: str, ha_token: str):
        """Test AutomationPreDeploymentValidator initialization."""
        validator = AutomationPreDeploymentValidator(ha_url=ha_url, ha_token=ha_token)
        
        assert validator.ha_url == ha_url.rstrip('/')
        assert validator.ha_token == ha_token
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validate_automation_valid(
        self,
        validator: AutomationPreDeploymentValidator,
        valid_automation_yaml: str,
        mock_ha_client: AsyncMock
    ):
        """Test validation of valid automation."""
        # Mock entity check - entity exists
        mock_entity_response = MagicMock()
        mock_entity_response.status_code = 200
        mock_entity_response.json = MagicMock(return_value={'state': 'on'})
        
        # Mock service check - services available
        mock_services_response = MagicMock()
        mock_services_response.status_code = 200
        mock_services_response.json = MagicMock(return_value={
            'light': {'turn_on': {}}
        })
        
        mock_ha_client.get = AsyncMock(side_effect=[
            mock_entity_response,  # binary_sensor.motion
            mock_entity_response,   # light.kitchen
            mock_services_response  # /api/services
        ])
        
        # Execute
        result = await validator.validate_automation(valid_automation_yaml, mock_ha_client)
        
        # Verify
        assert result['valid'] is True
        assert len(result['errors']) == 0
        assert 'binary_sensor.motion' in result['entity_validation']
        assert result['entity_validation']['binary_sensor.motion'] is True
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validate_automation_invalid_yaml(
        self,
        validator: AutomationPreDeploymentValidator,
        mock_ha_client: AsyncMock
    ):
        """Test validation with invalid YAML."""
        invalid_yaml = "invalid: yaml: content: ["
        
        # Execute
        result = await validator.validate_automation(invalid_yaml, mock_ha_client)
        
        # Verify
        assert result['valid'] is False
        assert len(result['errors']) > 0
        assert 'YAML parsing error' in result['errors'][0]
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validate_automation_missing_entity(
        self,
        validator: AutomationPreDeploymentValidator,
        valid_automation_yaml: str,
        mock_ha_client: AsyncMock
    ):
        """Test validation with missing entity."""
        # Mock entity check - entity does not exist
        mock_entity_response = MagicMock()
        mock_entity_response.status_code = 404
        
        # Mock services check
        mock_services_response = MagicMock()
        mock_services_response.status_code = 200
        mock_services_response.json = MagicMock(return_value={'light': {'turn_on': {}}})
        
        mock_ha_client.get = AsyncMock(side_effect=[
            mock_entity_response,  # binary_sensor.motion (not found)
            mock_entity_response,  # light.kitchen (not found)
            mock_services_response  # /api/services
        ])
        
        # Execute
        result = await validator.validate_automation(valid_automation_yaml, mock_ha_client)
        
        # Verify
        assert result['valid'] is False
        assert len(result['errors']) > 0
        assert any('does not exist' in error for error in result['errors'])
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validate_automation_missing_service(
        self,
        validator: AutomationPreDeploymentValidator,
        valid_automation_yaml: str,
        mock_ha_client: AsyncMock
    ):
        """Test validation with missing service."""
        # Mock entity check - entities exist
        mock_entity_response = MagicMock()
        mock_entity_response.status_code = 200
        mock_entity_response.json = MagicMock(return_value={'state': 'on'})
        
        # Mock service check - service not available
        mock_services_response = MagicMock()
        mock_services_response.status_code = 200
        mock_services_response.json = MagicMock(return_value={
            'light': {}  # turn_on not available
        })
        
        mock_ha_client.get = AsyncMock(side_effect=[
            mock_entity_response,  # binary_sensor.motion
            mock_entity_response,   # light.kitchen
            mock_services_response  # /api/services
        ])
        
        # Execute
        result = await validator.validate_automation(valid_automation_yaml, mock_ha_client)
        
        # Verify
        assert result['valid'] is False
        assert len(result['errors']) > 0
        assert any('Service' in error and 'not available' in error for error in result['errors'])
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validate_automation_missing_required_fields(
        self,
        validator: AutomationPreDeploymentValidator,
        mock_ha_client: AsyncMock
    ):
        """Test validation with missing required fields."""
        invalid_yaml = """
alias: Test
# Missing trigger and action
"""
        
        # Execute
        result = await validator.validate_automation(invalid_yaml, mock_ha_client)
        
        # Verify
        assert result['valid'] is False
        assert any('Missing required field: trigger' in error for error in result['errors'])
        assert any('Missing required field: action' in error for error in result['errors'])
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validate_automation_empty_condition_warning(
        self,
        validator: AutomationPreDeploymentValidator,
        mock_ha_client: AsyncMock
    ):
        """Test validation with empty condition list (warning)."""
        yaml_with_empty_condition = """
alias: Test Automation
trigger:
  - platform: state
    entity_id: binary_sensor.motion
action:
  - service: light.turn_on
    entity_id: light.kitchen
condition: []
"""
        
        # Mock entity and service checks
        mock_entity_response = MagicMock()
        mock_entity_response.status_code = 200
        mock_entity_response.json = MagicMock(return_value={'state': 'on'})
        
        mock_services_response = MagicMock()
        mock_services_response.status_code = 200
        mock_services_response.json = MagicMock(return_value={'light': {'turn_on': {}}})
        
        mock_ha_client.get = AsyncMock(side_effect=[
            mock_entity_response,
            mock_entity_response,
            mock_services_response
        ])
        
        # Execute
        result = await validator.validate_automation(yaml_with_empty_condition, mock_ha_client)
        
        # Verify
        assert result['valid'] is True  # Still valid, just a warning
        assert len(result['warnings']) > 0
        assert any('Empty condition list' in warning for warning in result['warnings'])
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    def test_extract_entity_ids(
        self,
        validator: AutomationPreDeploymentValidator
    ):
        """Test entity ID extraction from automation config."""
        config = {
            'trigger': [
                {'platform': 'state', 'entity_id': 'binary_sensor.motion'}
            ],
            'action': [
                {'service': 'light.turn_on', 'entity_id': 'light.kitchen'}
            ]
        }
        
        entities = validator._extract_entity_ids(config)
        
        assert 'binary_sensor.motion' in entities
        assert 'light.kitchen' in entities
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    def test_extract_services(
        self,
        validator: AutomationPreDeploymentValidator
    ):
        """Test service extraction from automation config."""
        config = {
            'action': [
                {'service': 'light.turn_on', 'entity_id': 'light.kitchen'},
                {'service': 'scene.turn_on', 'scene': 'scene.morning'}
            ]
        }
        
        services = validator._extract_services(config)
        
        assert 'light.turn_on' in services
        assert 'scene.turn_on' in services
