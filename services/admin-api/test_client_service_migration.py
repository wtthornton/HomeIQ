#!/usr/bin/env python3
"""
Comprehensive test script for Story DI-2.2: Client Service Migration

This script tests all client services (health-dashboard, ai-automation-service, admin-api)
to ensure they are working correctly with the Device Intelligence Service after migration.
"""

import asyncio
import httpx
import logging
import json
from typing import Dict, Any, List
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs
HEALTH_DASHBOARD_URL = "http://localhost:3000"
AI_AUTOMATION_SERVICE_URL = "http://localhost:8018"
ADMIN_API_URL = "http://localhost:8004"
DEVICE_INTELLIGENCE_SERVICE_URL = "http://localhost:8021"

class ClientServiceMigrationTester:
    """Test client services after migration to Device Intelligence Service."""
    
    def __init__(self):
        self.results = {}
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_device_intelligence_service_health(self) -> bool:
        """Test Device Intelligence Service health."""
        logger.info("🧪 Testing Device Intelligence Service health...")
        
        try:
            response = await self.client.get(f"{DEVICE_INTELLIGENCE_SERVICE_URL}/api/health")
            response.raise_for_status()
            
            data = response.json()
            if data.get("status") == "healthy":
                logger.info("  ✅ Device Intelligence Service is healthy")
                return True
            else:
                logger.error(f"  ❌ Device Intelligence Service is unhealthy: {data}")
                return False
                
        except Exception as e:
            logger.error(f"  ❌ Device Intelligence Service health check failed: {e}")
            return False
    
    async def test_device_intelligence_service_devices(self) -> bool:
        """Test Device Intelligence Service devices endpoint."""
        logger.info("🧪 Testing Device Intelligence Service /api/devices endpoint...")
        
        try:
            response = await self.client.get(f"{DEVICE_INTELLIGENCE_SERVICE_URL}/api/devices")
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"  ✅ Device Intelligence Service devices: {data.get('count', 0)} devices")
            
            # Verify response format
            if "devices" in data and "count" in data and "limit" in data:
                logger.info("  ✅ Response format is correct")
                return True
            else:
                logger.error(f"  ❌ Response format is incorrect: {data}")
                return False
                
        except Exception as e:
            logger.error(f"  ❌ Device Intelligence Service devices test failed: {e}")
            return False
    
    async def test_health_dashboard_devices(self) -> bool:
        """Test health-dashboard devices endpoint via nginx proxy."""
        logger.info("🧪 Testing health-dashboard /api/devices endpoint...")
        
        try:
            response = await self.client.get(f"{HEALTH_DASHBOARD_URL}/api/devices")
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"  ✅ Health dashboard devices: {data.get('count', 0)} devices")
            
            # Verify response format
            if "devices" in data and "count" in data and "limit" in data:
                logger.info("  ✅ Response format is correct")
                return True
            else:
                logger.error(f"  ❌ Response format is incorrect: {data}")
                return False
                
        except Exception as e:
            logger.error(f"  ❌ Health dashboard devices test failed: {e}")
            return False
    
    async def test_ai_automation_service_devices(self) -> bool:
        """Test ai-automation-service devices endpoint."""
        logger.info("🧪 Testing ai-automation-service /api/devices endpoint...")
        
        try:
            response = await self.client.get(f"{AI_AUTOMATION_SERVICE_URL}/api/devices")
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"  ✅ AI Automation Service devices: {data.get('count', 0)} devices")
            
            # Verify response format
            if "devices" in data and "count" in data:
                logger.info("  ✅ Response format is correct")
                return True
            else:
                logger.error(f"  ❌ Response format is incorrect: {data}")
                return False
                
        except Exception as e:
            logger.error(f"  ❌ AI Automation Service devices test failed: {e}")
            return False
    
    async def test_admin_api_devices(self) -> bool:
        """Test admin-api devices endpoint."""
        logger.info("🧪 Testing admin-api /api/devices endpoint...")
        
        try:
            response = await self.client.get(f"{ADMIN_API_URL}/api/devices")
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"  ✅ Admin API devices: {data.get('count', 0)} devices")
            
            # Verify response format
            if "devices" in data and "count" in data and "limit" in data:
                logger.info("  ✅ Response format is correct")
                return True
            else:
                logger.error(f"  ❌ Response format is incorrect: {data}")
                return False
                
        except Exception as e:
            logger.error(f"  ❌ Admin API devices test failed: {e}")
            return False
    
    async def test_data_consistency(self) -> bool:
        """Test data consistency across all services."""
        logger.info("🧪 Testing data consistency across all services...")
        
        try:
            # Get devices from all services
            services = {
                "Device Intelligence Service": DEVICE_INTELLIGENCE_SERVICE_URL,
                "Health Dashboard": HEALTH_DASHBOARD_URL,
                "AI Automation Service": AI_AUTOMATION_SERVICE_URL,
                "Admin API": ADMIN_API_URL
            }
            
            device_counts = {}
            for service_name, url in services.items():
                try:
                    response = await self.client.get(f"{url}/api/devices")
                    response.raise_for_status()
                    data = response.json()
                    count = data.get("count", 0)
                    device_counts[service_name] = count
                    logger.info(f"    {service_name}: {count} devices")
                except Exception as e:
                    logger.error(f"    ❌ {service_name}: Error getting devices - {e}")
                    device_counts[service_name] = -1
            
            # Check consistency
            counts = [c for c in device_counts.values() if c >= 0]
            if len(set(counts)) <= 1:  # All counts are the same (or only one service working)
                logger.info("  ✅ Data consistency check passed")
                return True
            else:
                logger.error(f"  ❌ Data consistency check failed: {device_counts}")
                return False
                
        except Exception as e:
            logger.error(f"  ❌ Data consistency test failed: {e}")
            return False
    
    async def test_service_health(self) -> bool:
        """Test health endpoints of all services."""
        logger.info("🧪 Testing service health endpoints...")
        
        try:
            services = {
                "Device Intelligence Service": f"{DEVICE_INTELLIGENCE_SERVICE_URL}/api/health",
                "Health Dashboard": f"{HEALTH_DASHBOARD_URL}/health",
                "AI Automation Service": f"{AI_AUTOMATION_SERVICE_URL}/health",
                "Admin API": f"{ADMIN_API_URL}/api/health"
            }
            
            all_healthy = True
            for service_name, health_url in services.items():
                try:
                    response = await self.client.get(health_url)
                    response.raise_for_status()
                    data = response.json()
                    status = data.get("status", "unknown")
                    if status == "healthy":
                        logger.info(f"    ✅ {service_name}: {status}")
                    else:
                        logger.error(f"    ❌ {service_name}: {status}")
                        all_healthy = False
                except Exception as e:
                    logger.error(f"    ❌ {service_name}: Health check failed - {e}")
                    all_healthy = False
            
            if all_healthy:
                logger.info("  ✅ All services are healthy")
                return True
            else:
                logger.error("  ❌ Some services are unhealthy")
                return False
                
        except Exception as e:
            logger.error(f"  ❌ Service health test failed: {e}")
            return False
    
    async def test_performance_comparison(self) -> bool:
        """Test performance of device queries across services."""
        logger.info("🧪 Testing performance of device queries...")
        
        try:
            services = {
                "Device Intelligence Service": DEVICE_INTELLIGENCE_SERVICE_URL,
                "Health Dashboard": HEALTH_DASHBOARD_URL,
                "AI Automation Service": AI_AUTOMATION_SERVICE_URL,
                "Admin API": ADMIN_API_URL
            }
            
            performance_results = {}
            for service_name, url in services.items():
                try:
                    start_time = datetime.now()
                    response = await self.client.get(f"{url}/api/devices")
                    response.raise_for_status()
                    end_time = datetime.now()
                    
                    duration_ms = (end_time - start_time).total_seconds() * 1000
                    performance_results[service_name] = duration_ms
                    logger.info(f"    {service_name}: {duration_ms:.2f}ms")
                    
                except Exception as e:
                    logger.error(f"    ❌ {service_name}: Performance test failed - {e}")
                    performance_results[service_name] = -1
            
            # Check if all services are reasonably fast (< 1 second)
            fast_services = [name for name, duration in performance_results.items() if 0 <= duration < 1000]
            if len(fast_services) == len(services):
                logger.info("  ✅ All services are performing well")
                return True
            else:
                logger.error(f"  ❌ Some services are slow: {performance_results}")
                return False
                
        except Exception as e:
            logger.error(f"  ❌ Performance test failed: {e}")
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all migration tests."""
        logger.info("🚀 Starting comprehensive client service migration tests...")
        logger.info("=" * 70)
        
        # Test Device Intelligence Service
        self.results["device_intelligence_health"] = await self.test_device_intelligence_service_health()
        self.results["device_intelligence_devices"] = await self.test_device_intelligence_service_devices()
        
        # Test client services
        self.results["health_dashboard_devices"] = await self.test_health_dashboard_devices()
        self.results["ai_automation_devices"] = await self.test_ai_automation_service_devices()
        self.results["admin_api_devices"] = await self.test_admin_api_devices()
        
        # Test integration
        self.results["data_consistency"] = await self.test_data_consistency()
        self.results["service_health"] = await self.test_service_health()
        self.results["performance"] = await self.test_performance_comparison()
        
        # Summary
        logger.info("\n📊 Client Service Migration Test Summary:")
        logger.info("=" * 70)
        for test_name, status in self.results.items():
            logger.info(f"  {test_name}: {'✅ PASS' if status else '❌ FAIL'}")
        logger.info("=" * 70)
        
        passed_count = sum(1 for status in self.results.values() if status)
        total_count = len(self.results)
        logger.info(f"Tests passed: {passed_count}/{total_count}")
        
        if all(self.results.values()):
            logger.info("🎉 All client service migration tests passed!")
            logger.info("✅ All client services successfully migrated to Device Intelligence Service")
            return True
        else:
            logger.error("❌ Some client service migration tests failed.")
            return False
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

async def main():
    """Main test function."""
    tester = ClientServiceMigrationTester()
    try:
        success = await tester.run_all_tests()
        return success
    finally:
        await tester.close()

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
