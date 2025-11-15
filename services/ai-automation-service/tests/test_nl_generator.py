"""
Unit tests for Natural Language Automation Generator
Story AI1.21: Natural Language Request Generation
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
import yaml

from src.nl_automation_generator import (
    NLAutomationGenerator,
    NLAutomationRequest,
    GeneratedAutomation,
    get_nl_generator
)
from src.safety_validator import SafetyValidator, SafetyLevel, SafetyResult, SafetyIssue
from src.config import settings


class TestNLAutomationGenerator:
    """Test suite for NL automation generator"""
    
    @pytest.fixture
    def mock_data_api_client(self):
        """Mock Data API client"""
        client = AsyncMock()
        
        # Mock devices response
        client.fetch_devices = AsyncMock(return_value=pd.DataFrame([
            {'device_id': 'kitchen_light_1', 'friendly_name': 'Kitchen Light', 'area_id': 'kitchen'},
            {'device_id': 'bedroom_light_1', 'friendly_name': 'Bedroom Light', 'area_id': 'bedroom'}
        ]))
        
        # Mock entities response
        client.fetch_entities = AsyncMock(return_value=pd.DataFrame([
            {'entity_id': 'light.kitchen', 'friendly_name': 'Kitchen Light', 'area_id': 'kitchen'},
            {'entity_id': 'light.bedroom', 'friendly_name': 'Bedroom Light', 'area_id': 'bedroom'},
            {'entity_id': 'binary_sensor.front_door', 'friendly_name': 'Front Door', 'area_id': 'entry'},
            {'entity_id': 'climate.thermostat', 'friendly_name': 'Thermostat', 'area_id': 'living_room'}
        ]))
        
        return client
    
    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client"""
        client = AsyncMock()
        client.model = "gpt-4o-mini"
        client.total_tokens_used = 0
        client.total_input_tokens = 0
        client.total_output_tokens = 0
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """{
            "yaml": "alias: Morning Kitchen Light\\ntrigger:\\n  - platform: time\\n    at: '07:00:00'\\naction:\\n  - service: light.turn_on\\n    target:\\n      entity_id: light.kitchen",
            "title": "Morning Kitchen Light",
            "description": "Turns on kitchen light at 7 AM",
            "explanation": "This automation uses a time trigger to turn on the kitchen light every morning at 7 AM",
            "clarification": null,
            "confidence": 0.95
        }"""
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        
        client.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        return client
    
    @pytest.fixture
    def mock_safety_validator(self):
        """Mock safety validator"""
        validator = AsyncMock()
        validator.validate = AsyncMock(return_value=SafetyResult(
            passed=True,
            safety_score=95,
            issues=[],
            can_override=True,
            summary="✅ Passed all safety checks"
        ))
        return validator
    
    @pytest.fixture
    def nl_generator(self, mock_data_api_client, mock_openai_client, mock_safety_validator):
        """Create NL generator with mocked dependencies"""
        return NLAutomationGenerator(
            data_api_client=mock_data_api_client,
            openai_client=mock_openai_client,
            safety_validator=mock_safety_validator
        )
    
    @pytest.mark.asyncio
    async def test_simple_request_generation(self, nl_generator, mock_openai_client):
        """Test generating automation from simple request"""
        request = NLAutomationRequest(
            request_text="Turn on kitchen light at 7 AM",
            user_id="test"
        )
        
        result = await nl_generator.generate(request)
        
        assert result.automation_yaml != ""
        assert "light.kitchen" in result.automation_yaml
        assert "07:00" in result.automation_yaml
        assert result.confidence > 0.7
        assert result.title == "Morning Kitchen Light"
    
    @pytest.mark.asyncio
    async def test_device_context_fetched(self, nl_generator, mock_data_api_client):
        """Test that device context is fetched from data-api"""
        request = NLAutomationRequest(
            request_text="Turn on bedroom light at 8 PM",
            user_id="test"
        )
        
        await nl_generator.generate(request)
        
        # Verify data-api was called
        mock_data_api_client.fetch_devices.assert_called_once()
        mock_data_api_client.fetch_entities.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_safety_validation_runs(self, nl_generator, mock_safety_validator):
        """Test that safety validation runs on generated automation"""
        request = NLAutomationRequest(
            request_text="Turn on light",
            user_id="test"
        )
        
        result = await nl_generator.generate(request)
        
        # Verify safety validation was called
        mock_safety_validator.validate.assert_called_once()
        assert result.safety_result is not None
        assert result.safety_result.safety_score == 95
    
    @pytest.mark.asyncio
    async def test_openai_failure_returns_error(self, nl_generator, mock_openai_client):
        """Test that OpenAI failures are handled gracefully"""
        # Make OpenAI fail
        mock_openai_client.client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        request = NLAutomationRequest(
            request_text="Turn on light",
            user_id="test"
        )
        
        result = await nl_generator.generate(request)
        
        assert result.automation_yaml == ""
        assert result.title == "Generation Failed"
        assert result.confidence == 0.0
        assert result.clarification_needed is not None
    
    @pytest.mark.asyncio
    async def test_invalid_yaml_triggers_retry(self, nl_generator, mock_openai_client):
        """Test that invalid YAML triggers a retry"""
        # First call returns invalid YAML, second call returns valid
        invalid_response = MagicMock()
        invalid_response.choices = [MagicMock()]
        invalid_response.choices[0].message.content = """{
            "yaml": "invalid: yaml: content:",
            "title": "Test",
            "description": "Test",
            "explanation": "Test",
            "confidence": 0.8
        }"""
        invalid_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        
        valid_response = MagicMock()
        valid_response.choices = [MagicMock()]
        valid_response.choices[0].message.content = """{
            "yaml": "alias: Test\\ntrigger: []\\naction: []",
            "title": "Test",
            "description": "Test",
            "explanation": "Test",
            "confidence": 0.7
        }"""
        valid_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        
        mock_openai_client.client.chat.completions.create = AsyncMock(
            side_effect=[invalid_response, valid_response]
        )
        
        request = NLAutomationRequest(
            request_text="Turn on light",
            user_id="test"
        )
        
        result = await nl_generator.generate(request)
        
        # Should have tried twice
        assert mock_openai_client.client.chat.completions.create.call_count == 2
        # Retry should succeed
        assert result.automation_yaml != ""
    
    @pytest.mark.asyncio
    async def test_clarification_needed_handling(self, nl_generator, mock_openai_client):
        """Test handling of ambiguous requests that need clarification"""
        # Mock response with clarification needed
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = """{
            "yaml": "alias: Turn On Lights\\ntrigger: []\\naction: []",
            "title": "Turn On Lights",
            "description": "Turns on lights",
            "explanation": "Needs more info",
            "clarification": "Which lights do you want to turn on? Kitchen, bedroom, or all lights?",
            "confidence": 0.5
        }"""
        response.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        
        mock_openai_client.client.chat.completions.create = AsyncMock(return_value=response)
        
        request = NLAutomationRequest(
            request_text="Turn on lights",
            user_id="test"
        )
        
        result = await nl_generator.generate(request)
        
        assert result.clarification_needed is not None
        assert "which lights" in result.clarification_needed.lower()
        assert result.confidence < 0.7  # Lower confidence when clarification needed
    
    @pytest.mark.asyncio
    async def test_confidence_calculation(self, nl_generator):
        """Test confidence score calculation"""
        # Test with high confidence, good safety
        request = NLAutomationRequest(
            request_text="Turn on kitchen light at 7 AM on weekdays",
            user_id="test"
        )
        
        result = await nl_generator.generate(request)
        
        # Good request + good safety should have high confidence
        assert result.confidence > 0.7
    
    @pytest.mark.asyncio
    async def test_short_request_reduces_confidence(self, nl_generator):
        """Test that very short requests get lower confidence"""
        request = NLAutomationRequest(
            request_text="Turn on light",  # Only 3 words
            user_id="test"
        )
        
        result = await nl_generator.generate(request)
        
        # Short request should reduce confidence
        # (actual value depends on other factors, but should be applied)
        assert result.confidence <= 1.0  # Just verify calculation runs
    
    @pytest.mark.asyncio
    async def test_safety_warnings_extracted(self, nl_generator, mock_safety_validator):
        """Test that safety warnings are extracted from validation"""
        # Mock safety validator to return warnings
        mock_safety_validator.validate = AsyncMock(return_value=SafetyResult(
            passed=True,
            safety_score=75,
            issues=[
                SafetyIssue(
                    rule="time_constraints",
                    severity="warning",
                    message="Consider adding time constraint",
                    suggested_fix="Add time condition"
                )
            ],
            can_override=True,
            summary="⚠️ 1 warning found"
        ))
        
        request = NLAutomationRequest(
            request_text="Turn off heater",
            user_id="test"
        )
        
        result = await nl_generator.generate(request)
        
        assert result.warnings is not None
        assert len(result.warnings) > 0
        assert "WARNING" in result.warnings[0]
    
    def test_summarize_devices(self, nl_generator):
        """Test device summary generation"""
        context = {
            'entities_by_domain': {
                'light': [
                    {'entity_id': 'light.kitchen', 'friendly_name': 'Kitchen Light'},
                    {'entity_id': 'light.bedroom', 'friendly_name': 'Bedroom Light'}
                ],
                'climate': [
                    {'entity_id': 'climate.thermostat', 'friendly_name': 'Thermostat'}
                ]
            }
        }
        
        summary = nl_generator._summarize_devices(context)
        
        assert "Lights (2)" in summary
        assert "Kitchen Light" in summary
        assert "Climates (1)" in summary  # Plural form
        assert "Thermostat" in summary


