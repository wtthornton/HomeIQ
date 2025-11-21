#!/usr/bin/env python3
"""
Integration test to verify the HA Ingestor system is working correctly
"""

import asyncio
import sys

import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_system_integration():
    """Test the complete HA Ingestor system integration"""

    print("Testing HA Ingestor System Integration")
    print("=" * 50)

    results = {
        "websocket_service": False,
        "admin_api": False,
        "dashboard": False,
        "event_processing": False,
        "influxdb": False,
    }

    try:
        # Test 1: WebSocket Service Health
        print("\n1. Testing WebSocket Service...")
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get("http://localhost:8001/health", timeout=10) as response:
                    if response.status == 200:
                        print("   SUCCESS: WebSocket service is healthy")
                        results["websocket_service"] = True
                    else:
                        print(f"   ERROR: WebSocket service unhealthy: {response.status}")
            except Exception as e:
                print(f"   ERROR: WebSocket service unreachable: {e}")

        # Test 2: Admin API Health
        print("\n2. Testing Admin API...")
        try:
            async with session.get("http://localhost:8003/health", timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    print("   SUCCESS: Admin API is healthy")
                    print(f"   Uptime: {data.get('uptime_human', 'Unknown')}")
                    results["admin_api"] = True
                else:
                    print(f"   ERROR: Admin API unhealthy: {response.status}")
        except Exception as e:
            print(f"   ERROR: Admin API unreachable: {e}")

        # Test 3: Dashboard Accessibility
        print("\n3. Testing Dashboard...")
        try:
            async with session.get("http://localhost:3000/", timeout=10) as response:
                if response.status == 200:
                    print("   SUCCESS: Dashboard is accessible")
                    results["dashboard"] = True
                else:
                    print(f"   ERROR: Dashboard unreachable: {response.status}")
        except Exception as e:
            print(f"   ERROR: Dashboard unreachable: {e}")

        # Test 4: Event Processing Stats
        print("\n4. Testing Event Processing...")
        try:
            async with session.get("http://localhost:3000/api/stats", timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    websocket_metrics = data.get("metrics", {}).get("websocket-ingestion", {})
                    events_per_min = websocket_metrics.get("events_per_minute", 0)
                    total_events = websocket_metrics.get("total_events_received", 0)

                    print("   SUCCESS: Event processing active")
                    print(f"   Events/minute: {events_per_min}")
                    print(f"   Total events: {total_events}")
                    results["event_processing"] = True
                else:
                    print(f"   ERROR: Stats API unreachable: {response.status}")
        except Exception as e:
            print(f"   ERROR: Stats API unreachable: {e}")

        # Test 5: InfluxDB Connection
        print("\n5. Testing InfluxDB...")
        try:
            async with session.get("http://localhost:8086/health", timeout=10) as response:
                if response.status == 200:
                    print("   SUCCESS: InfluxDB is healthy")
                    results["influxdb"] = True
                else:
                    print(f"   ERROR: InfluxDB unhealthy: {response.status}")
        except Exception as e:
            print(f"   ERROR: InfluxDB unreachable: {e}")

    except Exception as e:
        print(f"ERROR: Integration test failed: {e}")

    # Summary
    print("\n" + "=" * 50)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 50)

    passed = sum(results.values())
    total = len(results)

    for service, status in results.items():
        status_icon = "SUCCESS" if status else "ERROR"
        print(f"{status_icon} {service.replace('_', ' ').title()}: {'PASS' if status else 'FAIL'}")

    print(f"\nOverall: {passed}/{total} services healthy ({passed/total*100:.1f}%)")

    if passed == total:
        print("SUCCESS: All systems operational! HA Ingestor is working perfectly.")
        return True
    if passed >= total * 0.8:
        print("⚠️  Most systems operational. Minor issues detected.")
        return True
    print("❌ Multiple system failures detected.")
    return False

if __name__ == "__main__":
    success = asyncio.run(test_system_integration())
    sys.exit(0 if success else 1)
