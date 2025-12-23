"""
Tests for Condition Evaluator (Home Assistant Pattern Improvement #3 - 2025)
"""


from unittest.mock import AsyncMock, MagicMock

import pytest
from src.clients.ha_client import HomeAssistantClient
from src.condition_evaluator import ConditionEvaluator
from src.template_engine import TemplateEngine


@pytest.fixture
def mock_ha_client():
    """Mock Home Assistant client"""
    client = MagicMock(spec=HomeAssistantClient)
    client.get_states = AsyncMock(return_value=[
        {
            'entity_id': 'sensor.temperature',
            'state': '22.5',
            'attributes': {'unit_of_measurement': '°C'}
        },
        {
            'entity_id': 'light.office',
            'state': 'on',
            'attributes': {'brightness': 255}
        },
        {
            'entity_id': 'light.kitchen',
            'state': 'off',
            'attributes': {}
        },
        {
            'entity_id': 'sensor.motion',
            'state': 'on',
            'attributes': {}
        },
        {
            'entity_id': 'person.home',
            'state': 'home',
            'attributes': {'zone': 'home'}
        }
    ])
    return client


@pytest.fixture
def condition_evaluator(mock_ha_client):
    """Create condition evaluator with mocked HA client"""
    template_engine = TemplateEngine(mock_ha_client)
    return ConditionEvaluator(mock_ha_client, template_engine)


class TestStateCondition:
    """Test state condition evaluation"""

    @pytest.mark.asyncio
    async def test_state_condition_true(self, condition_evaluator):
        """Test state condition that evaluates to True"""
        condition = {
            'condition': 'state',
            'entity_id': 'light.office',
            'state': 'on'
        }
        result = await condition_evaluator.evaluate(condition)
        assert result is True

    @pytest.mark.asyncio
    async def test_state_condition_false(self, condition_evaluator):
        """Test state condition that evaluates to False"""
        condition = {
            'condition': 'state',
            'entity_id': 'light.office',
            'state': 'off'
        }
        result = await condition_evaluator.evaluate(condition)
        assert result is False

    @pytest.mark.asyncio
    async def test_state_condition_list(self, condition_evaluator):
        """Test state condition with list of acceptable states"""
        condition = {
            'condition': 'state',
            'entity_id': 'light.office',
            'state': ['on', 'off']
        }
        result = await condition_evaluator.evaluate(condition)
        assert result is True  # Office is 'on', which is in the list

    @pytest.mark.asyncio
    async def test_state_condition_missing_entity(self, condition_evaluator):
        """Test state condition with non-existent entity"""
        condition = {
            'condition': 'state',
            'entity_id': 'sensor.nonexistent',
            'state': 'on'
        }
        result = await condition_evaluator.evaluate(condition)
        assert result is False


class TestNumericStateCondition:
    """Test numeric state condition evaluation"""

    @pytest.mark.asyncio
    async def test_numeric_state_above(self, condition_evaluator):
        """Test numeric state condition with 'above' threshold"""
        condition = {
            'condition': 'numeric_state',
            'entity_id': 'sensor.temperature',
            'above': 20.0
        }
        result = await condition_evaluator.evaluate(condition)
        assert result is True  # 22.5 > 20.0

    @pytest.mark.asyncio
    async def test_numeric_state_below(self, condition_evaluator):
        """Test numeric state condition with 'below' threshold"""
        condition = {
            'condition': 'numeric_state',
            'entity_id': 'sensor.temperature',
            'below': 25.0
        }
        result = await condition_evaluator.evaluate(condition)
        assert result is True  # 22.5 < 25.0

    @pytest.mark.asyncio
    async def test_numeric_state_range(self, condition_evaluator):
        """Test numeric state condition with both above and below"""
        condition = {
            'condition': 'numeric_state',
            'entity_id': 'sensor.temperature',
            'above': 20.0,
            'below': 25.0
        }
        result = await condition_evaluator.evaluate(condition)
        assert result is True  # 22.5 is between 20.0 and 25.0

    @pytest.mark.asyncio
    async def test_numeric_state_out_of_range(self, condition_evaluator):
        """Test numeric state condition outside range"""
        condition = {
            'condition': 'numeric_state',
            'entity_id': 'sensor.temperature',
            'above': 30.0
        }
        result = await condition_evaluator.evaluate(condition)
        assert result is False  # 22.5 is not > 30.0