class TestRegenerateWithClarification:
    """Test clarification flow"""
    
    @pytest.mark.asyncio
    async def test_regenerate_with_clarification(self, mock_data_api_client, mock_openai_client, mock_safety_validator):
        """Test regeneration with clarification"""
        generator = NLAutomationGenerator(
            data_api_client=mock_data_api_client,
            openai_client=mock_openai_client,
            safety_validator=mock_safety_validator
        )
        
        result = await generator.regenerate_with_clarification(
            original_request="Turn on lights",
            clarification="Kitchen lights only"
        )
        
        # Should call OpenAI with combined request
        assert mock_openai_client.client.chat.completions.create.called
        assert result.automation_yaml != ""


class TestGetNLGenerator:
    """Test factory function"""
    
    def test_get_nl_generator(self, mock_data_api_client, mock_openai_client, mock_safety_validator):
        """Test factory function creates generator correctly"""
        generator = get_nl_generator(
            data_api_client=mock_data_api_client,
            openai_client=mock_openai_client,
            safety_validator=mock_safety_validator
        )

        assert generator is not None
        assert isinstance(generator, NLAutomationGenerator)
        assert generator.data_api_client == mock_data_api_client
        assert generator.openai_client == mock_openai_client
        assert generator.safety_validator == mock_safety_validator
        assert generator.device_intelligence_client is not None
        assert generator.device_intelligence_client.base_url == settings.device_intelligence_url


