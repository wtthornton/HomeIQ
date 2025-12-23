"""
Test suite for UnifiedPromptBuilder

Tests the unified prompt building system that consolidates all AI prompt generation
with device intelligence integration.
"""

from unittest.mock import AsyncMock

import pytest
from src.prompt_building.unified_prompt_builder import UnifiedPromptBuilder


class TestUnifiedPromptBuilder:
    """Test cases for UnifiedPromptBuilder"""

    @pytest.fixture
    def mock_device_intel_client(self):
        """Mock device intelligence client"""
        client = AsyncMock()
        client.get_device_details.return_value = {
            'capabilities': ['led_notifications', 'smart_bulb_mode'],
            'health_score': 85,
            'manufacturer': 'Inovelli',
            'model': 'LZW31-SN',
            'integration': 'z-wave',
            'friendly_name': 'Kitchen Switch'
        }
        return client

    @pytest.fixture
    def unified_builder(self, mock_device_intel_client):
        """Create UnifiedPromptBuilder instance"""
        return UnifiedPromptBuilder(device_intelligence_client=mock_device_intel_client)

    @pytest.fixture
    def sample_pattern(self):
        """Sample pattern for testing"""
        return {
            'type': 'time_of_day',
            'device_id': 'light.kitchen_switch',
            'hour': 7,
            'minute': 30,
            'confidence': 0.85,
            'occurrences': 25
        }

    @pytest.fixture
    def sample_entities(self):
        """Sample entities for testing"""
        return [
            {
                'entity_id': 'light.kitchen_switch',
                'friendly_name': 'Kitchen Switch',
                'domain': 'light',
                'state': 'on',
                'capabilities': ['led_notifications', 'smart_bulb_mode'],
                'health_score': 85,
                'manufacturer': 'Inovelli',
                'model': 'LZW31-SN'
            },
            {
                'entity_id': 'light.living_room',
                'friendly_name': 'Living Room Light',
                'domain': 'light',
                'state': 'off',
                'capabilities': ['color_temp', 'brightness'],
                'health_score': 92
            }
        ]

    @pytest.fixture
    def sample_opportunity(self):
        """Sample feature opportunity for testing"""
        return {
            'device_id': 'light.kitchen_switch',
            'device_name': 'Kitchen Switch',
            'feature_name': 'led_notifications',
            'feature_type': 'notification',
            'complexity': 'medium',
            'impact': 'high',
            'manufacturer': 'Inovelli',
            'model': 'LZW31-SN'
        }

    @pytest.mark.asyncio
    async def test_build_pattern_prompt_time_of_day(self, unified_builder, sample_pattern):
        """Test building time-of-day pattern prompt"""
        device_context = {
            'device_id': 'light.kitchen_switch',
            'friendly_name': 'Kitchen Switch',
            'manufacturer': 'Inovelli',
            'model': 'LZW31-SN',
            'capabilities': ['led_notifications'],
            'health_score': 85
        }

        result = await unified_builder.build_pattern_prompt(
            pattern=sample_pattern,
            device_context=device_context,
            output_mode="description"
        )

        assert "system_prompt" in result
        assert "user_prompt" in result
        assert "Kitchen Switch" in result["user_prompt"]
        assert "7:30" in result["user_prompt"]
        assert "led_notifications" in result["user_prompt"]
        assert "Health Score: 85" in result["user_prompt"]

    @pytest.mark.asyncio
    async def test_build_pattern_prompt_co_occurrence(self, unified_builder):
        """Test building co-occurrence pattern prompt"""
        pattern = {
            'type': 'co_occurrence',
            'device1': 'light.kitchen_switch',
            'device2': 'light.living_room',
            'confidence': 0.75,
            'occurrences': 15,
            'metadata': {'avg_time_delta_seconds': 5.2}
        }

        device_context = {
            'device1': {
                'name': 'Kitchen Switch',
                'domain': 'light'
            },
            'device2': {
                'name': 'Living Room Light',
                'domain': 'light'
            }
        }

        result = await unified_builder.build_pattern_prompt(
            pattern=pattern,
            device_context=device_context,
            output_mode="yaml"
        )

        assert "system_prompt" in result
        assert "user_prompt" in result
        assert "Kitchen Switch" in result["user_prompt"]
        assert "Living Room Light" in result["user_prompt"]
        assert "5 seconds" in result["user_prompt"]

    @pytest.mark.asyncio
    async def test_build_query_prompt(self, unified_builder, sample_entities):
        """Test building query prompt for Ask AI interface"""
        query = "Create a morning routine automation"

        result = await unified_builder.build_query_prompt(
            query=query,
            entities=sample_entities,
            output_mode="suggestions"
        )

        assert "system_prompt" in result
        assert "user_prompt" in result
        assert "morning routine automation" in result["user_prompt"]
        assert "Kitchen Switch" in result["user_prompt"]
        assert "led_notifications" in result["user_prompt"]
        assert "Living Room Light" in result["user_prompt"]

    @pytest.mark.asyncio
    async def test_build_feature_prompt(self, unified_builder, sample_opportunity):
        """Test building feature opportunity prompt"""
        device_context = {
            'device_id': 'light.kitchen_switch',
            'friendly_name': 'Kitchen Switch',
            'manufacturer': 'Inovelli',
            'model': 'LZW31-SN',
            'capabilities': ['led_notifications']
        }

        result = await unified_builder.build_feature_prompt(
            opportunity=sample_opportunity,
            device_context=device_context,
            output_mode="description"
        )

        assert "system_prompt" in result
        assert "user_prompt" in result
        assert "led_notifications" in result["user_prompt"]
        assert "Kitchen Switch" in result["user_prompt"]
        assert "Inovelli" in result["user_prompt"]

    @pytest.mark.asyncio
    async def test_get_enhanced_device_context(self, unified_builder, sample_pattern, mock_device_intel_client):
        """Test getting enhanced device context with device intelligence"""
        result = await unified_builder.get_enhanced_device_context(sample_pattern)

        assert result['device_id'] == 'light.kitchen_switch'
        assert 'capabilities' in result
        assert 'health_score' in result
        assert 'manufacturer' in result
        assert 'model' in result
        assert 'integration' in result
        assert 'friendly_name' in result

        # Verify device intelligence client was called
        mock_device_intel_client.get_device_details.assert_called_once_with('light.kitchen_switch')

    @pytest.mark.asyncio
    async def test_get_enhanced_device_context_no_client(self, sample_pattern):
        """Test getting device context without device intelligence client"""
        builder = UnifiedPromptBuilder(device_intelligence_client=None)
        result = await builder.get_enhanced_device_context(sample_pattern)

        assert result == {}

    @pytest.mark.asyncio
    async def test_get_enhanced_device_context_error_handling(self, sample_pattern):
        """Test error handling in device context retrieval"""
        mock_client = AsyncMock()
        mock_client.get_device_details.side_effect = Exception("Service unavailable")

        builder = UnifiedPromptBuilder(device_intelligence_client=mock_client)
        result = await builder.get_enhanced_device_context(sample_pattern)

        # Should return basic context on error
        assert result == {'device_id': 'light.kitchen_switch'}

    def test_build_device_context_section(self, unified_builder):
        """Test building device context section for prompts"""
        device_context = {
            'friendly_name': 'Kitchen Switch',
            'manufacturer': 'Inovelli',
            'model': 'LZW31-SN',
            'health_score': 85,
            'capabilities': ['led_notifications', 'smart_bulb_mode']
        }

        result = unified_builder._build_device_context_section(device_context)

        assert "Kitchen Switch" in result
        assert "Inovelli" in result
        assert "LZW31-SN" in result
        assert "Health Score: 85 (Excellent)" in result
        assert "led_notifications" in result
        assert "smart_bulb_mode" in result

    def test_build_device_context_section_minimal(self, unified_builder):
        """Test building device context section with minimal data"""
        device_context = {
            'friendly_name': 'Basic Light'
        }

        result = unified_builder._build_device_context_section(device_context)

        assert "Basic Light" in result
        assert "No device context available" not in result

    def test_build_device_context_section_none(self, unified_builder):
        """Test building device context section with None input"""
        result = unified_builder._build_device_context_section(None)

        assert "No specific device context available" in result

    def test_build_entity_context_section(self, unified_builder, sample_entities):
        """Test building entity context section for Ask AI prompts"""
        result = unified_builder._build_entity_context_section(sample_entities)

        assert "Kitchen Switch" in result
        assert "Living Room Light" in result
        assert "led_notifications" in result
        assert "smart_bulb_mode" in result
        assert "Health: 85" in result
        assert "Health: 92" in result

    def test_build_entity_context_section_empty(self, unified_builder):
        """Test building entity context section with empty entities"""
        result = unified_builder._build_entity_context_section([])

        assert "No devices detected in query" in result

    def test_build_time_of_day_prompt(self, unified_builder):
        """Test building time-of-day specific prompt"""
        pattern = {
            'time_range': '7:30 AM',
            'frequency': 'daily'
        }
        device_section = "Device: Kitchen Switch\nHealth Score: 85 (Excellent)"

        result = unified_builder._build_time_of_day_prompt(
            pattern, device_section, "description"
        )

        assert "7:30 AM" in result
        assert "daily" in result
        assert "Kitchen Switch" in result
        assert "Health Score: 85" in result
        assert "description" in result.lower()

    def test_build_co_occurrence_prompt(self, unified_builder):
        """Test building co-occurrence specific prompt"""
        pattern = {
            'entities': ['light.kitchen', 'light.living_room'],
            'confidence': 0.75
        }
        device_section = "Device: Kitchen Light\nDevice: Living Room Light"

        result = unified_builder._build_co_occurrence_prompt(
            pattern, device_section, "yaml"
        )

        assert "light.kitchen" in result
        assert "light.living_room" in result
        assert "0.75" in result
        assert "Kitchen Light" in result
        assert "yaml" in result.lower()

    def test_build_synergy_prompt(self, unified_builder):
        """Test building synergy specific prompt"""
        pattern = {
            'synergy_type': 'lighting_sequence',
            'devices': ['light.kitchen', 'light.living_room']
        }
        device_section = "Device: Kitchen Light\nDevice: Living Room Light"

        result = unified_builder._build_synergy_prompt(
            pattern, device_section, "description"
        )

        assert "lighting_sequence" in result
        assert "light.kitchen" in result
        assert "light.living_room" in result
        assert "Kitchen Light" in result
        assert "description" in result.lower()

    def test_build_generic_pattern_prompt(self, unified_builder):
        """Test building generic pattern prompt"""
        pattern = {
            'data': {'custom_field': 'test_value'}
        }
        device_section = "Device: Test Device"

        result = unified_builder._build_generic_pattern_prompt(
            pattern, device_section, "yaml"
        )

        assert "test_value" in result
        assert "Test Device" in result
        assert "yaml" in result.lower()

    def test_unified_system_prompt_consistency(self, unified_builder):
        """Test that unified system prompt is consistent across all methods"""
        # Test pattern prompt
        pattern_result = unified_builder.build_pattern_prompt({}, None, "description")
        pattern_system = pattern_result["system_prompt"]

        # Test query prompt
        query_result = unified_builder.build_query_prompt("test", [], "suggestions")
        query_system = query_result["system_prompt"]

        # Test feature prompt
        feature_result = unified_builder.build_feature_prompt({}, {}, "description")
        feature_system = feature_result["system_prompt"]

        # All should use the same unified system prompt
        assert pattern_system == query_system == feature_system
        assert "Home Assistant automation expert" in pattern_system
        assert "device capabilities" in pattern_system
        assert "device health" in pattern_system


