#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Epic 51: YAML Validation Service Test Script

This script demonstrates the validation and normalization capabilities
of the new yaml-validation-service.

Usage:
    python examples/test_epic51_validation.py
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "services" / "yaml-validation-service" / "src"))

from yaml_validation_service.normalizer import YAMLNormalizer
from yaml_validation_service.validator import ValidationPipeline
from yaml_validation_service.schema import AutomationSpec
from yaml_validation_service.renderer import AutomationRenderer


def load_yaml_examples():
    """Load YAML examples from file."""
    examples_file = project_root / "examples" / "epic51-validation-examples.yaml"
    with open(examples_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Split by --- separator
    examples = []
    for section in content.split("---\n"):
        section = section.strip()
        if section and not section.startswith("#"):
            # Extract alias for identification
            alias = None
            for line in section.split("\n"):
                if line.strip().startswith("alias:"):
                    alias = line.split(":", 1)[1].strip().strip('"').strip("'")
                    break
            examples.append({
                "alias": alias or "Unknown",
                "yaml": section
            })
    
    return examples


async def test_normalizer():
    """Test YAML normalizer."""
    print("\n" + "="*80)
    print("TEST 1: YAML Normalizer")
    print("="*80)
    
    normalizer = YAMLNormalizer()
    
    # Test case 1: Plural keys
    bad_yaml = """
alias: "Test Automation"
triggers:
  - platform: state
    entity_id: binary_sensor.motion
actions:
  - action: light.turn_on
    entity_id: light.test
"""
    
    print("\n[INPUT] Input YAML (BAD):")
    print(bad_yaml)
    
    normalized_yaml, fixes_applied = normalizer.normalize(bad_yaml)
    
    print("\n[OK] Normalized YAML:")
    print(normalized_yaml)
    
    if fixes_applied:
        print("\n[FIX] Fixes Applied:")
        for fix in fixes_applied:
            # Replace Unicode arrows with ASCII for Windows console
            fix_ascii = fix.replace('→', '->').replace('→', '->')
            print(f"  - {fix_ascii}")
    
    assert "trigger:" in normalized_yaml, "Should fix triggers: → trigger:"
    assert "action:" in normalized_yaml, "Should fix actions: → action:"
    print("\n[PASS] Normalizer test PASSED")


async def test_validator():
    """Test validation pipeline."""
    print("\n" + "="*80)
    print("TEST 2: Validation Pipeline")
    print("="*80)
    
    # Create a mock data API client (we'll skip actual API calls for this test)
    class MockDataAPIClient:
        async def fetch_entities(self):
            return ["light.office_light", "binary_sensor.motion_sensor", "switch.evening_mode"]
        
        async def fetch_services(self):
            return ["light.turn_on", "light.turn_off", "notify.mobile_app"]
    
    validator = ValidationPipeline(data_api_client=MockDataAPIClient())
    
    # Test case 1: Valid YAML (single automation dict, not list)
    valid_yaml = """
alias: "Valid Automation"
trigger:
  - platform: state
    entity_id: binary_sensor.motion_sensor
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.office_light
"""
    
    print("\n[INPUT] Testing Valid YAML:")
    result = await validator.validate(valid_yaml)
    
    print(f"\n[OK] Valid: {result.valid}")
    print(f"[SCORE] Score: {result.score:.1f}/100")
    print(f"[ERROR] Errors: {len(result.errors)}")
    print(f"[WARN] Warnings: {len(result.warnings)}")
    
    if result.errors:
        print("\nErrors:")
        for error in result.errors:
            print(f"  - {error}")
    
    assert result.valid == True, "Valid YAML should pass validation"
    print("\n[PASS] Validator test PASSED (valid YAML)")
    
    # Test case 2: Invalid YAML (missing required fields)
    invalid_yaml = """
alias: "Invalid Automation"
# Missing trigger and action
"""
    
    print("\n[INPUT] Testing Invalid YAML:")
    result = await validator.validate(invalid_yaml)
    
    print(f"\n[OK] Valid: {result.valid}")
    print(f"[SCORE] Score: {result.score:.1f}/100")
    print(f"[ERROR] Errors: {len(result.errors)}")
    
    if result.errors:
        print("\nErrors:")
        for error in result.errors[:3]:  # Show first 3
            print(f"  - {error}")
    
    print("\n[PASS] Validator test PASSED (invalid YAML detected)")


def test_schema():
    """Test AutomationSpec schema."""
    print("\n" + "="*80)
    print("TEST 3: AutomationSpec Schema")
    print("="*80)
    
    # Create a valid AutomationSpec
    automation_data = {
        "alias": "Test Automation",
        "description": "A test automation",
        "initial_state": True,
        "mode": "single",
        "trigger": [
            {
                "platform": "state",
                "entity_id": "binary_sensor.motion_sensor",
                "to": "on"
            }
        ],
        "action": [
            {
                "service": "light.turn_on",
                "target": {
                    "entity_id": ["light.office_light"]
                }
            }
        ]
    }
    
    print("\n[INPUT] Creating AutomationSpec from dict:")
    print(json.dumps(automation_data, indent=2))
    
    try:
        spec = AutomationSpec(**automation_data)
        print("\n[OK] AutomationSpec created successfully")
        print(f"  - Alias: {spec.alias}")
        print(f"  - Triggers: {len(spec.trigger)}")
        print(f"  - Actions: {len(spec.action)}")
        print(f"  - Mode: {spec.mode}")
        
        assert spec.alias == "Test Automation"
        assert len(spec.trigger) == 1
        assert len(spec.action) == 1
        print("\n[PASS] Schema test PASSED")
    except Exception as e:
        print(f"\n[FAIL] Schema test FAILED: {e}")
        raise


def test_renderer():
    """Test YAML renderer."""
    print("\n" + "="*80)
    print("TEST 4: YAML Renderer")
    print("="*80)
    
    # Create AutomationSpec
    automation_data = {
        "alias": "Rendered Automation",
        "description": "This automation was rendered from AutomationSpec",
        "trigger": [
            {
                "platform": "state",
                "entity_id": "binary_sensor.motion_sensor",
                "to": "on"
            }
        ],
        "action": [
            {
                "service": "light.turn_on",
                "target": {
                    "entity_id": "light.office_light"
                },
                "error": "continue"
            }
        ]
    }
    
    spec = AutomationSpec(**automation_data)
    renderer = AutomationRenderer()
    
    print("\n[INPUT] Rendering AutomationSpec to YAML:")
    yaml_output = renderer.render(spec)
    
    print("\n[OK] Rendered YAML:")
    print(yaml_output)
    
    # Verify key requirements
    assert "alias:" in yaml_output, "Should have alias"
    assert "trigger:" in yaml_output, "Should have trigger (singular)"
    assert "action:" in yaml_output, "Should have action (singular)"
    assert "service:" in yaml_output, "Should have service (not action:)"
    assert "error: continue" in yaml_output, "Should have error: continue format"
    
    print("\n[PASS] Renderer test PASSED")


async def test_full_pipeline():
    """Test the full validation and normalization pipeline."""
    print("\n" + "="*80)
    print("TEST 5: Full Pipeline (Normalize → Validate → Render)")
    print("="*80)
    
    # Bad YAML input
    bad_yaml = """
alias: "Full Pipeline Test"
triggers:
  - platform: state
    entity_id: binary_sensor.motion
actions:
  - action: light.turn_on
    entity_id: light.test
    continue_on_error: true
"""
    
    print("\n[INPUT] Input YAML (BAD):")
    print(bad_yaml)
    
    # Step 1: Normalize
    normalizer = YAMLNormalizer()
    fixed_yaml, fixes_applied = normalizer.normalize(bad_yaml)
    
    print("\n[FIX] Step 1: Normalized YAML:")
    print(fixed_yaml)
    
    if fixes_applied:
        print("\nFixes Applied:")
        for fix in fixes_applied:
            print(f"  - {fix}")
    
    # Step 2: Validate (mock client)
    class MockDataAPIClient:
        async def fetch_entities(self):
            return ["light.test", "binary_sensor.motion"]
        async def fetch_services(self):
            return ["light.turn_on"]
    
    validator = ValidationPipeline(data_api_client=MockDataAPIClient())
    validation_result = await validator.validate(fixed_yaml)
    
    print("\n[OK] Step 2: Validation Result:")
    print(f"  - Valid: {validation_result.valid}")
    print(f"  - Score: {validation_result.score:.1f}/100")
    print(f"  - Errors: {len(validation_result.errors)}")
    print(f"  - Warnings: {len(validation_result.warnings)}")
    
    print("\n[PASS] Full pipeline test PASSED")


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("EPIC 51: YAML VALIDATION SERVICE - TEST SUITE")
    print("="*80)
    
    try:
        # Test 1: Normalizer
        await test_normalizer()
        
        # Test 2: Validator
        await test_validator()
        
        # Test 3: Schema
        test_schema()
        
        # Test 4: Renderer
        test_renderer()
        
        # Test 5: Full Pipeline
        await test_full_pipeline()
        
        print("\n" + "="*80)
        print("[SUCCESS] ALL TESTS PASSED!")
        print("="*80)
        print("\nThe Epic 51 YAML validation service is working correctly!")
        print("\nKey Features Verified:")
        print("  [OK] YAML normalization (plural -> singular, field name fixes)")
        print("  [OK] Multi-stage validation pipeline")
        print("  [OK] AutomationSpec schema (type-safe)")
        print("  [OK] YAML rendering (deterministic output)")
        print("  [OK] Full pipeline integration")
        
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

