#!/usr/bin/env python3
"""Test real query to verify device names"""
import asyncio
import json
import os
import sys

import aiohttp


async def test_real_query():
    """Test the actual API with a real query"""
    print("=" * 120)
    print("TESTING REAL QUERY: Flash all the Office Hue lights")
    print("=" * 120)

    url = "http://localhost:8024/api/v1/ask-ai/query"
    query = "Flash all the Office Hue lights for 30 seconds at the top of every hour"

    payload = {
        "query": query,
        "user_id": "test_user",
    }

    # Get API key from environment or use default
    api_key = os.getenv("AI_AUTOMATION_API_KEY", "hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR")

    headers = {
        "Content-Type": "application/json",
        "X-HomeIQ-API-Key": api_key,
    }

    try:
        async with aiohttp.ClientSession() as session:
            print(f"\nSending query: '{query}'")
            print(f"URL: {url}")

            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status == 200:
                    result = await response.json()

                    print(f"\n[OK] Response Status: {response.status}")
                    print("\n" + "=" * 120)
                    print("RESPONSE ANALYSIS")
                    print("=" * 120)

                    # Check for suggestions
                    suggestions = result.get("suggestions", [])
                    print(f"\nFound {len(suggestions)} suggestion(s)")

                    for i, suggestion in enumerate(suggestions, 1):
                        print(f"\n--- Suggestion {i} ---")
                        print(f"Description: {suggestion.get('description', 'N/A')}")

                        # Check devices_involved
                        devices_involved = suggestion.get("devices_involved", [])
                        print(f"\nDevices Involved ({len(devices_involved)}):")
                        for device in devices_involved:
                            print(f"  - {device}")

                        # Check if we see friendly names
                        has_friendly_names = any(
                            "Office" in device or "Back" in device or "Front" in device
                            for device in devices_involved
                        )

                        if has_friendly_names:
                            print("\n[PASS] Found friendly device names (Office Back Left, etc.)")
                        else:
                            print("\n[WARN] No friendly names found - still showing generic names")
                            print("       This might indicate:")
                            print("       1. Entity Registry not being queried")
                            print("       2. name_by_user not set in HA")
                            print("       3. Enrichment not including name fields")

                        # Check validated_entities
                        validated_entities = suggestion.get("validated_entities", {})
                        if validated_entities:
                            print(f"\nValidated Entities ({len(validated_entities)}):")
                            for device_name, entity_id in list(validated_entities.items())[:5]:
                                print(f"  {device_name} -> {entity_id}")

                    # Check for clarification needed
                    clarification = result.get("clarification_needed")
                    if clarification:
                        print("\n" + "=" * 120)
                        print("CLARIFICATION NEEDED")
                        print("=" * 120)
                        print(json.dumps(clarification, indent=2))

                    return True
                error_text = await response.text()
                print(f"\n[FAIL] Response Status: {response.status}")
                print(f"Error: {error_text}")
                return False

    except Exception as e:
        print(f"\n[ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_real_query())
    sys.exit(0 if success else 1)

