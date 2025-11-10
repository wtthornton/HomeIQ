"""
OpenVINO Service Tests
Tests for the OpenVINO model inference service
"""

import pytest
import httpx
import asyncio
from typing import List, Dict, Any

# Test configuration
OPENVINO_SERVICE_URL = "http://localhost:8019"

class TestOpenVINOService:
    """Test suite for OpenVINO Service"""
    
    @pytest.fixture
    async def client(self):
        """HTTP client for testing"""
        async with httpx.AsyncClient() as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint"""
        response = await client.get(f"{OPENVINO_SERVICE_URL}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "openvino-service"
        assert "models_loaded" in data
    
    @pytest.mark.asyncio
    async def test_model_status(self, client):
        """Test model status endpoint"""
        response = await client.get(f"{OPENVINO_SERVICE_URL}/models/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "embedding_model" in data
        assert "reranker_model" in data
        assert "classifier_model" in data
        assert data["embedding_model"] == "all-MiniLM-L6-v2"
        assert data["reranker_model"] == "bge-reranker-base"
        assert data["classifier_model"] == "flan-t5-small"
    
    @pytest.mark.asyncio
    async def test_embeddings_generation(self, client):
        """Test embeddings generation"""
        test_texts = [
            "Turn on the living room lights",
            "Set temperature to 72 degrees",
            "Lock the front door"
        ]
        
        response = await client.post(
            f"{OPENVINO_SERVICE_URL}/embeddings",
            json={
                "texts": test_texts,
                "normalize": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "embeddings" in data
        assert "model_name" in data
        assert "processing_time" in data
        assert len(data["embeddings"]) == len(test_texts)
        assert data["model_name"] == "all-MiniLM-L6-v2"
        assert data["processing_time"] > 0
    
    @pytest.mark.asyncio
    async def test_reranking(self, client):
        """Test candidate re-ranking"""
        query = "Turn on lights when motion detected"
        candidates = [
            {"description": "Motion sensor triggers lights", "id": 1},
            {"description": "Temperature control system", "id": 2},
            {"description": "Door lock automation", "id": 3}
        ]
        
        response = await client.post(
            f"{OPENVINO_SERVICE_URL}/rerank",
            json={
                "query": query,
                "candidates": candidates,
                "top_k": 2
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "ranked_candidates" in data
        assert "model_name" in data
        assert "processing_time" in data
        assert len(data["ranked_candidates"]) == 2
        assert data["model_name"] == "bge-reranker-base"
        assert data["processing_time"] > 0
    
    @pytest.mark.asyncio
    async def test_pattern_classification(self, client):
        """Test pattern classification"""
        pattern_description = "Turn on lights when motion is detected in the living room"
        
        response = await client.post(
            f"{OPENVINO_SERVICE_URL}/classify",
            json={
                "pattern_description": pattern_description
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "category" in data
        assert "priority" in data
        assert "model_name" in data
        assert "processing_time" in data
        assert data["category"] in ["energy", "comfort", "security", "convenience"]
        assert data["priority"] in ["high", "medium", "low"]
        assert data["model_name"] == "flan-t5-small"
        assert data["processing_time"] > 0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, client):
        """Test error handling for invalid requests"""
        # Test with empty texts
        response = await client.post(
            f"{OPENVINO_SERVICE_URL}/embeddings",
            json={
                "texts": [],
                "normalize": True
            }
        )
        
        # Should handle empty input gracefully
        assert response.status_code in [200, 400]
    
    @pytest.mark.asyncio
    async def test_performance(self, client):
        """Test performance with larger datasets"""
        # Generate test data
        test_texts = [f"Test pattern {i}" for i in range(50)]
        
        response = await client.post(
            f"{OPENVINO_SERVICE_URL}/embeddings",
            json={
                "texts": test_texts,
                "normalize": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should complete within reasonable time
        assert data["processing_time"] < 10.0  # Less than 10 seconds
        assert len(data["embeddings"]) == 50

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
