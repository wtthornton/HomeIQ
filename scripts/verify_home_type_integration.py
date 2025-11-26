#!/usr/bin/env python3
"""
Home Type Integration Verification Script

Verifies that all home type integrations are working correctly.
Run this after deployment to ensure everything is functioning.

Usage:
    python scripts/verify_home_type_integration.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def verify_home_type_client():
    """Verify HomeTypeClient is accessible and working."""
    logger.info("=" * 60)
    logger.info("Verifying HomeTypeClient...")
    
    try:
        # Add service path
        service_path = project_root / "services" / "ai-automation-service" / "src"
        sys.path.insert(0, str(service_path))
        
        from clients.home_type_client import HomeTypeClient
        
        client = HomeTypeClient(base_url="http://localhost:8018")
        
        # Test getting home type
        home_type_data = await client.get_home_type(use_cache=False)
        
        logger.info(f"✅ HomeTypeClient working")
        logger.info(f"   Home Type: {home_type_data.get('home_type', 'unknown')}")
        logger.info(f"   Confidence: {home_type_data.get('confidence', 0.0):.2f}")
        
        await client.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ HomeTypeClient verification failed: {e}")
        return False


async def verify_integration_helpers():
    """Verify integration helpers are working."""
    logger.info("=" * 60)
    logger.info("Verifying Integration Helpers...")
    
    try:
        from home_type.integration_helpers import (
            calculate_home_type_boost,
            adjust_pattern_thresholds,
            get_home_type_preferred_categories,
        )
        
        # Test preferred categories
        categories = get_home_type_preferred_categories("security_focused")
        assert "security" in categories, "Security should be in preferred categories"
        
        # Test boost calculation
        boost = calculate_home_type_boost("security", "security_focused")
        assert boost > 0, "Boost should be positive for matching category"
        
        # Test threshold adjustment
        conf, occ = adjust_pattern_thresholds("apartment", 0.7, 10)
        assert conf < 0.7, "Confidence should be lower for apartments"
        
        logger.info("✅ Integration helpers working")
        logger.info(f"   Preferred categories (security_focused): {categories}")
        logger.info(f"   Boost for security category: {boost:.3f}")
        logger.info(f"   Adjusted thresholds (apartment): conf={conf:.2f}, occ={occ}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Integration helpers verification failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def verify_api_endpoints():
    """Verify API endpoints are accessible."""
    logger.info("=" * 60)
    logger.info("Verifying API Endpoints...")
    
    endpoints = [
        ("http://localhost:8018/api/home-type/classify?home_id=default", "Home Type Classification"),
        ("http://localhost:8006/api/v1/events/categories?hours=24", "Event Categories"),  # Fixed: /api/v1 prefix
    ]
    
    results = []
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for url, name in endpoints:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.info(f"✅ {name} endpoint working")
                    results.append(True)
                else:
                    logger.warning(f"⚠️ {name} endpoint returned {response.status_code}")
                    results.append(False)
            except Exception as e:
                logger.warning(f"⚠️ {name} endpoint not accessible: {e}")
                results.append(False)
    
    return all(results)


async def verify_suggestion_ranking():
    """Verify suggestion ranking with home type is working."""
    logger.info("=" * 60)
    logger.info("Verifying Suggestion Ranking...")
    
    try:
        # This would require database access, so we'll just verify the function exists
        from database.crud import get_suggestions_with_home_type
        
        logger.info("✅ get_suggestions_with_home_type function exists")
        logger.info("   Note: Full testing requires database connection")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Suggestion ranking verification failed: {e}")
        return False


async def verify_event_categorization():
    """Verify event categorization is working."""
    logger.info("=" * 60)
    logger.info("Verifying Event Categorization...")
    
    try:
        # Add websocket-ingestion path
        ws_path = project_root / "services" / "websocket-ingestion" / "src"
        sys.path.insert(0, str(ws_path))
        
        from influxdb_schema import InfluxDBSchema
        
        schema = InfluxDBSchema()
        
        # Test event categorization
        test_event = {
            "entity_id": "light.living_room",
            "attributes": {"device_class": "light"},
            "event_type": "state_changed"
        }
        
        category = schema._categorize_event(test_event)
        assert category == "lighting", f"Expected 'lighting', got '{category}'"
        
        # Test security event
        security_event = {
            "entity_id": "binary_sensor.front_door",
            "attributes": {"device_class": "door"},
            "event_type": "state_changed"
        }
        
        category = schema._categorize_event(security_event)
        assert category == "security", f"Expected 'security', got '{category}'"
        
        logger.info("✅ Event categorization working")
        logger.info(f"   Light event → {schema._categorize_event(test_event)}")
        logger.info(f"   Security event → {schema._categorize_event(security_event)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Event categorization verification failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def main():
    """Run all verification tests."""
    logger.info("=" * 60)
    logger.info("Home Type Integration Verification")
    logger.info("=" * 60)
    
    results = []
    
    # Run verifications
    results.append(await verify_home_type_client())
    results.append(await verify_integration_helpers())
    results.append(await verify_suggestion_ranking())
    results.append(await verify_event_categorization())
    results.append(await verify_api_endpoints())
    
    # Summary
    logger.info("=" * 60)
    logger.info("Verification Summary")
    logger.info("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    logger.info(f"Passed: {passed}/{total}")
    
    if passed == total:
        logger.info("✅ All verifications passed!")
        return 0
    else:
        logger.warning(f"⚠️ {total - passed} verification(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

