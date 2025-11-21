#!/usr/bin/env python3
"""Check what entity IDs and names exist in HA for Hue devices"""
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

HA_URL = os.getenv('HOME_ASSISTANT_URL', 'http://192.168.1.86:8123').replace('https://', 'ws://').replace('http://', 'ws://')
HA_TOKEN = os.getenv('HOME_ASSISTANT_TOKEN')

async def check_ha_entities():
    """Check entity registry for Hue entities with names"""
    
    websocket_url = HA_URL.rstrip('/') + '/api/websocket'
    print(f"Connecting to HA WebSocket: {websocket_url}")
    
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(websocket_url) as ws:
            # Auth flow
            msg = await ws.receive_json()
            await ws.send_json({"type": "auth", "access_token": HA_TOKEN})
            msg = await ws.receive_json()
            
            if msg['type'] != 'auth_ok':
                print(f"Auth failed: {msg}")
                return
            
            print("Authenticated!\n")
            
            # Get entity registry
            message_id = 1
            await ws.send_json({
                "id": message_id,
                "type": "config/entity_registry/list"
            })
            
            entities = None
            while True:
                msg = await ws.receive_json()
                if msg.get('id') == message_id:
                    if msg.get('success'):
                        entities = msg.get('result', [])
                        break
            
            print(f"Found {len(entities)} entities\n")
            
            # Search for entities with "Back", "LR", "Office", "Downlight", "Play" in names
            search_terms = ['back', 'lr', 'office', 'downlight', 'play', 'ceiling']
            matching_entities = []
            
            for entity in entities:
                entity_id = entity.get('entity_id', '').lower()
                name = (entity.get('name') or '').lower()
                name_by_user = (entity.get('name_by_user') or '').lower()
                original_name = (entity.get('original_name') or '').lower()
                
                # Check if any search term matches
                if any(term in entity_id or term in name or term in name_by_user or term in original_name 
                       for term in search_terms):
                    matching_entities.append(entity)
            
            print(f"Found {len(matching_entities)} matching entities:\n")
            
            for entity in matching_entities[:30]:
                entity_id = entity.get('entity_id', '')
                name = entity.get('name', '')
                name_by_user = entity.get('name_by_user', '')
                original_name = entity.get('original_name', '')
                device_id = entity.get('device_id', '')
                
                print(f"{entity_id}:")
                print(f"   device_id: {device_id}")
                print(f"   name: {name}")
                print(f"   name_by_user: {name_by_user}")
                print(f"   original_name: {original_name}")
                print()

if __name__ == '__main__':
    asyncio.run(check_ha_entities())



