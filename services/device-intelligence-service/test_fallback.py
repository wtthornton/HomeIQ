#!/usr/bin/env python3
"""
Test script to verify NABU_CASA_URL fallback functionality.
"""

import os
import sys
import asyncio
import logging
from src.config import Settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_ha_url_fallback():
    """Test the HA URL fallback logic."""
    
    print("🧪 Testing HA URL Fallback Logic")
    print("=" * 50)
    
    # Test 1: Default local URL
    print("\n1. Testing default local URL:")
    settings = Settings()
    print(f"   HA_URL: {settings.HA_URL}")
    print(f"   NABU_CASA_URL: {settings.NABU_CASA_URL}")
    print(f"   Effective URL: {settings.get_ha_url()}")
    
    # Test 2: With NABU_CASA_URL set
    print("\n2. Testing with NABU_CASA_URL set:")
    os.environ["NABU_CASA_URL"] = "https://test-nabu-casa.ui.nabu.casa"
    settings = Settings()
    print(f"   HA_URL: {settings.HA_URL}")
    print(f"   NABU_CASA_URL: {settings.NABU_CASA_URL}")
    print(f"   Effective URL: {settings.get_ha_url()}")
    
    # Test 3: With both URLs set
    print("\n3. Testing with both URLs set:")
    os.environ["HA_URL"] = "http://localhost:8123"
    os.environ["NABU_CASA_URL"] = "https://test-nabu-casa.ui.nabu.casa"
    settings = Settings()
    print(f"   HA_URL: {settings.HA_URL}")
    print(f"   NABU_CASA_URL: {settings.NABU_CASA_URL}")
    print(f"   Effective URL: {settings.get_ha_url()}")
    
    # Test 4: Environment variables from actual deployment
    print("\n4. Testing with environment variables:")
    print(f"   Current HA_URL env: {os.getenv('HA_URL', 'Not set')}")
    print(f"   Current NABU_CASA_URL env: {os.getenv('NABU_CASA_URL', 'Not set')}")
    print(f"   Current HA_TOKEN env: {'Set' if os.getenv('HA_TOKEN') else 'Not set'}")
    
    print("\n✅ HA URL fallback test completed!")

if __name__ == "__main__":
    asyncio.run(test_ha_url_fallback())
