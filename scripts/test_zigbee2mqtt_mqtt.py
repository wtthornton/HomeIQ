#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify Zigbee2MQTT MQTT topics.

This script connects to the MQTT broker and subscribes to Zigbee2MQTT topics
to verify if bridge/devices topic exists and receives messages.
"""

import json
import os
import sys
import time
from typing import Any

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("ERROR: paho-mqtt not installed. Install with: pip install paho-mqtt")
    sys.exit(1)

# Configuration
MQTT_BROKER = "192.168.1.86"
MQTT_PORT = 1883
BASE_TOPIC = "zigbee2mqtt"
TOPICS_TO_TEST = [
    f"{BASE_TOPIC}/bridge/devices",
    f"{BASE_TOPIC}/bridge/response/device/list",
    f"{BASE_TOPIC}/bridge/groups",
    f"{BASE_TOPIC}/bridge/info",
]


def on_connect(client, userdata, flags, rc):
    """MQTT connection callback."""
    if rc == 0:
        print(f"[OK] Connected to MQTT broker {MQTT_BROKER}:{MQTT_PORT}")
        # Subscribe to all test topics
        for topic in TOPICS_TO_TEST:
            client.subscribe(topic)
            print(f"[SUB] Subscribed to: {topic}")
        
        # Request device list
        request_topic = f"{BASE_TOPIC}/bridge/request/device/list"
        client.publish(request_topic, "{}")
        print(f"[PUB] Published request to: {request_topic}")
    else:
        print(f"[FAIL] Failed to connect to MQTT broker (code: {rc})")


def on_message(client, userdata, msg):
    """MQTT message callback."""
    topic = msg.topic
    payload = msg.payload.decode('utf-8')
    
    print(f"\n{'='*80}")
    print(f"[MSG] Message received on topic: {topic}")
    print(f"[SIZE] Payload size: {len(payload)} bytes")
    print(f"{'='*80}")
    
    # Try to parse as JSON
    try:
        data = json.loads(payload)
        
        # If it's bridge/devices, show device count
        if topic.endswith("/bridge/devices") or topic.endswith("/bridge/response/device/list"):
            if isinstance(data, list):
                print(f"[OK] Device list received: {len(data)} devices")
                if data:
                    print(f"   First device: {data[0].get('friendly_name', 'unknown')} ({data[0].get('ieee_address', 'unknown')})")
            elif isinstance(data, dict):
                # Check for nested data/result
                if "data" in data and isinstance(data["data"], list):
                    devices = data["data"]
                    print(f"[OK] Device list received (nested): {len(devices)} devices")
                    if devices:
                        print(f"   First device: {devices[0].get('friendly_name', 'unknown')} ({devices[0].get('ieee_address', 'unknown')})")
                elif "result" in data and isinstance(data["result"], list):
                    devices = data["result"]
                    print(f"[OK] Device list received (result): {len(devices)} devices")
                    if devices:
                        print(f"   First device: {devices[0].get('friendly_name', 'unknown')} ({devices[0].get('ieee_address', 'unknown')})")
                else:
                    print(f"[WARN] Unexpected format: {type(data)}")
                    print(f"   Keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
        
        # Show preview of payload
        payload_preview = json.dumps(data, indent=2)[:500]
        print(f"\n[PREVIEW] Payload preview:\n{payload_preview}...")
        
    except json.JSONDecodeError:
        print(f"[WARN] Non-JSON payload: {payload[:200]}")
    
    print(f"{'='*80}\n")


def main():
    """Main function."""
    print("="*80)
    print("Zigbee2MQTT MQTT Topic Test Script")
    print("="*80)
    print(f"Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"Base Topic: {BASE_TOPIC}")
    print(f"Testing topics: {', '.join(TOPICS_TO_TEST)}")
    print("="*80)
    print("\n[INFO] Connecting to MQTT broker...\n")
    
    # Create MQTT client
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        # Connect
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        # Start loop in background thread
        client.loop_start()
        
        # Wait for messages (30 seconds)
        print("\n[INFO] Listening for messages (30 seconds)...\n")
        time.sleep(30)
        
        # Stop loop
        client.loop_stop()
        client.disconnect()
        
        print("\n[OK] Test completed")
        
    except KeyboardInterrupt:
        print("\n\n[WARN] Interrupted by user")
        client.loop_stop()
        client.disconnect()
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
