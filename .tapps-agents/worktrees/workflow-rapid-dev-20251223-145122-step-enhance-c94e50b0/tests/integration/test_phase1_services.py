"""
Phase 1 Services Integration Tests
Tests the complete containerized AI services architecture
"""

import pytest
import httpx
import asyncio
from typing import List, Dict, Any

# Service URLs
OPENVINO_URL = "http://localhost:8019"
ML_URL = "http://localhost:8021"
AI_CORE_URL = "http://localhost:8018"
NER_URL = "http://localhost:8019"  # Same port as OpenVINO
OPENAI_URL = "http://localhost:8020"

class TestPhase1Integration:
    """Integration tests for Phase 1 containerized services"""
    
    @pytest.fixture
    async def clients(self):
        """HTTP clients for all services"""
        clients = {}
        async with httpx.AsyncClient() as client:
            clients["openvino"] = client
            clients["ml"] = client
            clients["ai_core"] = client
            clients["ner"] = client
            clients["openai"] = client
            yield clients
    
    @pytest.mark.asyncio
    async def test_all_services_healthy(self, clients):
        """Test that all services are healthy"""
        services = [
            ("openvino", OPENVINO_URL),
            ("ml", ML_URL),
            ("ai_core", AI_CORE_URL),
            ("ner", NER_URL),
            ("openai", OPENAI_URL)
        ]
        
        for service_name, url in services:
            try:
                response = await clients[service_name].get(f"{url}/health")
                assert response.status_code == 200, f"{service_name} service not healthy"
                
                data = response.json()
                assert data["status"] == "healthy", f"{service_name} service status not healthy"
                
            except Exception as e:
                pytest.fail(f"{service_name} service health check failed: {e}")
    
    @pytest.mark.asyncio
    async def test_end_to_end_analysis_pipeline(self, clients):
        """Test complete analysis pipeline from AI Core Service"""
        # Test data
        test_data = [
            {"description": "Turn on lights when motion detected in living room", "type": "automation"},
            {"description": "Set temperature to 72 degrees at 6 PM", "type": "automation"},
            {"description": "Lock front door when leaving home", "type": "automation"},
            {"description": "Turn off TV when no one is watching", "type": "automation"},
            {"description": "Dim lights in evening for energy saving", "type": "automation"}
        ]
        
        # Test analysis through AI Core Service
        response = await clients["ai_core"].post(
            f"{AI_CORE_URL}/analyze",
            json={
                "data": test_data,
                "analysis_type": "pattern_detection",
                "options": {
                    "n_clusters": 3,
                    "contamination": 0.1
                }
            }
        )
        
        assert response.status_code == 200, "AI Core analysis failed"
        
        data = response.json()
        assert "results" in data
        assert "services_used" in data
        assert "processing_time" in data
        assert len(data["services_used"]) > 0, "No services were used"
        assert data["processing_time"] > 0
    
    @pytest.mark.asyncio
    async def test_service_communication(self, clients):
        """Test direct communication between services"""
        # Test OpenVINO embeddings
        texts = ["Test automation pattern", "Another test pattern"]
        response = await clients["openvino"].post(
            f"{OPENVINO_URL}/embeddings",
            json={"texts": texts, "normalize": True}
        )
        assert response.status_code == 200
        
        # Test ML clustering
        embeddings = response.json()["embeddings"]
        response = await clients["ml"].post(
            f"{ML_URL}/cluster",
            json={
                "data": embeddings,
                "algorithm": "kmeans",
                "n_clusters": 2
            }
        )
        assert response.status_code == 200
        
        # Test pattern classification
        response = await clients["openvino"].post(
            f"{OPENVINO_URL}/classify",
            json={"pattern_description": "Motion sensor triggers lights"}
        )
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_service_fallback_mechanisms(self, clients):
        """Test that services handle failures gracefully"""
        # Test with invalid data to trigger fallbacks
        response = await clients["ai_core"].post(
            f"{AI_CORE_URL}/analyze",
            json={
                "data": [],  # Empty data
                "analysis_type": "pattern_detection",
                "options": {}
            }
        )
        
        # Should either succeed with fallback or fail gracefully
        assert response.status_code in [200, 400, 500]
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, clients):
        """Test performance with multiple concurrent requests"""
        # Generate test data
        test_data = [
            {"description": f"Test pattern {i}", "type": "automation"}
            for i in range(20)
        ]
        
        # Create multiple concurrent requests
        tasks = []
        for i in range(5):
            task = clients["ai_core"].post(
                f"{AI_CORE_URL}/analyze",
                json={
                    "data": test_data,
                    "analysis_type": "pattern_detection",
                    "options": {"n_clusters": 3}
                }
            )
            tasks.append(task)
        
        # Wait for all requests to complete
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check that most requests succeeded
        successful_responses = [r for r in responses if isinstance(r, httpx.Response) and r.status_code == 200]
        assert len(successful_responses) >= 3, "Too many requests failed under load"
    
    @pytest.mark.asyncio
    async def test_service_discovery(self, clients):
        """Test that AI Core Service can discover and communicate with all services"""
        response = await clients["ai_core"].get(f"{AI_CORE_URL}/services/status")
        assert response.status_code == 200
        
        data = response.json()
        expected_services = ["openvino", "ml", "ner", "openai"]
        
        for service_name in expected_services:
            assert service_name in data, f"{service_name} not found in service discovery"
            service_info = data[service_name]
            assert "url" in service_info
            assert "healthy" in service_info
    
    @pytest.mark.asyncio
    async def test_data_consistency(self, clients):
        """Test that data flows correctly through the pipeline"""
        # Test pattern detection
        patterns = [
            {"description": "Motion sensor triggers lights", "frequency": "daily"},
            {"description": "Temperature control at night", "frequency": "continuous"}
        ]
        
        response = await clients["ai_core"].post(
            f"{AI_CORE_URL}/patterns",
            json={
                "patterns": patterns,
                "detection_type": "full"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify that patterns are processed and returned
        assert len(data["detected_patterns"]) == len(patterns)
        
        # Check that each pattern has been enhanced
        for pattern in data["detected_patterns"]:
            assert "description" in pattern
            # Should have additional fields from processing
            assert "category" in pattern or "priority" in pattern
    
    @pytest.mark.asyncio
    async def test_error_propagation(self, clients):
        """Test that errors are properly handled and propagated"""
        # Test with malformed request
        response = await clients["ai_core"].post(
            f"{AI_CORE_URL}/analyze",
            json={
                "data": "invalid_data",  # Should be a list
                "analysis_type": "pattern_detection"
            }
        )
        
        # Should return an error
        assert response.status_code in [400, 422, 500]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
