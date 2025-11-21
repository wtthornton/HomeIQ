#!/usr/bin/env python3
"""Test MQTT connection WITHOUT authentication (anonymous)"""

import os
import sys
import time
from pathlib import Path

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / "infrastructure" / "env.ai-automation"
load_dotenv(env_path)

MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

print("🧪 Testing MQTT with ANONYMOUS access (no username/password)")
print(f"Broker: {MQTT_BROKER}:{MQTT_PORT}")

connected = False

def on_connect(client, userdata, flags, rc):
    global connected
    if rc == 0:
        print("✅ Connected anonymously!")
        connected = True
    else:
        print(f"❌ Connection failed (code: {rc})")

client = mqtt.Client(client_id="test-anonymous")
# NO username/password set
client.on_connect = on_connect

try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    time.sleep(2)
    client.loop_stop()

    if connected:
        print("\n✅ Anonymous MQTT access works!")
        print("   You can remove MQTT_USERNAME and MQTT_PASSWORD from config")
    else:
        print("\n❌ Anonymous access not allowed")
        print("   MQTT credentials required")

except Exception as e:
    print(f"❌ Error: {e}")

sys.exit(0 if connected else 1)

