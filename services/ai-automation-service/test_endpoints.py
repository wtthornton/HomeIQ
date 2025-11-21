#!/usr/bin/env python3
"""Test various HA API endpoints to find conversation agents."""
import os
import sys
from pathlib import Path

import requests

# Fix Windows console encoding
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Load .env
env_file = Path(__file__).parent.parent.parent / "infrastructure" / ".env.websocket"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, value = line.strip().split("=", 1)
            os.environ[key.strip()] = value.strip()

ha_url = os.environ.get("HA_HTTP_URL") or os.environ.get("HOME_ASSISTANT_URL") or os.environ.get("HA_URL", "")
ha_url = ha_url.replace("ws://", "http://").replace("wss://", "https://").replace("/api/websocket", "").rstrip("/")
ha_token = os.environ.get("HA_TOKEN") or os.environ.get("HOME_ASSISTANT_TOKEN", "")

headers = {
    "Authorization": f"Bearer {ha_token}",
    "Content-Type": "application/json",
}

# Test various endpoints
endpoints_to_test = [
    "/api/conversation/agents",
    "/api/conversation/list",
    "/api/conversation/pipelines",
    "/api/config/integrations",
    "/api/config/config_entries",
    "/api/hassio/addons",
]

print(f"Testing endpoints against: {ha_url}\n")
for endpoint in endpoints_to_test:
    try:
        response = requests.get(f"{ha_url}{endpoint}", headers=headers, timeout=5)
        status_emoji = "✅" if response.status_code == 200 else "⚠️ " if response.status_code == 404 else "❌"
        print(f"{status_emoji} {endpoint}: {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list):
                    print(f"   → Found {len(data)} items")
                    if len(data) > 0 and isinstance(data[0], dict):
                        print(f"   → Sample keys: {list(data[0].keys())[:5]}")
                elif isinstance(data, dict):
                    print(f"   → Keys: {list(data.keys())[:10]}")
            except:
                print(f"   → Response: {response.text[:100]}")
    except Exception as e:
        print(f"❌ {endpoint}: Error - {e}")

