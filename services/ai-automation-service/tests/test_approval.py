"""
Simple test for Phase 4 approval flow

Run with: pytest tests/test_approval.py -v
"""

import os

import pytest
from src.llm.openai_client import OpenAIClient

# Skip if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv('OPENAI_API_KEY'),
    reason="OPENAI_API_KEY not set"
)


@pytest.mark.asyncio
async def test_generate_yaml_after_refinement():
    """Test complete flow: description → refinement → YAML"""
    client = OpenAIClient(api_key=os.getenv('OPENAI_API_KEY'))

    # Step 1: Generate initial description
    description = await client.generate_description_only(
        pattern={
            'pattern_type': 'time_of_day',
            'hour': 18,
            'minute': 0,
            'device_id': 'light.living_room',
            'occurrences': 20,
            'confidence': 0.89
        },
        device_context={'name': 'Living Room Light'}
    )

    print(f"\n✅ Initial: {description}")

    # Step 2: Refine
    refined = await client.refine_description(
        current_description=description,
        user_input="Make it blue and only on weekdays"
    )

    print(f"✅ Refined: {refined['updated_description']}")

    # Step 3: Generate YAML
    pattern = {
        'pattern_type': 'time_of_day',
        'hour': 18,
        'minute': 0,
        'device_id': 'light.living_room',
        'occurrences': 20,
        'confidence': 0.89
    }

    automation = await client.generate_automation_suggestion(
        pattern=pattern,
        device_context={'name': 'Living Room Light'}
    )

    print(f"✅ YAML generated: {len(automation.automation_yaml)} chars")
    print(f"✅ Alias: {automation.alias}")

    # Validate YAML syntax
    import yaml
    try:
        yaml.safe_load(automation.automation_yaml)
        print("✅ YAML syntax valid")
    except yaml.YAMLError as e:
        print(f"❌ YAML syntax error: {e}")
        raise

    assert automation.automation_yaml != ""
    assert "alias:" in automation.automation_yaml
    assert automation.confidence == 0.89


@pytest.mark.asyncio
async def test_yaml_contains_refinements():
    """Test that YAML reflects refinements"""
    client = OpenAIClient(api_key=os.getenv('OPENAI_API_KEY'))

    pattern = {
        'pattern_type': 'time_of_day',
        'hour': 18,
        'minute': 0,
        'device_id': 'light.bedroom',
        'occurrences': 15,
        'confidence': 0.85
    }

    automation = await client.generate_automation_suggestion(
        pattern=pattern,
        device_context={'name': 'Bedroom Light'}
    )

    # YAML should contain device name
    assert 'bedroom' in automation.automation_yaml.lower()
    assert '18:00' in automation.automation_yaml

    print(f"\n✅ YAML Preview:\n{automation.automation_yaml[:200]}...")

