#!/usr/bin/env python3
"""
Test Multiple Flash/Strobe Scenarios

Validates that the updated prompt handles various flash/strobe patterns correctly.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_quick_test_prototype import simplify_with_openai, execute_with_ha, load_env_file, OPENAI_API_KEY

env_vars = load_env_file("infrastructure/env.ai-automation")
HA_URL = env_vars.get("HA_URL")
HA_TOKEN = env_vars.get("HA_TOKEN")

async def test_scenario(description: str):
    """Test a single scenario"""
    print(f"\nOriginal: '{description}'")
    
    # Simplify
    simplified = await simplify_with_openai(description)
    print(f"Simplified: '{simplified}'")
    
    # Check if it's a standard HA action
    standard_actions = ["turn on", "turn off", "dim", "brighten"]
    is_standard = any(simplified.lower().startswith(action) for action in standard_actions)
    print(f"Standard HA action: {is_standard}")
    
    if is_standard:
        print("GOOD - Will work with HA Conversation API")
    else:
        print("WARNING - May not work with HA Conversation API")
    
    return simplified

async def main():
    print("=" * 80)
    print("Multiple Flash/Strobe Scenario Testing")
    print("=" * 80)
    
    scenarios = [
        "Flash office lights every 30 seconds only after 5pm",
        "Strobe the kitchen lights when door opens",
        "Flash all lights 3 times when motion detected",
        "Turn on and flash the office lights",
        "Make the bedroom lights flash",
    ]
    
    for scenario in scenarios:
        await test_scenario(scenario)
    
    print("\n" + "=" * 80)
    print("Testing complete")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())

