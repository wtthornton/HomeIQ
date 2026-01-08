#!/usr/bin/env python3
"""
Troubleshoot Home Assistant Connection for Entity Discovery

This script helps diagnose why entity discovery is failing in websocket-ingestion service.
Checks:
1. Home Assistant HTTP URL accessibility
2. Token validation
3. Entity registry endpoint (HTTP - should fail, WebSocket-only)
4. WebSocket connection capability
"""

import asyncio
import os
import sys
from typing import Optional

import aiohttp

# Windows encoding fix
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


async def test_ha_http_connection(ha_url: str, ha_token: Optional[str]) -> dict:
    """Test basic HTTP connectivity to Home Assistant"""
    result = {
        "success": False,
        "url": ha_url,
        "status_code": None,
        "error": None,
        "response_text": None
    }
    
    try:
        # Normalize URL
        ha_url = ha_url.replace('ws://', 'http://').replace('wss://', 'https://').rstrip('/')
        
        async with aiohttp.ClientSession() as session:
            headers = {}
            if ha_token:
                headers["Authorization"] = f"Bearer {ha_token}"
            
            # Test basic connectivity with /api/config endpoint
            async with session.get(
                f"{ha_url}/api/config",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                result["status_code"] = response.status
                response_text = await response.text()
                result["response_text"] = response_text[:200]  # First 200 chars
                
                if response.status == 200:
                    result["success"] = True
                elif response.status == 401:
                    result["error"] = "Unauthorized - Token may be invalid or expired"
                elif response.status == 404:
                    result["error"] = "Not Found - URL may be incorrect"
                else:
                    result["error"] = f"HTTP {response.status}"
                    
    except aiohttp.ClientConnectorError as e:
        result["error"] = f"Connection error: {e}"
    except asyncio.TimeoutError:
        result["error"] = "Connection timeout - Home Assistant may be unreachable"
    except Exception as e:
        result["error"] = f"Unexpected error: {e}"
    
    return result


async def test_entity_registry_http(ha_url: str, ha_token: Optional[str]) -> dict:
    """
    Test entity registry HTTP endpoint (this should fail - endpoint doesn't exist)
    
    Note: Home Assistant entity registry listing is WebSocket-only.
    This test confirms the endpoint doesn't exist (expected 404).
    """
    result = {
        "success": False,
        "endpoint": "/api/config/entity_registry/list",
        "status_code": None,
        "error": None,
        "note": "Entity registry listing is WebSocket-only in Home Assistant"
    }
    
    try:
        ha_url = ha_url.replace('ws://', 'http://').replace('wss://', 'https://').rstrip('/')
        
        async with aiohttp.ClientSession() as session:
            headers = {}
            if ha_token:
                headers["Authorization"] = f"Bearer {ha_token}"
            
            async with session.get(
                f"{ha_url}/api/config/entity_registry/list",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                result["status_code"] = response.status
                
                if response.status == 404:
                    result["success"] = True  # Expected - endpoint doesn't exist
                    result["error"] = "404 Not Found (expected - endpoint is WebSocket-only)"
                elif response.status == 200:
                    result["error"] = "Unexpected: Endpoint exists (this is unusual)"
                else:
                    result["error"] = f"HTTP {response.status}"
                    
    except Exception as e:
        result["error"] = f"Error: {e}"
    
    return result


async def test_ha_api_health(ha_url: str, ha_token: Optional[str]) -> dict:
    """Test Home Assistant API health/version endpoint"""
    result = {
        "success": False,
        "endpoint": "/api/",
        "version": None,
        "error": None
    }
    
    try:
        ha_url = ha_url.replace('ws://', 'http://').replace('wss://', 'https://').rstrip('/')
        
        async with aiohttp.ClientSession() as session:
            headers = {}
            if ha_token:
                headers["Authorization"] = f"Bearer {ha_token}"
            
            async with session.get(
                f"{ha_url}/api/",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    result["success"] = True
                    result["version"] = data.get("message", "Unknown")
                else:
                    result["error"] = f"HTTP {response.status}"
                    
    except Exception as e:
        result["error"] = f"Error: {e}"
    
    return result


async def main():
    """Run all connection tests"""
    print("=" * 80)
    print("Home Assistant Connection Troubleshooting")
    print("=" * 80)
    print()
    
    # Get configuration from environment
    ha_url = os.getenv('HA_HTTP_URL') or os.getenv('HOME_ASSISTANT_URL', 'http://192.168.1.86:8123')
    ha_token = os.getenv('HA_TOKEN') or os.getenv('HOME_ASSISTANT_TOKEN')
    
    print(f"Configuration:")
    print(f"  HA_URL: {ha_url}")
    print(f"  HA_TOKEN: {'***' + ha_token[-10:] if ha_token and len(ha_token) > 10 else 'NOT SET'}")
    print()
    
    if not ha_token:
        print("[WARN] WARNING: HA_TOKEN not set - authentication tests will fail")
        print()
    
    # Test 1: Basic HTTP connectivity
    print("Test 1: Basic HTTP Connectivity")
    print("-" * 80)
    http_result = await test_ha_http_connection(ha_url, ha_token)
    if http_result["success"]:
        print(f"[OK] HTTP connection successful (Status: {http_result['status_code']})")
    else:
        print(f"[FAIL] HTTP connection failed: {http_result['error']}")
        print(f"   Status: {http_result.get('status_code', 'N/A')}")
        if http_result.get('response_text'):
            print(f"   Response: {http_result['response_text']}")
    print()
    
    # Test 2: API Health/Version
    print("Test 2: Home Assistant API Health")
    print("-" * 80)
    health_result = await test_ha_api_health(ha_url, ha_token)
    if health_result["success"]:
        print(f"[OK] API accessible")
        if health_result.get("version"):
            print(f"   {health_result['version']}")
    else:
        print(f"[FAIL] API health check failed: {health_result['error']}")
    print()
    
    # Test 3: Entity Registry HTTP Endpoint (should fail - WebSocket-only)
    print("Test 3: Entity Registry HTTP Endpoint")
    print("-" * 80)
    entity_result = await test_entity_registry_http(ha_url, ha_token)
    print(f"Endpoint: {entity_result['endpoint']}")
    print(f"Note: {entity_result['note']}")
    if entity_result["status_code"] == 404:
        print(f"[OK] Expected result: 404 Not Found (endpoint is WebSocket-only)")
        print(f"   This confirms entity registry listing requires WebSocket connection")
    else:
        print(f"[FAIL] Unexpected status: {entity_result.get('status_code', 'N/A')}")
        if entity_result.get("error"):
            print(f"   {entity_result['error']}")
    print()
    
    # Summary and recommendations
    print("=" * 80)
    print("Summary & Recommendations")
    print("=" * 80)
    
    if not http_result["success"]:
        print("[FAIL] Basic HTTP connection failed")
        print("   Recommendations:")
        print("   1. Verify HA_HTTP_URL is correct (e.g., http://192.168.1.86:8123)")
        print("   2. Ensure Home Assistant is running and accessible from this machine")
        print("   3. Check network connectivity and firewall rules")
    elif not ha_token:
        print("[WARN] HA_TOKEN not configured")
        print("   Recommendations:")
        print("   1. Generate Long-Lived Access Token in Home Assistant:")
        print("      Settings -> Profile -> Long-Lived Access Tokens -> Create Token")
        print("   2. Set HA_TOKEN environment variable")
    elif http_result["status_code"] == 401:
        print("[FAIL] Authentication failed (401 Unauthorized)")
        print("   Recommendations:")
        print("   1. Verify HA_TOKEN is correct (copy entire token)")
        print("   2. Regenerate token in Home Assistant if expired")
        print("   3. Ensure token has not been revoked")
    elif entity_result["status_code"] == 404:
        print("[OK] HTTP connectivity confirmed")
        print("[OK] Entity registry endpoint correctly returns 404 (WebSocket-only)")
        print()
        print("[WARN] Entity discovery requires WebSocket connection")
        print("   Recommendations:")
        print("   1. Ensure WebSocket connection is established in websocket-ingestion")
        print("   2. Check HA_WS_URL or HA_URL for WebSocket URL (ws://host:8123/api/websocket)")
        print("   3. Verify WebSocket connection in logs:")
        print("      docker-compose logs websocket-ingestion | grep -i websocket")
        print("   4. Check connection status:")
        print("      curl http://localhost:8001/health")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
