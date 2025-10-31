#!/usr/bin/env python3
"""Get HomeIQ conversation agent ID from Home Assistant."""
import os
import sys
from pathlib import Path

# Load .env if it exists
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, value = line.strip().split("=", 1)
            os.environ[key.strip()] = value.strip()

# Get HA credentials
ha_url = os.environ.get("HA_URL") or os.environ.get("HOME_ASSISTANT_URL", "")
ha_token = os.environ.get("HA_TOKEN") or os.environ.get("HOME_ASSISTANT_TOKEN", "")

if not ha_url or not ha_token:
    print("Error: HA_URL and HA_TOKEN must be set", file=sys.stderr)
    sys.exit(1)

# Try to fetch agents via API
try:
    import requests
    url = f"{ha_url.rstrip('/')}/api/conversation/agents"
    headers = {
        "Authorization": f"Bearer {ha_token}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        agents = response.json()
        # Find HomeIQ
        homeiq = next((a for a in agents if a.get("name") == "HomeIQ"), None)
        
        if homeiq:
            print(f"✅ HomeIQ Agent Found via API:")
            print(f"   Name: {homeiq['name']}")
            print(f"   ID: {homeiq['id']}")
            print(f"\n💡 Set in .env as:")
            print(f"   HA_CONVERSATION_AGENT_ID={homeiq['id']}")
        else:
            print("ℹ️  HomeIQ agent not found in API response. Available agents:")
            for agent in agents:
                print(f"   - {agent.get('name')}: {agent.get('id')}")
    elif response.status_code == 404:
        print("⚠️  API endpoint /api/conversation/agents not available (404)")
        print("   This might not be supported in your Home Assistant version.")
        print("\n📋 Manual Method to Get HomeIQ Agent ID:")
        print("   1. Open Home Assistant UI")
        print("   2. Go to Settings → Voice Assistants (Assist)")
        print("   3. Find 'HomeIQ' in the list")
        print("   4. Click the three-dot menu (⋮) next to HomeIQ")
        print("   5. Select 'Copy ID'")
        print("   6. Add to .env: HA_CONVERSATION_AGENT_ID=<pasted_id>")
        print("\n   Alternatively, the agent ID might be something like:")
        print("   - conversation.homeiq")
        print("   - homeiq")
        print("   - Or check your Assist configuration in Home Assistant")
    else:
        print(f"⚠️  API returned status {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        print("\n📋 Try manual method (see instructions above)")
        
except requests.exceptions.RequestException as e:
    print(f"❌ Error connecting to Home Assistant: {e}", file=sys.stderr)
    print("\n📋 Manual Method to Get HomeIQ Agent ID:")
    print("   1. Open Home Assistant UI")
    print("   2. Go to Settings → Voice Assistants (Assist)")
    print("   3. Find 'HomeIQ' in the list")
    print("   4. Click the three-dot menu (⋮) next to HomeIQ")
    print("   5. Select 'Copy ID'")
    print("   6. Add to .env: HA_CONVERSATION_AGENT_ID=<pasted_id>")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}", file=sys.stderr)
    sys.exit(1)

