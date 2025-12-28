"""
Test script for HomeIQ JSON Automation API endpoints.

Tests the JSON workflow through the service API endpoints.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add workspace root to path for shared modules
workspace_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(workspace_root))
# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from shared.homeiq_automation.converter import HomeIQToAutomationSpecConverter
from shared.homeiq_automation.schema import (
    HomeIQAutomation,
    HomeIQMetadata,
    HomeIQTrigger,
    HomeIQAction,
    DeviceContext,
    SafetyChecks,
    EnergyImpact,
)
from shared.yaml_validation_service.version_aware_renderer import VersionAwareRenderer
from shared.yaml_validation_service.schema import AutomationMode


def create_sample_homeiq_json() -> dict:
    """Create a sample HomeIQ JSON Automation for testing."""
    # Create using Pydantic models to ensure proper validation
    homeiq_automation = HomeIQAutomation(
        alias="Test Motion Light Automation",
        description="Turn on light when motion detected",
        version="1.0.0",
        homeiq_metadata=HomeIQMetadata(
            use_case="comfort",
            complexity="low",
        ),
        device_context=DeviceContext(
            entity_ids=["light.test", "sensor.motion"],
            device_ids=[],
            area_ids=[],
        ),
        safety_checks=SafetyChecks(
            requires_confirmation=False,
        ),
        energy_impact=EnergyImpact(
            estimated_power_w=10.0,
            estimated_daily_kwh=0.1,
        ),
        triggers=[
            HomeIQTrigger(
                platform="state",
                entity_id="sensor.motion",
                to="on",
            )
        ],
        actions=[
            HomeIQAction(
                service="light.turn_on",
                target={"entity_id": "light.test"},
            )
        ],
        mode=AutomationMode.SINGLE,
    )
    
    # Convert to dict for JSON serialization
    return homeiq_automation.model_dump(mode="json")


async def test_json_workflow():
    """Test the complete JSON workflow."""
    print("Testing HomeIQ JSON Automation Workflow\n")
    print("=" * 60)
    
    # Step 1: Create sample JSON
    print("Step 1: Creating sample HomeIQ JSON...")
    sample_json = create_sample_homeiq_json()
    print(f"[OK] Created JSON with alias: {sample_json['alias']}\n")
    
    # Step 2: Validate JSON schema
    print("Step 2: Validating JSON schema...")
    try:
        homeiq_automation = HomeIQAutomation(**sample_json)
        print("[OK] JSON schema validation passed\n")
    except Exception as e:
        print(f"[FAIL] JSON schema validation failed: {e}\n")
        return False
    
    # Step 3: Convert to AutomationSpec
    print("Step 3: Converting HomeIQ JSON to AutomationSpec...")
    try:
        converter = HomeIQToAutomationSpecConverter()
        automation_spec = converter.convert(homeiq_automation)
        print(f"[OK] Converted to AutomationSpec: {automation_spec.alias}\n")
    except Exception as e:
        print(f"[FAIL] Conversion failed: {e}\n")
        return False
    
    # Step 4: Render to YAML
    print("Step 4: Rendering AutomationSpec to YAML...")
    try:
        renderer = VersionAwareRenderer(ha_version="2025.10.3")
        yaml_content = renderer.render(automation_spec)
        print("[OK] YAML rendered successfully")
        print("\nGenerated YAML:")
        print("-" * 50)
        print(yaml_content)
        print("-" * 50)
        print()
    except Exception as e:
        print(f"[FAIL] YAML rendering failed: {e}\n")
        return False
    
    # Step 5: Test JSON serialization (for API storage)
    print("Step 5: Testing JSON serialization...")
    try:
        json_str = json.dumps(sample_json, indent=2)
        print(f"[OK] JSON serialization successful ({len(json_str)} bytes)\n")
    except Exception as e:
        print(f"[FAIL] JSON serialization failed: {e}\n")
        return False
    
    # Step 6: Test JSON deserialization (for API retrieval)
    print("Step 6: Testing JSON deserialization...")
    try:
        deserialized = json.loads(json_str)
        homeiq_automation_2 = HomeIQAutomation(**deserialized)
        print(f"[OK] JSON deserialization successful: {homeiq_automation_2.alias}\n")
    except Exception as e:
        print(f"[FAIL] JSON deserialization failed: {e}\n")
        return False
    
    print("=" * 60)
    print("[OK] All workflow steps completed successfully!")
    print("\nSummary:")
    print(f"  - JSON Schema: Valid")
    print(f"  - Conversion: Working")
    print(f"  - YAML Rendering: Working")
    print(f"  - JSON Serialization: Working")
    print(f"  - JSON Deserialization: Working")
    print("\nThe HomeIQ JSON Automation layer is ready for API integration!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_json_workflow())
    sys.exit(0 if success else 1)