class TestAndCondition:
    """Test AND condition logic"""

    @pytest.mark.asyncio
    async def test_and_condition_all_true(self, condition_evaluator):
        """Test AND condition where all sub-conditions are True"""
        condition = {
            'condition': 'and',
            'conditions': [
                {
                    'condition': 'state',
                    'entity_id': 'light.office',
                    'state': 'on'
                },
                {
                    'condition': 'numeric_state',
                    'entity_id': 'sensor.temperature',
                    'above': 20.0
                }
            ]
        }
        result = await condition_evaluator.evaluate(condition)
        assert result is True

    @pytest.mark.asyncio
    async def test_and_condition_one_false(self, condition_evaluator):
        """Test AND condition where one sub-condition is False"""
        condition = {
            'condition': 'and',
            'conditions': [
                {
                    'condition': 'state',
                    'entity_id': 'light.office',
                    'state': 'on'
                },
                {
                    'condition': 'state',
                    'entity_id': 'light.kitchen',
                    'state': 'on'
                }
            ]
        }
        result = await condition_evaluator.evaluate(condition)
        assert result is False  # Kitchen light is off

    @pytest.mark.asyncio
    async def test_and_condition_empty(self, condition_evaluator):
        """Test AND condition with no sub-conditions (should be True)"""
        condition = {
            'condition': 'and',
            'conditions': []
        }
        result = await condition_evaluator.evaluate(condition)
        assert result is True  # Empty AND is True


class TestOrCondition:
    """Test OR condition logic"""

    @pytest.mark.asyncio
    async def test_or_condition_one_true(self, condition_evaluator):
        """Test OR condition where one sub-condition is True"""
        condition = {
            'condition': 'or',
            'conditions': [
                {
                    'condition': 'state',
                    'entity_id': 'light.office',
                    'state': 'on'
                },
                {
                    'condition': 'state',
                    'entity_id': 'light.kitchen',
                    'state': 'on'
                }
            ]
        }
        result = await condition_evaluator.evaluate(condition)
        assert result is True  # Office light is on

    @pytest.mark.asyncio
    async def test_or_condition_all_false(self, condition_evaluator):
        """Test OR condition where all sub-conditions are False"""
        condition = {
            'condition': 'or',
            'conditions': [
                {
                    'condition': 'state',
                    'entity_id': 'light.kitchen',
                    'state': 'on'
                },
                {
                    'condition': 'numeric_state',
                    'entity_id': 'sensor.temperature',
                    'above': 30.0
                }
            ]
        }
        result = await condition_evaluator.evaluate(condition)
        assert result is False

    @pytest.mark.asyncio
    async def test_or_condition_empty(self, condition_evaluator):
        """Test OR condition with no sub-conditions (should be False)"""
        condition = {
            'condition': 'or',
            'conditions': []
        }
        result = await condition_evaluator.evaluate(condition)
        assert result is False  # Empty OR is False


class TestNotCondition:
    """Test NOT condition logic"""

    @pytest.mark.asyncio
    async def test_not_condition_true(self, condition_evaluator):
        """Test NOT condition that evaluates to True"""
        condition = {
            'condition': 'not',
            'conditions': [
                {
                    'condition': 'state',
                    'entity_id': 'light.kitchen',
                    'state': 'on'
                }
            ]
        }
        result = await condition_evaluator.evaluate(condition)
        assert result is True  # Kitchen is off, so NOT(on) is True

    @pytest.mark.asyncio
    async def test_not_condition_false(self, condition_evaluator):
        """Test NOT condition that evaluates to False"""
        condition = {
            'condition': 'not',
            'conditions': [
                {
                    'condition': 'state',
                    'entity_id': 'light.office',
                    'state': 'on'
                }
            ]
        }
        result = await condition_evaluator.evaluate(condition)
        assert result is False  # Office is on, so NOT(on) is False


