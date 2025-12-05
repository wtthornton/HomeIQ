"""Get validation errors for a deployed automation."""
import asyncio
import httpx
import yaml

API_KEY = "hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR"
BASE_URL = "http://localhost:8024"
AUTOMATION_ID = "automation.office_wled_fireworks_every_15_minutes"

async def get_automation_yaml(automation_id: str):
    """Get automation YAML from Home Assistant."""
    headers = {"X-HomeIQ-API-Key": API_KEY}
    
    # Get automation from HA
    url = f"{BASE_URL}/api/deploy/automations/{automation_id}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("data"):
                    # HA returns automation config which includes YAML
                    automation = data["data"]
                    # Try to get YAML from automation config
                    if "config" in automation:
                        return automation["config"]
                    elif "source" in automation:
                        return automation["source"]
                    # Otherwise, try to reconstruct from automation data
                    return automation
            return None
        except Exception as e:
            print(f"Error getting automation: {e}")
            return None

async def validate_yaml(yaml_content: str):
    """Validate YAML and get all errors."""
    headers = {"X-HomeIQ-API-Key": API_KEY}
    url = f"{BASE_URL}/api/v1/yaml/validate"
    
    # If yaml_content is a dict, convert to YAML string
    if isinstance(yaml_content, dict):
        yaml_content = yaml.dump(yaml_content, default_flow_style=False)
    
    payload = {
        "yaml": yaml_content,
        "validate_entities": True,
        "validate_safety": True
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Validation failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error validating YAML: {e}")
            return None

async def main():
    print("=" * 70)
    print(f"Getting Validation Errors for: {AUTOMATION_ID}")
    print("=" * 70)
    
    # Step 1: Get automation YAML
    print("\n📥 Step 1: Fetching automation from Home Assistant...")
    automation_data = await get_automation_yaml(AUTOMATION_ID)
    
    if not automation_data:
        print("❌ Could not retrieve automation")
        return
    
    # Extract YAML
    if isinstance(automation_data, dict):
        # Try to get YAML from various possible fields
        yaml_str = automation_data.get("source") or automation_data.get("config") or str(automation_data)
        if isinstance(yaml_str, dict):
            yaml_str = yaml.dump(yaml_str, default_flow_style=False)
    else:
        yaml_str = automation_data
    
    print(f"✅ Retrieved automation YAML ({len(yaml_str)} chars)")
    
    # Step 2: Validate YAML
    print("\n🔍 Step 2: Running comprehensive validation...")
    validation_result = await validate_yaml(yaml_str)
    
    if not validation_result:
        print("❌ Validation failed")
        return
    
    # Step 3: Display results
    print("\n" + "=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)
    
    print(f"\n✅ Overall Status: {'VALID' if validation_result.get('valid') else 'INVALID'}")
    print(f"📊 Safety Score: {validation_result.get('safety_score', 'N/A')}")
    print(f"📝 Summary: {validation_result.get('summary', 'N/A')}")
    
    # Errors
    errors = validation_result.get('errors', [])
    if errors:
        print(f"\n❌ ERRORS ({len(errors)}):")
        print("-" * 70)
        for i, error in enumerate(errors, 1):
            print(f"\n{i}. [{error.get('stage', 'unknown').upper()}] {error.get('severity', 'error').upper()}")
            print(f"   Message: {error.get('message', 'N/A')}")
            if error.get('fix'):
                print(f"   Fix: {error.get('fix')}")
    else:
        print("\n✅ No errors found")
    
    # Warnings
    warnings = validation_result.get('warnings', [])
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        print("-" * 70)
        for i, warning in enumerate(warnings, 1):
            print(f"\n{i}. [{warning.get('stage', 'unknown').upper()}]")
            print(f"   Message: {warning.get('message', 'N/A')}")
            if warning.get('fix'):
                print(f"   Fix: {warning.get('fix')}")
    else:
        print("\n✅ No warnings found")
    
    # Stages
    stages = validation_result.get('stages', {})
    if stages:
        print(f"\n📋 VALIDATION STAGES:")
        print("-" * 70)
        for stage_name, passed in stages.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status} - {stage_name}")
    
    # Entity Results
    entity_results = validation_result.get('entity_results', [])
    if entity_results:
        print(f"\n🔌 ENTITY VALIDATION ({len(entity_results)} entities):")
        print("-" * 70)
        for entity in entity_results:
            status = "✅" if entity.get('exists') else "❌"
            print(f"  {status} {entity.get('entity_id', 'N/A')}")
            if entity.get('alternatives'):
                print(f"     Alternatives: {', '.join(entity.get('alternatives', []))}")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    asyncio.run(main())

