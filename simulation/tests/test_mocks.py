"""
Unit tests for Mock Service Implementations

Tests for all 8 mock services to ensure they maintain correct interfaces.
"""

import pytest
import pandas as pd
from datetime import datetime, timezone, timedelta

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mocks.influxdb_client import MockInfluxDBClient
from mocks.openai_client import MockOpenAIClient
from mocks.mqtt_client import MockMQTTClient
from mocks.data_api_client import MockDataAPIClient
from mocks.device_intelligence_client import MockDeviceIntelligenceClient
from mocks.ha_conversation_api import MockHAConversationAPI
from mocks.ha_client import MockHAClient
from mocks.safety_validator import MockSafetyValidator


class TestMockInfluxDBClient:
    """Tests for MockInfluxDBClient."""

    @pytest.mark.asyncio
    async def test_fetch_events_empty(self):
        """Test fetching events from empty storage."""
        client = MockInfluxDBClient()
        df = await client.fetch_events()
        assert df.empty

    @pytest.mark.asyncio
    async def test_load_and_fetch_events(self):
        """Test loading and fetching events."""
        client = MockInfluxDBClient()
        
        # Create test events
        events = pd.DataFrame({
            '_time': [datetime.now(timezone.utc) - timedelta(hours=i) for i in range(5)],
            'entity_id': ['light.office'] * 5,
            'state': ['on', 'off', 'on', 'off', 'on'],
            'domain': ['light'] * 5,
            'device_id': ['light.office'] * 5
        })
        
        client.load_events(events)
        df = await client.fetch_events(limit=10)
        
        assert len(df) == 5
        assert 'entity_id' in df.columns

    @pytest.mark.asyncio
    async def test_fetch_entity_attributes(self):
        """Test fetching entity attributes."""
        client = MockInfluxDBClient()
        
        # Create events with attributes
        events = pd.DataFrame({
            '_time': [datetime.now(timezone.utc)],
            'entity_id': ['light.office'],
            'attr_brightness': [255],
            'attr_color_temp': [None]
        })
        
        client.load_events(events)
        usage = await client.fetch_entity_attributes('light.office', ['brightness', 'color_temp'])
        
        assert usage['brightness'] is True
        assert usage['color_temp'] is False


class TestMockOpenAIClient:
    """Tests for MockOpenAIClient."""

    @pytest.mark.asyncio
    async def test_generate_yaml(self):
        """Test YAML generation."""
        client = MockOpenAIClient()
        
        prompt_dict = {
            "system_prompt": "You are an automation expert",
            "user_prompt": "Create automation for light.office"
        }
        
        result = await client.generate_with_unified_prompt(
            prompt_dict,
            output_format="yaml"
        )
        
        assert "automation_yaml" in result
        assert "alias" in result
        assert "light.office" in result["automation_yaml"]

    @pytest.mark.asyncio
    async def test_generate_description(self):
        """Test description generation."""
        client = MockOpenAIClient()
        
        prompt_dict = {
            "user_prompt": "Create automation for device"
        }
        
        result = await client.generate_with_unified_prompt(
            prompt_dict,
            output_format="description"
        )
        
        assert "title" in result
        assert "description" in result

    @pytest.mark.asyncio
    async def test_token_tracking(self):
        """Test token usage tracking."""
        client = MockOpenAIClient()
        
        prompt_dict = {"user_prompt": "test"}
        await client.generate_with_unified_prompt(prompt_dict)
        
        assert client.total_tokens_used > 0
        assert client.last_usage is not None


class TestMockMQTTClient:
    """Tests for MockMQTTClient."""

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Test connection and disconnection."""
        client = MockMQTTClient()
        
        assert not client.is_connected
        await client.connect()
        assert client.is_connected
        
        await client.disconnect()
        assert not client.is_connected

    @pytest.mark.asyncio
    async def test_publish(self):
        """Test message publishing (no-op)."""
        client = MockMQTTClient()
        await client.connect()
        
        # Should not raise
        await client.publish("test/topic", "test payload")


class TestMockDataAPIClient:
    """Tests for MockDataAPIClient."""

    @pytest.mark.asyncio
    async def test_fetch_events(self):
        """Test fetching events."""
        client = MockDataAPIClient()
        
        # Create test events
        events = pd.DataFrame({
            'timestamp': [datetime.now(timezone.utc) - timedelta(hours=i) for i in range(3)],
            'entity_id': ['light.office'] * 3,
            'device_id': ['light.office'] * 3
        })
        
        client.load_events(events)
        df = await client.fetch_events(limit=10)
        
        assert len(df) == 3


class TestMockDeviceIntelligenceClient:
    """Tests for MockDeviceIntelligenceClient."""

    @pytest.mark.asyncio
    async def test_register_and_get_device(self):
        """Test device registration and retrieval."""
        client = MockDeviceIntelligenceClient()
        
        device_data = {
            'device_id': 'light.office',
            'name': 'Office Light',
            'area_id': 'office'
        }
        
        client.register_device('light.office', device_data)
        device = await client.get_device_details('light.office')
        
        assert device is not None
        assert device['device_id'] == 'light.office'

    @pytest.mark.asyncio
    async def test_get_devices_by_area(self):
        """Test getting devices by area."""
        client = MockDeviceIntelligenceClient()
        
        client.register_device('light.office', {'area_id': 'office'})
        devices = await client.get_devices_by_area('office')
        
        assert len(devices) == 1


class TestMockHAConversationAPI:
    """Tests for MockHAConversationAPI."""

    @pytest.mark.asyncio
    async def test_extract_entities(self):
        """Test entity extraction."""
        client = MockHAConversationAPI()
        
        result = await client.process("Turn on the office lights")
        
        assert "entities" in result
        assert len(result["entities"]) > 0


class TestMockHAClient:
    """Tests for MockHAClient."""

    @pytest.mark.asyncio
    async def test_get_entity_state(self):
        """Test getting entity state."""
        client = MockHAClient()
        
        client.register_entity('light.office', {
            'entity_id': 'light.office',
            'state': 'on',
            'attributes': {}
        })
        
        state = await client.get_entity_state('light.office')
        assert state is not None
        assert state['state'] == 'on'

    @pytest.mark.asyncio
    async def test_validate_automation(self):
        """Test automation validation."""
        client = MockHAClient()
        
        yaml_content = """
alias: Test Automation
trigger:
  - platform: time
    at: "07:00:00"
action:
  - service: light.turn_on
"""
        
        result = await client.validate_automation(yaml_content)
        assert result["valid"] is True


class TestMockSafetyValidator:
    """Tests for MockSafetyValidator."""

    @pytest.mark.asyncio
    async def test_validate_safe_automation(self):
        """Test validation of safe automation."""
        validator = MockSafetyValidator()
        
        yaml_content = """
alias: Safe Automation
trigger:
  - platform: time
    at: "07:00:00"
action:
  - service: light.turn_on
"""
        
        result = await validator.validate(yaml_content)
        assert result["passed"] is True
        assert result["safety_score"] == 1.0

    @pytest.mark.asyncio
    async def test_validate_invalid_yaml(self):
        """Test validation of invalid YAML."""
        validator = MockSafetyValidator()
        
        result = await validator.validate("invalid: yaml: content: [")
        assert result["passed"] is False
        assert result["safety_score"] == 0.0

