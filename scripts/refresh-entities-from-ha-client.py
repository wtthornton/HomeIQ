#!/usr/bin/env python3
"""
Refresh entity registry data using HA client and store via data-api.
This uses the same method as EntityAttributeService to fetch entity registry.
"""
import asyncio
import os
import sys

from dotenv import load_dotenv

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../services/ai-automation-service/src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../shared"))

load_dotenv()

async def refresh_entities():
    """Fetch entity registry using HA client and store via data-api"""
    from clients.ha_client import HomeAssistantClient

    ha_url = os.getenv("HOME_ASSISTANT_URL", "http://192.168.1.86:8123").replace("ws://", "http://").replace("wss://", "https://").rstrip("/")
    ha_token = os.getenv("HOME_ASSISTANT_TOKEN")
    data_api_url = os.getenv("DATA_API_URL", "http://localhost:8006")
    data_api_key = os.getenv("DATA_API_API_KEY") or os.getenv("DATA_API_KEY") or os.getenv("API_KEY")

    print(f"Connecting to Home Assistant: {ha_url}")

    # Create HA client
    ha_client = HomeAssistantClient(ha_url=ha_url, access_token=ha_token)

    try:
        # Fetch entity registry (same method used by EntityAttributeService)
        print("Fetching entity registry from HA...")
        registry = await ha_client.get_entity_registry()

        if not registry:
            print("ERROR: No entity registry data received")
            return

        print(f"SUCCESS: Retrieved {len(registry)} entities from Entity Registry")

        # Convert registry dict to list format expected by bulk_upsert
        entities_list = []
        for entity_id, entity_data in registry.items():
            # Ensure entity_id is included in the data
            entity_data["entity_id"] = entity_id
            entities_list.append(entity_data)

        # Show sample entity
        if entities_list:
            sample = entities_list[0]
            print("\nSample entity:")
            print(f"   entity_id: {sample.get('entity_id')}")
            print(f"   name: {sample.get('name')}")
            print(f"   name_by_user: {sample.get('name_by_user')}")
            print(f"   original_name: {sample.get('original_name')}")

        # Filter for Hue entities
        hue_entities = [e for e in entities_list if "hue" in e.get("entity_id", "").lower() or "hue" in e.get("platform", "").lower()]
        print(f"\nFound {len(hue_entities)} Hue-related entities")

        # Show Hue entities with name fields
        print("\nHue entities with name fields:")
        for entity in hue_entities[:10]:
            entity_id = entity.get("entity_id", "")
            name = entity.get("name", "")
            name_by_user = entity.get("name_by_user", "")
            original_name = entity.get("original_name", "")
            print(f"   {entity_id}:")
            print(f"      name: {name}")
            print(f"      name_by_user: {name_by_user}")
            print(f"      original_name: {original_name}")

        # Store entities via data-api bulk_upsert endpoint
        print(f"\nStoring {len(entities_list)} entities to database via data-api...")

        import aiohttp
        async with aiohttp.ClientSession() as session:
            api_headers = {"Content-Type": "application/json"}
            if data_api_key:
                api_headers["Authorization"] = f"Bearer {data_api_key}"

            async with session.post(
                f"{data_api_url}/internal/entities/bulk_upsert",
                json=entities_list,
                headers=api_headers,
            ) as api_response:
                if api_response.status == 200:
                    result = await api_response.json()
                    print(f"SUCCESS: Stored {result.get('upserted', 0)} entities")
                else:
                    error_text = await api_response.text()
                    print(f"ERROR: Failed to store entities: HTTP {api_response.status}")
                    print(f"Response: {error_text}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await ha_client.close()

if __name__ == "__main__":
    asyncio.run(refresh_entities())

