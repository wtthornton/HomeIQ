#!/usr/bin/env python3
"""
Test MQTT connection to Home Assistant broker.
Verifies credentials and topic publishing work.
"""

import sys
import time
from pathlib import Path

import paho.mqtt.client as mqtt

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / "infrastructure" / "env.ai-automation"
    load_dotenv(env_path)
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
    sys.exit(1)

import os

# Configuration
MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

print("=" * 60)
print("🧪 Testing MQTT Connection to Home Assistant")
print("=" * 60)
print(f"Broker: {MQTT_BROKER}:{MQTT_PORT}")
print(f"Username: {MQTT_USERNAME}")
print("=" * 60)

# Verify credentials loaded
if not all([MQTT_BROKER, MQTT_USERNAME, MQTT_PASSWORD]):
    print("❌ MQTT credentials not configured in env.ai-automation")
    print(f"   MQTT_BROKER: {'✅' if MQTT_BROKER else '❌ MISSING'}")
    print(f"   MQTT_USERNAME: {'✅' if MQTT_USERNAME else '❌ MISSING'}")
    print(f"   MQTT_PASSWORD: {'✅' if MQTT_PASSWORD else '❌ MISSING'}")
    sys.exit(1)

# Test results
test_results = {
    "connection": False,
    "authentication": False,
    "publish": False,
    "subscribe": False,
}

messages_received = []

def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker"""
    if rc == 0:
        print("✅ Connected to MQTT broker successfully")
        test_results["connection"] = True
        test_results["authentication"] = True

        # Subscribe to test topic
        client.subscribe("ha-ai/test/#", qos=1)
        print("✅ Subscribed to ha-ai/test/#")
        test_results["subscribe"] = True

    else:
        error_messages = {
            1: "Incorrect protocol version",
            2: "Invalid client identifier",
            3: "Server unavailable",
            4: "Bad username or password",
            5: "Not authorized",
        }
        print(f"❌ Connection failed: {error_messages.get(rc, f'Unknown error {rc}')}")

def on_disconnect(client, userdata, rc):
    """Callback when disconnected"""
    if rc != 0:
        print(f"⚠️  Unexpected disconnection (code: {rc})")

def on_message(client, userdata, msg):
    """Callback when message received"""
    payload = msg.payload.decode()
    print(f"✅ Message received on {msg.topic}: {payload}")
    messages_received.append((msg.topic, payload))

def on_publish(client, userdata, mid):
    """Callback when message published"""
    print("✅ Message published successfully")
    test_results["publish"] = True

# Create client
client = mqtt.Client(client_id="ai-automation-test")
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# Set callbacks
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.on_publish = on_publish

# Test connection
try:
    print(f"\n⏳ Connecting to {MQTT_BROKER}:{MQTT_PORT}...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    # Start network loop
    client.loop_start()

    # Wait for connection
    time.sleep(2)

    if test_results["connection"]:
        # Test publishing
        print("\n⏳ Testing message publishing...")
        result = client.publish(
            "ha-ai/test/connection",
            "Hello from AI Automation Service!",
            qos=1,
        )

        # Wait for publish and receive
        time.sleep(2)

        # Check if we received our own message
        if messages_received:
            print(f"✅ Received {len(messages_received)} message(s)")
        else:
            print("⚠️  No messages received (might need to check HA MQTT subscriptions)")

    # Stop loop
    client.loop_stop()
    client.disconnect()

    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Connection:      {'✅ PASS' if test_results['connection'] else '❌ FAIL'}")
    print(f"Authentication:  {'✅ PASS' if test_results['authentication'] else '❌ FAIL'}")
    print(f"Subscribe:       {'✅ PASS' if test_results['subscribe'] else '❌ FAIL'}")
    print(f"Publish:         {'✅ PASS' if test_results['publish'] else '❌ FAIL'}")
    print("=" * 60)

    if all(test_results.values()):
        print("\n🎉 All MQTT tests passed!")
        print("\n✅ Ready to proceed with Story AI1.2 (Backend Foundation)")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check credentials in infrastructure/env.ai-automation")
        sys.exit(1)

except ConnectionRefusedError:
    print(f"\n❌ Connection refused to {MQTT_BROKER}:{MQTT_PORT}")
    print("\nTroubleshooting:")
    print("  1. Verify MQTT broker is running on Home Assistant")
    print("  2. Check firewall isn't blocking port 1883")
    print(f"  3. Try: ping {MQTT_BROKER}")
    print(f"  4. Try: telnet {MQTT_BROKER} 1883")
    sys.exit(1)

except Exception as e:
    print(f"\n❌ Error: {e}")
    sys.exit(1)

