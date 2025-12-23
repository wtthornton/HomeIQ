"""
Integration tests for Core Services

Epic 39, Story 39.10: Automation Service Foundation
Tests the core business logic services with mocked external dependencies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.suggestion_service import SuggestionService
from src.services.yaml_generation_service import YAMLGenerationService
from src.services.deployment_service import DeploymentService
from src.clients.data_api_client import DataAPIClient
from src.clients.openai_client import OpenAIClient
from src.clients.ha_client import HomeAssistantClient
from src.database.models import Suggestion, AutomationVersion


@pytest.mark.integration
class TestSuggestionService:
    """Integration tests for SuggestionService."""
    
    @pytest.fixture
    def mock_data_api_client(self):
        """Mock DataAPIClient."""
        client = AsyncMock(spec=DataAPIClient)
        client.fetch_events = AsyncMock(return_value=[
            {
                "entity_id": "light.office_lamp",
                "state": "on",
                "last_changed": "2025-12-22T07:00:00Z"
            }
        ])
        client.fetch_devices = AsyncMock(return_value=[])
        client.fetch_entities = AsyncMock(return_value=[])
        return client
    
    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAIClient."""
        client = AsyncMock(spec=OpenAIClient)
        client.generate_yaml = AsyncMock(return_value="""id: 'test-123'
alias: Test Automation
trigger:
  - platform: time
    at: '07:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: light.office_lamp
""")
        return client
    
    @pytest.fixture
    def suggestion_service(self, test_db: AsyncSession, mock_data_api_client, mock_openai_client):
        """Create SuggestionService instance."""
        return SuggestionService(
            db=test_db,
            data_api_client=mock_data_api_client,
            openai_client=mock_openai_client
        )
    
    @pytest.mark.asyncio
    async def test_generate_suggestions(self, suggestion_service: SuggestionService):
        """Test generating suggestions from events."""
        result = await suggestion_service.generate_suggestions(
            pattern_ids=None,
            days=30,
            limit=10
        )
        
        assert result is not None
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_list_suggestions(self, suggestion_service: SuggestionService, test_db: AsyncSession):
        """Test listing suggestions with pagination."""
        # Create test suggestions
        suggestion1 = Suggestion(
            title="Test 1",
            description="Description 1",
            status="draft",
            confidence_score=0.8
        )
        suggestion2 = Suggestion(
            title="Test 2",
            description="Description 2",
            status="approved",
            confidence_score=0.9
        )
        test_db.add(suggestion1)
        test_db.add(suggestion2)
        await test_db.commit()
        
        # List all suggestions
        result = await suggestion_service.list_suggestions(limit=10, offset=0)
        
        assert result is not None
        assert "suggestions" in result
        assert "total" in result
        assert len(result["suggestions"]) >= 2
    
    @pytest.mark.asyncio
    async def test_get_suggestion(self, suggestion_service: SuggestionService, test_db: AsyncSession):
        """Test getting a single suggestion."""
        # Create test suggestion
        suggestion = Suggestion(
            title="Test Suggestion",
            description="Test description",
            status="draft",
            confidence_score=0.85
        )
        test_db.add(suggestion)
        await test_db.commit()
        await test_db.refresh(suggestion)
        
        # Get suggestion
        result = await suggestion_service.get_suggestion(suggestion.id)
        
        assert result is not None
        assert result["id"] == suggestion.id
        assert result["title"] == "Test Suggestion"
    
    @pytest.mark.asyncio
    async def test_update_suggestion_status(self, suggestion_service: SuggestionService, test_db: AsyncSession):
        """Test updating suggestion status."""
        # Create test suggestion
        suggestion = Suggestion(
            title="Test Suggestion",
            description="Test description",
            status="draft",
            confidence_score=0.85
        )
        test_db.add(suggestion)
        await test_db.commit()
        await test_db.refresh(suggestion)
        
        # Update status
        result = await suggestion_service.update_suggestion_status(
            suggestion.id,
            "approved"
        )
        
        assert result is True
        
        # Verify status was updated
        updated = await suggestion_service.get_suggestion(suggestion.id)
        assert updated["status"] == "approved"
    
    @pytest.mark.asyncio
    async def test_get_usage_stats(self, suggestion_service: SuggestionService, test_db: AsyncSession):
        """Test getting usage statistics."""
        # Create test suggestions with different statuses
        for status in ["draft", "approved", "deployed"]:
            suggestion = Suggestion(
                title=f"Test {status}",
                description="Test",
                status=status,
                confidence_score=0.8
            )
            test_db.add(suggestion)
        await test_db.commit()
        
        # Get stats
        stats = await suggestion_service.get_usage_stats()
        
        assert stats is not None
        assert "total" in stats
        assert "by_status" in stats


