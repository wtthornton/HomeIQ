#!/usr/bin/env python3
"""
Service Startup Test Script (Epic 44.3: Service Startup Tests in CI/CD)

Tests that services can start without errors, configuration loads correctly,
and health check endpoints respond. Can run against Docker containers or local services.

Usage:
    python scripts/test_service_startup.py                    # Test all services
    python scripts/test_service_startup.py --service <name>  # Test specific service
    python scripts/test_service_startup.py --skip-startup-tests  # Skip tests
"""

import argparse
import asyncio
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiohttp

# Project root
project_root = Path(__file__).parent.parent

# Service configurations (port, health endpoint, startup timeout)
SERVICE_CONFIGS: Dict[str, Dict[str, any]] = {
    'websocket-ingestion': {
        'port': 8001,
        'health_endpoint': '/health',
        'timeout': 30,
        'critical': True
    },
    'device-intelligence-service': {
        'port': 8004,
        'health_endpoint': '/health',
        'timeout': 30,
        'critical': True
    },
    'data-api': {
        'port': 8006,
        'health_endpoint': '/health',
        'timeout': 30,
        'critical': True
    },
    'admin-api': {
        'port': 8003,
        'health_endpoint': '/health',
        'timeout': 30,
        'critical': True
    },
    'ai-automation-service': {
        'port': 8007,
        'health_endpoint': '/health',
        'timeout': 45,
        'critical': False
    },
    'weather-api': {
        'port': 8009,
        'health_endpoint': '/health',
        'timeout': 30,
        'critical': False
    },
}


async def check_service_health(service_name: str, config: Dict[str, any], use_docker: bool = True) -> Tuple[bool, str]:
    """
    Check if a service is healthy.
    
    Returns:
        Tuple of (is_healthy: bool, message: str)
    """
    port = config['port']
    health_endpoint = config['health_endpoint']
    timeout = config.get('timeout', 30)
    
    if use_docker:
        # Check if container is running
        try:
            result = subprocess.run(
                ['docker', 'ps', '--filter', f'name={service_name}', '--format', '{{.Names}}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if service_name not in result.stdout:
                return False, f"Container '{service_name}' not running"
        except subprocess.TimeoutError:
            return False, "Docker command timed out"
        except FileNotFoundError:
            return False, "Docker not found - cannot check container"
    
    # Try to connect to health endpoint
    url = f"http://localhost:{port}{health_endpoint}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                if response.status == 200:
                    return True, "Health check passed"
                else:
                    return False, f"Health check returned status {response.status}"
    except aiohttp.ClientConnectorError:
        return False, f"Cannot connect to {url} - service may not be running"
    except asyncio.TimeoutError:
        return False, f"Health check timed out after {timeout}s"
    except Exception as e:
        return False, f"Error checking health: {e}"


async def test_service_startup(service_name: str, config: Dict[str, any], use_docker: bool = True) -> Tuple[bool, str]:
    """
    Test that a service can start and respond to health checks.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"\n🔍 Testing {service_name}...")
    
    # Check if service is already running
    is_healthy, message = await check_service_health(service_name, config, use_docker)
    
    if is_healthy:
        print(f"✅ {service_name}: Already running and healthy")
        return True, message
    
    # If using Docker, try to start the service
    if use_docker:
        print(f"   Starting {service_name} container...")
        try:
            # Start service using docker compose
            result = subprocess.run(
                ['docker', 'compose', 'up', '-d', service_name],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                return False, f"Failed to start container: {result.stderr}"
            
            # Wait for service to be ready
            timeout = config.get('timeout', 30)
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                is_healthy, message = await check_service_health(service_name, config, use_docker)
                if is_healthy:
                    print(f"✅ {service_name}: Started and healthy")
                    return True, message
                await asyncio.sleep(2)
            
            return False, f"Service did not become healthy within {timeout}s"
            
        except subprocess.TimeoutError:
            return False, "Startup command timed out"
        except FileNotFoundError:
            return False, "Docker not found - cannot start service"
        except Exception as e:
            return False, f"Error starting service: {e}"
    else:
        return False, f"Service not running and cannot start (Docker not available)"


async def test_all_services(services: List[str], use_docker: bool = True) -> Dict[str, Tuple[bool, str]]:
    """Test all specified services."""
    results: Dict[str, Tuple[bool, str]] = {}
    
    for service_name in services:
        if service_name not in SERVICE_CONFIGS:
            print(f"⚠️  Unknown service: {service_name} (skipping)")
            continue
        
        config = SERVICE_CONFIGS[service_name]
        success, message = await test_service_startup(service_name, config, use_docker)
        results[service_name] = (success, message)
    
    return results


def print_results(results: Dict[str, Tuple[bool, str]]) -> bool:
    """Print test results and return whether all tests passed."""
    print("\n" + "="*80)
    print("STARTUP TEST RESULTS")
    print("="*80)
    
    all_passed = True
    critical_failed = []
    
    for service_name, (success, message) in results.items():
        config = SERVICE_CONFIGS.get(service_name, {})
        is_critical = config.get('critical', False)
        
        if success:
            icon = "✅"
            status = "PASSED"
        else:
            icon = "❌"
            status = "FAILED"
            all_passed = False
            if is_critical:
                critical_failed.append(service_name)
        
        critical_marker = "🔴 CRITICAL" if is_critical else "🟡 OPTIONAL"
        print(f"{icon} {service_name}: {status} ({critical_marker})")
        print(f"   {message}")
    
    if critical_failed:
        print(f"\n❌ Critical services failed: {', '.join(critical_failed)}")
        print("   System cannot start without critical services")
    
    return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="Test service startup and health checks (Epic 44.3)"
    )
    parser.add_argument(
        '--service',
        type=str,
        help='Test specific service'
    )
    parser.add_argument(
        '--skip',
        type=str,
        action='append',
        help='Skip specific service (can be used multiple times)'
    )
    parser.add_argument(
        '--skip-startup-tests',
        action='store_true',
        help='Skip startup tests (for testing)'
    )
    parser.add_argument(
        '--no-docker',
        action='store_true',
        help='Do not use Docker (test against already-running services)'
    )
    
    args = parser.parse_args()
    
    if args.skip_startup_tests:
        print("⚠️  Skipping startup tests (--skip-startup-tests flag)")
        return 0
    
    # Determine which services to test
    if args.service:
        services = [args.service]
    else:
        # Test all configured services
        services = list(SERVICE_CONFIGS.keys())
    
    # Filter out skipped services
    skip_list = args.skip or []
    services = [s for s in services if s not in skip_list]
    
    if not services:
        print("⚠️  No services to test")
        return 0
    
    print("="*80)
    print("SERVICE STARTUP TESTS (Epic 44.3)")
    print("="*80)
    print(f"Testing {len(services)} service(s)...")
    print(f"Mode: {'Docker' if not args.no_docker else 'Local (no Docker)'}")
    
    use_docker = not args.no_docker
    
    # Run async tests
    results = asyncio.run(test_all_services(services, use_docker=use_docker))
    
    all_passed = print_results(results)
    
    if all_passed:
        print("\n✅ All startup tests passed")
        return 0
    else:
        print("\n❌ Some startup tests failed - review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())

