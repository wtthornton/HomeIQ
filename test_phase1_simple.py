#!/usr/bin/env python3
"""
Simple Phase 1 Containerized AI Services Test
Tests the core functionality without waiting for health checks
"""

import asyncio
import httpx
import json
import time
from typing import Dict, Any

# Service URLs
SERVICES = {
    "ml_service": "http://localhost:8021",
    "openvino_service": "http://localhost:8022", 
    "ner_service": "http://localhost:8019",
    "openai_service": "http://localhost:8020",
    "ai_core_service": "http://localhost:8018"
}

async def test_service_health(service_name: str, url: str) -> Dict[str, Any]:
    """Test if a service is responding"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{url}/health")
            if response.status_code == 200:
                return {
                    "service": service_name,
                    "status": "healthy",
                    "response": response.json()
                }
            else:
                return {
                    "service": service_name,
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}"
                }
    except Exception as e:
        return {
            "service": service_name,
            "status": "error",
            "error": str(e)
        }

async def test_ml_service():
    """Test ML service functionality"""
    print("🧪 Testing ML Service...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test clustering
            clustering_data = {
                "data": [[1.0, 2.0], [1.1, 2.1], [5.0, 6.0], [5.1, 6.1]],
                "n_clusters": 2
            }
            
            response = await client.post(
                f"{SERVICES['ml_service']}/cluster",
                json=clustering_data
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ ML Clustering: {result}")
                return True
            else:
                print(f"❌ ML Clustering failed: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ ML Service test failed: {e}")
        return False

async def test_openvino_service():
    """Test OpenVINO service functionality"""
    print("🧪 Testing OpenVINO Service...")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Test embeddings
            embedding_data = {
                "texts": ["hello world", "test sentence"]
            }
            
            response = await client.post(
                f"{SERVICES['openvino_service']}/embeddings",
                json=embedding_data
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ OpenVINO Embeddings: Generated {len(result.get('embeddings', []))} embeddings")
                return True
            else:
                print(f"❌ OpenVINO Embeddings failed: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ OpenVINO Service test failed: {e}")
        return False

async def test_ner_service():
    """Test NER service functionality"""
    print("🧪 Testing NER Service...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test entity extraction
            ner_data = {
                "query": "Turn on the living room lights"
            }
            
            response = await client.post(
                f"{SERVICES['ner_service']}/extract",
                json=ner_data
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ NER Extraction: {result}")
                return True
            else:
                print(f"❌ NER Extraction failed: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ NER Service test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Phase 1 Containerized AI Services Test")
    print("=" * 50)
    
    # Test service health
    print("\n📊 Testing Service Health...")
    health_tasks = [
        test_service_health(name, url) 
        for name, url in SERVICES.items()
    ]
    health_results = await asyncio.gather(*health_tasks)
    
    for result in health_results:
        status_icon = "✅" if result["status"] == "healthy" else "❌"
        print(f"{status_icon} {result['service']}: {result['status']}")
        if result["status"] != "healthy":
            print(f"   Error: {result.get('error', 'Unknown')}")
    
    # Test individual services
    print("\n🧪 Testing Service Functionality...")
    
    # Test ML service
    ml_success = await test_ml_service()
    
    # Test OpenVINO service  
    openvino_success = await test_openvino_service()
    
    # Test NER service
    ner_success = await test_ner_service()
    
    # Summary
    print("\n📋 Test Summary:")
    print(f"ML Service: {'✅ PASS' if ml_success else '❌ FAIL'}")
    print(f"OpenVINO Service: {'✅ PASS' if openvino_success else '❌ FAIL'}")
    print(f"NER Service: {'✅ PASS' if ner_success else '❌ FAIL'}")
    
    total_tests = 3
    passed_tests = sum([ml_success, openvino_success, ner_success])
    
    print(f"\n🎯 Overall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All Phase 1 services are working correctly!")
    else:
        print("⚠️  Some services need attention. Check logs for details.")

if __name__ == "__main__":
    asyncio.run(main())
