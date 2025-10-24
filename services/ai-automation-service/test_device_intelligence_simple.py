"""
Simple test script to verify Device Intelligence Service connectivity
"""

import asyncio
import httpx

async def test_device_intelligence_service():
    """Test Device Intelligence Service connectivity"""
    print("🔌 Testing Device Intelligence Service connectivity...")
    
    base_url = "http://localhost:8021"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test health check
            print("  → Testing health check...")
            response = await client.get(f"{base_url}/health/")
            response.raise_for_status()
            health = response.json()
            print(f"  ✅ Health check passed: {health.get('status', 'unknown')}")
            
            # Test device query
            print("  → Testing device query...")
            response = await client.get(f"{base_url}/api/devices", params={"limit": 10})
            response.raise_for_status()
            devices = response.json()
            print(f"  ✅ Device query passed: {len(devices)} devices found")
            
            # Test device stats
            print("  → Testing device stats...")
            response = await client.get(f"{base_url}/api/stats")
            response.raise_for_status()
            stats = response.json()
            print(f"  ✅ Device stats passed: {stats}")
            
            print("🎉 All connectivity tests passed!")
            return True
            
    except Exception as e:
        print(f"❌ Connectivity test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_device_intelligence_service())
    exit(0 if success else 1)
