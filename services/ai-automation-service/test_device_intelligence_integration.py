"""
Test script to verify Device Intelligence Service integration
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from clients.device_intelligence_client import DeviceIntelligenceClient
from config import settings

async def test_integration():
    """Test Device Intelligence Service integration"""
    print("🔌 Testing Device Intelligence Service integration...")
    
    # Initialize client
    client = DeviceIntelligenceClient(base_url=settings.device_intelligence_url)
    
    try:
        # Test health check
        print("  → Testing health check...")
        health = await client.health_check()
        print(f"  ✅ Health check passed: {health.get('status', 'unknown')}")
        
        # Test device query
        print("  → Testing device query...")
        devices = await client.get_devices(limit=10)
        print(f"  ✅ Device query passed: {len(devices)} devices found")
        
        # Test device stats
        print("  → Testing device stats...")
        stats = await client.get_device_stats()
        print(f"  ✅ Device stats passed: {stats}")
        
        print("🎉 All integration tests passed!")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False
    finally:
        await client.close()
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_integration())
    sys.exit(0 if success else 1)
