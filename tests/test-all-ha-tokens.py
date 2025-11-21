#!/usr/bin/env python3
"""Test all 3 HA tokens from .env to find which works best"""

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load main .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

HA_URL = "http://192.168.1.86:8123"

tokens = {
    "HOME_ASSISTANT_TOKEN": os.getenv("HOME_ASSISTANT_TOKEN"),
    "NABU_CASA_TOKEN": os.getenv("NABU_CASA_TOKEN"),
    "LOCAL_HA_TOKEN": os.getenv("LOCAL_HA_TOKEN"),
}

print("=" * 70)
print("🧪 Testing All 3 HA Tokens")
print("=" * 70)
print(f"HA URL: {HA_URL}\n")

results = {}

for token_name, token_value in tokens.items():
    if not token_value:
        print(f"⚠️  {token_name}: NOT SET")
        continue

    print(f"\n{'=' * 70}")
    print(f"Testing: {token_name}")
    print(f"Token: {token_value[:30]}... (length: {len(token_value)})")
    print(f"{'=' * 70}")

    headers = {
        "Authorization": f"Bearer {token_value}",
        "Content-Type": "application/json",
    }

    tests = {
        "api_status": False,
        "config": False,
        "states": False,
        "services": False,
        "automations": False,
    }

    # Test 1: API Status
    try:
        response = requests.get(f"{HA_URL}/api/", headers=headers, timeout=5)
        if response.status_code == 200:
            print("  ✅ API Status: PASS")
            tests["api_status"] = True
        else:
            print(f"  ❌ API Status: FAIL ({response.status_code})")
    except Exception as e:
        print(f"  ❌ API Status: ERROR - {e}")

    # Test 2: Config
    try:
        response = requests.get(f"{HA_URL}/api/config", headers=headers, timeout=5)
        if response.status_code == 200:
            config = response.json()
            print(f"  ✅ Config: PASS (HA {config.get('version', 'unknown')})")
            tests["config"] = True
        else:
            print(f"  ❌ Config: FAIL ({response.status_code})")
    except Exception as e:
        print(f"  ❌ Config: ERROR - {e}")

    # Test 3: States
    try:
        response = requests.get(f"{HA_URL}/api/states", headers=headers, timeout=5)
        if response.status_code == 200:
            states = response.json()
            print(f"  ✅ States: PASS ({len(states)} entities)")
            tests["states"] = True
        else:
            print(f"  ❌ States: FAIL ({response.status_code})")
    except Exception as e:
        print(f"  ❌ States: ERROR - {e}")

    # Test 4: Services
    try:
        response = requests.get(f"{HA_URL}/api/services", headers=headers, timeout=5)
        if response.status_code == 200:
            print("  ✅ Services: PASS")
            tests["services"] = True
        else:
            print(f"  ❌ Services: FAIL ({response.status_code})")
    except Exception as e:
        print(f"  ❌ Services: ERROR - {e}")

    # Test 5: Automations (try different endpoints)
    automation_endpoints = [
        "/api/config/automation/config",
        "/api/states?domain=automation",
        "/api/services/automation",
    ]

    for endpoint in automation_endpoints:
        try:
            response = requests.get(f"{HA_URL}{endpoint}", headers=headers, timeout=5)
            if response.status_code == 200:
                print(f"  ✅ Automations ({endpoint}): PASS")
                tests["automations"] = True
                break
            else:
                print(f"  ⚠️  {endpoint}: {response.status_code}")
        except Exception:
            print(f"  ⚠️  {endpoint}: ERROR")

    # Store results
    passed = sum(tests.values())
    total = len(tests)
    results[token_name] = {
        "tests": tests,
        "score": f"{passed}/{total}",
        "token": token_value,
    }

    print(f"\n  📊 Score: {passed}/{total} tests passed")

# Summary
print("\n" + "=" * 70)
print("📊 FINAL SUMMARY")
print("=" * 70)

for token_name, result in results.items():
    passed = sum(result["tests"].values())
    total = len(result["tests"])
    status = "✅ BEST" if passed == total else "⚠️ PARTIAL" if passed > 0 else "❌ FAIL"
    print(f"{token_name:25} {result['score']:5} {status}")

# Recommend best token
best_token_name = max(results.items(), key=lambda x: sum(x[1]["tests"].values()))[0]
best_token_value = results[best_token_name]["token"]

print("\n" + "=" * 70)
print(f"🏆 RECOMMENDED TOKEN: {best_token_name}")
print("=" * 70)
print(f"Token: {best_token_value[:40]}...")
print(f"Tests passed: {results[best_token_name]['score']}")
print("\n✅ Use this token in infrastructure/env.ai-automation")
print(f"   HA_TOKEN={best_token_value}")

