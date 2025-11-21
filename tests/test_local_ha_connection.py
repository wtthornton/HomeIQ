#!/usr/bin/env python3
"""
Test connection to local Home Assistant instance
"""

import asyncio
import os
import sys
from urllib.parse import urljoin

import aiohttp
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

async def test_local_ha_connection():
    """Test connection to local Home Assistant instance"""

    # Get HA URL and token from environment
    # Check for both HOME_ASSISTANT_URL (primary) and LOCAL_HA_URL (fallback)
    ha_url = os.getenv("HOME_ASSISTANT_URL") or os.getenv("LOCAL_HA_URL", "http://192.168.1.86:8123")
    ha_token = os.getenv("HOME_ASSISTANT_TOKEN") or os.getenv("LOCAL_HA_TOKEN")

    if not ha_token:
        print("ERROR: HOME_ASSISTANT_TOKEN or LOCAL_HA_TOKEN not found in environment variables")
        return False

    print(f"Testing connection to local Home Assistant: {ha_url}")
    print(f"Using token: {ha_token[:8]}...")

    try:
        async with aiohttp.ClientSession() as session:
            # Test basic connection
            headers = {
                "Authorization": f"Bearer {ha_token}",
                "Content-Type": "application/json",
            }

            # Test /api/ endpoint
            api_url = urljoin(ha_url, "/api/")
            print(f"Testing API endpoint: {api_url}")

            async with session.get(api_url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    print("SUCCESS: Local Home Assistant API connection successful")

                    # Test config endpoint
                    config_url = urljoin(ha_url, "/api/config")
                    print(f"Testing config endpoint: {config_url}")

                    async with session.get(config_url, headers=headers, timeout=10) as config_response:
                        if config_response.status == 200:
                            config_data = await config_response.json()
                            print("SUCCESS: Home Assistant config retrieved")
                            print(f"   - Version: {config_data.get('version', 'Unknown')}")
                            print(f"   - Location: {config_data.get('location_name', 'Unknown')}")
                            return True
                        print(f"ERROR: Config endpoint failed: {config_response.status}")
                        return False
                else:
                    print(f"ERROR: API endpoint failed: {response.status}")
                    return False

    except asyncio.TimeoutError:
        print("ERROR: Connection timeout - Home Assistant may not be reachable")
        return False
    except aiohttp.ClientError as e:
        print(f"ERROR: Connection error: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_local_ha_connection())
    sys.exit(0 if success else 1)
