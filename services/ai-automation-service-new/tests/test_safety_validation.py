"""
Safety Validation Tests

Epic 39, Story 39.12: Query & Automation Service Testing
Tests for safety validation in deployment service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.deployment_service import (
    DeploymentService,
    DeploymentError,
    SafetyValidationError
)
from src.clients.ha_client import HomeAssistantClient
from src.services.yaml_generation_service import YAMLGenerationService
from src.database.models import Suggestion, AutomationVersion


@pytest.mark.unit
class TestSafetyValidation:
    """Unit tests for safety validation in deployment service."""
    
    @pytest.fixture
    def mock_ha_client(self):
        """Mock Home Assistant client."""
        client = AsyncMock(spec=HomeAssistantClient)
        client.deploy_automation = AsyncMock(return_value={
            "status": "deployed",
            "automation_id": "automation.test_123"
        })
        return client
    
    @pytest.fixture
    def mock_yaml_service(self):
        """Mock YAML generation service."""
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
        service.validate_yaml = AsyncMock(return_value=(True, None))
        service.validate_entities = AsyncMock(return_value=(True, []))
        return service
    
    @pytest.fixture
    def deployment_service(self, test_db: AsyncSession, mock_ha_client, mock_yaml_service):
        """Create deployment service instance."""
        return DeploymentService(
            db=test_db,
            ha_client=mock_ha_client,
            yaml_service=mock_yaml_service
        )
    
    @pytest.fixture
    async def approved_suggestion(self, test_db: AsyncSession):
        """Create an approved suggestion for testing."""
        suggestion = Suggestion(
            title="Test Automation",
            description="Turn on lights at 7 AM",
            status="approved",
            automation_yaml=None,
            confidence_score=0.85
        )
        test_db.add(suggestion)
        await test_db.commit()
        await test_db.refresh(suggestion)
        return suggestion
    
    @pytest.mark.asyncio
    async def test_safety_validation_passes_with_valid_entities(
        self,
        deployment_service: DeploymentService,
        approved_suggestion: Suggestion,
        mock_yaml_service
    ):
        """Test that safety validation passes when all entities are valid."""
        # Setup: Mock entity validation to return valid
        mock_yaml_service.validate_entities = AsyncMock(return_value=(True, []))
        
        # Execute
        result = await deployment_service.deploy_suggestion(approved_suggestion.id)
        
        # Assert
        assert result["success"] is True
        assert result["data"]["status"] == "deployed"
        mock_yaml_service.validate_entities.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_safety_validation_fails_with_invalid_entities(
        self,
        deployment_service: DeploymentService,
        approved_suggestion: Suggestion,
        mock_yaml_service
    ):
        """Test that safety validation fails when invalid entities are found."""
        # Setup: Mock entity validation to return invalid entities
        invalid_entities = ["light.nonexistent", "switch.invalid"]
        mock_yaml_service.validate_entities = AsyncMock(return_value=(False, invalid_entities))
        
        # Execute & Assert
        with pytest.raises(SafetyValidationError) as exc_info:
            await deployment_service.deploy_suggestion(approved_suggestion.id)
        
        assert "Invalid entities found" in str(exc_info.value)
        assert "light.nonexistent" in str(exc_info.value)
        assert "switch.invalid" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_force_deploy_skips_safety_validation(
        self,
        deployment_service: DeploymentService,
        approved_suggestion: Suggestion,
        mock_yaml_service
    ):
        """Test that force_deploy flag skips safety validation."""
        # Setup: Mock entity validation to return invalid (should be skipped)
        mock_yaml_service.validate_entities = AsyncMock(return_value=(False, ["light.invalid"]))
        
        # Execute with force_deploy=True
        result = await deployment_service.deploy_suggestion(
            approved_suggestion.id,
            force_deploy=True
        )
        
        # Assert: Deployment succeeds despite invalid entities
        assert result["success"] is True
        # Safety validation should NOT be called when force_deploy=True
        mock_yaml_service.validate_entities.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_safety_validation_with_mixed_entities(
        self,
        deployment_service: DeploymentService,
        approved_suggestion: Suggestion,
        mock_yaml_service
    ):
        """Test safety validation with mix of valid and invalid entities."""
        # Setup: Some entities valid, some invalid
        mock_yaml_service.validate_entities = AsyncMock(return_value=(
            False,
            ["light.invalid", "switch.missing"]
        ))
        
        # Execute & Assert
        with pytest.raises(SafetyValidationError) as exc_info:
            await deployment_service.deploy_suggestion(approved_suggestion.id)
        
        assert "Invalid entities found" in str(exc_info.value)
        assert "light.invalid" in str(exc_info.value)
        assert "switch.missing" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_safety_validation_with_empty_entity_list(
        self,
        deployment_service: DeploymentService,
        approved_suggestion: Suggestion,
        mock_yaml_service
    ):
        """Test safety validation when no entities are found (edge case)."""
        # Setup: Empty entity list (all valid)
        mock_yaml_service.validate_entities = AsyncMock(return_value=(True, []))
        
        # Execute
        result = await deployment_service.deploy_suggestion(approved_suggestion.id)
        
        # Assert: Should pass validation
        assert result["success"] is True
        mock_yaml_service.validate_entities.assert_called_once()


@pytest.mark.unit
class TestStatusValidation:
    """Unit tests for status validation in deployment service."""
    
    @pytest.fixture
    def mock_yaml_service(self):
        """Mock YAML generation service."""
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
        service.validate_yaml = AsyncMock(return_value=(True, None))
        service.validate_entities = AsyncMock(return_value=(True, []))
        return service
    
    @pytest.fixture
    def deployment_service(self, test_db: AsyncSession, mock_ha_client, mock_yaml_service):
        """Create deployment service instance."""
        return DeploymentService(
            db=test_db,
            ha_client=mock_ha_client,
            yaml_service=mock_yaml_service
        )
    
    @pytest.fixture
    async def draft_suggestion(self, test_db: AsyncSession):
        """Create a draft suggestion (not approved)."""
        suggestion = Suggestion(
            title="Draft Automation",
            description="Draft automation",
            status="draft",
            automation_yaml=None
        )
        test_db.add(suggestion)
        await test_db.commit()
        await test_db.refresh(suggestion)
        return suggestion
    
    @pytest.mark.asyncio
    async def test_status_validation_requires_approved_status(
        self,
        deployment_service: DeploymentService,
        draft_suggestion: Suggestion
    ):
        """Test that deployment requires 'approved' or 'deployed' status."""
        # Execute & Assert
        with pytest.raises(DeploymentError) as exc_info:
            await deployment_service.deploy_suggestion(draft_suggestion.id)
        
        assert "status must be 'approved' or 'deployed'" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_skip_validation_bypasses_status_check(
        self,
        deployment_service: DeploymentService,
        draft_suggestion: Suggestion,
        mock_yaml_service,
        mock_ha_client
    ):
        """Test that skip_validation flag bypasses status check."""
        # Setup: Mock successful deployment
        mock_yaml_service.validate_entities = AsyncMock(return_value=(True, []))
        mock_ha_client.deploy_automation = AsyncMock(return_value={
            "status": "deployed",
            "automation_id": "automation.test_123"
        })
        
        # Execute with skip_validation=True
        result = await deployment_service.deploy_suggestion(
            draft_suggestion.id,
            skip_validation=True
        )
        
        # Assert: Deployment succeeds despite draft status
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_deployed_status_allows_redeployment(
        self,
        deployment_service: DeploymentService,
        test_db: AsyncSession,
        mock_yaml_service,
        mock_ha_client
    ):
        """Test that 'deployed' status allows redeployment."""
        # Setup: Create suggestion with 'deployed' status
        suggestion = Suggestion(
            title="Already Deployed",
            description="Already deployed automation",
            status="deployed",
            automation_yaml="""id: 'existing'
