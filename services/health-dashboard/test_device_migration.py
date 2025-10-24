#!/usr/bin/env python3
"""
Test script to verify health-dashboard device migration to Device Intelligence Service.

This script tests the nginx proxy configuration change from data-api to Device Intelligence Service.
"""

import asyncio
import httpx
import logging
import json
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test URLs
HEALTH_DASHBOARD_URL = "http://localhost:3000"  # Health dashboard nginx proxy
DEVICE_INTELLIGENCE_URL = "http://localhost:8021"  # Device Intelligence Service direct
DATA_API_URL = "http://localhost:8006"  # Data API direct (for comparison)

async def test_health_dashboard_devices() -> bool:
    """Test health-dashboard /api/devices endpoint via nginx proxy."""
    logger.info("🧪 Testing health-dashboard /api/devices endpoint...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{HEALTH_DASHBOARD_URL}/api/devices")
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"  ✅ Health dashboard devices response: {json.dumps(data, indent=2)}")
            
            # Verify response format matches data-api format
            if "devices" in data and "count" in data and "limit" in data:
                logger.info("  ✅ Response format is compatible with data-api")
                return True
            else:
                logger.error(f"  ❌ Response format is incompatible: {data}")
                return False
                
    except httpx.HTTPStatusError as e:
        logger.error(f"  ❌ HTTP error: {e}")
        return False
    except httpx.RequestError as e:
        logger.error(f"  ❌ Request error: {e}")
        return False
    except Exception as e:
        logger.error(f"  ❌ Unexpected error: {e}")
        return False

async def test_device_intelligence_direct() -> bool:
    """Test Device Intelligence Service /api/devices endpoint directly."""
    logger.info("🧪 Testing Device Intelligence Service /api/devices endpoint directly...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{DEVICE_INTELLIGENCE_URL}/api/devices")
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"  ✅ Device Intelligence Service response: {json.dumps(data, indent=2)}")
            
            # Verify response format matches data-api format
            if "devices" in data and "count" in data and "limit" in data:
                logger.info("  ✅ Response format is compatible with data-api")
                return True
            else:
                logger.error(f"  ❌ Response format is incompatible: {data}")
                return False
                
    except httpx.HTTPStatusError as e:
        logger.error(f"  ❌ HTTP error: {e}")
        return False
    except httpx.RequestError as e:
        logger.error(f"  ❌ Request error: {e}")
        return False
    except Exception as e:
        logger.error(f"  ❌ Unexpected error: {e}")
        return False

async def test_data_api_comparison() -> bool:
    """Test data-api /api/devices endpoint for comparison."""
    logger.info("🧪 Testing data-api /api/devices endpoint for comparison...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{DATA_API_URL}/api/devices")
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"  ✅ Data API response: {json.dumps(data, indent=2)}")
            
            # Verify response format
            if "devices" in data and "count" in data and "limit" in data:
                logger.info("  ✅ Data API response format is correct")
                return True
            else:
                logger.error(f"  ❌ Data API response format is incorrect: {data}")
                return False
                
    except httpx.HTTPStatusError as e:
        logger.error(f"  ❌ HTTP error: {e}")
        return False
    except httpx.RequestError as e:
        logger.error(f"  ❌ Request error: {e}")
        return False
    except Exception as e:
        logger.error(f"  ❌ Unexpected error: {e}")
        return False

async def test_response_format_compatibility() -> bool:
    """Test that Device Intelligence Service response format is compatible with health-dashboard."""
    logger.info("🧪 Testing response format compatibility...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Get response from Device Intelligence Service
            di_response = await client.get(f"{DEVICE_INTELLIGENCE_URL}/api/devices")
            di_response.raise_for_status()
            di_data = di_response.json()
            
            # Get response from data-api for comparison
            da_response = await client.get(f"{DATA_API_URL}/api/devices")
            da_response.raise_for_status()
            da_data = da_response.json()
            
            # Compare structure
            di_keys = set(di_data.keys())
            da_keys = set(da_data.keys())
            
            if di_keys == da_keys:
                logger.info("  ✅ Response structure is identical")
                
                # Compare device object structure
                if di_data["devices"] and da_data["devices"]:
                    di_device_keys = set(di_data["devices"][0].keys())
                    da_device_keys = set(da_data["devices"][0].keys())
                    
                    if di_device_keys == da_device_keys:
                        logger.info("  ✅ Device object structure is identical")
                        return True
                    else:
                        logger.error(f"  ❌ Device object structure differs:")
                        logger.error(f"    Device Intelligence Service: {di_device_keys}")
                        logger.error(f"    Data API: {da_device_keys}")
                        return False
                else:
                    logger.info("  ✅ Both services return empty device lists")
                    return True
            else:
                logger.error(f"  ❌ Response structure differs:")
                logger.error(f"    Device Intelligence Service: {di_keys}")
                logger.error(f"    Data API: {da_keys}")
                return False
                
    except Exception as e:
        logger.error(f"  ❌ Error comparing response formats: {e}")
        return False

async def run_migration_tests():
    """Run all migration tests."""
    logger.info("🚀 Starting health-dashboard device migration tests...")
    logger.info("=" * 60)
    
    results = {}
    
    # Test 1: Health dashboard via nginx proxy
    results["health_dashboard_devices"] = await test_health_dashboard_devices()
    
    # Test 2: Device Intelligence Service direct
    results["device_intelligence_direct"] = await test_device_intelligence_direct()
    
    # Test 3: Data API comparison
    results["data_api_comparison"] = await test_data_api_comparison()
    
    # Test 4: Response format compatibility
    results["response_format_compatibility"] = await test_response_format_compatibility()
    
    # Summary
    logger.info("\n📊 Migration Test Summary:")
    logger.info("=" * 60)
    for test_name, status in results.items():
        logger.info(f"  {test_name}: {'✅ PASS' if status else '❌ FAIL'}")
    logger.info("=" * 60)
    
    passed_count = sum(1 for status in results.values() if status)
    total_count = len(results)
    logger.info(f"Tests passed: {passed_count}/{total_count}")
    
    if all(results.values()):
        logger.info("🎉 All migration tests passed!")
        logger.info("✅ Health-dashboard successfully migrated to Device Intelligence Service")
        return True
    else:
        logger.error("❌ Some migration tests failed.")
        return False

if __name__ == "__main__":
    asyncio.run(run_migration_tests())
