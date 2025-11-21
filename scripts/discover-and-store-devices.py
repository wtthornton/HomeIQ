#!/usr/bin/env python3
"""
One-time script to discover devices/entities from HA and store in InfluxDB
Run this to populate the device registry data
"""
import asyncio
import os
import sys
from datetime import datetime

import aiohttp
from dotenv import load_dotenv

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../services/websocket-ingestion/src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../shared"))

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

load_dotenv()

HA_URL = os.getenv("HOME_ASSISTANT_URL", "").replace("wss://", "ws://").replace("https://", "ws://")
HA_TOKEN = os.getenv("HOME_ASSISTANT_TOKEN")
INFLUX_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUX_ORG = os.getenv("INFLUXDB_ORG", "homeassistant")
INFLUX_BUCKET = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")

async def discover_and_store():
    """Discover devices and entities, store in InfluxDB"""

    websocket_url = HA_URL + "/api/websocket"
    print(f"Connecting to HA: {websocket_url}")

    # Connect to InfluxDB
    influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    print(f"Connected to InfluxDB: {INFLUX_URL}")

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(websocket_url) as ws:
            # Auth flow
            msg = await ws.receive_json()
            print(f"Auth required: {msg['type']}")

            await ws.send_json({"type": "auth", "access_token": HA_TOKEN})
            msg = await ws.receive_json()

            if msg["type"] != "auth_ok":
                print(f"Auth failed: {msg}")
                return

            print("Authenticated!\n")

            # Discover devices
            print("Discovering devices...")
            await ws.send_json({"id": 1, "type": "config/device_registry/list"})
            msg = await ws.receive_json()

            devices = msg.get("result", [])
            print(f"Found {len(devices)} devices\n")

            # Write devices to InfluxDB
            device_points = []
            for device in devices:
                point = Point("devices") \
                    .tag("device_id", device.get("id", "unknown")) \
                    .tag("manufacturer", device.get("manufacturer", "unknown")) \
                    .tag("model", device.get("model", "unknown")) \
                    .field("name", device.get("name_by_user") or device.get("name", "Unknown")) \
                    .field("sw_version", device.get("sw_version", "")) \
                    .field("area_id", device.get("area_id", "")) \
                    .time(datetime.utcnow(), WritePrecision.NS)

                device_points.append(point)

            if device_points:
                write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=device_points)
                print(f"OK - Wrote {len(device_points)} devices to InfluxDB")

            # Discover entities
            print("\nDiscovering entities...")
            await ws.send_json({"id": 2, "type": "config/entity_registry/list"})
            msg = await ws.receive_json()

            entities = msg.get("result", [])
            print(f"Found {len(entities)} entities\n")

            # Write entities to InfluxDB
            entity_points = []
            for entity in entities:
                point = Point("entities") \
                    .tag("entity_id", entity.get("entity_id", "unknown")) \
                    .tag("platform", entity.get("platform", "unknown")) \
                    .tag("domain", entity.get("entity_id", "").split(".")[0] if "." in entity.get("entity_id", "") else "unknown") \
                    .field("device_id", entity.get("device_id", "")) \
                    .field("area_id", entity.get("area_id", "")) \
                    .field("disabled", entity.get("disabled_by") is not None) \
                    .time(datetime.utcnow(), WritePrecision.NS)

                entity_points.append(point)

            if entity_points:
                write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=entity_points)
                print(f"OK - Wrote {len(entity_points)} entities to InfluxDB")

            print("\nDONE - Discovery and storage complete!")
            print(f"   Devices: {len(devices)}")
            print(f"   Entities: {len(entities)}")

    influx_client.close()

if __name__ == "__main__":
    asyncio.run(discover_and_store())

