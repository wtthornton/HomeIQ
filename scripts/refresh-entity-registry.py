#!/usr/bin/env python3
"""
Refresh entity registry data from Home Assistant HTTP API and store in database.
This bypasses WebSocket concurrency issues by using HTTP API directly.
"""
import asyncio
import aiohttp
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

load_dotenv()

HA_URL = os.getenv('HOME_ASSISTANT_URL', 'http://192.168.1.86:8123').replace('ws://', 'http://').replace('wss://', 'https://').rstrip('/')
HA_TOKEN = os.getenv('HOME_ASSISTANT_TOKEN')
DATA_API_URL = os.getenv('DATA_API_URL', 'http://localhost:8006')
DATA_API_KEY = os.getenv('DATA_API_API_KEY') or os.getenv('DATA_API_KEY') or os.getenv('API_KEY')

async def refresh_entity_registry():
    """Fetch entity registry from HA HTTP API and store via data-api"""
    
    print(f"Fetching entity registry from {HA_URL}/api/config/entity_registry/list")
    
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        # Fetch entity registry via HTTP API
        async with session.get(
            f"{HA_URL}/api/config/entity_registry/list",
            headers=headers
        ) as response:
            if response.status != 200:
                print(f"ERROR: Failed to fetch entity registry: HTTP {response.status}")
                text = await response.text()
                print(f"Response: {text}")
                return
            
            data = await response.json()
            entities = data if isinstance(data, list) else data.get('entities', [])
            
            print(f"SUCCESS: Retrieved {len(entities)} entities from HA Entity Registry")
            
            # Show sample entity with name fields
            if entities:
                sample = entities[0]
                print(f"\nSample entity:")
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
            
            api_headers = {}
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
    asyncio.run(refresh_entity_registry())

