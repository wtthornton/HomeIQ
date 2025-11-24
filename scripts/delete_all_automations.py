#!/usr/bin/env python3
"""
Delete all automations in Home Assistant via API.

DISCOVERY (Oct 2025): There IS an API endpoint to delete automations!
Use the 'id' from automation attributes, NOT the entity_id.

Correct: DELETE /api/config/automation/config/{id-from-attributes}
Wrong:   DELETE /api/config/automation/config/{entity_id}
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
import aiohttp

# Load environment variables from .env file
load_dotenv()


async def main():
    # Get Home Assistant configuration from environment variables
    # Support both standardized and legacy variable names
    url = (
        os.getenv('HOME_ASSISTANT_URL') or 
        os.getenv('HA_HTTP_URL') or 
        os.getenv('HA_URL')
    )
    token = (
        os.getenv('HOME_ASSISTANT_TOKEN') or 
        os.getenv('HA_TOKEN')
    )
    
    # Validate configuration
    if not url:
        print("ERROR: Home Assistant URL not found in .env file")
        print("Please set HOME_ASSISTANT_URL (or HA_HTTP_URL/HA_URL for legacy)")
        sys.exit(1)
    
    if not token:
        print("ERROR: Home Assistant token not found in .env file")
        print("Please set HOME_ASSISTANT_TOKEN (or HA_TOKEN for legacy)")
        sys.exit(1)
    
    # Normalize URL (remove trailing slash, ensure http/https)
    url = url.rstrip('/').replace('ws://', 'http://').replace('wss://', 'https://')
    
    print(f"Connecting to {url}...")
    print()
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    async with aiohttp.ClientSession() as session:
        # Test connection first
        try:
            async with session.get(f"{url}/api/", headers=headers) as resp:
                if resp.status == 401:
                    print("ERROR: Authentication failed. Please check your token.")
                    sys.exit(1)
                elif resp.status != 200:
                    print(f"ERROR: Connection failed with status {resp.status}")
                    sys.exit(1)
        except aiohttp.ClientError as e:
            print(f"ERROR: Failed to connect to Home Assistant: {e}")
            sys.exit(1)
        
        # Get all automations
        try:
            async with session.get(f"{url}/api/states", headers=headers) as resp:
                if resp.status != 200:
                    print(f"ERROR: Failed to fetch states (HTTP {resp.status})")
                    text = await resp.text()
                    print(f"Response: {text[:200]}")
                    sys.exit(1)
                states = await resp.json()
                automations = [s for s in states if s.get('entity_id', '').startswith('automation.')]
        except aiohttp.ClientError as e:
            print(f"ERROR: Failed to fetch automations: {e}")
            sys.exit(1)
        
        print(f"Found {len(automations)} automations")
        print()
        
        if not automations:
            print("No automations to delete.")
            return
        
        # Display what will be deleted
        print("Automations to delete:")
        for auto in automations[:10]:  # Show first 10
            entity_id = auto.get('entity_id')
            attrs = auto.get('attributes', {})
            friendly_name = attrs.get('friendly_name', entity_id)
            auto_id = attrs.get('id')
            print(f"  - {entity_id}: {friendly_name} (id: {auto_id})")
        if len(automations) > 10:
            print(f"  ... and {len(automations) - 10} more")
        print()
        
        # Confirmation
        confirm = input(f"Type 'DELETE ALL' to delete {len(automations)} automations: ")
        
        if confirm != "DELETE ALL":
            print("Cancelled.")
            return
        
        print()
        print("Deleting automations...")
        print()
        
        # Delete each automation using the 'id' from attributes
        success = 0
        failed = 0
        
        for auto in automations:
            entity_id = auto.get('entity_id')
            attrs = auto.get('attributes', {})
            friendly_name = attrs.get('friendly_name', entity_id)
            auto_id = attrs.get('id')
            
            if not auto_id:
                print(f"SKIPPED - {entity_id}: No ID found in attributes")
                failed += 1
                continue
            
            # Use the ID from attributes
            async with session.delete(f"{url}/api/config/automation/config/{auto_id}", 
                                    headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get('result') == 'ok':
                        success += 1
                        print(f"OK - Deleted {entity_id}: {friendly_name}")
                    else:
                        failed += 1
                        print(f"FAILED - {entity_id}: Unexpected response")
                else:
                    failed += 1
                    text = await resp.text()
                    print(f"FAILED - {entity_id}: HTTP {resp.status} - {text[:100]}")
        
        print()
        print("=" * 60)
        print(f"Completed: {success} deleted, {failed} failed out of {len(automations)} total")
        print("=" * 60)
        print()
        
        # Verify deletion by checking remaining automations
        print("Verifying deletion...")
        try:
            async with session.get(f"{url}/api/states", headers=headers) as resp:
                if resp.status == 200:
                    states = await resp.json()
                    remaining = [s for s in states if s.get('entity_id', '').startswith('automation.')]
                    print(f"Remaining automations: {len(remaining)}")
                    if len(remaining) == 0:
                        print("*** ALL AUTOMATIONS DELETED SUCCESSFULLY! ***")
                    else:
                        print(f"WARNING: {len(remaining)} automations still remain")
                        for auto in remaining:
                            print(f"  - {auto.get('entity_id')}")
        except Exception as e:
            print(f"Warning: Could not verify deletion: {e}")


if __name__ == "__main__":
    asyncio.run(main())

