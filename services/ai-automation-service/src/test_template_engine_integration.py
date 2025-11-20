#!/usr/bin/env python3
"""
Quick integration test for Template Engine and Condition Evaluator
Tests that components work in runtime environment
"""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock

from clients.ha_client import HomeAssistantClient
from condition_evaluator import ConditionEvaluator
from template_engine import TemplateEngine


async def test_template_engine():
    """Test template engine"""
    print("Testing TemplateEngine...")

    # Create mock HA client
    mock_ha_client = MagicMock(spec=HomeAssistantClient)
    mock_ha_client.get_states = AsyncMock(return_value=[
        {
            'entity_id': 'sensor.temperature',
            'state': '22.5',
            'attributes': {}
        }
    ])

    engine = TemplateEngine(mock_ha_client)

    # Test simple template
    result = await engine.render("Temperature: {{ states('sensor.temperature') }}")
    assert "22.5" in result
    print("  ✓ Simple template rendering")

    # Test template with filter
    result = await engine.render("{{ states('sensor.temperature') | float + 2 }}")
    assert float(result) == 24.5
    print("  ✓ Template with filter")

    # Test validation
    is_valid, error = await engine.validate_template("Temperature: {{ states('sensor.temp') }}")
    assert is_valid
    print("  ✓ Template validation")

    print("  ✅ TemplateEngine tests passed\n")
    return True


async def test_condition_evaluator():
    """Test condition evaluator"""
    print("Testing ConditionEvaluator...")

    # Create mock HA client
    mock_ha_client = MagicMock(spec=HomeAssistantClient)
    mock_ha_client.get_states = AsyncMock(return_value=[
        {
            'entity_id': 'light.office',
            'state': 'on',
            'attributes': {}
        },
        {
            'entity_id': 'sensor.temperature',
            'state': '22.5',
            'attributes': {}
        }
    ])

    template_engine = TemplateEngine(mock_ha_client)
    evaluator = ConditionEvaluator(mock_ha_client, template_engine)

    # Test state condition
    condition = {
        'condition': 'state',
        'entity_id': 'light.office',
        'state': 'on'
    }
    result = await evaluator.evaluate(condition)
    assert result is True
    print("  ✓ State condition evaluation")

    # Test AND condition
    and_condition = {
        'condition': 'and',
        'conditions': [
            {'condition': 'state', 'entity_id': 'light.office', 'state': 'on'},
            {'condition': 'numeric_state', 'entity_id': 'sensor.temperature', 'above': 20.0}
        ]
    }
    result = await evaluator.evaluate(and_condition)
    assert result is True
    print("  ✓ AND condition evaluation")

    # Test OR condition
    or_condition = {
        'condition': 'or',
        'conditions': [
            {'condition': 'state', 'entity_id': 'light.office', 'state': 'on'},
            {'condition': 'state', 'entity_id': 'light.kitchen', 'state': 'on'}
        ]
    }
    result = await evaluator.evaluate(or_condition)
    assert result is True
    print("  ✓ OR condition evaluation")

    # Test NOT condition
    not_condition = {
        'condition': 'not',
        'conditions': [
            {'condition': 'state', 'entity_id': 'light.office', 'state': 'off'}
        ]
    }
    result = await evaluator.evaluate(not_condition)
    assert result is True  # Office is on, so NOT(off) is True
    print("  ✓ NOT condition evaluation")

    print("  ✅ ConditionEvaluator tests passed\n")
    return True


async def main():
    """Run all integration tests"""
    print("=" * 60)
    print("Template Engine & Condition Evaluator Integration Test")
    print("=" * 60)
    print()

    success = True
    success &= await test_template_engine()
    success &= await test_condition_evaluator()

    print("=" * 60)
    if success:
        print("✅ All integration tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

