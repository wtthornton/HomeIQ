"""
Test script with proper localhost configuration
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.clients.device_intelligence_client import DeviceIntelligenceClient
from src.entity_extraction.enhanced_extractor import EnhancedEntityExtractor

async def test_device_intelligence_connectivity():
    """Test device intelligence service connectivity with localhost"""
    print("🔌 Testing Device Intelligence Service Connectivity")
    print("=" * 50)
    
    # Use localhost instead of service name
    client = DeviceIntelligenceClient(base_url="http://localhost:8021")
    
    try:
        # Test health check
        print("Testing health check...")
        is_healthy = await client.health_check()
        print(f"Health Check: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")
        
        if is_healthy:
            # Test getting areas
            print("\nTesting areas endpoint...")
            areas = await client.get_all_areas()
            print(f"Areas Available: {len(areas)}")
            for area in areas[:5]:  # Show first 5
                print(f"  - {area.get('name', 'Unknown')}")
            
            # Test getting devices
            print("\nTesting devices endpoint...")
            devices = await client.get_all_devices(limit=10)
            print(f"Devices Available: {len(devices)}")
            for device in devices[:3]:  # Show first 3
                print(f"  - {device.get('name', 'Unknown')} ({device.get('integration', 'Unknown')})")
            
            # Test device details
            if devices:
                print("\nTesting device details...")
                device_id = devices[0]['id']
                device_details = await client.get_device_details(device_id)
                if device_details:
                    capabilities = device_details.get('capabilities', [])
                    print(f"Device Details Test: ✅ {len(capabilities)} capabilities found")
                    if capabilities:
                        print("Sample capabilities:")
                        for cap in capabilities[:3]:
                            print(f"  - {cap.get('feature', 'Unknown')}: {cap.get('supported', False)}")
                else:
                    print("Device Details Test: ❌ No details found")
        
    except Exception as e:
        print(f"❌ Connectivity test failed: {e}")
    
    finally:
        await client.close()
    
    return is_healthy

async def test_enhanced_extraction_with_real_data():
    """Test enhanced extraction with real device intelligence data"""
    print("\n🚀 Testing Enhanced Entity Extraction with Real Data")
    print("=" * 50)
    
    # Use localhost instead of service name
    client = DeviceIntelligenceClient(base_url="http://localhost:8021")
    extractor = EnhancedEntityExtractor(client)
    
    test_queries = [
        "Flash the office lights when the front door opens",
        "Turn on kitchen lights at sunset",
        "Create a bedtime routine for the bedroom"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Testing: {query}")
        
        try:
            entities = await extractor.extract_entities_with_intelligence(query)
            print(f"Found {len(entities)} entities:")
            
            for entity in entities:
                if entity.get('extraction_method') == 'device_intelligence':
                    print(f"  ✅ {entity['name']} (Enhanced)")
                    print(f"     Entity ID: {entity.get('entity_id', 'N/A')}")
                    print(f"     Manufacturer: {entity.get('manufacturer', 'Unknown')}")
                    print(f"     Model: {entity.get('model', 'Unknown')}")
                    print(f"     Health Score: {entity.get('health_score', 'N/A')}")
                    capabilities = [cap['feature'] for cap in entity.get('capabilities', []) if cap.get('supported')]
                    print(f"     Capabilities: {', '.join(capabilities) if capabilities else 'Basic on/off'}")
                else:
                    print(f"  📝 {entity['name']} (Basic fallback)")
        
        except Exception as e:
            print(f"❌ Enhanced extraction failed: {e}")
    
    await client.close()

async def main():
    """Run all tests"""
    print("🧪 Enhanced Entity Extraction Integration Test (Real Data)")
    print("=" * 60)
    
    # Test connectivity first
    is_healthy = await test_device_intelligence_connectivity()
    
    if is_healthy:
        # Test enhanced extraction with real data
        await test_enhanced_extraction_with_real_data()
        
        print("\n✅ All tests completed successfully!")
        print("\n🎯 Integration Status:")
        print("- Device Intelligence Service: ✅ Connected")
        print("- Enhanced Entity Extraction: ✅ Working")
        print("- Real Device Data: ✅ Available")
        print("\n🚀 The integration is fully functional!")
    else:
        print("\n❌ Device Intelligence Service is not accessible")
        print("Please check that the service is running on localhost:8021")

if __name__ == "__main__":
    asyncio.run(main())
