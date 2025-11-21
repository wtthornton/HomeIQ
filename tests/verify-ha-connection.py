#!/usr/bin/env python3
"""
Test Home Assistant API connection.
Verifies token authentication and API access.
"""

import sys
from pathlib import Path

import requests

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / "infrastructure" / "env.ai-automation"
    load_dotenv(env_path)
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
    sys.exit(1)

import os

# Configuration
HA_URL = os.getenv("HA_URL")
HA_TOKEN = os.getenv("HA_TOKEN")

print("=" * 60)
print("🧪 Testing Home Assistant API Connection")
print("=" * 60)
print(f"HA URL: {HA_URL}")
print(f"Token: {HA_TOKEN[:20]}... (length: {len(HA_TOKEN) if HA_TOKEN else 0})")
print("=" * 60)

# Verify credentials loaded
if not HA_URL or not HA_TOKEN:
    print("❌ HA credentials not configured in env.ai-automation")
    print(f"   HA_URL: {'✅' if HA_URL else '❌ MISSING'}")
    print(f"   HA_TOKEN: {'✅' if HA_TOKEN else '❌ MISSING'}")
    sys.exit(1)

# Test results
test_results = {
    "connection": False,
    "authentication": False,
    "api_call": False,
    "automations_access": False,
}

headers = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

# Test 1: Basic API status
try:
    print("\n⏳ Test 1: Checking HA API status...")
    response = requests.get(f"{HA_URL}/api/", headers=headers, timeout=10)

    if response.status_code == 200:
        print(f"✅ API responding: {response.json().get('message', 'OK')}")
        test_results["connection"] = True
        test_results["authentication"] = True
        test_results["api_call"] = True
    elif response.status_code == 401:
        print("❌ Authentication failed - Invalid token")
        print("   Please check your HA_TOKEN in env.ai-automation")
    else:
        print(f"⚠️  Unexpected status code: {response.status_code}")

except requests.exceptions.ConnectionError:
    print(f"❌ Cannot connect to {HA_URL}")
    print("\nTroubleshooting:")
    print("  1. Verify Home Assistant is running")
    print("  2. Check HA_URL is correct (include http:// and :8123)")
    print("  3. Check firewall isn't blocking port 8123")
    print(f"  4. Try in browser: {HA_URL}")
    sys.exit(1)

except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Test 2: Get automation config (API we'll use for deployment)
try:
    print("\n⏳ Test 2: Testing automation config endpoint...")
    response = requests.get(
        f"{HA_URL}/api/config/automation/config",
        headers=headers,
        timeout=10,
    )

    if response.status_code == 200:
        automations = response.json()
        print(f"✅ Automation API accessible - Found {len(automations)} existing automations")
        test_results["automations_access"] = True

        # Show sample
        if automations:
            print(f"   Example: {automations[0].get('alias', 'Unnamed')}")
    else:
        print(f"⚠️  Automation API returned {response.status_code}")
        print(f"   Response: {response.text[:200]}")

except Exception as e:
    print(f"⚠️  Automation API error: {e}")

# Test 3: Get HA config info
try:
    print("\n⏳ Test 3: Getting Home Assistant config info...")
    response = requests.get(
        f"{HA_URL}/api/config",
        headers=headers,
        timeout=10,
    )

    if response.status_code == 200:
        config = response.json()
        print(f"✅ HA Version: {config.get('version', 'unknown')}")
        print(f"   Location: {config.get('location_name', 'unknown')}")
        print(f"   Timezone: {config.get('time_zone', 'unknown')}")
    else:
        print(f"⚠️  Config API returned {response.status_code}")

except Exception as e:
    print(f"⚠️  Config API error: {e}")

# Print summary
print("\n" + "=" * 60)
print("📊 TEST SUMMARY")
print("=" * 60)
print(f"Connection:           {'✅ PASS' if test_results['connection'] else '❌ FAIL'}")
print(f"Authentication:       {'✅ PASS' if test_results['authentication'] else '❌ FAIL'}")
print(f"API Call:             {'✅ PASS' if test_results['api_call'] else '❌ FAIL'}")
print(f"Automations Access:   {'✅ PASS' if test_results['automations_access'] else '❌ FAIL'}")
print("=" * 60)

if all(test_results.values()):
    print("\n🎉 All Home Assistant API tests passed!")
    print("\n✅ HA API connection verified and ready")
    sys.exit(0)
else:
    print("\n⚠️  Some tests failed. Review errors above.")
    sys.exit(1)