class TestUnifiedPromptBuilderIntegration:
    """Integration tests for UnifiedPromptBuilder with real scenarios"""

    @pytest.fixture
    def real_world_pattern(self):
        """Real-world pattern example"""
        return {
            'type': 'time_of_day',
            'device_id': 'light.bedroom_lamp',
            'hour': 22,
            'minute': 0,
            'confidence': 0.92,
            'occurrences': 28,
            'pattern_type': 'time_of_day'
        }

    @pytest.fixture
    def real_world_entities(self):
        """Real-world entities example"""
        return [
            {
                'entity_id': 'light.bedroom_lamp',
                'friendly_name': 'Bedroom Lamp',
                'domain': 'light',
                'state': 'on',
                'capabilities': ['brightness', 'color_temp'],
                'health_score': 78,
                'manufacturer': 'Philips',
                'model': 'Hue White Ambiance'
            },
            {
                'entity_id': 'sensor.bedroom_motion',
                'friendly_name': 'Bedroom Motion Sensor',
                'domain': 'binary_sensor',
                'state': 'off',
                'capabilities': ['motion_detection'],
                'health_score': 95
            }
        ]

    @pytest.mark.asyncio
    async def test_real_world_pattern_processing(self, real_world_pattern):
        """Test processing real-world pattern with device intelligence"""
        mock_client = AsyncMock()
        mock_client.get_device_details.return_value = {
            'capabilities': ['brightness', 'color_temp', 'night_light_mode'],
            'health_score': 78,
            'manufacturer': 'Philips',
            'model': 'Hue White Ambiance',
            'integration': 'hue',
            'friendly_name': 'Bedroom Lamp'
        }

        builder = UnifiedPromptBuilder(device_intelligence_client=mock_client)

        # Test enhanced context retrieval
        enhanced_context = await builder.get_enhanced_device_context(real_world_pattern)
        assert enhanced_context['device_id'] == 'light.bedroom_lamp'
        assert 'night_light_mode' in enhanced_context['capabilities']
        assert enhanced_context['health_score'] == 78

        # Test pattern prompt building
        prompt_dict = await builder.build_pattern_prompt(
            pattern=real_world_pattern,
            device_context=enhanced_context,
            output_mode="description"
        )

        assert "Bedroom Lamp" in prompt_dict["user_prompt"]
        assert "22:00" in prompt_dict["user_prompt"]
        assert "night_light_mode" in prompt_dict["user_prompt"]
        assert "Health Score: 78" in prompt_dict["user_prompt"]

    @pytest.mark.asyncio
    async def test_real_world_query_processing(self, real_world_entities):
        """Test processing real-world query with multiple entities"""
        builder = UnifiedPromptBuilder(device_intelligence_client=None)

        query = "Create a bedtime routine that dims the lights and turns on the motion sensor"

        prompt_dict = await builder.build_query_prompt(
            query=query,
            entities=real_world_entities,
            output_mode="suggestions"
        )

        assert "bedtime routine" in prompt_dict["user_prompt"]
        assert "Bedroom Lamp" in prompt_dict["user_prompt"]
        assert "Bedroom Motion Sensor" in prompt_dict["user_prompt"]
        assert "brightness" in prompt_dict["user_prompt"]
        assert "motion_detection" in prompt_dict["user_prompt"]
        assert "Health: 78" in prompt_dict["user_prompt"]
        assert "Health: 95" in prompt_dict["user_prompt"]


