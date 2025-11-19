#!/usr/bin/env python3
"""
Script to identify and delete duplicate automations in Home Assistant.
"""

import requests
import json
from typing import List, Dict

# Home Assistant configuration
HA_URL = "http://192.168.1.86:8123"
HA_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIyZTNlMjg1MzVlZGY0ZDg1OWE1YTljMmYzMDJjYzUyNCIsImlhdCI6MTczMDEzMjQzOSwiZXhwIjoyMDQ1NDkyNDM5fQ.F8hKpkQf5AkUlZHWrS5HuLKYqmWxLVQCb_5M9AYcLvw"

headers = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json"
}


def list_automations() -> List[Dict]:
    """List all automations from Home Assistant."""
    url = f"{HA_URL}/api/config/automation/config"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Failed to list automations: {response.status_code}")
        print(response.text)
        return []


def list_automation_states() -> List[Dict]:
    """List all automation entity states."""
    url = f"{HA_URL}/api/states"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        states = response.json()
        # Filter for automation entities
        automations = [s for s in states if s.get('entity_id', '').startswith('automation.')]
        return automations
    else:
        print(f"❌ Failed to list states: {response.status_code}")
        return []


def delete_automation(automation_id: str) -> bool:
    """Delete an automation by ID."""
    url = f"{HA_URL}/api/config/automation/config/{automation_id}"
    response = requests.delete(url, headers=headers)
    
    if response.status_code == 200:
        print(f"✅ Deleted automation: {automation_id}")
        return True
    else:
        print(f"❌ Failed to delete {automation_id}: {response.status_code}")
        print(response.text)
        return False


def main():
    print("=" * 60)
    print("🔍 Checking for duplicate automations...")
    print("=" * 60)
    
    # List all automation states
    automations = list_automation_states()
    
    if not automations:
        print("⚠️  No automations found or failed to retrieve")
        return
    
    print(f"\n📋 Found {len(automations)} total automations:\n")
    
    # Group by friendly name
    by_name = {}
    for auto in automations:
        entity_id = auto['entity_id']
        friendly_name = auto.get('attributes', {}).get('friendly_name', 'Unknown')
        last_triggered = auto.get('attributes', {}).get('last_triggered', 'Never')
        state = auto.get('state', 'unknown')
        
        print(f"  • {friendly_name}")
        print(f"    Entity ID: {entity_id}")
        print(f"    State: {state}")
        print(f"    Last Triggered: {last_triggered}")
        print()
        
        if friendly_name not in by_name:
            by_name[friendly_name] = []
        by_name[friendly_name].append({
            'entity_id': entity_id,
            'last_triggered': last_triggered,
            'state': state
        })
    
    # Find duplicates
    duplicates = {name: autos for name, autos in by_name.items() if len(autos) > 1}
    
    if not duplicates:
        print("✅ No duplicate automations found!")
        return
    
    print("\n" + "=" * 60)
    print(f"⚠️  Found {len(duplicates)} sets of duplicate automations:")
    print("=" * 60)
    
    for name, autos in duplicates.items():
        print(f"\n🔴 Duplicate: '{name}' ({len(autos)} copies)")
        for i, auto in enumerate(autos, 1):
            print(f"  {i}. {auto['entity_id']}")
            print(f"     Last Triggered: {auto['last_triggered']}")
            print(f"     State: {auto['state']}")
        
        # Keep the most recently triggered one, or the first if none triggered
        to_keep = None
        to_delete = []
        
        # Sort by last_triggered (most recent first)
        sorted_autos = sorted(autos, key=lambda x: x['last_triggered'] or '', reverse=True)
        
        # Keep the first one (most recently triggered or first in list)
        to_keep = sorted_autos[0]
        to_delete = sorted_autos[1:]
        
        print(f"\n  ✅ Keeping: {to_keep['entity_id']} (Last triggered: {to_keep['last_triggered']})")
        print(f"  ❌ Will delete {len(to_delete)} duplicate(s):")
        for auto in to_delete:
            print(f"     • {auto['entity_id']}")
        
        # Ask for confirmation
        response = input(f"\n  Delete these {len(to_delete)} duplicate(s)? (yes/no): ")
        if response.lower() in ['yes', 'y']:
            for auto in to_delete:
                # Extract automation ID from entity_id (automation.XXXXX -> XXXXX)
                auto_id = auto['entity_id'].replace('automation.', '')
                delete_automation(auto_id)
        else:
            print("  ⏭️  Skipped")
    
    print("\n" + "=" * 60)
    print("✅ Duplicate automation cleanup complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

