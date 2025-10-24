#!/usr/bin/env python3
"""
OpenVINO Service Loading Monitor
Monitors the OpenVINO service until it finishes loading all models
"""

import time
import httpx
import asyncio
from datetime import datetime

async def check_openvino_health():
    """Check if OpenVINO service is healthy and ready"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8022/health")
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "healthy" and data.get("models_loaded", False)
    except:
        pass
    return False

async def test_openvino_functionality():
    """Test if OpenVINO service can actually process requests"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8022/embeddings",
                json={"texts": ["test sentence"]}
            )
            return response.status_code == 200
    except:
        pass
    return False

async def monitor_openvino_loading():
    """Monitor OpenVINO service until it's fully loaded"""
    print("🔍 Monitoring OpenVINO Service Loading...")
    print("=" * 50)
    
    start_time = time.time()
    check_interval = 10  # Check every 10 seconds
    
    while True:
        current_time = time.time()
        elapsed = current_time - start_time
        
        print(f"\n⏰ [{datetime.now().strftime('%H:%M:%S')}] Checking OpenVINO service... (elapsed: {elapsed:.0f}s)")
        
        # Check health endpoint
        health_ok = await check_openvino_health()
        print(f"   Health Check: {'✅ Healthy' if health_ok else '❌ Not Ready'}")
        
        if health_ok:
            # Test actual functionality
            functionality_ok = await test_openvino_functionality()
            print(f"   Functionality Test: {'✅ Working' if functionality_ok else '❌ Not Working'}")
            
            if functionality_ok:
                print(f"\n🎉 SUCCESS! OpenVINO service is fully loaded and working!")
                print(f"   Total loading time: {elapsed:.0f} seconds")
                print(f"   Ready for production use!")
                return True
        
        print(f"   Status: Still loading... (checking again in {check_interval}s)")
        await asyncio.sleep(check_interval)
        
        # Safety timeout (10 minutes)
        if elapsed > 600:
            print(f"\n⚠️  TIMEOUT: OpenVINO service took longer than 10 minutes to load")
            print(f"   This might indicate an issue. Check logs with:")
            print(f"   docker-compose logs openvino-service")
            return False

async def main():
    """Main monitoring function"""
    print("🚀 OpenVINO Service Loading Monitor")
    print("This script will monitor the OpenVINO service until it's fully loaded")
    print("Press Ctrl+C to stop monitoring\n")
    
    try:
        success = await monitor_openvino_loading()
        if success:
            print("\n✅ Monitoring complete - OpenVINO service is ready!")
        else:
            print("\n❌ Monitoring failed - check service logs for issues")
    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoring stopped by user")
    except Exception as e:
        print(f"\n❌ Error during monitoring: {e}")

if __name__ == "__main__":
    asyncio.run(main())
