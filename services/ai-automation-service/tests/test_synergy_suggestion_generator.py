"""
Unit tests for Synergy Suggestion Generator

Story AI3.4: Synergy-Based Suggestion Generation
Epic AI-3: Cross-Device Synergy & Contextual Opportunities
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from src.synergy_detection.synergy_suggestion_generator import SynergySuggestionGenerator


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_client():
    """Mock OpenAI client"""
    client = MagicMock()
    
    # Mock client.client.chat.completions.create (nested structure)
    completion_api = AsyncMock()
    
    async def mock_create(**kwargs):
        # Create mock response
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message = MagicMock()
        response.choices[0].message.content = """
```yaml
alias: "AI Suggested: Motion-Activated Bedroom Lighting"
description: "Automatically turn on bedroom light when motion detected"
trigger:
  - platform: state
    entity_id: binary_sensor.bedroom_motion
    to: 'on'
action:
  - service: light.turn_on
    target:
      entity_id: light.bedroom_ceiling
```

RATIONALE: You have Bedroom Motion and Bedroom Light in the same room with no automation connecting them. This automation adds convenience by automatically turning on the light when you enter the room.
CATEGORY: convenience
PRIORITY: medium
"""
        
        # Mock usage
        response.usage = MagicMock()
        response.usage.prompt_tokens = 200
        response.usage.completion_tokens = 150
        response.usage.total_tokens = 350
        
        return response
    
    completion_api.create = mock_create
    
    # Set up nested structure
    chat_api = MagicMock()
    chat_api.completions = completion_api
    client.client = MagicMock()
    client.client.chat = chat_api
    
    # Mock attributes
    client.model = "gpt-4o-mini"
    client.total_tokens_used = 0
    client.total_input_tokens = 0
    client.total_output_tokens = 0
    
    return client


@pytest.fixture
def sample_device_pair_synergy():
    """Sample device pair synergy"""
    return {
        'synergy_id': 'test-synergy-123',
        'synergy_type': 'device_pair',
        'trigger_entity': 'binary_sensor.bedroom_motion',
        'action_entity': 'light.bedroom_ceiling',
        'area': 'bedroom',
        'relationship': 'motion_to_light',
        'impact_score': 0.85,
        'complexity': 'low',
        'confidence': 0.90,
        'devices': ['binary_sensor.bedroom_motion', 'light.bedroom_ceiling'],
        'opportunity_metadata': {
            'trigger_name': 'Bedroom Motion',
            'action_name': 'Bedroom Light',
            'trigger_entity': 'binary_sensor.bedroom_motion',
            'action_entity': 'light.bedroom_ceiling',
            'relationship': 'motion_to_light',
            'rationale': 'Motion sensor and light in bedroom with no automation'
        }
    }


@pytest.fixture
def sample_synergies(sample_device_pair_synergy):
    """List of sample synergies for batch testing"""
    return [
        sample_device_pair_synergy,
        {
            'synergy_id': 'test-synergy-456',
            'synergy_type': 'device_pair',
            'trigger_entity': 'binary_sensor.front_door',
            'action_entity': 'lock.front_door',
            'area': 'entry',
            'relationship': 'door_to_lock',
            'impact_score': 0.95,
            'complexity': 'medium',
            'confidence': 0.88,
            'devices': ['binary_sensor.front_door', 'lock.front_door'],
            'opportunity_metadata': {
                'trigger_name': 'Front Door',
                'action_name': 'Front Door Lock',
                'trigger_entity': 'binary_sensor.front_door',
                'action_entity': 'lock.front_door',
                'relationship': 'door_to_lock'
            }
        }
    ]


# ============================================================================
# Suggestion Generation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_generate_suggestions_basic(mock_llm_client, sample_synergies):
    """Test basic suggestion generation"""
    generator = SynergySuggestionGenerator(mock_llm_client)
    
    suggestions = await generator.generate_suggestions(sample_synergies)
    
    assert len(suggestions) > 0
    assert len(suggestions) <= len(sample_synergies)


@pytest.mark.asyncio
async def test_suggestion_structure(mock_llm_client, sample_device_pair_synergy):
    """Test that generated suggestion has correct structure"""
    generator = SynergySuggestionGenerator(mock_llm_client)
    
    suggestions = await generator.generate_suggestions([sample_device_pair_synergy])
    
    assert len(suggestions) == 1
    suggestion = suggestions[0]
    
    # Check required fields
    assert 'type' in suggestion
    assert 'synergy_id' in suggestion
    assert 'title' in suggestion
    assert 'description' in suggestion
    assert 'automation_yaml' in suggestion
    assert 'rationale' in suggestion
    assert 'category' in suggestion
    assert 'priority' in suggestion
    assert 'confidence' in suggestion
    assert 'complexity' in suggestion
    
    # Check field types and values
    assert suggestion['type'] == 'synergy_device_pair'
    assert suggestion['synergy_id'] == 'test-synergy-123'
    assert suggestion['category'] in ['energy', 'comfort', 'security', 'convenience']
    assert suggestion['priority'] in ['high', 'medium', 'low']


@pytest.mark.asyncio
async def test_max_suggestions_limit(mock_llm_client):
    """Test that max_suggestions limit is respected"""
    # Create 20 synergies
    synergies = [
        {
            'synergy_id': f'synergy-{i}',
            'synergy_type': 'device_pair',
            'trigger_entity': f'sensor.{i}',
            'action_entity': f'light.{i}',
            'area': 'test',
            'relationship': 'motion_to_light',
            'impact_score': 0.8,
            'complexity': 'low',
            'confidence': 0.9,
            'devices': [f'sensor.{i}', f'light.{i}'],
            'opportunity_metadata': {}
        }
        for i in range(20)
    ]
    
    generator = SynergySuggestionGenerator(mock_llm_client)
    
    suggestions = await generator.generate_suggestions(synergies, max_suggestions=5)
    
    # Should only generate 5
    assert len(suggestions) <= 5


@pytest.mark.asyncio
async def test_empty_synergies_handling(mock_llm_client):
    """Test handling of empty synergies list"""
    generator = SynergySuggestionGenerator(mock_llm_client)
    
    suggestions = await generator.generate_suggestions([])
    
    assert suggestions == []


# ============================================================================
# Prompt Building Tests
# ============================================================================

@pytest.mark.asyncio
async def test_device_pair_prompt_building(sample_device_pair_synergy):
    """Test device pair prompt generation"""
    generator = SynergySuggestionGenerator(MagicMock())
    
    prompt = generator._build_device_pair_prompt(sample_device_pair_synergy)
    
    # Check prompt contains key information
    assert 'Bedroom Motion' in prompt or 'bedroom_motion' in prompt
    assert 'Bedroom Light' in prompt or 'bedroom_ceiling' in prompt
    assert 'bedroom' in prompt.lower()
    assert 'motion' in prompt.lower()


def test_unknown_synergy_type_handling():
    """Test handling of unknown synergy type"""
    generator = SynergySuggestionGenerator(MagicMock())
    
    invalid_synergy = {
        'synergy_type': 'unknown_type',
        'synergy_id': 'test'
    }
    
    # Should raise ValueError
    with pytest.raises(ValueError):
        generator._build_prompt(invalid_synergy)


# ============================================================================
# Response Parsing Tests
# ============================================================================

def test_parse_response_complete():
    """Test parsing complete OpenAI response"""
    generator = SynergySuggestionGenerator(MagicMock())
    
    response_content = """
