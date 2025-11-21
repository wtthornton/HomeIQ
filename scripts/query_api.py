#!/usr/bin/env python3
"""Query Device Intelligence API to see what's in the database"""
import json

import requests

# Get devices from office area
response = requests.get("http://localhost:8028/api/devices", params={"area_name": "office"})
if response.status_code == 200:
    data = response.json()
    devices = data.get("devices", [])

    print(f"Found {len(devices)} devices in office area:")
    print("=" * 80)

    # Show first 10 devices with ALL their fields
    print("\nFirst 10 devices from office area:")
    for i, device in enumerate(devices[:10], 1):
        print(f"\nDevice {i}: {json.dumps(device, indent=2)}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)

