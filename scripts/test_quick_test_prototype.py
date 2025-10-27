#!/usr/bin/env python3
"""
Standalone YAML Test Prototype - Option 1

Tests the flow:
1. Generate YAML automation with OpenAI
2. Create automation in HA
3. Trigger automation manually
4. Wait for execution
5. Delete automation

No dependencies on project service code.
"""

import asyncio
import aiohttp
from openai import AsyncOpenAI
import os
import json
import logging
import yaml
import secrets

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables from file
def load_env_file(filepath: str) -> dict:
    """Load environment variables from a file"""
    env_vars = {}
    if os.path.exists(filepath):
        with open(filepath, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    # Remove everything after # (comments)
                    if "#" in value:
                        value = value.split("#")[0]
                    env_vars[key.strip()] = value.strip()
    return env_vars

# Load from infrastructure/env.ai-automation
env_vars = load_env_file("infrastructure/env.ai-automation")
OPENAI_API_KEY = env_vars.get("OPENAI_API_KEY")
HA_URL = env_vars.get("HA_URL")
HA_TOKEN = env_vars.get("HA_TOKEN")


async def get_device_capabilities_for_area(area_name: str, manufacturer_filter: str = None) -> list:
    """Get all device capabilities for an area from Device Intelligence API"""
    try:
        async with aiohttp.ClientSession() as session:
            # First get all devices for the area
            async with session.get(
                f"http://localhost:8028/api/devices",
                params={"area_name": area_name, "limit": 50},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    print(f"  Could not get devices: {response.status}")
                    return []
                
                devices = await response.json()
                if isinstance(devices, dict):
                    devices = devices.get('devices', [])
                
                print(f"  Found {len(devices)} total devices in {area_name} area")
                if len(devices) > 0:
                    # Show first 5 devices for debugging
                    for i, device in enumerate(devices[:5]):
                        print(f"  Device {i+1}: {device.get('name', 'Unknown')} - Manufacturer: {device.get('manufacturer', 'Unknown')} - Integration: {device.get('integration', 'Unknown')}")
                
                # Filter by manufacturer if specified (also check integration field)
                if manufacturer_filter:
                    devices = [d for d in devices if 
                              manufacturer_filter.lower() in d.get('manufacturer', '').lower() or 
                              manufacturer_filter.lower() in d.get('name', '').lower() or
                              manufacturer_filter.lower() in d.get('integration', '').lower()]
                    print(f"  Filtered to {len(devices)} devices matching '{manufacturer_filter}'")
                    
                    if len(devices) > 0:
                        for i, device in enumerate(devices[:3]):
                            print(f"    Matched device {i+1}: {device.get('name', 'Unknown')} ({device.get('integration', 'Unknown')})")
                
                all_capabilities = []
                
                # For each device, get its capabilities
                for device in devices:
                    device_id = device.get('id')
                    if not device_id:
                        continue
                    
                    # Get capabilities for this device
                    async with session.get(
                        f"http://localhost:8028/api/devices/{device_id}/capabilities",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as cap_response:
                        if cap_response.status == 200:
                            capabilities = await cap_response.json()
                            if isinstance(capabilities, list):
                                for cap in capabilities:
                                    all_capabilities.append({
                                        'device_id': device_id,
                                        'device_name': device.get('name', ''),
                                        'capability_name': cap.get('capability_name', ''),
                                        'capability_type': cap.get('capability_type', ''),
                                        'properties': cap.get('properties', {})
                                    })
                
                print(f"  Found {len(all_capabilities)} capabilities for {area_name}")
                return all_capabilities
                
    except Exception as e:
        print(f"  Could not get device capabilities: {e}")
    return []


async def generate_test_yaml(description: str, area_name: str = "office", manufacturer_filter: str = None) -> str:
    """Generate YAML automation for testing with device-specific features"""
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    # Generate random ID
    random_id = secrets.token_hex(4)
    
    # Fetch device capabilities for the area (filtered by manufacturer if specified)
    filter_text = f" (filtering for '{manufacturer_filter}')" if manufacturer_filter else ""
    print(f"Fetching device capabilities for '{area_name}'{filter_text}...")
    capabilities = await get_device_capabilities_for_area(area_name, manufacturer_filter)
    
    # Build capabilities context
    capabilities_text = ""
    if capabilities:
        capabilities_text = f"\nAVAILABLE DEVICE CAPABILITIES IN '{area_name.upper()}' AREA:\n"
        for cap in capabilities:
            capabilities_text += f"- Device: {cap.get('device_name', 'Unknown')}\n"
            capabilities_text += f"  - {cap.get('capability_name', 'Unknown')} ({cap.get('capability_type', 'Unknown')})\n"
            if cap.get('properties'):
                props = cap.get('properties', {})
                if isinstance(props, dict):
                    for key, value in props.items():
                        capabilities_text += f"    - {key}: {value}\n"
    else:
        capabilities_text = "\nNOTE: No device capabilities found for this area. Using generic capabilities.\n"
    
    prompt = f"""Generate a Home Assistant automation YAML for testing.

AUTOMATION DESCRIPTION: "{description}"
{capabilities_text}

CRITICAL TEST RULES:
- STRIP OUT all time constraints (after 5pm, before sunset, etc.)
- STRIP OUT all interval patterns (every 30 seconds, every weekday, etc.)  
- Keep action SIMPLE: Execute the core action once when triggered
- Use the available device capabilities shown above to create the correct action
- This is for TESTING, not production - simplicity is key

REQUIRED FIELDS:
1. id: test_automation_{random_id}
2. alias: "[TEST] {{core_action_description}}"
3. description: "{{core_action_description}}"
4. mode: single
5. trigger: platform: event, event_type: test_automation_trigger
6. action: Use the correct service call based on device capabilities

EXAMPLE:
```yaml
id: test_automation_abc12345
alias: "[TEST] Turn on office lights"
description: "Turn on office lights"
mode: single
trigger:
  - platform: event
    event_type: test_automation_trigger
action:
  - service: light.turn_on
    target:
      entity_id: light.office_left
    data:
      brightness: 255
```

Return ONLY valid YAML, no explanations, no markdown code blocks."""
    
    print("OPENAI PROMPT:")
    print("=" * 80)
    print(f"System: You are a HA YAML expert. Return ONLY valid YAML, no markdown blocks.")
    print(f"User: {prompt}")
    print("=" * 80)
    print()
    
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a HA YAML expert. Return ONLY valid YAML, no markdown blocks."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=400
    )
    
    print("OPENAI RESPONSE:")
    print("=" * 80)
    print(response.choices[0].message.content)
    print("=" * 80)
    print()
    
    yaml_content = response.choices[0].message.content.strip()
    
    # Remove markdown code blocks if present
    if yaml_content.startswith("```"):
        lines = yaml_content.split("\n")
        # Remove first line (```yaml or ```)
        lines = lines[1:] if lines[0].startswith("```") else lines
        # Remove last line (```)
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        yaml_content = "\n".join(lines)
    
    return yaml_content.strip()


async def create_automation(yaml_content: str) -> dict:
    """Create automation via HA REST API"""
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json"
    }
    
    automation_data = yaml.safe_load(yaml_content)
    automation_id = automation_data.get('id')
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{HA_URL}/api/config/automation/config/{automation_id}",
            headers=headers,
            json=automation_data,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status in [200, 201]:
                return {"success": True, "automation_id": f"automation.{automation_id}"}
            else:
                text = await response.text()
                return {"success": False, "error": f"HTTP {response.status}: {text}"}

async def trigger_automation(automation_id: str) -> dict:
    """Trigger automation manually via HA REST API"""
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{HA_URL}/api/services/automation/trigger",
            headers=headers,
            json={"entity_id": automation_id},
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status in [200, 201]:
                return {"success": True}
            else:
                text = await response.text()
                return {"success": False, "error": f"HTTP {response.status}: {text}"}

async def delete_automation(automation_id: str) -> dict:
    """Delete automation via HA REST API"""
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Extract just the ID part (remove "automation." prefix if present)
    automation_id_clean = automation_id.replace("automation.", "")
    
    async with aiohttp.ClientSession() as session:
        async with session.delete(
            f"{HA_URL}/api/config/automation/config/{automation_id_clean}",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status in [200, 204]:
                return {"success": True}
            else:
                text = await response.text()
                return {"success": False, "error": f"HTTP {response.status}: {text}"}


async def test_quick_test_flow():
    """Test Option 1: Create-Trigger-Delete pattern"""
    print("=" * 80)
    print("YAML TEST BUTTON PROTOTYPE - OPTION 1")
    print("=" * 80)
    print()
    
    original_description = "Flash office lights every 30 seconds only after 5pm"
    
    print(f"Original Description: {original_description}")
    print()
    
    # STEP 1: Generate YAML automation (now with device capabilities)
    print("STEP 1: Generating YAML automation with OpenAI + Device Capabilities...")
    area_name = "office"  # Extract or pass as parameter
    manufacturer_filter = "hue"  # Filter for Hue devices (check integration field)
    yaml_content = await generate_test_yaml(original_description, area_name, manufacturer_filter)
    print("Generated YAML:")
    print("-" * 40)
    print(yaml_content)
    print("-" * 40)
    print()
    
    # STEP 2: Create automation in HA
    print("STEP 2: Creating automation in Home Assistant...")
    create_result = await create_automation(yaml_content)
    
    if not create_result.get("success"):
        print(f"  ERROR: Failed to create automation: {create_result.get('error')}")
        return False
    
    automation_id = create_result.get("automation_id")
    print(f"  SUCCESS: Created automation '{automation_id}'")
    print()
    
    try:
        # STEP 3: Trigger automation
        print("STEP 3: Triggering automation...")
        trigger_result = await trigger_automation(automation_id)
        
        if not trigger_result.get("success"):
            print(f"  ERROR: Failed to trigger: {trigger_result.get('error')}")
            return False
        
        print(f"  SUCCESS: Automation triggered")
        print()
        
        # STEP 4: Wait for execution
        print("STEP 4: Waiting for automation to execute...")
        print("  Waiting 30 seconds so you can review the automation in HA")
        await asyncio.sleep(30)
        print("  Execution complete (30 second wait)")
        print()
        
        # STEP 5: Verify result
        print("STEP 5: Verification")
        print("  Check your Home Assistant device to confirm flash/action occurred")
        print("  For 'Flash office lights': Office lights should have flashed")
        print()
        
        return True
        
    finally:
        # STEP 6: Cleanup - always delete automation
        print("STEP 6: Cleaning up (deleting automation)...")
        delete_result = await delete_automation(automation_id)
        
        if delete_result.get("success"):
            print(f"  SUCCESS: Deleted automation '{automation_id}'")
        else:
            print(f"  WARNING: Failed to delete automation: {delete_result.get('error')}")
            print(f"  You may need to manually delete '{automation_id}' from HA")
        print()


async def main():
    """Run the prototype test"""
    # Load environment variables
    if not OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY not set in environment")
        return
    
    if not HA_URL or not HA_TOKEN:
        print("ERROR: HA_HTTP_URL or HA_TOKEN not set in .env")
        return
    
    print(f"Configuration:")
    print(f"  OpenAI API Key: {'OK' if OPENAI_API_KEY else 'MISSING'}")
    print(f"  HA URL: {HA_URL}")
    print(f"  HA Token: {'OK' if HA_TOKEN else 'MISSING'}")
    print()
    
    # Run test
    success = await test_quick_test_flow()
    
    print()
    print("=" * 80)
    print(f"RESULT: {'PASSED' if success else 'FAILED'}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

