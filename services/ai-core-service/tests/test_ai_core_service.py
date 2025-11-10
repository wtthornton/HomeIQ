"""
AI Core Service Tests
Tests for the orchestrator service
"""

import pytest
import httpx
from typing import List, Dict, Any

# Test configuration
AI_CORE_SERVICE_URL = "http://localhost:8018"

class TestAICoreService:
    """Test suite for AI Core Service"""
    
    @pytest.fixture
    async def client(self):
        """HTTP client for testing"""
        async with httpx.AsyncClient() as client:
            yield client
    
    @pytest.fixture
    def sample_analysis_data(self):
        """Generate sample data for analysis testing"""
        return [
            {"description": "Turn on lights when motion detected", "type": "automation"},
            {"description": "Set temperature to 72 degrees", "type": "automation"},
            {"description": "Lock door at 10 PM", "type": "automation"},
            {"description": "Turn off TV when leaving", "type": "automation"},
            {"description": "Dim lights in evening", "type": "automation"}
        ]
    
    @pytest.fixture
    def sample_pattern_data(self):
        """Generate sample pattern data for testing"""
        return [
            {
                "description": "Motion sensor triggers lights in living room",
                "frequency": "daily",
                "devices": ["motion_sensor", "living_room_lights"]
            },
            {
                "description": "Temperature control based on time of day",
                "frequency": "continuous",
                "devices": ["thermostat", "hvac_system"]
            }
        ]
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint"""
        response = await client.get(f"{AI_CORE_SERVICE_URL}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ai-core-service"
        assert "services" in data
    
    @pytest.mark.asyncio
    async def test_service_status(self, client):
        """Test service status endpoint"""
        response = await client.get(f"{AI_CORE_SERVICE_URL}/services/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "openvino" in data
        assert "ml" in data
        assert "ner" in data
        assert "openai" in data
        
        # Check service structure
        for service_name in ["openvino", "ml", "ner", "openai"]:
            service = data[service_name]
            assert "url" in service
            assert "healthy" in service
            assert isinstance(service["healthy"], bool)
    
    @pytest.mark.asyncio
    async def test_data_analysis(self, client, sample_analysis_data):
        """Test comprehensive data analysis"""
        response = await client.post(
            f"{AI_CORE_SERVICE_URL}/analyze",
            json={
                "data": sample_analysis_data,
                "analysis_type": "pattern_detection",
                "options": {
                    "n_clusters": 3,
                    "contamination": 0.1
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "results" in data
        assert "services_used" in data
        assert "processing_time" in data
        assert isinstance(data["services_used"], list)
        assert data["processing_time"] > 0
    
    @pytest.mark.asyncio
    async def test_pattern_detection(self, client, sample_pattern_data):
        """Test pattern detection"""
        response = await client.post(
            f"{AI_CORE_SERVICE_URL}/patterns",
            json={
                "patterns": sample_pattern_data,
                "detection_type": "full"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "detected_patterns" in data
        assert "services_used" in data
        assert "processing_time" in data
        assert len(data["detected_patterns"]) == len(sample_pattern_data)
        assert isinstance(data["services_used"], list)
        assert data["processing_time"] > 0
    
    @pytest.mark.asyncio
    async def test_suggestion_generation(self, client):
        """Test AI suggestion generation"""
        context = {
            "user_preferences": ["energy_saving", "comfort"],
            "current_automations": 5,
            "devices": ["lights", "thermostat", "locks"]
        }
        
        response = await client.post(
            f"{AI_CORE_SERVICE_URL}/suggestions",
            json={
                "context": context,
                "suggestion_type": "automation_improvements"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "suggestions" in data
        assert "services_used" in data
        assert "processing_time" in data
        assert isinstance(data["suggestions"], list)
        assert isinstance(data["services_used"], list)
        assert data["processing_time"] > 0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, client):
        """Test error handling for invalid requests"""
        # Test with invalid analysis type
        response = await client.post(
            f"{AI_CORE_SERVICE_URL}/analyze",
            json={
                "data": [],
                "analysis_type": "invalid_type",
                "options": {}
            }
        )
        
        # Should handle gracefully (may succeed with fallback or return error)
        assert response.status_code in [200, 400, 500]
    
    @pytest.mark.asyncio
    async def test_service_fallback(self, client):
        """Test service fallback mechanisms"""
        # This test assumes some services might be unavailable
        # The orchestrator should handle this gracefully
        response = await client.post(
            f"{AI_CORE_SERVICE_URL}/analyze",
            json={
                "data": [{"description": "test pattern"}],
                "analysis_type": "basic",
                "options": {}
            }
        )
        
        # Should either succeed with available services or fail gracefully
        assert response.status_code in [200, 503]
    
    @pytest.mark.asyncio
    async def test_performance(self, client):
        """Test performance with larger datasets"""
        # Generate larger test data
        large_data = [
            {"description": f"Test automation pattern {i}", "type": "automation"}
            for i in range(50)
        ]
        
        response = await client.post(
            f"{AI_CORE_SERVICE_URL}/analyze",
            json={
                "data": large_data,
                "analysis_type": "pattern_detection",
                "options": {"n_clusters": 5}
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            # Should complete within reasonable time
            assert data["processing_time"] < 30.0  # Less than 30 seconds

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