```yaml
alias: "AI Suggested: Test Automation"
description: "Test description"
trigger:
  - platform: state
    entity_id: test.sensor
action:
  - service: test.action
```

RATIONALE: This is a test rationale
CATEGORY: convenience
PRIORITY: medium
"""
    
    synergy = {
        'synergy_id': 'test-123',
        'synergy_type': 'device_pair',
        'confidence': 0.85,
        'complexity': 'low',
        'impact_score': 0.7,
        'devices': ['test.sensor', 'test.action']
    }
    
    suggestion = generator._parse_response(response_content, synergy)
    
    assert suggestion['title'] == "AI Suggested: Test Automation"
    assert suggestion['description'] == "Test description"
    assert 'alias:' in suggestion['automation_yaml']
    assert suggestion['rationale'] == "This is a test rationale"
    assert suggestion['category'] == 'convenience'
    assert suggestion['priority'] == 'medium'


def test_parse_response_missing_fields():
    """Test parsing response with missing fields (graceful degradation)"""
    generator = SynergySuggestionGenerator(MagicMock())
    
    response_content = """
```yaml
alias: "Test Automation"
description: "Test description"
```

No rationale or category provided
"""
    
    synergy = {
        'synergy_id': 'test-123',
        'synergy_type': 'device_pair',
        'relationship': 'test_relationship',
        'confidence': 0.85,
        'complexity': 'low',
        'impact_score': 0.7,
        'devices': [],
        'rationale': 'Fallback rationale'
    }
    
    suggestion = generator._parse_response(response_content, synergy)
    
    # Should extract title from alias
    assert suggestion['title'] == "Test Automation"
    assert suggestion['description'] == "Test description"
    assert suggestion['category'] == 'convenience'  # Default
    assert suggestion['priority'] == 'medium'  # Default


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_token_usage_tracking(mock_llm_client, sample_device_pair_synergy):
    """Test that token usage is tracked"""
    generator = SynergySuggestionGenerator(mock_llm_client)
    
    initial_tokens = mock_llm_client.total_tokens_used
    
    await generator.generate_suggestions([sample_device_pair_synergy])
    
    # Token usage should increase
    assert mock_llm_client.total_tokens_used > initial_tokens


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_llm_failure_graceful_handling():
    """Test graceful handling when LLM fails"""
    mock_client = MagicMock()
    
    # Mock client that raises exception
    completion_api = AsyncMock()
    completion_api.create = AsyncMock(side_effect=Exception("OpenAI API error"))
    
    chat_api = MagicMock()
    chat_api.completions = completion_api
    mock_client.client = MagicMock()
    mock_client.client.chat = chat_api
    mock_client.model = "gpt-4o-mini"
    
    generator = SynergySuggestionGenerator(mock_client)
    
    synergy = {
        'synergy_id': 'test',
        'synergy_type': 'device_pair',
        'impact_score': 0.7,  # Required for sorting
        'opportunity_metadata': {}
    }
    
    # Should continue and log error, not return suggestions
    suggestions = await generator.generate_suggestions([synergy])
    
    # Empty list because generation failed
    assert suggestions == []


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

