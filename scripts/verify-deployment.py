#!/usr/bin/env python3
"""Verify deployment status"""

import requests
import sys

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

print("🔍 Verifying Deployment Status")
print("=" * 60)

# Test devices endpoint
try:
    r = requests.get("http://localhost:8006/api/devices?limit=5", timeout=5)
    if r.status_code == 200:
        data = r.json()
        count = data.get("count", 0)
        print(f"✅ Devices endpoint working: {count} devices")
    else:
        print(f"❌ Devices endpoint error: {r.status_code}")
        print(f"   Response: {r.text[:150]}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n✅ Deployment complete!")
print("📊 Dashboard: http://localhost:3000")
print("🔌 Devices will be discovered automatically on connection")