class TestUnifiedPromptBuilderErrorHandling:
    """Test error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_pattern_with_missing_fields(self):
        """Test handling patterns with missing fields"""
        builder = UnifiedPromptBuilder(device_intelligence_client=None)

        incomplete_pattern = {
            'type': 'time_of_day',
            'device_id': 'light.test'
            # Missing hour, minute, confidence
        }

        result = await builder.build_pattern_prompt(
            pattern=incomplete_pattern,
            device_context=None,
            output_mode="description"
        )

        # Should handle gracefully
        assert "system_prompt" in result
        assert "user_prompt" in result
        assert "unknown time" in result["user_prompt"]

    @pytest.mark.asyncio
    async def test_empty_entities_list(self):
        """Test handling empty entities list"""
        builder = UnifiedPromptBuilder(device_intelligence_client=None)

        result = await builder.build_query_prompt(
            query="test query",
            entities=[],
            output_mode="suggestions"
        )

        assert "No devices detected in query" in result["user_prompt"]

    @pytest.mark.asyncio
    async def test_none_device_context(self):
        """Test handling None device context"""
        builder = UnifiedPromptBuilder(device_intelligence_client=None)

        result = await builder.build_pattern_prompt(
            pattern={'type': 'time_of_day', 'device_id': 'light.test'},
            device_context=None,
            output_mode="description"
        )

        assert "No specific device context available" in result["user_prompt"]

    def test_health_score_classification(self):
        """Test health score classification in device context"""
        builder = UnifiedPromptBuilder(device_intelligence_client=None)

        # Test excellent health score
        context_excellent = {'health_score': 85}
        result_excellent = builder._build_device_context_section(context_excellent)
        assert "Excellent" in result_excellent

        # Test good health score
        context_good = {'health_score': 70}
        result_good = builder._build_device_context_section(context_good)
        assert "Good" in result_good

        # Test fair health score
        context_fair = {'health_score': 50}
        result_fair = builder._build_device_context_section(context_fair)
        assert "Fair" in result_fair