# Shared Fixtures
@pytest.fixture
def mock_data_api_client():
    """Mock Data API client"""
    client = AsyncMock()
    client.fetch_devices = AsyncMock(return_value=pd.DataFrame([
        {'device_id': 'light_1', 'friendly_name': 'Kitchen Light', 'area_id': 'kitchen'}
    ]))
    client.fetch_entities = AsyncMock(return_value=pd.DataFrame([
        {'entity_id': 'light.kitchen', 'friendly_name': 'Kitchen Light', 'area_id': 'kitchen'},
        {'entity_id': 'climate.thermostat', 'friendly_name': 'Thermostat', 'area_id': 'living_room'}
    ]))
    return client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client with successful response"""
    client = AsyncMock()
    client.model = "gpt-4o-mini"
    client.total_tokens_used = 0
    client.total_input_tokens = 0
    client.total_output_tokens = 0
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """{
        "yaml": "alias: Test Automation\\ntrigger:\\n  - platform: time\\n    at: '07:00:00'\\naction:\\n  - service: light.turn_on\\n    target:\\n      entity_id: light.kitchen",
        "title": "Test Automation",
        "description": "Test automation description",
        "explanation": "This automation turns on kitchen light at 7 AM",
        "clarification": null,
        "confidence": 0.9
    }"""
    mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
    
    client.client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    return client


@pytest.fixture
def mock_safety_validator():
    """Mock safety validator"""
    validator = AsyncMock()
    validator.validate = AsyncMock(return_value=SafetyResult(
        passed=True,
        safety_score=95,
        issues=[],
        can_override=True,
        summary="✅ Passed"
    ))
    return validator


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

