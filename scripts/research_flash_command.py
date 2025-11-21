#!/usr/bin/env python3
"""
Research Script: Why does HA interpret "flash" as an area name?

Tests different variations of flash commands to understand HA's interpretation.
"""

import asyncio
import json
import os

import aiohttp


def load_env_file(filepath: str) -> dict:
    """Load environment variables from a file"""
    env_vars = {}
    if os.path.exists(filepath):
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    if "#" in value:
                        value = value.split("#")[0]
                    env_vars[key.strip()] = value.strip()
    return env_vars

# Load environment
env_vars = load_env_file("infrastructure/env.ai-automation")
HA_URL = env_vars.get("HA_URL")
HA_TOKEN = env_vars.get("HA_TOKEN")

async def test_command(cmd: str):
    """Test a command with HA Conversation API"""
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session, session.post(
        f"{HA_URL}/api/conversation/process",
        headers=headers,
        json={"text": cmd},
        timeout=aiohttp.ClientTimeout(total=10),
    ) as response:
        if response.status in [200, 201]:
            result = await response.json()
            print(f"\nCommand: '{cmd}'")
            print(f"Response Type: {result.get('response', {}).get('response_type', 'unknown')}")
            print(f"Speech: {result.get('response', {}).get('speech', {}).get('plain', {}).get('speech', 'N/A')}")
            if "data" in result.get("response", {}):
                print(f"Data: {json.dumps(result['response']['data'], indent=2)}")
            print("-" * 80)
            return result
        print(f"ERROR: HTTP {response.status}")
        return None

async def main():
    print("=" * 80)
    print("Research: HA Conversation API with 'flash' commands")
    print("=" * 80)

    # Test different variations
    test_commands = [
        "Flash the office lights",
        "Flash office lights",
        "Flash the lights",
        "Turn on the office lights",
        "Turn on and flash the office lights",
        "Make the office lights flash",
        "Strobe the office lights",
        "Turn on the office light and flash it 3 times",
    ]

    for cmd in test_commands:
        await test_command(cmd)

    print("\n" + "=" * 80)
    print("Research complete")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())