alias: Existing Automation
trigger:
  - platform: time
    at: '08:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: light.office_lamp
"""
        )
        test_db.add(suggestion)
        await test_db.commit()
        await test_db.refresh(suggestion)
        
        # Setup: Mock validation and deployment
        mock_yaml_service.validate_entities = AsyncMock(return_value=(True, []))
        mock_ha_client.deploy_automation = AsyncMock(return_value={
            "status": "deployed",
            "automation_id": "automation.test_123"
        })
        
        # Execute
        result = await deployment_service.deploy_suggestion(suggestion.id)
        
        # Assert: Should succeed
        assert result["success"] is True


@pytest.mark.unit
class TestDeploymentErrorHandling:
    """Unit tests for error handling in deployment service."""
    
    @pytest.fixture
    def mock_yaml_service(self):
        """Mock YAML generation service."""
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
        service.validate_yaml = AsyncMock(return_value=(True, None))
        service.validate_entities = AsyncMock(return_value=(True, []))
        return service
    
    @pytest.fixture
    def deployment_service(self, test_db: AsyncSession, mock_ha_client, mock_yaml_service):
        """Create deployment service instance."""
        return DeploymentService(
            db=test_db,
            ha_client=mock_ha_client,
            yaml_service=mock_yaml_service
        )
    
    @pytest.mark.asyncio
    async def test_deployment_error_on_missing_suggestion(
        self,
        deployment_service: DeploymentService
    ):
        """Test that DeploymentError is raised for non-existent suggestion."""
        # Execute & Assert
        with pytest.raises(DeploymentError) as exc_info:
            await deployment_service.deploy_suggestion(99999)
        
        assert "not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_deployment_error_on_invalid_yaml(
        self,
        deployment_service: DeploymentService,
        test_db: AsyncSession,
        mock_yaml_service
    ):
        """Test that DeploymentError is raised for invalid YAML."""
        # Setup: Create approved suggestion
        suggestion = Suggestion(
            title="Test",
            description="Test automation",
            status="approved",
            automation_yaml="invalid: yaml: content: ["
        )
        test_db.add(suggestion)
        await test_db.commit()
        await test_db.refresh(suggestion)
        
        # Setup: Mock YAML validation to fail
        mock_yaml_service.validate_yaml = AsyncMock(return_value=(
            False,
            "YAML syntax error: line 1"
        ))
        
        # Execute & Assert
        with pytest.raises(DeploymentError) as exc_info:
            await deployment_service.deploy_suggestion(suggestion.id)
        
        assert "Invalid YAML" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_deployment_error_on_ha_deployment_failure(
        self,
        deployment_service: DeploymentService,
        test_db: AsyncSession,
        mock_ha_client,
        mock_yaml_service
    ):
        """Test that DeploymentError is raised when HA deployment fails."""
        # Setup: Create approved suggestion
        suggestion = Suggestion(
            title="Test",
            description="Test automation",
            status="approved",
            automation_yaml="""id: 'test'
alias: Test
trigger:
  - platform: time
    at: '07:00:00'
action:
  - service: light.turn_on
"""
        )
        test_db.add(suggestion)
        await test_db.commit()
        await test_db.refresh(suggestion)
        
        # Setup: Mock HA client to return failure
        mock_ha_client.deploy_automation = AsyncMock(return_value={
            "status": "failed",
            "error": "Connection timeout"
        })
        mock_yaml_service.validate_entities = AsyncMock(return_value=(True, []))
        
        # Execute & Assert
        with pytest.raises(DeploymentError) as exc_info:
            await deployment_service.deploy_suggestion(suggestion.id)
        
        assert "Deployment failed" in str(exc_info.value)

