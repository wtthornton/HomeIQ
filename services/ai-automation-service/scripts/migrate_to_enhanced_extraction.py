"""
Migration script to enable enhanced entity extraction
"""

import asyncio
import logging

from src.clients.device_intelligence_client import DeviceIntelligenceClient
from src.entity_extraction.enhanced_extractor import EnhancedEntityExtractor
from src.monitoring.enhanced_extraction_metrics import extraction_metrics

logger = logging.getLogger(__name__)

async def test_enhanced_extraction():
    """Test enhanced extraction with sample queries"""

    client = DeviceIntelligenceClient()
    extractor = EnhancedEntityExtractor(client)

    test_queries = [
        "Flash the office lights when the front door opens",
        "Turn on kitchen lights at sunset",
        "Create a bedtime routine for the bedroom",
        "Monitor garage door and send alerts",
        "Use LED notifications for door status"
    ]

    print("🚀 Testing Enhanced Entity Extraction")
    print("=" * 50)

    for query in test_queries:
        print(f"\n🔍 Testing: {query}")

        start_time = time.time()
        entities = await extractor.extract_entities_with_intelligence(query)
        extraction_time = time.time() - start_time

        # Track metrics
        await extraction_metrics.track_extraction(query, entities, extraction_time)

        print(f"Found {len(entities)} entities:")
        for entity in entities:
            if entity.get('extraction_method') == 'device_intelligence':
                capabilities = [cap['feature'] for cap in entity.get('capabilities', []) if cap.get('supported')]
                print(f"  ✅ {entity['name']} ({entity.get('manufacturer', 'Unknown')} {entity.get('model', 'Unknown')})")
                print(f"     Entity: {entity.get('entity_id', 'N/A')}")
                print(f"     Health: {entity.get('health_score', 'N/A')}")
                print(f"     Capabilities: {', '.join(capabilities) if capabilities else 'Basic on/off'}")
            else:
                print(f"  📝 {entity['name']} ({entity.get('domain', 'unknown')}) - Basic entity")

        print(f"⏱️  Extraction time: {extraction_time:.2f}s")

    # Show performance summary
    print("\n" + extraction_metrics.get_performance_summary())

    await client.close()

async def test_device_intelligence_connectivity():
    """Test device intelligence service connectivity"""

    print("\n🔌 Testing Device Intelligence Service Connectivity")
    print("=" * 50)

    client = DeviceIntelligenceClient()

    try:
        # Test health check
        is_healthy = await client.health_check()
        print(f"Health Check: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")

        # Test getting areas
        areas = await client.get_all_areas()
        print(f"Areas Available: {len(areas)}")
        for area in areas[:5]:  # Show first 5
            print(f"  - {area.get('name', 'Unknown')}")

        # Test getting devices
        devices = await client.get_all_devices(limit=10)
        print(f"Devices Available: {len(devices)}")
        for device in devices[:3]:  # Show first 3
            print(f"  - {device.get('name', 'Unknown')} ({device.get('integration', 'Unknown')})")

        # Test device details
        if devices:
            device_id = devices[0]['id']
            device_details = await client.get_device_details(device_id)
            if device_details:
                capabilities = device_details.get('capabilities', [])
                print(f"Device Details Test: ✅ {len(capabilities)} capabilities found")
            else:
                print("Device Details Test: ❌ No details found")

    except Exception as e:
        print(f"❌ Connectivity test failed: {e}")

    finally:
        await client.close()

if __name__ == "__main__":
    import time

    async def main():
        await test_device_intelligence_connectivity()
        await test_enhanced_extraction()

    asyncio.run(main())
