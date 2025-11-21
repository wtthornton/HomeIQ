#!/usr/bin/env python3
"""Check device registry and state API for Hue device names"""
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

HA_URL = os.getenv('HOME_ASSISTANT_URL', 'http://192.168.1.86:8123').replace('https://', 'ws://').replace('http://', 'ws://')
HA_TOKEN = os.getenv('HOME_ASSISTANT_TOKEN')

async def check_device_names():
    """Check device registry and state API for names"""
    
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
            
            # Get device registry
            print("Fetching device registry...")
            message_id = 1
            await ws.send_json({
                "id": message_id,
                "type": "config/device_registry/list"
            })
            
            devices = None
            while True:
                msg = await ws.receive_json()
                if msg.get('id') == message_id:
                    if msg.get('success'):
                        devices = msg.get('result', [])
                        break
            
            print(f"Found {len(devices)} devices\n")
            
            # Find Hue devices
            hue_devices = [d for d in devices if 'hue' in (d.get('name_by_user') or '').lower() or 
                          'hue' in (d.get('name') or '').lower() or
                          'hue' in (d.get('model') or '').lower() or
                          'hue' in (d.get('manufacturer') or '').lower()]
            
            print(f"Found {len(hue_devices)} Hue devices:\n")
            
            for device in hue_devices[:20]:
                device_id = device.get('id', '')
                name = device.get('name', '')
                name_by_user = device.get('name_by_user', '')
                model = device.get('model', '')
                manufacturer = device.get('manufacturer', '')
                
                print(f"Device ID: {device_id}")
                print(f"   name: {name}")
                print(f"   name_by_user: {name_by_user}")
                print(f"   model: {model}")
                print(f"   manufacturer: {manufacturer}")
                print()
            
            # Check state API for specific entities
            print("\n" + "=" * 80)
            print("Checking State API for entity friendly names:")
            print("=" * 80)
            
            entity_ids_to_check = [
                'light.hue_color_downlight_1_5',
                'light.hue_color_downlight_1_3',
                'light.hue_color_downlight_1_7',
                'light.hue_play_1',
                'light.office',
            ]
            
            for entity_id in entity_ids_to_check:
                message_id += 1
                await ws.send_json({
                    "id": message_id,
                    "type": "states/get",
                    "entity_id": entity_id
                })
                
                while True:
                    msg = await ws.receive_json()
                    if msg.get('id') == message_id:
                        if msg.get('success'):
                            state = msg.get('result')
                            if state:
                                friendly_name = state.get('attributes', {}).get('friendly_name', '')
                                print(f"{entity_id}: friendly_name = {friendly_name}")
                            else:
                                print(f"{entity_id}: NOT FOUND")
                        break

if __name__ == '__main__':
    asyncio.run(check_device_names())



