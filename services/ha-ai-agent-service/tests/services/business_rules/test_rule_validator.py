"""
Tests for rule_validator.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.business_rules.rule_validator import BusinessRuleValidator
from src.services.entity_resolution.entity_resolution_service import EntityResolutionService


@pytest.fixture
def mock_entity_resolution_service():
    """Mock entity resolution service"""
    service = MagicMock(spec=EntityResolutionService)
    service.resolve_entities = AsyncMock(return_value=MagicMock(
        success=True,
        matched_entities=["light.office"],
        matched_areas=["office"]
    ))
    return service


class TestBusinessRuleValidator:
    """Test BusinessRuleValidator class."""

    def test___init__(self, mock_entity_resolution_service):
        """Test __init__ method."""
        validator = BusinessRuleValidator(mock_entity_resolution_service)
        assert validator.entity_resolution_service == mock_entity_resolution_service

    def test_validate_effect_names_exact_match(self):
        """Test validate_effect_names with exact match."""
        validator = BusinessRuleValidator()
        
        available = ["Rainbow", "Fire", "Ocean", "Sunset"]
        is_valid, error, suggestions = validator.validate_effect_names("Rainbow", available)
        
        assert is_valid is True
        assert error is None
        assert len(suggestions) == 0

    def test_validate_effect_names_case_sensitive(self):
        """Test validate_effect_names is case-sensitive."""
        validator = BusinessRuleValidator()
        
        available = ["Rainbow", "Fire", "Ocean"]
        is_valid, error, suggestions = validator.validate_effect_names("rainbow", available)
        
        assert is_valid is False
        assert error is not None
        assert len(suggestions) > 0

    def test_validate_effect_names_not_found(self):
        """Test validate_effect_names when effect not found."""
        validator = BusinessRuleValidator()
        
        available = ["Rainbow", "Fire", "Ocean", "Sunset", "Aurora"]
        is_valid, error, suggestions = validator.validate_effect_names("Unknown", available)
        
        assert is_valid is False
        assert error is not None
        assert len(suggestions) <= 5

    def test_validate_context_completeness_complete(self):
        """Test validate_context_completeness with complete context."""
        validator = BusinessRuleValidator()
        
        required_entities = ["light.office"]
        context_entities = [
            {"entity_id": "light.office", "friendly_name": "Office Light"}
        ]
        
        is_complete, missing = validator.validate_context_completeness(
            user_prompt="turn on office light",
            required_entities=required_entities,
            context_entities=context_entities
        )
        assert is_complete is True
        assert len(missing) == 0

    def test_validate_context_completeness_incomplete(self):
        """Test validate_context_completeness with incomplete context."""
        validator = BusinessRuleValidator()
        
        required_entities = ["light.office", "light.kitchen"]
        context_entities = [
            {"entity_id": "light.office", "friendly_name": "Office Light"}
            # Missing light.kitchen
        ]
        
        is_complete, missing = validator.validate_context_completeness(
            user_prompt="turn on office and kitchen lights",
            required_entities=required_entities,
            context_entities=context_entities
        )
        assert is_complete is False
        assert len(missing) > 0

    def test_check_safety_requirements_security_domain(self):
        """Test check_safety_requirements with security domain."""
        validator = BusinessRuleValidator()
        
        entities = ["lock.front_door"]
        services = ["lock.lock"]
        automation_dict = {"alias": "test"}
        
        is_safe, warnings = validator.check_safety_requirements(
            entities=entities,
            services=services,
            automation_dict=automation_dict
        )
        
        # Security domains should generate warnings
        assert len(warnings) > 0

    def test_check_safety_requirements_critical_service(self):
        """Test check_safety_requirements with critical service."""
        validator = BusinessRuleValidator()
        
        entities = ["lock.front_door"]
        services = ["lock.lock"]  # Critical service
        automation_dict = {"alias": "test"}
        
        is_safe, warnings = validator.check_safety_requirements(
            entities=entities,
            services=services,
            automation_dict=automation_dict
        )
        
        # Critical services should generate warnings
        assert len(warnings) > 0

    @pytest.mark.asyncio
    async def test_validate_entity_resolution(self, mock_entity_resolution_service):
        """Test validate_entity_resolution method."""
        validator = BusinessRuleValidator(mock_entity_resolution_service)
        
        result = await validator.validate_entity_resolution(
            "turn on office lights",
            target_domain="light"
        )
        
        assert result.success is True
        assert len(result.matched_entities) > 0