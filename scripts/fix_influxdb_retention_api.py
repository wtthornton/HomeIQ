#!/usr/bin/env python3
"""
Fix InfluxDB retention policies using REST API directly.

This script uses the InfluxDB REST API to set retention policies.
"""
import os
import sys
import requests
import json

# Configuration
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', 'ha-ingestor-token')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', 'ha-ingestor')

def get_bucket_id(bucket_name):
    """Get bucket ID by name"""
    url = f"{INFLUXDB_URL}/api/v2/buckets"
    headers = {
        "Authorization": f"Token {INFLUXDB_TOKEN}",
        "Content-Type": "application/json"
    }
    params = {"org": INFLUXDB_ORG}
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"  ❌ Error getting buckets: {response.status_code} - {response.text}")
        return None
    
    buckets = response.json().get("buckets", [])
    for bucket in buckets:
        if bucket.get("name") == bucket_name:
            return bucket.get("id")
    return None

def update_bucket_retention(bucket_name, retention_seconds):
    """Update bucket retention policy"""
    bucket_id = get_bucket_id(bucket_name)
    if not bucket_id:
        print(f"  ⚠️  Bucket '{bucket_name}' not found")
        return False
    
    url = f"{INFLUXDB_URL}/api/v2/buckets/{bucket_id}"
    headers = {
        "Authorization": f"Token {INFLUXDB_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Get current bucket info
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"  ❌ Error getting bucket info: {response.status_code}")
        return False
    
    bucket_data = response.json()
    
    # Update retention rules
    retention_rules = [{
        "everySeconds": retention_seconds,
        "type": "expire"
    }]
    
    bucket_data["retentionRules"] = retention_rules
    
    # Update bucket
    response = requests.patch(url, headers=headers, json=bucket_data)
    if response.status_code == 200:
        return True
    else:
        print(f"  ❌ Error updating bucket: {response.status_code} - {response.text}")
        return False

def main():
    """Main entry point"""
    print("=" * 80)
    print("FIXING INFLUXDB RETENTION POLICIES (REST API)")
    print("=" * 80)
    print()
    print(f"URL: {INFLUXDB_URL}")
    print(f"Org: {INFLUXDB_ORG}")
    print()
    
    changes_applied = []
    
    # Set retention for home_assistant_events (365 days = 31536000 seconds)
    print("Step 1: Setting retention for home_assistant_events (365 days)")
    print("-" * 80)
    if update_bucket_retention("home_assistant_events", 365 * 24 * 60 * 60):
        changes_applied.append("home_assistant_events: Set to 365 days")
        print("  ✅ Retention set to 365 days")
    print()
    
    # Set retention for weather_data (365 days = 31536000 seconds)
    print("Step 2: Setting retention for weather_data (365 days)")
    print("-" * 80)
    if update_bucket_retention("weather_data", 365 * 24 * 60 * 60):
        changes_applied.append("weather_data: Set to 365 days")
        print("  ✅ Retention set to 365 days")
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    if changes_applied:
        print("✅ Changes Applied:")
        for change in changes_applied:
            print(f"  - {change}")
    else:
        print("✅ No changes needed or changes failed")
    print()
    
    return len(changes_applied) > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

