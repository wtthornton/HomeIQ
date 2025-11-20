"""
Tests for events endpoints
"""

from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
from src.events_endpoints import EventData, EventFilter, EventSearch, EventsEndpoints


class TestEventsEndpoints:
    """Test EventsEndpoints class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.events_endpoints = EventsEndpoints()
        self.client = TestClient(self.events_endpoints.router)

    def test_init(self):
        """Test EventsEndpoints initialization"""
        assert self.events_endpoints.router is not None
        assert hasattr(self.events_endpoints, 'router')
        assert hasattr(self.events_endpoints, 'service_urls')

    def test_events_endpoint(self):
        """Test events endpoint"""
        response = self.client.get("/events")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_events_endpoint_with_limit(self):
        """Test events endpoint with limit parameter"""
        response = self.client.get("/events?limit=50")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 50

    def test_events_endpoint_with_offset(self):
        """Test events endpoint with offset parameter"""
        response = self.client.get("/events?offset=10")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_events_endpoint_with_entity_id(self):
        """Test events endpoint with entity_id parameter"""
        response = self.client.get("/events?entity_id=sensor.temperature")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_events_endpoint_with_event_type(self):
        """Test events endpoint with event_type parameter"""
        response = self.client.get("/events?event_type=state_changed")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_events_endpoint_with_start_time(self):
        """Test events endpoint with start_time parameter"""
        response = self.client.get("/events?start_time=2024-01-01T00:00:00Z")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_events_endpoint_with_end_time(self):
        """Test events endpoint with end_time parameter"""
        response = self.client.get("/events?end_time=2024-01-01T23:59:59Z")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_events_endpoint_with_service(self):
        """Test events endpoint with service parameter"""
        response = self.client.get("/events?service=websocket-ingestion")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_events_endpoint_with_invalid_service(self):
        """Test events endpoint with invalid service"""
        response = self.client.get("/events?service=invalid-service")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_event_by_id_endpoint(self):
        """Test event by ID endpoint"""
        response = self.client.get("/events/test-event-id")

        # Should handle gracefully (may return 404 if event not found)
        assert response.status_code in [200, 404]

    def test_search_events_endpoint(self):
        """Test search events endpoint"""
        search_data = {
            "query": "temperature",
            "fields": ["entity_id", "event_type", "attributes"],
            "limit": 100
        }

        response = self.client.post("/events/search", json=search_data)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_search_events_endpoint_with_minimal_data(self):
        """Test search events endpoint with minimal data"""
        search_data = {
            "query": "test"
        }

        response = self.client.post("/events/search", json=search_data)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_events_stats_endpoint(self):
        """Test events stats endpoint"""
        response = self.client.get("/events/stats")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_events_stats_endpoint_with_period(self):
        """Test events stats endpoint with period parameter"""
        response = self.client.get("/events/stats?period=1h")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_events_stats_endpoint_with_service(self):
        """Test events stats endpoint with service parameter"""
        response = self.client.get("/events/stats?service=websocket-ingestion")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_active_entities_endpoint(self):
        """Test active entities endpoint"""
        response = self.client.get("/events/entities")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_active_entities_endpoint_with_limit(self):
        """Test active entities endpoint with limit parameter"""
        response = self.client.get("/events/entities?limit=50")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 50

    def test_active_entities_endpoint_with_service(self):
        """Test active entities endpoint with service parameter"""
        response = self.client.get("/events/entities?service=websocket-ingestion")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_event_types_endpoint(self):
        """Test event types endpoint"""
        response = self.client.get("/events/types")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_event_types_endpoint_with_limit(self):
        """Test event types endpoint with limit parameter"""
        response = self.client.get("/events/types?limit=25")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 25

    def test_event_types_endpoint_with_service(self):
        """Test event types endpoint with service parameter"""
        response = self.client.get("/events/types?service=websocket-ingestion")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_events_stream_endpoint(self):
        """Test events stream endpoint"""
        response = self.client.get("/events/stream")

        assert response.status_code == 200
        data = response.json()
        assert "duration" in data
        assert "events" in data
        assert "start_time" in data
        assert "end_time" in data

    def test_events_stream_endpoint_with_duration(self):
        """Test events stream endpoint with duration parameter"""
        response = self.client.get("/events/stream?duration=120")

        assert response.status_code == 200
        data = response.json()
        assert data["duration"] == 120

    def test_events_stream_endpoint_with_entity_id(self):
        """Test events stream endpoint with entity_id parameter"""
        response = self.client.get("/events/stream?entity_id=sensor.temperature")

        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == "sensor.temperature"

    def test_events_endpoint_error_handling(self):
        """Test events endpoint error handling"""
        # Mock the _get_all_events method to raise an exception
        with patch.object(self.events_endpoints, '_get_all_events', side_effect=Exception("Test error")):
            response = self.client.get("/events")

            # Should handle error gracefully
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Failed to get recent events" in data["detail"]

    def test_event_by_id_endpoint_error_handling(self):
        """Test event by ID endpoint error handling"""
        # Mock the _get_event_by_id method to raise an exception
        with patch.object(self.events_endpoints, '_get_event_by_id', side_effect=Exception("Test error")):
            response = self.client.get("/events/test-event-id")

            # Should handle error gracefully
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Failed to get event" in data["detail"]

    def test_search_events_endpoint_error_handling(self):
        """Test search events endpoint error handling"""
        search_data = {
            "query": "test",
            "fields": ["entity_id", "event_type"],
            "limit": 100
        }

        # Mock the _search_events method to raise an exception
        with patch.object(self.events_endpoints, '_search_events', side_effect=Exception("Test error")):
            response = self.client.post("/events/search", json=search_data)

            # Should handle error gracefully
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Failed to search events" in data["detail"]

    def test_events_stats_endpoint_error_handling(self):
        """Test events stats endpoint error handling"""
        # Mock the _get_all_events_stats method to raise an exception
        with patch.object(self.events_endpoints, '_get_all_events_stats', side_effect=Exception("Test error")):
            response = self.client.get("/events/stats")

            # Should handle error gracefully
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Failed to get events statistics" in data["detail"]

    def test_active_entities_endpoint_error_handling(self):
        """Test active entities endpoint error handling"""
        # Mock the _get_all_active_entities method to raise an exception
        with patch.object(self.events_endpoints, '_get_all_active_entities', side_effect=Exception("Test error")):
            response = self.client.get("/events/entities")

            # Should handle error gracefully
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Failed to get active entities" in data["detail"]

    def test_event_types_endpoint_error_handling(self):
        """Test event types endpoint error handling"""
        # Mock the _get_all_event_types method to raise an exception
        with patch.object(self.events_endpoints, '_get_all_event_types', side_effect=Exception("Test error")):
            response = self.client.get("/events/types")

            # Should handle error gracefully
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Failed to get event types" in data["detail"]

    def test_events_stream_endpoint_error_handling(self):
        """Test events stream endpoint error handling"""
        # Mock the _get_events_stream method to raise an exception
        with patch.object(self.events_endpoints, '_get_events_stream', side_effect=Exception("Test error")):
            response = self.client.get("/events/stream")

            # Should handle error gracefully
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Failed to get events stream" in data["detail"]

    def test_event_data_model(self):
        """Test EventData model"""
        event_data = EventData(
            id="test-id",
            timestamp=datetime.now(),
            entity_id="sensor.temperature",
            event_type="state_changed",
            old_state={"state": "20"},
            new_state={"state": "21"},
            attributes={"unit_of_measurement": "°C"},
            tags={"service": "websocket-ingestion"}
        )

        assert event_data.id == "test-id"
        assert event_data.entity_id == "sensor.temperature"
        assert event_data.event_type == "state_changed"
        assert event_data.old_state["state"] == "20"
        assert event_data.new_state["state"] == "21"
        assert event_data.attributes["unit_of_measurement"] == "°C"
        assert event_data.tags["service"] == "websocket-ingestion"

    def test_event_filter_model(self):
        """Test EventFilter model"""
        event_filter = EventFilter(
            entity_id="sensor.temperature",
            event_type="state_changed",
            start_time=datetime.now(),
            end_time=datetime.now(),
            tags={"service": "websocket-ingestion"}
        )

        assert event_filter.entity_id == "sensor.temperature"
        assert event_filter.event_type == "state_changed"
        assert event_filter.tags["service"] == "websocket-ingestion"

    def test_event_search_model(self):
        """Test EventSearch model"""
        event_search = EventSearch(
            query="temperature",
            fields=["entity_id", "event_type"],
            limit=100
        )

        assert event_search.query == "temperature"
        assert event_search.fields == ["entity_id", "event_type"]
        assert event_search.limit == 100

    def test_event_search_model_defaults(self):
        """Test EventSearch model defaults"""
        event_search = EventSearch(query="test")

        assert event_search.query == "test"
        assert event_search.fields == ["entity_id", "event_type", "attributes"]
        assert event_search.limit == 100

    def test_events_endpoint_response_time(self):
        """Test events endpoint response time"""
        import time

        start_time = time.time()
        response = self.client.get("/events")
        end_time = time.time()

        assert response.status_code == 200

        # Should respond quickly (less than 1 second)
        response_time = end_time - start_time
        assert response_time < 1.0

    def test_events_endpoint_content_type(self):
        """Test events endpoint content type"""
        response = self.client.get("/events")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_events_endpoint_post_method(self):
        """Test events endpoint with POST method"""
        response = self.client.post("/events")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405

    def test_events_endpoint_put_method(self):
        """Test events endpoint with PUT method"""
        response = self.client.put("/events")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405

    def test_events_endpoint_delete_method(self):
        """Test events endpoint with DELETE method"""
        response = self.client.delete("/events")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405

    def test_search_events_endpoint_get_method(self):
        """Test search events endpoint with GET method"""
        response = self.client.get("/events/search")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405

    def test_search_events_endpoint_put_method(self):
        """Test search events endpoint with PUT method"""
        response = self.client.put("/events/search")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405

    def test_search_events_endpoint_delete_method(self):
        """Test search events endpoint with DELETE method"""
        response = self.client.delete("/events/search")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405
