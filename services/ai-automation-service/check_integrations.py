#!/usr/bin/env python3
"""Check HA integrations for conversation/assist."""
import os
import sys
import json
import requests
from pathlib import Path

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
    "Content-Type": "application/json"
}

# Try integrations endpoint
print(f"Checking integrations at: {ha_url}\n")
try:
    response = requests.get(f"{ha_url}/api/config/config_entries/entry", headers=headers, timeout=10)
    if response.status_code == 200:
        entries = response.json()
        print(f"Found {len(entries)} config entries")
        conversation_entries = [e for e in entries if 'conversation' in e.get('domain', '').lower() or 'assist' in e.get('domain', '').lower() or 'assistant' in e.get('title', '').lower()]
        if conversation_entries:
            print("\nConversation/Assist related entries:")
            for entry in conversation_entries:
                print(f"  - {entry.get('title', 'Unknown')} ({entry.get('domain', 'Unknown')})")
                print(f"    Entry ID: {json.dumps(entry, indent=4)}")
        else:
            print("\nNo conversation/assist entries found")
            print("\nAll entries:")
            for entry in entries[:10]:
                print(f"  - {entry.get('title', 'Unknown')} ({entry.get('domain', 'Unknown')})")
    else:
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")

# Also try direct conversation process to see what happens
print("\n" + "="*60)
print("Testing /api/conversation/process (POST)")
try:
    response = requests.post(
        f"{ha_url}/api/conversation/process",
        headers=headers,
        json={"text": "test", "language": "en"},
        timeout=10
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response keys: {list(data.keys())}")
        if 'response' in data:
            print(f"Response type: {data['response'].get('response_type', 'Unknown')}")
    else:
        print(f"Response: {response.text[:300]}")
except Exception as e:
    print(f"Error: {e}")

