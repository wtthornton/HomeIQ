"""
Tests for statistics endpoints
"""

from unittest.mock import patch

from fastapi.testclient import TestClient
from src.stats_endpoints import StatsEndpoints


class TestStatsEndpoints:
    """Test StatsEndpoints class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.stats_endpoints = StatsEndpoints()
        self.client = TestClient(self.stats_endpoints.router)

    def test_init(self):
        """Test StatsEndpoints initialization"""
        assert self.stats_endpoints.router is not None
        assert hasattr(self.stats_endpoints, 'router')
        assert hasattr(self.stats_endpoints, 'service_urls')

    def test_stats_endpoint(self):
        """Test stats endpoint"""
        response = self.client.get("/stats")

        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "period" in data
        assert "metrics" in data
        assert "trends" in data
        assert "alerts" in data

    def test_stats_endpoint_with_period(self):
        """Test stats endpoint with period parameter"""
        response = self.client.get("/stats?period=1h")

        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "1h"

    def test_stats_endpoint_with_service(self):
        """Test stats endpoint with service parameter"""
        response = self.client.get("/stats?service=websocket-ingestion")

        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "period" in data
        assert "metrics" in data
        assert "trends" in data
        assert "alerts" in data

    def test_stats_endpoint_with_invalid_service(self):
        """Test stats endpoint with invalid service"""
        response = self.client.get("/stats?service=invalid-service")

        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "period" in data
        assert "metrics" in data
        assert "trends" in data
        assert "alerts" in data

    def test_services_stats_endpoint(self):
        """Test services stats endpoint"""
        response = self.client.get("/stats/services")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_metrics_endpoint(self):
        """Test metrics endpoint"""
        response = self.client.get("/stats/metrics")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_metrics_endpoint_with_limit(self):
        """Test metrics endpoint with limit parameter"""
        response = self.client.get("/stats/metrics?limit=50")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 50

    def test_metrics_endpoint_with_metric_name(self):
        """Test metrics endpoint with metric name parameter"""
        response = self.client.get("/stats/metrics?metric_name=events_per_minute")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_metrics_endpoint_with_service(self):
        """Test metrics endpoint with service parameter"""
        response = self.client.get("/stats/metrics?service=websocket-ingestion")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_performance_stats_endpoint(self):
        """Test performance stats endpoint"""
        response = self.client.get("/stats/performance")

        assert response.status_code == 200
        data = response.json()
        assert "overall" in data
        assert "services" in data
        assert "recommendations" in data

    def test_alerts_endpoint(self):
        """Test alerts endpoint"""
        response = self.client.get("/stats/alerts")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_stats_endpoint_error_handling(self):
        """Test stats endpoint error handling"""
        # Mock the _get_all_stats method to raise an exception
        with patch.object(self.stats_endpoints, '_get_all_stats', side_effect=Exception("Test error")):
            response = self.client.get("/stats")

            # Should handle error gracefully
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Failed to get statistics" in data["detail"]

    def test_services_stats_endpoint_error_handling(self):
        """Test services stats endpoint error handling"""
        # Mock the _get_service_stats method to raise an exception
        with patch.object(self.stats_endpoints, '_get_service_stats', side_effect=Exception("Test error")):
            response = self.client.get("/stats/services")

            # Should handle error gracefully
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Failed to get services statistics" in data["detail"]

    def test_metrics_endpoint_error_handling(self):
        """Test metrics endpoint error handling"""
        # Mock the _get_metrics method to raise an exception
        with patch.object(self.stats_endpoints, '_get_metrics', side_effect=Exception("Test error")):
            response = self.client.get("/stats/metrics")

            # Should handle error gracefully
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Failed to get metrics" in data["detail"]

    def test_performance_stats_endpoint_error_handling(self):
        """Test performance stats endpoint error handling"""
        # Mock the _get_performance_stats method to raise an exception
        with patch.object(self.stats_endpoints, '_get_performance_stats', side_effect=Exception("Test error")):
            response = self.client.get("/stats/performance")

            # Should handle error gracefully
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Failed to get performance statistics" in data["detail"]

    def test_alerts_endpoint_error_handling(self):
        """Test alerts endpoint error handling"""
        # Mock the _get_alerts method to raise an exception
        with patch.object(self.stats_endpoints, '_get_alerts', side_effect=Exception("Test error")):
            response = self.client.get("/stats/alerts")

            # Should handle error gracefully
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Failed to get alerts" in data["detail"]

    def test_calculate_overall_performance(self):
        """Test overall performance calculation"""
        services_stats = {
            "service1": {
                "total_requests": 100,
                "total_errors": 5,
                "average_response_time": 100,
                "throughput": 10
            },
            "service2": {
                "total_requests": 200,
                "total_errors": 10,
                "average_response_time": 200,
                "throughput": 20
            }
        }

        overall = self.stats_endpoints._calculate_overall_performance(services_stats)

        assert overall["total_requests"] == 300
        assert overall["total_errors"] == 15
        assert overall["average_response_time"] == 150
        assert overall["throughput"] == 30
        assert overall["success_rate"] == 95.0

    def test_calculate_overall_performance_with_errors(self):
        """Test overall performance calculation with error services"""
        services_stats = {
            "service1": {
                "total_requests": 100,
                "total_errors": 5,
                "average_response_time": 100,
                "throughput": 10
            },
            "service2": {
                "error": "Service unavailable"
            }
        }

        overall = self.stats_endpoints._calculate_overall_performance(services_stats)

        assert overall["total_requests"] == 100
        assert overall["total_errors"] == 5
        assert overall["average_response_time"] == 100
        assert overall["throughput"] == 10
        assert overall["success_rate"] == 95.0

    def test_generate_recommendations(self):
        """Test recommendations generation"""
        services_stats = {
            "service1": {
                "average_response_time": 1500,  # High response time
                "success_rate": 90,  # Low success rate
                "throughput": 5  # Low throughput
            },
            "service2": {
                "average_response_time": 500,  # Normal response time
                "success_rate": 98,  # Good success rate
                "throughput": 50  # Good throughput
            }
        }

        recommendations = self.stats_endpoints._generate_recommendations(services_stats)

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

        # Check that recommendations are generated for service1
        service1_recommendations = [r for r in recommendations if r["service"] == "service1"]
        assert len(service1_recommendations) > 0

        # Check that no recommendations are generated for service2
        service2_recommendations = [r for r in recommendations if r["service"] == "service2"]
        assert len(service2_recommendations) == 0

    def test_generate_recommendations_with_errors(self):
        """Test recommendations generation with error services"""
        services_stats = {
            "service1": {
                "average_response_time": 1500,
                "success_rate": 90,
                "throughput": 5
            },
            "service2": {
                "error": "Service unavailable"
            }
        }

        recommendations = self.stats_endpoints._generate_recommendations(services_stats)

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

        # Check that recommendations are generated for service1
        service1_recommendations = [r for r in recommendations if r["service"] == "service1"]
        assert len(service1_recommendations) > 0

    def test_stats_endpoint_response_time(self):
        """Test stats endpoint response time"""
        import time

        start_time = time.time()
        response = self.client.get("/stats")
        end_time = time.time()

        assert response.status_code == 200

        # Should respond quickly (less than 1 second)
        response_time = end_time - start_time
        assert response_time < 1.0

    def test_stats_endpoint_content_type(self):
        """Test stats endpoint content type"""
        response = self.client.get("/stats")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_stats_endpoint_post_method(self):
        """Test stats endpoint with POST method"""
        response = self.client.post("/stats")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405

    def test_stats_endpoint_put_method(self):
        """Test stats endpoint with PUT method"""
        response = self.client.put("/stats")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405

    def test_stats_endpoint_delete_method(self):
        """Test stats endpoint with DELETE method"""
        response = self.client.delete("/stats")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405

    def test_services_stats_endpoint_post_method(self):
        """Test services stats endpoint with POST method"""
        response = self.client.post("/stats/services")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405

    def test_metrics_endpoint_post_method(self):
        """Test metrics endpoint with POST method"""
        response = self.client.post("/stats/metrics")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405

    def test_performance_stats_endpoint_post_method(self):
        """Test performance stats endpoint with POST method"""
        response = self.client.post("/stats/performance")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405

    def test_alerts_endpoint_post_method(self):
        """Test alerts endpoint with POST method"""
        response = self.client.post("/stats/alerts")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405
