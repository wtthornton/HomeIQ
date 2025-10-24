#!/usr/bin/env python3
"""
Phase 1 Services Test Runner
Runs comprehensive tests for all containerized AI services
"""

import subprocess
import sys
import time
import httpx
import asyncio
from pathlib import Path

# Service URLs
SERVICES = {
    "openvino": "http://localhost:8019",
    "ml": "http://localhost:8021", 
    "ai_core": "http://localhost:8018",
    "ner": "http://localhost:8019",
    "openai": "http://localhost:8020"
}

async def check_service_health(service_name: str, url: str) -> bool:
    """Check if a service is healthy"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{url}/health", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "healthy"
    except Exception as e:
        print(f"❌ {service_name} service check failed: {e}")
    return False

async def wait_for_services(max_wait: int = 300) -> bool:
    """Wait for all services to be healthy"""
    print("🔄 Waiting for services to be healthy...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        all_healthy = True
        for service_name, url in SERVICES.items():
            if not await check_service_health(service_name, url):
                all_healthy = False
                break
        
        if all_healthy:
            print("✅ All services are healthy!")
            return True
        
        print("⏳ Waiting for services...")
        await asyncio.sleep(10)
    
    print("❌ Timeout waiting for services to be healthy")
    return False

def run_pytest_tests(test_path: str, service_name: str) -> bool:
    """Run pytest tests for a specific service"""
    print(f"\n🧪 Running tests for {service_name}...")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            test_path, "-v", "--tb=short"
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ {service_name} tests passed")
            return True
        else:
            print(f"❌ {service_name} tests failed")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ {service_name} tests timed out")
        return False
    except Exception as e:
        print(f"❌ Error running {service_name} tests: {e}")
        return False

def main():
    """Main test runner"""
    print("🚀 Phase 1 Services Test Runner")
    print("=" * 50)
    
    # Check if services are running
    print("🔍 Checking service health...")
    
    # Run async health checks
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    if not loop.run_until_complete(wait_for_services()):
        print("❌ Services are not healthy. Please start services first:")
        print("   docker-compose up -d")
        sys.exit(1)
    
    # Test results
    test_results = {}
    
    # Run individual service tests
    service_tests = [
        ("services/openvino-service/tests/test_openvino_service.py", "OpenVINO"),
        ("services/ml-service/tests/test_ml_service.py", "ML"),
        ("services/ai-core-service/tests/test_ai_core_service.py", "AI Core")
    ]
    
    for test_path, service_name in service_tests:
        if Path(test_path).exists():
            test_results[service_name] = run_pytest_tests(test_path, service_name)
        else:
            print(f"⚠️  Test file not found: {test_path}")
            test_results[service_name] = False
    
    # Run integration tests
    integration_test_path = "tests/integration/test_phase1_services.py"
    if Path(integration_test_path).exists():
        test_results["Integration"] = run_pytest_tests(integration_test_path, "Integration")
    else:
        print(f"⚠️  Integration test file not found: {integration_test_path}")
        test_results["Integration"] = False
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    all_passed = True
    for service_name, passed in test_results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{service_name:15} {status}")
        if not passed:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