@pytest.mark.integration
class TestYAMLGenerationService:
    """Integration tests for YAMLGenerationService."""
    
    @pytest.fixture
    def mock_data_api_client(self):
        """Mock DataAPIClient."""
        client = AsyncMock(spec=DataAPIClient)
        client.fetch_entities = AsyncMock(return_value=[
            {"entity_id": "light.office_lamp", "state": "on"}
        ])
        return client
    
    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAIClient."""
        client = AsyncMock(spec=OpenAIClient)
        client.generate_yaml = AsyncMock(return_value="""id: 'test-123'
alias: Test Automation
trigger:
  - platform: time
    at: '07:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: light.office_lamp
""")
        return client
    
    @pytest.fixture
    def yaml_service(self, mock_data_api_client, mock_openai_client):
        """Create YAMLGenerationService instance."""
        return YAMLGenerationService(
            data_api_client=mock_data_api_client,
            openai_client=mock_openai_client
        )
    
    @pytest.mark.asyncio
    async def test_generate_yaml_from_suggestion(self, yaml_service: YAMLGenerationService):
        """Test generating YAML from suggestion."""
        suggestion_data = {
            "title": "Turn on lights at 7 AM",
            "description": "Automatically turn on office lights at 7 AM",
            "device_id": "light.office_lamp"
        }
        
        result = await yaml_service.generate_automation_yaml(suggestion_data)
        
        assert result is not None
        assert isinstance(result, str)
        assert "test-123" in result or "id:" in result
    
    @pytest.mark.asyncio
    async def test_validate_yaml(self, yaml_service: YAMLGenerationService):
        """Test YAML validation."""
        valid_yaml = """id: 'test-123'
alias: Test Automation
trigger:
  - platform: time
    at: '07:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: light.office_lamp
"""
        
        is_valid, error = await yaml_service.validate_yaml(valid_yaml)
        
        assert is_valid is True
        assert error is None
    
    @pytest.mark.asyncio
    async def test_validate_invalid_yaml(self, yaml_service: YAMLGenerationService):
        """Test invalid YAML validation."""
        invalid_yaml = """id: 'test-123'