class TestNestedConditions:
    """Test nested condition logic"""

    @pytest.mark.asyncio
    async def test_nested_and_or(self, condition_evaluator):
        """Test nested AND/OR conditions"""
        condition = {
            'condition': 'and',
            'conditions': [
                {
                    'condition': 'state',
                    'entity_id': 'light.office',
                    'state': 'on'
                },
                {
                    'condition': 'or',
                    'conditions': [
                        {
                            'condition': 'state',
                            'entity_id': 'light.kitchen',
                            'state': 'on'
                        },
                        {
                            'condition': 'numeric_state',
                            'entity_id': 'sensor.temperature',
                            'above': 20.0
                        }
                    ]
                }
            ]
        }
        result = await condition_evaluator.evaluate(condition)
        assert result is True  # Office is on AND (kitchen is off OR temp > 20)

    @pytest.mark.asyncio
    async def test_nested_not_and(self, condition_evaluator):
        """Test nested NOT and AND"""
        condition = {
            'condition': 'not',
            'conditions': [
                {
                    'condition': 'and',
                    'conditions': [
                        {
                            'condition': 'state',
                            'entity_id': 'light.office',
                            'state': 'off'
                        },
                        {
                            'condition': 'state',
                            'entity_id': 'light.kitchen',
                            'state': 'off'
                        }
                    ]
                }
            ]
        }
        result = await condition_evaluator.evaluate(condition)
        assert result is True  # NOT (office off AND kitchen off) = True since office is on


class TestListConditions:
    """Test list of conditions (defaults to AND)"""

    @pytest.mark.asyncio
    async def test_list_conditions_all_true(self, condition_evaluator):
        """Test list of conditions where all are True"""
        conditions = [
            {
                'condition': 'state',
                'entity_id': 'light.office',
                'state': 'on'
            },
            {
                'condition': 'numeric_state',
                'entity_id': 'sensor.temperature',
                'above': 20.0
            }
        ]
        result = await condition_evaluator.evaluate(conditions)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_conditions_one_false(self, condition_evaluator):
        """Test list of conditions where one is False"""
        conditions = [
            {
                'condition': 'state',
                'entity_id': 'light.office',
                'state': 'on'
            },
            {
                'condition': 'state',
                'entity_id': 'light.kitchen',
                'state': 'on'
            }
        ]
        result = await condition_evaluator.evaluate(conditions)
        assert result is False  # Kitchen is off


class TestTimeCondition:
    """Test time-based conditions"""

    @pytest.mark.asyncio
    async def test_time_condition_after(self, condition_evaluator):
        """Test time condition with 'after' parameter"""
        condition = {
            'condition': 'time',
            'after': '06:00:00'
        }
        result = await condition_evaluator.evaluate(condition)
        # Result depends on current time, but should not raise error
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_time_condition_before(self, condition_evaluator):
        """Test time condition with 'before' parameter"""
        condition = {
            'condition': 'time',
            'before': '23:59:59'
        }
        result = await condition_evaluator.evaluate(condition)
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_time_condition_weekday(self, condition_evaluator):
        """Test time condition with weekday"""
        condition = {
            'condition': 'time',
            'weekday': ['mon', 'tue', 'wed', 'thu', 'fri']
        }
        result = await condition_evaluator.evaluate(condition)
        assert isinstance(result, bool)


class TestTemplateCondition:
    """Test template-based conditions"""

    @pytest.mark.asyncio
    async def test_template_condition(self, condition_evaluator):
        """Test template condition evaluation"""
        condition = {
            'condition': 'template',
            'value_template': "{{ states('sensor.temperature') | float > 20 }}"
        }
        result = await condition_evaluator.evaluate(condition)
        assert result is True  # 22.5 > 20

    @pytest.mark.asyncio
    async def test_template_condition_false(self, condition_evaluator):
        """Test template condition that evaluates to False"""
        condition = {
            'condition': 'template',
            'value_template': "{{ states('sensor.temperature') | float > 30 }}"
        }
        result = await condition_evaluator.evaluate(condition)
        assert result is False  # 22.5 is not > 30

