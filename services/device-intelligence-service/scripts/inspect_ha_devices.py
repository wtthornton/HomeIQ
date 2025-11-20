"""Script to inspect what HA actually returns for device data."""
import asyncio

from src.clients.ha_client import HomeAssistantClient
from src.config import Settings


async def inspect_ha_devices():
    settings = Settings()

    # Create HA client
    client = HomeAssistantClient(
        settings.HA_URL,
        None,
        settings.HA_TOKEN
    )

    # Connect
    if not await client.connect():
        print("Failed to connect to HA")
        return

    # Get device registry
    print("Fetching device registry from HA...")
    devices = await client.get_device_registry()

    print(f"\nTotal devices: {len(devices)}\n")

    # Inspect first 10 devices
    for i, device in enumerate(devices[:10]):
        print(f"Device {i+1}:")
        print(f"  Name: {device.name}")
        print(f"  Manufacturer: {device.manufacturer}")
        print(f"  Model: {device.model}")
        print(f"  Integration: {device.integration}")
        print(f"  Area ID: {device.area_id}")
        print(f"  SW Version: {device.sw_version}")
        print(f"  HW Version: {device.hw_version}")
        print()

if __name__ == "__main__":
    asyncio.run(inspect_ha_devices())