alias: Test Automation
trigger:
  - platform: time
    at: '07:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: light.office_lamp
    invalid_key: [unclosed bracket
"""
        
        is_valid, error = await yaml_service.validate_yaml(invalid_yaml)
        
        assert is_valid is False
        assert error is not None


@pytest.mark.integration
class TestDeploymentService:
    """Integration tests for DeploymentService."""
    
    @pytest.fixture
    def mock_ha_client(self):
        """Mock HomeAssistantClient."""
        client = AsyncMock(spec=HomeAssistantClient)
        async def mock_deploy_automation(yaml_content):
            return {
                "automation_id": "automation.test_automation_123",
                "status": "deployed",
                "data": {}
            }
        client.deploy_automation = AsyncMock(side_effect=mock_deploy_automation)
        client.list_automations = AsyncMock(return_value=[
            {
                "id": "automation.test_automation_123",
                "alias": "Test Automation",
                "state": "on"
            }
        ])
        client.get_automation = AsyncMock(return_value={
            "id": "automation.test_automation_123",
            "alias": "Test Automation",
            "state": "on"
        })
        client.enable_automation = AsyncMock(return_value=True)
        client.disable_automation = AsyncMock(return_value=True)
        return client
    
    @pytest.fixture
    def mock_yaml_service(self):
        """Mock YAMLGenerationService."""
        service = AsyncMock(spec=YAMLGenerationService)
        service.generate_automation_yaml = AsyncMock(return_value="""id: 'test-123'
alias: Test Automation
trigger:
  - platform: time
    at: '07:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: light.office_lamp
""")
        async def mock_validate_yaml(yaml_content):
            return (True, None)
        async def mock_validate_entities(yaml_content):
            return (True, [])
        service.validate_yaml = AsyncMock(side_effect=mock_validate_yaml)
        service.validate_entities = AsyncMock(side_effect=mock_validate_entities)
        return service
    
    @pytest.fixture
    def deployment_service(self, test_db: AsyncSession, mock_ha_client, mock_yaml_service):
        """Create DeploymentService instance."""
        return DeploymentService(
            db=test_db,
            ha_client=mock_ha_client,
            yaml_service=mock_yaml_service
        )
    
    @pytest.mark.asyncio
    async def test_deploy_suggestion(self, deployment_service: DeploymentService, test_db: AsyncSession):
        """Test deploying a suggestion."""
        # Create test suggestion
        suggestion = Suggestion(
            title="Test Automation",
            description="Test description",
            status="approved",
            confidence_score=0.85,
            automation_yaml="""id: 'test-123'
alias: Test Automation
trigger:
  - platform: time
    at: '07:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: light.office_lamp
"""
        )
        test_db.add(suggestion)
        await test_db.commit()
        await test_db.refresh(suggestion)
        
        # Deploy suggestion
        result = await deployment_service.deploy_suggestion(
            suggestion.id,
            skip_validation=False
        )
        
        assert result is not None
        assert "success" in result
        assert result["success"] is True
        assert "data" in result
        assert "automation_id" in result["data"]
        assert result["data"]["status"] == "deployed"
    
    @pytest.mark.asyncio
    async def test_list_deployed_automations(self, deployment_service: DeploymentService):
        """Test listing deployed automations."""
        result = await deployment_service.list_deployed_automations()
        
        assert result is not None
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_get_automation_status(self, deployment_service: DeploymentService):
        """Test getting automation status."""
        result = await deployment_service.get_automation_status("automation.test_automation_123")
        
        assert result is not None
        assert "id" in result or "automation_id" in result
        assert "state" in result or "status" in result
    
    @pytest.mark.asyncio
    async def test_rollback_automation(self, deployment_service: DeploymentService, test_db: AsyncSession):
        """Test rolling back an automation."""
        # Create a suggestion first
        suggestion = Suggestion(
            title="Test Suggestion",
            description="Test",
            status="approved"
        )
        test_db.add(suggestion)
        await test_db.commit()
        await test_db.refresh(suggestion)
        
        # Create at least 2 versions for rollback (need previous version)
        version1 = AutomationVersion(
            suggestion_id=suggestion.id,
            automation_id="automation.test_123",
            version_number=1,
            automation_yaml="""id: 'test-123'
alias: Test Automation v1
trigger:
  - platform: time
    at: '07:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: light.office_lamp
""",
            safety_score=0.9
        )
        version2 = AutomationVersion(
            suggestion_id=suggestion.id,
            automation_id="automation.test_123",
            version_number=2,
            automation_yaml="""id: 'test-123'
alias: Test Automation v2
trigger:
  - platform: time
    at: '08:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: light.office_lamp
""",
            safety_score=0.95
        )
        test_db.add(version1)
        test_db.add(version2)
        await test_db.commit()
        
        # Rollback
        result = await deployment_service.rollback_automation("automation.test_123")
        
        assert result is not None
        assert "success" in result
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_get_automation_versions(self, deployment_service: DeploymentService, test_db: AsyncSession):
        """Test getting automation version history."""
        # Create a suggestion first
        suggestion = Suggestion(
            title="Test Suggestion",
            description="Test",
            status="approved"
        )
        test_db.add(suggestion)
        await test_db.commit()
        await test_db.refresh(suggestion)
        
        # Create test versions
        for i in range(3):
            version = AutomationVersion(
                suggestion_id=suggestion.id,
                automation_id="automation.test_123",
                version_number=i + 1,
                automation_yaml=f"version {i}",
                safety_score=0.9
            )
            test_db.add(version)
        await test_db.commit()
        
        # Get versions
        result = await deployment_service.get_automation_versions("automation.test_123")
        
        assert result is not None
        assert isinstance(result, list)
        assert len(result) >= 3

