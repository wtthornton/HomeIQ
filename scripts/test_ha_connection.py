#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify Home Assistant API connectivity and authentication.

This script tests:
1. Network connectivity to HA
2. Authentication with bearer token
3. API endpoint responses
4. Version retrieval from /api/config
"""

import asyncio
import aiohttp
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    print(f"⚠️  Warning: .env file not found at {env_path}")

# Get HA configuration
HA_URL = os.getenv("HA_URL") or os.getenv("HOME_ASSISTANT_URL", "http://192.168.1.86:8123")
HA_TOKEN = os.getenv("HA_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN", "")

# Normalize URL (remove trailing slash)
HA_URL = HA_URL.rstrip("/")

print("=" * 70)
print("Home Assistant API Connection Test")
print("=" * 70)
print(f"HA URL: {HA_URL}")
print(f"HA Token: {'*' * 20 if HA_TOKEN else 'NOT SET'}")
print()


async def test_connection():
    """Test HA API connection and endpoints"""
    
    results = {
        "network": False,
        "authentication": False,
        "api_root": False,
        "api_config": False,
        "version": None,
        "errors": []
    }
    
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json"
    }
    
    timeout = aiohttp.ClientTimeout(total=10)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        # Test 1: Network connectivity (without auth)
        print("[1] Testing network connectivity...")
        try:
            async with session.get(f"{HA_URL}/api/", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status in [200, 401, 403]:
                    print(f"   [OK] Network reachable (HTTP {response.status})")
                    results["network"] = True
                else:
                    print(f"   [WARN] Unexpected status: HTTP {response.status}")
                    results["errors"].append(f"Unexpected status: {response.status}")
        except aiohttp.ClientConnectorError as e:
            print(f"   [FAIL] Network unreachable: {e}")
            results["errors"].append(f"Network error: {e}")
            return results
        except asyncio.TimeoutError:
            print(f"   [FAIL] Connection timeout")
            results["errors"].append("Connection timeout")
            return results
        except Exception as e:
            print(f"   [FAIL] Error: {e}")
            results["errors"].append(f"Connection error: {e}")
            return results
        
        print()
        
        # Test 2: API root endpoint (with auth)
        print("[2] Testing API root endpoint (/api/)...")
        try:
            async with session.get(f"{HA_URL}/api/", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   [OK] API root accessible (HTTP {response.status})")
                    print(f"   Response: {data}")
                    results["api_root"] = True
                    if "version" in data:
                        results["version"] = data["version"]
                        print(f"   Version from /api/: {data['version']}")
                elif response.status == 401:
                    print(f"   [FAIL] Authentication failed (HTTP 401)")
                    results["errors"].append("Authentication failed (401)")
                elif response.status == 403:
                    print(f"   [FAIL] Forbidden (HTTP 403)")
                    results["errors"].append("Forbidden (403)")
                else:
                    print(f"   [WARN] Unexpected status: HTTP {response.status}")
                    text = await response.text()
                    print(f"   Response: {text[:200]}")
                    results["errors"].append(f"Unexpected status: {response.status}")
        except Exception as e:
            print(f"   [FAIL] Error: {e}")
            results["errors"].append(f"API root error: {e}")
        
        print()
        
        # Test 3: API config endpoint (with auth) - This is what we use in health_service
        print("[3] Testing API config endpoint (/api/config)...")
        try:
            async with session.get(f"{HA_URL}/api/config", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   [OK] API config accessible (HTTP {response.status})")
                    results["api_config"] = True
                    results["authentication"] = True
                    
                    # Extract version
                    version = data.get("version", "unknown")
                    results["version"] = version
                    print(f"   Version: {version}")
                    print(f"   Location: {data.get('location_name', 'N/A')}")
                    print(f"   Time Zone: {data.get('time_zone', 'N/A')}")
                    print(f"   Components: {len(data.get('components', []))}")
                    
                elif response.status == 401:
                    print(f"   [FAIL] Authentication failed (HTTP 401)")
                    print(f"   [TIP] Check if HA_TOKEN is valid")
                    results["errors"].append("Authentication failed (401)")
                elif response.status == 403:
                    print(f"   [FAIL] Forbidden (HTTP 403)")
                    results["errors"].append("Forbidden (403)")
                else:
                    print(f"   [WARN] Unexpected status: HTTP {response.status}")
                    text = await response.text()
                    print(f"   Response: {text[:200]}")
                    results["errors"].append(f"Unexpected status: {response.status}")
        except Exception as e:
            print(f"   [FAIL] Error: {e}")
            results["errors"].append(f"API config error: {e}")
        
        print()
        
        # Test 4: Test from container perspective (if running in Docker)
        print("[4] Testing from container network perspective...")
        try:
            # Try common Docker network hostnames
            container_urls = [
                "http://host.docker.internal:8123",
                "http://192.168.1.86:8123",
                "http://172.17.0.1:8123",  # Default Docker bridge gateway
            ]
            
            for test_url in container_urls:
                try:
                    async with session.get(
                        f"{test_url}/api/config",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=3)
                    ) as response:
                        if response.status == 200:
                            print(f"   [OK] Container can reach HA via: {test_url}")
                            break
                except:
                    pass
            else:
                print(f"   [SKIP] Could not test container connectivity (running locally)")
        except Exception as e:
            print(f"   [SKIP] Container test skipped: {e}")
    
    return results


async def main():
    """Main test function"""
    
    if not HA_TOKEN:
        print("[ERROR] HA_TOKEN not set!")
        print("   Set it in .env file or environment variable")
        sys.exit(1)
    
    print()
    results = await test_connection()
    print()
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Network Reachable: {'[OK]' if results['network'] else '[FAIL]'}")
    print(f"Authentication: {'[OK]' if results['authentication'] else '[FAIL]'}")
    print(f"API Root Access: {'[OK]' if results['api_root'] else '[FAIL]'}")
    print(f"API Config Access: {'[OK]' if results['api_config'] else '[FAIL]'}")
    print(f"Version Retrieved: {results['version'] or '[FAIL] Not available'}")
    
    if results['errors']:
        print()
        print("Errors:")
        for error in results['errors']:
            print(f"  - {error}")
    
    print()
    
    # Recommendations
    if not results['network']:
        print("[TIP] Recommendation: Check network connectivity to HA")
        print(f"   Try: curl {HA_URL}/api/")
    elif not results['authentication']:
        print("[TIP] Recommendation: Check HA_TOKEN is valid")
        print("   Generate new token in HA: Profile -> Long-Lived Access Tokens")
    elif not results['api_config']:
        print("[TIP] Recommendation: Check HA API is accessible")
        print(f"   Try: curl -H 'Authorization: Bearer <token>' {HA_URL}/api/config")
    elif results['version']:
        print("[SUCCESS] All tests passed! HA API is accessible and working.")
        print(f"   Version: {results['version']}")
    
    print("=" * 70)
    
    # Exit code
    if results['api_config'] and results['version']:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

