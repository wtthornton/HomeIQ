#!/usr/bin/env python3
"""
Standalone entity discovery script that opens its own WebSocket connection.
This bypasses concurrency issues by using a separate WebSocket connection.
"""
import asyncio
import aiohttp
import os
import sys
from dotenv import load_dotenv

load_dotenv()

HA_URL = os.getenv('HOME_ASSISTANT_URL', 'http://192.168.1.86:8123').replace('https://', 'ws://').replace('http://', 'ws://')
HA_TOKEN = os.getenv('HOME_ASSISTANT_TOKEN')
DATA_API_URL = os.getenv('DATA_API_URL', 'http://localhost:8006')
DATA_API_KEY = os.getenv('DATA_API_API_KEY') or os.getenv('DATA_API_KEY') or os.getenv('API_KEY')

async def discover_and_store():
    """Discover entities via WebSocket and store via data-api"""
    
    websocket_url = HA_URL.rstrip('/') + '/api/websocket'
    print(f"Connecting to HA WebSocket: {websocket_url}")
    
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(websocket_url) as ws:
            # Auth flow
            msg = await ws.receive_json()
            print(f"Auth required: {msg['type']}")
            
            await ws.send_json({"type": "auth", "access_token": HA_TOKEN})
            msg = await ws.receive_json()
            
            if msg['type'] != 'auth_ok':
                print(f"Auth failed: {msg}")
                return
            
            print("Authenticated!\n")
            
            # Discover entities
            print("Discovering entities from entity registry...")
            message_id = 1
            await ws.send_json({
                "id": message_id,
                "type": "config/entity_registry/list"
            })
            
            # Wait for response
            entities = None
            while True:
                msg = await ws.receive_json()
                if msg.get('id') == message_id:
                    if msg.get('success'):
                        entities = msg.get('result', [])
                        break
                    else:
                        error = msg.get('error', {})
                        print(f"ERROR: Entity registry command failed: {error}")
                        return
            
            print(f"SUCCESS: Retrieved {len(entities)} entities from HA Entity Registry\n")
            
            # Show sample entity with name fields
            if entities:
                sample = entities[0]
                print("Sample entity:")
                print(f"   entity_id: {sample.get('entity_id')}")
                print(f"   name: {sample.get('name')}")
                print(f"   name_by_user: {sample.get('name_by_user')}")
                print(f"   original_name: {sample.get('original_name')}")
            
            # Filter for Hue entities to check
            hue_entities = [e for e in entities if 'hue' in e.get('entity_id', '').lower() or 'hue' in e.get('platform', '').lower()]
            print(f"\nFound {len(hue_entities)} Hue-related entities")
            
            # Show Hue entities with name fields
            print("\nHue entities with name fields:")
            for entity in hue_entities[:10]:
                entity_id = entity.get('entity_id', '')
                name = entity.get('name', '')
                name_by_user = entity.get('name_by_user', '')
                original_name = entity.get('original_name', '')
                print(f"   {entity_id}:")
                print(f"      name: {name}")
                print(f"      name_by_user: {name_by_user}")
                print(f"      original_name: {original_name}")
            
            # Store entities via data-api bulk_upsert endpoint
            print(f"\nStoring {len(entities)} entities to database via data-api...")
            
            api_headers = {"Content-Type": "application/json"}
            if DATA_API_KEY:
                api_headers["Authorization"] = f"Bearer {DATA_API_KEY}"
            
            async with session.post(
                f"{DATA_API_URL}/internal/entities/bulk_upsert",
                json=entities,
                headers=api_headers
            ) as api_response:
                if api_response.status == 200:
                    result = await api_response.json()
                    print(f"SUCCESS: Stored {result.get('upserted', 0)} entities")
                else:
                    error_text = await api_response.text()
                    print(f"ERROR: Failed to store entities: HTTP {api_response.status}")
                    print(f"Response: {error_text}")

if __name__ == '__main__':
    asyncio.run(discover_and_store())


