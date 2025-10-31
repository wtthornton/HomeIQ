#!/usr/bin/env python3
"""Test deployment by checking services and triggering discovery"""

import requests
import time
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

print("=" * 80)
print("🧪 Testing Deployment")
print("=" * 80)

# Test 1: Check service health
print("\n1️⃣  Checking service health...")
services = {
    "Data API": "http://localhost:8006/health",
    "WebSocket Ingestion": "http://localhost:8001/health",
    "Dashboard": "http://localhost:3000"
}

all_healthy = True
for name, url in services.items():
    try:
        r = requests.get(url, timeout=5)
        status = "✅ Healthy" if r.status_code == 200 else f"❌ Status {r.status_code}"
        print(f"   {name}: {status}")
        if r.status_code != 200:
            all_healthy = False
    except Exception as e:
        print(f"   {name}: ❌ Error - {e}")
        all_healthy = False

if not all_healthy:
    print("\n❌ Some services are not healthy. Please check logs.")
    sys.exit(1)

# Test 2: Check device count before discovery
print("\n2️⃣  Checking current device count...")
try:
    r = requests.get("http://localhost:8006/api/devices?limit=5", timeout=5)
    if r.status_code == 200:
        data = r.json()
        device_count = data.get("count", 0)
        print(f"   Current devices: {device_count}")
    else:
        print(f"   ❌ Error getting devices: {r.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Trigger discovery
print("\n3️⃣  Triggering device discovery...")
try:
    r = requests.post("http://localhost:8001/api/v1/discovery/trigger", timeout=60)
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ Discovery triggered successfully")
        print(f"   Devices discovered: {data.get('devices_discovered', 0)}")
        print(f"   Entities discovered: {data.get('entities_discovered', 0)}")
    else:
        print(f"   ⚠️  Discovery endpoint returned: {r.status_code}")
        print(f"   Response: {r.text[:200]}")
except Exception as e:
    print(f"   ⚠️  Could not trigger discovery: {e}")
    print("   (This is okay - discovery may happen automatically)")

# Test 4: Check device count after discovery
print("\n4️⃣  Waiting 5 seconds for devices to be stored...")
time.sleep(5)

print("   Checking device count again...")
try:
    r = requests.get("http://localhost:8006/api/devices?limit=5", timeout=5)
    if r.status_code == 200:
        data = r.json()
        device_count = data.get("count", 0)
        print(f"   Devices found: {device_count}")
        if device_count > 0:
            print("   ✅ Devices are being discovered!")
        else:
            print("   ⚠️  No devices yet - discovery may still be in progress")
    else:
        print(f"   ❌ Error getting devices: {r.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 80)
print("✅ Deployment test complete!")
print("=" * 80)
print("\n💡 Next steps:")
print("   1. Check the dashboard at http://localhost:3000")
print("   2. Devices should appear after discovery completes")
print("   3. The integration field should now be properly populated")

