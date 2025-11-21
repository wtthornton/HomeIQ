"""
Tests for Template Engine (Home Assistant Pattern Improvement #2 - 2025)
"""


from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.clients.ha_client import HomeAssistantClient
from src.template_engine import StateProxy, TemplateEngine, TimeProxy


@pytest.fixture
def mock_ha_client():
    """Mock Home Assistant client"""
    client = MagicMock(spec=HomeAssistantClient)
    client.get_states = AsyncMock(return_value=[
        {
            "entity_id": "sensor.temperature",
            "state": "22.5",
            "attributes": {"unit_of_measurement": "°C"},
        },
        {
            "entity_id": "light.office",
            "state": "on",
            "attributes": {"brightness": 255},
        },
        {
            "entity_id": "sensor.temp_threshold",
            "state": "20.0",
            "attributes": {},
        },
    ])
    return client


@pytest.fixture
def template_engine(mock_ha_client):
    """Create template engine with mocked HA client"""
    return TemplateEngine(mock_ha_client)


class TestStateProxy:
    """Test StateProxy for state access"""

    @pytest.mark.asyncio
    async def test_state_callable(self, mock_ha_client):
        """Test states('entity_id') callable interface"""
        proxy = StateProxy(mock_ha_client)
        state = await proxy("sensor.temperature")
        assert state == "22.5"

    @pytest.mark.asyncio
    async def test_state_caching(self, mock_ha_client):
        """Test that states are cached"""
        proxy = StateProxy(mock_ha_client)

        # First call
        await proxy("sensor.temperature")

        # Second call should use cache (same timestamp)
        await proxy("sensor.temperature")

        # Should only call get_states once (cached for 5 seconds)
        assert mock_ha_client.get_states.call_count == 1

    @pytest.mark.asyncio
    async def test_state_not_found(self, mock_ha_client):
        """Test state for non-existent entity"""
        proxy = StateProxy(mock_ha_client)
        state = await proxy("sensor.nonexistent")
        assert state == "unknown"


class TestTimeProxy:
    """Test TimeProxy for time access"""

    def test_now(self):
        """Test now() method"""
        proxy = TimeProxy()
        now = proxy.now()
        assert isinstance(now, datetime)

    def test_utcnow(self):
        """Test utcnow() method"""
        proxy = TimeProxy()
        utcnow = proxy.utcnow()
        assert isinstance(utcnow, datetime)


class TestTemplateEngine:
    """Test TemplateEngine functionality"""

    @pytest.mark.asyncio
    async def test_simple_template(self, template_engine):
        """Test simple template rendering"""
        template_str = "Temperature is {{ states('sensor.temperature') }}"
        result = await template_engine.render(template_str)
        assert result == "Temperature is 22.5"

    @pytest.mark.asyncio
    async def test_template_with_filter(self, template_engine):
        """Test template with Jinja2 filter"""
        template_str = "{{ states('sensor.temperature') | float + 2 }}"
        result = await template_engine.render(template_str)
        assert float(result) == 24.5

    @pytest.mark.asyncio
    async def test_template_with_context(self, template_engine):
        """Test template with additional context"""
        template_str = "Value: {{ value }}"
        result = await template_engine.render(template_str, {"value": 42})
        assert result == "Value: 42"

    @pytest.mark.asyncio
    async def test_template_with_time(self, template_engine):
        """Test template with time object"""
        template_str = "Current time: {{ now.strftime('%Y-%m-%d') }}"
        result = await template_engine.render(template_str)
        assert datetime.now().strftime("%Y-%m-%d") in result

    @pytest.mark.asyncio
    async def test_template_undefined_variable(self, template_engine):
        """Test template with undefined variable raises error"""
        template_str = "Value: {{ undefined_var }}"
        with pytest.raises(Exception):  # Jinja2 StrictUndefined will raise
            await template_engine.render(template_str)

    @pytest.mark.asyncio
    async def test_render_automation(self, template_engine):
        """Test rendering automation YAML with templates"""
        automation_yaml = """
triggers:
  - trigger: state
    entity_id: sensor.temperature
    above: "{{ states('sensor.temp_threshold') | float }}"
actions:
  - action: climate.set_temperature
    data:
      temperature: "{{ states('sensor.temperature') | float + 2 }}"
"""
        result = await template_engine.render_automation(automation_yaml)

        # Check that templates were evaluated (should have "20.0" for threshold and "24.5" for temp+2)
        assert "20.0" in result  # Threshold template was evaluated
        assert "24.5" in result  # Temperature + 2 template was evaluated
        assert "above" in result.lower()

    @pytest.mark.asyncio
    async def test_validate_template_valid(self, template_engine):
        """Test validating a valid template"""
        template_str = "Temperature: {{ states('sensor.temperature') }}"
        is_valid, error = await template_engine.validate_template(template_str)
        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_template_invalid(self, template_engine):
        """Test validating an invalid template"""
        template_str = "Temperature: {{ states('sensor.temperature' }}"  # Missing closing paren
        is_valid, error = await template_engine.validate_template(template_str)
        assert is_valid is False
        assert error is not None

    @pytest.mark.asyncio
    async def test_get_available_filters(self, template_engine):
        """Test getting available filters"""
        filters = template_engine.get_available_filters()
        assert "float" in filters
        assert "int" in filters
        assert "round" in filters

    @pytest.mark.asyncio
    async def test_get_available_objects(self, template_engine):
        """Test getting available template objects"""
        objects = template_engine.get_available_objects()
        assert "states" in objects
        assert "time" in objects
        assert "now" in objects
        assert "utcnow" in objects

    @pytest.mark.asyncio
    async def test_complex_template(self, template_engine):
        """Test complex template with multiple states"""
        template_str = """
{% if states('light.office') == 'on' %}
Office light is on with brightness {{ states('light.office') }}
{% else %}
Office light is off
{% endif %}
"""
        result = await template_engine.render(template_str)
        assert "on" in result.lower() or "off" in result.lower()

    @pytest.mark.asyncio
    async def test_template_error_handling(self, template_engine):
        """Test template error handling"""
        # Invalid Jinja2 syntax
        template_str = "{% if %} invalid {% endif %}"
        with pytest.raises(Exception):
            await template_engine.render(template_str)

