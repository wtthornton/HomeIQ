#!/usr/bin/env python3
"""List all Home Assistant Assist agents and their pipelines."""
import os
import sys
import json
from pathlib import Path

# Try to load .env from multiple locations (check root .env first)
env_files = [
    Path(__file__).parent.parent.parent / ".env",  # Root .env first (user mentioned variables are here)
    Path(__file__).parent.parent.parent / "infrastructure" / ".env.websocket",
    Path(__file__).parent / ".env",
]

for env_file in env_files:
    if env_file.exists():
        print(f"📄 Loading environment from: {env_file}", file=sys.stderr)
        loaded_count = 0
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.strip().split("=", 1)
                key = key.strip()
                value = value.strip()
                os.environ[key] = value
                # Only show keys that might be relevant (not tokens/URLs for security)
                if "URL" in key or "TOKEN" in key:
                    print(f"  ✓ Loaded: {key} = {'*' * min(len(value), 20)}", file=sys.stderr)
                    loaded_count += 1
        if loaded_count == 0:
            print(f"  ⚠️  No URL/TOKEN variables found in {env_file}", file=sys.stderr)
        break

# Get HA credentials
ha_url = os.environ.get("HA_HTTP_URL") or os.environ.get("HOME_ASSISTANT_URL") or os.environ.get("HA_URL", "")
ha_token = os.environ.get("HA_TOKEN") or os.environ.get("HOME_ASSISTANT_TOKEN", "")

# Convert WebSocket URL to HTTP URL if needed
if ha_url:
    # Convert ws:// to http:// and wss:// to https://
    ha_url = ha_url.replace("ws://", "http://").replace("wss://", "https://")
    # Remove /api/websocket suffix if present
    ha_url = ha_url.replace("/api/websocket", "").rstrip("/")
    # Also try default if it's a common pattern
    if not ha_url or ha_url.startswith("http://192.168.1"):
        # Check for common HA default
        pass

if not ha_url or not ha_token:
    print("❌ Error: HA URL and Token must be set", file=sys.stderr)
    print("\nFound environment variables:", file=sys.stderr)
    print(f"  HA_HTTP_URL: {os.environ.get('HA_HTTP_URL', 'Not set')}", file=sys.stderr)
    print(f"  HOME_ASSISTANT_URL: {os.environ.get('HOME_ASSISTANT_URL', 'Not set')}", file=sys.stderr)
    print(f"  HA_URL: {os.environ.get('HA_URL', 'Not set')}", file=sys.stderr)
    print(f"  HA_TOKEN: {'Set' if os.environ.get('HA_TOKEN') or os.environ.get('HOME_ASSISTANT_TOKEN') else 'Not set'}", file=sys.stderr)
    print("\nPlease set one of the following:", file=sys.stderr)
    print("  - HA_HTTP_URL or HOME_ASSISTANT_URL or HA_URL (HTTP URL like http://192.168.1.86:8123)", file=sys.stderr)
    print("  - HA_TOKEN or HOME_ASSISTANT_TOKEN", file=sys.stderr)
    print("\nOr run with environment variables:", file=sys.stderr)
    print("  $env:HA_URL='http://192.168.1.86:8123'; $env:HA_TOKEN='your_token'; python list_agents.py", file=sys.stderr)
    sys.exit(1)

