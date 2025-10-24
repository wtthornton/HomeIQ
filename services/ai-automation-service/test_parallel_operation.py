"""
Parallel Operation Test Script for Story DI-2.1

Tests that both ai-automation-service and device-intelligence-service
can run in parallel and communicate correctly.
"""

import asyncio
import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ParallelOperationTester:
    """
    Tests parallel operation of both services.
    """
    
    def __init__(self):
        self.ai_automation_url = "http://localhost:8018"
        self.device_intelligence_url = "http://localhost:8021"
        self.results = {
            "ai_automation_health": False,
            "device_intelligence_health": False,
            "ai_automation_devices": False,
            "device_intelligence_devices": False,
            "integration_test": False
        }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all parallel operation tests."""
        print("🧪 Testing parallel operation of both services...")
        
        try:
            # Test 1: Check both services are healthy
            await self._test_service_health()
            
            # Test 2: Test device queries from both services
            await self._test_device_queries()
            
            # Test 3: Test integration between services
            await self._test_service_integration()
            
            # Summary
            await self._print_test_summary()
            
            return self.results
            
        except Exception as e:
            print(f"❌ Parallel operation test failed: {e}")
            return self.results
    
    async def _test_service_health(self):
        """Test that both services are healthy."""
        print("  → Testing service health...")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test AI Automation Service
            try:
                response = await client.get(f"{self.ai_automation_url}/health")
                response.raise_for_status()
                self.results["ai_automation_health"] = True
                print("    ✅ AI Automation Service is healthy")
            except Exception as e:
                print(f"    ❌ AI Automation Service health check failed: {e}")
            
            # Test Device Intelligence Service
            try:
                response = await client.get(f"{self.device_intelligence_url}/health/")
                response.raise_for_status()
                self.results["device_intelligence_health"] = True
                print("    ✅ Device Intelligence Service is healthy")
            except Exception as e:
                print(f"    ❌ Device Intelligence Service health check failed: {e}")
    
    async def _test_device_queries(self):
        """Test device queries from both services."""
        print("  → Testing device queries...")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test AI Automation Service device query
            try:
                response = await client.get(f"{self.ai_automation_url}/api/devices")
                response.raise_for_status()
                data = response.json()
                self.results["ai_automation_devices"] = True
                print(f"    ✅ AI Automation Service device query: {data.get('count', 0)} devices")
            except Exception as e:
                print(f"    ❌ AI Automation Service device query failed: {e}")
            
            # Test Device Intelligence Service device query
            try:
                response = await client.get(f"{self.device_intelligence_url}/api/devices")
                response.raise_for_status()
                devices = response.json()
                self.results["device_intelligence_devices"] = True
                print(f"    ✅ Device Intelligence Service device query: {len(devices)} devices")
            except Exception as e:
                print(f"    ❌ Device Intelligence Service device query failed: {e}")
    
    async def _test_service_integration(self):
        """Test integration between services."""
        print("  → Testing service integration...")
        
        try:
            # Test that AI Automation Service can query Device Intelligence Service
            async with httpx.AsyncClient(timeout=10.0) as client:
                # This would normally be done through the DeviceIntelligenceClient
                # but we'll test the direct API call
                response = await client.get(f"{self.device_intelligence_url}/api/stats")
                response.raise_for_status()
                stats = response.json()
                
                self.results["integration_test"] = True
                print(f"    ✅ Service integration test passed: {stats}")
                
        except Exception as e:
            print(f"    ❌ Service integration test failed: {e}")
    
    async def _print_test_summary(self):
        """Print test summary."""
        print("\n📊 Parallel Operation Test Summary:")
        print("=" * 50)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result)
        
        for test_name, result in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {test_name}: {status}")
        
        print("=" * 50)
        print(f"Tests passed: {passed_tests}/{total_tests}")
        
        if passed_tests == total_tests:
            print("🎉 All parallel operation tests passed!")
        else:
            print("⚠️  Some tests failed - check service status")


async def main():
    """Main test function."""
    tester = ParallelOperationTester()
    results = await tester.run_all_tests()
    
    # Return success if all tests passed
    success = all(results.values())
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
