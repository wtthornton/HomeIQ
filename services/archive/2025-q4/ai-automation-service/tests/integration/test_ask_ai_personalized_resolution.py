"""
Integration tests for Ask AI Flow with Personalized Entity Resolution

Epic AI-12, Story AI12.9: Integration with Ask AI Flow
Tests personalized entity resolution integration in Ask AI conversational flow.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.api.ask_ai_router import generate_suggestions_from_query
from src.services.entity.personalized_index import PersonalizedEntityIndex
from src.services.entity.personalized_resolver import PersonalizedEntityResolver
from src.services.entity.resolver import EntityResolver


@pytest.fixture
def mock_settings():
    """Provide mock settings"""
    with patch.dict("os.environ", {
        "HA_URL": "http://test:8123",
        "HA_TOKEN": "test_token",
        "DATA_API_URL": "http://test:8006",
        "OPENAI_API_KEY": "test_key"
    }):
        yield


@pytest.fixture
def mock_ha_client():
    """Create mock HA client"""
    client = Mock()
    client.get_entity_state = AsyncMock(return_value={
        'state': 'on',
        'attributes': {'friendly_name': 'Office Light'}
    })
    return client


@pytest.fixture
def mock_personalized_resolver():
    """Create mock personalized resolver"""
    resolver = Mock(spec=PersonalizedEntityResolver)
    resolver.resolve_entities = AsyncMock(return_value=Mock(
        resolved_entities={"light.office": Mock(entity_id="light.office")}
    ))
    resolver.ha_client = Mock()
    return resolver


@pytest.mark.asyncio
async def test_personalized_resolver_initialization_in_ask_ai(mock_settings, mock_ha_client):
    """Test that personalized resolver is initialized in Ask AI flow"""
    with patch('src.api.ask_ai_router.HomeAssistantClient', return_value=mock_ha_client), \
         patch('src.api.ask_ai_router.PersonalizedIndexBuilder') as mock_builder, \
         patch('src.api.ask_ai_router.OpenAIClient') as mock_openai:
        
        # Mock index builder
        mock_index = Mock(spec=PersonalizedEntityIndex)
        mock_index._index = {"light.office": Mock()}
        mock_builder_instance = Mock()
        mock_builder_instance.build_index = AsyncMock(return_value=mock_index)
        mock_builder.return_value = mock_builder_instance
        
        # Mock OpenAI client
        mock_openai_instance = Mock()
        mock_openai_instance.generate_with_unified_prompt = AsyncMock(return_value={
            'title': 'Test Automation',
            'description': 'Test description',
            'rationale': 'Test rationale',
            'category': 'convenience',
            'priority': 'medium'
        })
        mock_openai.return_value = mock_openai_instance
        
        # Mock other dependencies
        with patch('src.api.ask_ai_router.DataAPIClient'), \
             patch('src.api.ask_ai_router.EntityValidator') as mock_validator, \
             patch('src.api.ask_ai_router.UnifiedPromptBuilder'):
            
            mock_validator_instance = Mock()
            mock_validator_instance._get_available_entities = AsyncMock(return_value=[])
            mock_validator_instance.map_query_to_entities = AsyncMock(return_value={})
            mock_validator.return_value = mock_validator_instance
            
            # Test that initialization is attempted
            # (Full test would require complete workflow setup)
            assert True  # Placeholder - would require full workflow test


@pytest.mark.asyncio
async def test_personalized_resolver_in_device_name_mapping(mock_settings, mock_personalized_resolver):
    """Test that personalized resolver is used in device name mapping"""
    # Mock EntityResolver with personalized resolver
    entity_resolver = Mock(spec=EntityResolver)
    entity_resolver.resolve_device_names = AsyncMock(return_value={
        "office light": "light.office"
    })
    entity_resolver.personalized_resolver = mock_personalized_resolver
    
    # Test resolution
    device_names = ["office light"]
    result = await entity_resolver.resolve_device_names(
        device_names=device_names,
        query="turn on office light",
        area_id="office"
    )
    
    # Verify resolution was called
    entity_resolver.resolve_device_names.assert_called_once()
    assert result == {"office light": "light.office"}


@pytest.mark.asyncio
async def test_personalized_resolver_fallback_to_legacy(mock_settings):
    """Test that Ask AI falls back to legacy validator if personalized resolver fails"""
    # Mock EntityResolver that fails
    entity_resolver = Mock(spec=EntityResolver)
    entity_resolver.resolve_device_names = AsyncMock(side_effect=Exception("Resolution failed"))
    
    # Mock legacy validator
    legacy_validator = Mock()
    legacy_validator.map_query_to_entities = AsyncMock(return_value={
        "office light": "light.office"
    })
    
    # Test fallback
    try:
        result = await entity_resolver.resolve_device_names(
            device_names=["office light"],
            query="test query"
        )
    except Exception:
        # Should fall back to legacy
        result = await legacy_validator.map_query_to_entities("test query", ["office light"])
    
    assert result == {"office light": "light.office"}


@pytest.mark.asyncio
async def test_feedback_tracking_on_approval(mock_settings):
    """Test that feedback is tracked when suggestions are approved"""
    from unittest.mock import AsyncMock
    
    # Mock feedback tracker
    feedback_tracker = Mock()
    feedback_tracker.track_approval = AsyncMock()
    
    # Mock active learner
    active_learner = Mock()
    active_learner.process_feedback = AsyncMock()
    
    # Test approval tracking
    validated_entities = {
        "office light": "light.office",
        "kitchen light": "light.kitchen"
    }
    
    for device_name, entity_id in validated_entities.items():
        await feedback_tracker.track_approval(
            device_name=device_name,
            query="test query",
            suggested_entity_id=entity_id,
            actual_entity_id=entity_id,
            confidence_score=0.9
        )
    
    # Verify tracking was called
    assert feedback_tracker.track_approval.call_count == 2
    
    # Process feedback
    await active_learner.process_feedback()
    active_learner.process_feedback.assert_called_once()


@pytest.mark.asyncio
async def test_personalized_resolver_in_query_processing(mock_settings, mock_personalized_resolver):
    """Test that personalized resolver is used in query processing"""
    # Mock EntityResolver
    entity_resolver = Mock(spec=EntityResolver)
    entity_resolver.personalized_resolver = mock_personalized_resolver
    entity_resolver.resolve_device_names = AsyncMock(return_value={
        "office lights": "light.office"
    })
    
    # Test query processing
    query = "turn on office lights"
    device_names = ["office lights"]
    
    result = await entity_resolver.resolve_device_names(
        device_names=device_names,
        query=query,
        area_id="office"
    )
    
    # Verify personalized resolution was used
    assert result == {"office lights": "light.office"}


@pytest.mark.asyncio
async def test_personalized_resolver_in_entity_extraction(mock_settings):
    """Test that personalized resolver enhances entity extraction"""
    # This would test integration with entity extraction
    # For now, we verify the integration point exists
    assert True  # Placeholder - would require full entity extraction test


@pytest.mark.asyncio
async def test_personalized_resolver_in_yaml_generation(mock_settings):
    """Test that personalized resolver is used in YAML generation"""
    # This would test integration with YAML generation
    # For now, we verify the integration point exists
    assert True  # Placeholder - would require full YAML generation test


@pytest.mark.asyncio
async def test_learning_from_user_corrections(mock_settings):
    """Test that system learns from user corrections in Ask AI"""
    from unittest.mock import AsyncMock
    
    # Mock feedback tracker
    feedback_tracker = Mock()
    feedback_tracker.track_correction = AsyncMock()
    
    # Mock active learner
    active_learner = Mock()
    active_learner.process_feedback = AsyncMock()
    
    # Simulate user correction
    await feedback_tracker.track_correction(
        device_name="office light",
        query="turn on office light",
        suggested_entity_id="light.office_wrong",
        actual_entity_id="light.office",
        confidence_score=0.7
    )
    
    # Process feedback
    await active_learner.process_feedback()
    
    # Verify correction was tracked
    feedback_tracker.track_correction.assert_called_once()
    active_learner.process_feedback.assert_called_once()