# Query the API
try:
    import requests
    url = f"{ha_url.rstrip('/')}/api/conversation/agents"
    headers = {
        "Authorization": f"Bearer {ha_token}",
        "Content-Type": "application/json"
    }
    
    print(f"🔍 Querying: {url}", file=sys.stderr)
    response = requests.get(url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        agents = response.json()
        
        if not agents:
            print("ℹ️  No agents found. You may need to create assistants in Home Assistant.", file=sys.stderr)
            print("\nTo create assistants:", file=sys.stderr)
            print("  1. Open Home Assistant UI", file=sys.stderr)
            print("  2. Go to Settings → Voice Assistants (Assist)", file=sys.stderr)
            print("  3. Click 'Create Assistant'", file=sys.stderr)
            sys.exit(0)
        
        print(f"\n✅ Found {len(agents)} agent(s):\n")
        
        # Output as JSON for easy parsing
        output = {
            "agents": [],
            "summary": {
                "total_agents": len(agents),
                "ha_url": ha_url
            }
        }
        
        for idx, agent in enumerate(agents, start=1):
            agent_name = agent.get("name", "Unknown")
            agent_id = agent.get("id", "Unknown")
            agent_type = agent.get("type", "Unknown")
            
            # Try to get pipeline information if available
            pipeline_info = agent.get("pipeline", {})
            pipeline_id = agent.get("pipeline_id") or pipeline_info.get("id") or "N/A"
            
            agent_info = {
                "number": idx,
                "name": agent_name,
                "id": agent_id,
                "type": agent_type,
                "pipeline_id": pipeline_id,
                "raw_data": agent
            }
            output["agents"].append(agent_info)
            
            # Pretty print
            print(f"{idx}. {agent_name}")
            print(f"   ID: {agent_id}")
            print(f"   Type: {agent_type}")
            print(f"   Pipeline ID: {pipeline_id}")
            if "description" in agent:
                print(f"   Description: {agent.get('description')}")
            print()
        
        # Show summary table
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"{'#':<3} {'Agent Name':<30} {'Agent ID':<35} {'Pipeline ID':<30}")
        print("-"*80)
        for agent in output["agents"]:
            print(f"{agent['number']:<3} {agent['name']:<30} {agent['id']:<35} {agent['pipeline_id']:<30}")
        
        # Also output JSON for programmatic use
        print("\n" + "="*80)
        print("JSON Output (for programmatic use)")
        print("="*80)
        print(json.dumps(output, indent=2))
        
        # Show usage examples
        print("\n" + "="*80)
        print("API Usage Examples")
        print("="*80)
        for agent in output["agents"]:
            pipeline_param = f'"{agent["pipeline_id"]}"' if agent["pipeline_id"] != "N/A" else "null  # (use default)"
            print(f"\n# Example: Use '{agent['name']}' Assistant")
            print("POST /api/conversation/process")
            print("Content-Type: application/json")
            print("Authorization: Bearer YOUR_TOKEN")
            print()
            print(json.dumps({
                "text": "Turn on the living room lights",
                "language": "en",
                "pipeline": agent["pipeline_id"] if agent["pipeline_id"] != "N/A" else None
            }, indent=2))
            
        print("\n" + "="*80)
        print("Python Code Example")
        print("="*80)
        print("""
import aiohttp

async def call_assistant(pipeline_id, text):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "{}/api/conversation/process".format(ha_url),
            headers={{"Authorization": "Bearer YOUR_TOKEN"}},
            json={{"text": text, "language": "en", "pipeline": pipeline_id}}
        ) as response:
            return await response.json()
""".format(ha_url=ha_url))
            
    elif response.status_code == 404:
        print("⚠️  API endpoint /api/conversation/agents not available (404)", file=sys.stderr)
        print("\nFor HA 2025.10, this endpoint may have changed.", file=sys.stderr)
        print("\nTrying alternative methods...", file=sys.stderr)
        
        # Try to verify connectivity first
        try:
            config_response = requests.get(
                f"{ha_url.rstrip('/')}/api/config",
                headers=headers,
                timeout=10
            )
            if config_response.status_code == 200:
                config = config_response.json()
                ha_version = config.get("version", "Unknown")
                print(f"✅ Connected to Home Assistant {ha_version}", file=sys.stderr)
            else:
                print(f"⚠️  Could not verify HA version (status: {config_response.status_code})", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  Could not verify connectivity: {e}", file=sys.stderr)
        
        # Try alternative endpoints for HA 2025.10+
        alternative_endpoints = [
            "/api/conversation/pipelines",
            "/api/conversation/list",
            "/api/config/integrations",  # Check if Assist integration is configured
        ]
        
        for alt_endpoint in alternative_endpoints:
            try:
                alt_url = f"{ha_url.rstrip('/')}{alt_endpoint}"
                print(f"🔍 Trying alternative endpoint: {alt_url}", file=sys.stderr)
                alt_response = requests.get(alt_url, headers=headers, timeout=10)
                if alt_response.status_code == 200:
                    print(f"✅ Alternative endpoint {alt_endpoint} works! Processing response...", file=sys.stderr)
                    data = alt_response.json()
                    
                    # Handle pipelines endpoint (likely structure for HA 2025.10)
                    if alt_endpoint == "/api/conversation/pipelines":
                        if isinstance(data, list):
                            agents = data
                        elif isinstance(data, dict) and "pipelines" in data:
                            agents = data["pipelines"]
                        elif isinstance(data, dict):
                            # Convert pipeline dict to list format
                            agents = [data] if data else []
                        else:
                            agents = []
                        
                        if agents:
                            print(f"\n✅ Found {len(agents)} pipeline(s)/agent(s):\n")
                            for idx, agent in enumerate(agents, start=1):
                                if isinstance(agent, dict):
                                    agent_id = agent.get("id") or agent.get("conversation_language") or f"pipeline_{idx}"
                                    agent_name = agent.get("name") or agent.get("conversation_engine") or f"Pipeline {idx}"
                                    print(f"{idx}. {agent_name}")
                                    print(f"   ID: {agent_id}")
                                    if "language" in agent:
                                        print(f"   Language: {agent['language']}")
                                    print()
                                else:
                                    print(f"{idx}. {agent}")
                            sys.exit(0)
                        else:
                            print(f"⚠️  No agents found in {alt_endpoint} response", file=sys.stderr)
                    elif alt_endpoint == "/api/config/integrations":
                        # Check for Assist/Conversation integrations
                        assist_integrations = []
                        if isinstance(data, list):
                            assist_integrations = [item for item in data if isinstance(item, dict) and (
                                "conversation" in item.get("domain", "").lower() or
                                "assist" in item.get("domain", "").lower() or
                                "assistant" in item.get("title", "").lower()
                            )]
                        
                        if assist_integrations:
                            print(f"\n✅ Found {len(assist_integrations)} Assist/Conversation integration(s):\n")
                            for idx, integration in enumerate(assist_integrations, start=1):
                                print(f"{idx}. {integration.get('title', integration.get('domain', 'Unknown'))}")
                                print(f"   Domain: {integration.get('domain', 'N/A')}")
                                if "config_entry_id" in integration:
                                    print(f"   Config Entry ID: {integration.get('config_entry_id')}")
                                print()
                            print("\n⚠️  Note: The /api/conversation/agents endpoint is not available in HA 2025.10.4", file=sys.stderr)
                            print("You may need to create assistants manually in the UI or check HA documentation for the new API.", file=sys.stderr)
                            sys.exit(0)
                        else:
                            print("⚠️  No Assist/Conversation integrations found", file=sys.stderr)
                            print("You may need to install and configure the Assist integration first.", file=sys.stderr)
                    else:
                        # For other endpoints, try to parse as agents
                        if isinstance(data, list) and data:
                            print(f"\n✅ Found {len(data)} item(s) in {alt_endpoint}:\n")
                            for idx, item in enumerate(data[:10], start=1):  # Limit to first 10
                                if isinstance(item, dict):
                                    print(f"{idx}. {item}")
                                else:
                                    print(f"{idx}. {str(item)[:100]}")
                            sys.exit(0)
                else:
                    print(f"⚠️  {alt_endpoint} returned {alt_response.status_code}", file=sys.stderr)
            except Exception as e:
                print(f"⚠️  {alt_endpoint} failed: {e}", file=sys.stderr)
        
        print("\nFor HA 2025.10, try the following:", file=sys.stderr)
        print("  1. Open Home Assistant UI", file=sys.stderr)
        print("  2. Go to Settings → Voice Assistants", file=sys.stderr)
        print("  3. View your assistants and note their configuration", file=sys.stderr)
        print("\nYou can also check available endpoints at:", file=sys.stderr)
        print(f"  {ha_url}/api/", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"❌ API returned status {response.status_code}", file=sys.stderr)
        print(f"Response: {response.text[:500]}", file=sys.stderr)
        sys.exit(1)
        
except requests.exceptions.RequestException as e:
    print(f"❌ Error connecting to Home Assistant: {e}", file=sys.stderr)
    print(f"\nPlease verify:", file=sys.stderr)
    print(f"  - HA_URL is correct: {ha_url}", file=sys.stderr)
    print(f"  - HA_TOKEN is valid and has proper permissions", file=sys.stderr)
    print(f"  - Home Assistant is accessible from this machine", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)

