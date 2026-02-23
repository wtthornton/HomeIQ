"""
Tests for Real-Time Device Monitoring (DI-3.1)

This module contains comprehensive tests for the WebSocket-based real-time device monitoring
including WebSocket management, device state tracking, and performance metrics collection.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.api.websocket_router import router
from src.core.device_state_tracker import DeviceStateTracker
from src.core.performance_collector import PerformanceCollector
from src.core.websocket_manager import WebSocketManager


class TestWebSocketManager:
    """Test cases for WebSocketManager."""

    @pytest.fixture
    def websocket_manager(self):
        """Create WebSocket manager instance for testing."""
        return WebSocketManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket for testing."""
        websocket = Mock()
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    @pytest.mark.asyncio
    async def test_websocket_connection(self, websocket_manager, mock_websocket):
        """Test WebSocket connection establishment."""
        client_id = "test_client"

        await websocket_manager.connect(mock_websocket, client_id)

        assert mock_websocket in websocket_manager.active_connections
        assert websocket_manager.connection_info[mock_websocket]["client_id"] == client_id
        assert "connected_at" in websocket_manager.connection_info[mock_websocket]

        # Verify welcome message was sent
        mock_websocket.send_text.assert_called_once()
        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_message["type"] == "connection_established"
        assert sent_message["client_id"] == client_id

    @pytest.mark.asyncio
    async def test_websocket_disconnection(self, websocket_manager, mock_websocket):
        """Test WebSocket disconnection."""
        await websocket_manager.connect(mock_websocket, "test_client")

        websocket_manager.disconnect(mock_websocket)

        assert mock_websocket not in websocket_manager.active_connections
        assert mock_websocket not in websocket_manager.connection_info

    @pytest.mark.asyncio
    async def test_device_subscription(self, websocket_manager, mock_websocket):
        """Test device subscription functionality."""
        await websocket_manager.connect(mock_websocket, "test_client")
        device_id = "test_device"

        await websocket_manager.subscribe_to_device(mock_websocket, device_id)

        assert mock_websocket in websocket_manager.device_subscribers[device_id]
        assert device_id in websocket_manager.connection_info[mock_websocket]["subscribed_devices"]

    @pytest.mark.asyncio
    async def test_device_unsubscription(self, websocket_manager, mock_websocket):
        """Test device unsubscription functionality."""
        await websocket_manager.connect(mock_websocket, "test_client")
        device_id = "test_device"

        await websocket_manager.subscribe_to_device(mock_websocket, device_id)
        await websocket_manager.unsubscribe_from_device(mock_websocket, device_id)

        assert mock_websocket not in websocket_manager.device_subscribers[device_id]
        assert device_id not in websocket_manager.connection_info[mock_websocket]["subscribed_devices"]

    @pytest.mark.asyncio
    async def test_device_update_broadcast(self, websocket_manager, mock_websocket):
        """Test device update broadcasting."""
        await websocket_manager.connect(mock_websocket, "test_client")
        device_id = "test_device"

        await websocket_manager.subscribe_to_device(mock_websocket, device_id)

        update_data = {
            "status": "online",
            "temperature": 25.5,
            "battery_level": 85
        }

        await websocket_manager.broadcast_device_update(device_id, update_data)

        # Verify message was sent
        assert mock_websocket.send_text.call_count >= 2  # Welcome + update
        sent_calls = mock_websocket.send_text.call_args_list

        # Check the last call (device update)
        last_message = json.loads(sent_calls[-1][0][0])
        assert last_message["type"] == "device_update"
        assert last_message["device_id"] == device_id
        assert last_message["data"] == update_data

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, websocket_manager, mock_websocket):
        """Test broadcasting to all connected clients."""
        await websocket_manager.connect(mock_websocket, "test_client")

        message = {
            "type": "system_alert",
            "message": "System maintenance scheduled"
        }

        await websocket_manager.broadcast_to_all(message)

        # Verify message was sent
        assert mock_websocket.send_text.call_count >= 2  # Welcome + broadcast
        sent_calls = mock_websocket.send_text.call_args_list

        # Check the last call (broadcast)
        last_message = json.loads(sent_calls[-1][0][0])
        assert last_message["type"] == "system_alert"
        assert last_message["message"] == "System maintenance scheduled"

    @pytest.mark.asyncio
    async def test_client_message_handling(self, websocket_manager, mock_websocket):
        """Test handling client messages."""
        await websocket_manager.connect(mock_websocket, "test_client")

        # Test subscribe message
        subscribe_message = {
            "type": "subscribe_device",
            "device_id": "test_device"
        }

        await websocket_manager.handle_client_message(mock_websocket, subscribe_message)

        assert mock_websocket in websocket_manager.device_subscribers["test_device"]

        # Test unsubscribe message
        unsubscribe_message = {
            "type": "unsubscribe_device",
            "device_id": "test_device"
        }

        await websocket_manager.handle_client_message(mock_websocket, unsubscribe_message)

        assert mock_websocket not in websocket_manager.device_subscribers["test_device"]

    def test_connection_statistics(self, websocket_manager):
        """Test connection statistics."""
        stats = websocket_manager.get_connection_stats()

        assert "total_connections" in stats
        assert "device_subscriptions" in stats
        assert "connection_details" in stats
        assert stats["total_connections"] == 0  # No connections yet


class TestDeviceStateTracker:
    """Test cases for DeviceStateTracker."""

    @pytest.fixture
    def device_tracker(self):
        """Create device state tracker instance for testing."""
        return DeviceStateTracker(max_history=100)

    @pytest.fixture
    def sample_device_data(self):
        """Sample device data for testing."""
        return {
            "status": "online",
            "temperature": 25.5,
            "humidity": 60.0,
            "battery_level": 85,
            "signal_strength": -65,
            "response_time": 150,
            "error_rate": 0.02
        }

    @pytest.mark.asyncio
    async def test_device_state_update(self, device_tracker, sample_device_data):
        """Test device state update."""
        device_id = "test_device"

        await device_tracker.update_device_state(device_id, sample_device_data)

        assert device_id in device_tracker.device_states
        assert device_tracker.device_states[device_id]["status"] == "online"
        assert device_tracker.device_states[device_id]["online"] is True
        assert "last_updated" in device_tracker.device_states[device_id]

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, device_tracker, sample_device_data):
        """Test metrics tracking."""
        device_id = "test_device"

        await device_tracker.update_device_state(device_id, sample_device_data)

        assert device_id in device_tracker.device_metrics
        assert len(device_tracker.device_metrics[device_id]) == 1

        metric_entry = device_tracker.device_metrics[device_id][0]
        assert metric_entry["temperature"] == 25.5
        assert metric_entry["battery_level"] == 85
        assert "timestamp" in metric_entry

    @pytest.mark.asyncio
    async def test_anomaly_detection(self, device_tracker):
        """Test anomaly detection."""
        device_id = "test_device"

        # Normal data
        normal_data = {
            "response_time": 150,
            "error_rate": 0.02,
            "battery_level": 85,
            "signal_strength": -65
        }

        await device_tracker.update_device_state(device_id, normal_data)

        # Anomalous data
        anomalous_data = {
            "response_time": 2000,  # High response time
            "error_rate": 0.15,     # High error rate
            "battery_level": 15,    # Low battery
            "signal_strength": -85  # Weak signal
        }

        await device_tracker.update_device_state(device_id, anomalous_data)

        # Check if anomalies were detected (this would trigger alerts in real implementation)
        assert device_id in device_tracker.device_states

    @pytest.mark.asyncio
    async def test_device_offline_detection(self, device_tracker, sample_device_data):
        """Test device offline detection."""
        device_id = "test_device"

        # Set device online
        await device_tracker.update_device_state(device_id, sample_device_data)

        # Mark device as offline
        await device_tracker.mark_device_offline(device_id)

        assert device_tracker.device_states[device_id]["online"] is False

    @pytest.mark.asyncio
    async def test_metrics_history_limit(self, device_tracker, sample_device_data):
        """Test metrics history limit."""
        device_id = "test_device"

        # Add more metrics than the limit
        for i in range(150):  # More than max_history=100
            data = sample_device_data.copy()
            data["temperature"] = 20 + i
            await device_tracker.update_device_state(device_id, data)

        # Should only keep the last 100 entries
        assert len(device_tracker.device_metrics[device_id]) == 100

    def test_get_device_state(self, device_tracker, sample_device_data):
        """Test getting device state."""
        device_id = "test_device"

        # Update state
        asyncio.run(device_tracker.update_device_state(device_id, sample_device_data))

        state = device_tracker.get_device_state(device_id)
        assert state is not None
        assert state["status"] == "online"
        assert state["temperature"] == 25.5

    def test_get_device_metrics(self, device_tracker, sample_device_data):
        """Test getting device metrics."""
        device_id = "test_device"

        # Update state multiple times
        for i in range(5):
            data = sample_device_data.copy()
            data["temperature"] = 20 + i
            asyncio.run(device_tracker.update_device_state(device_id, data))

        metrics = device_tracker.get_device_metrics(device_id)
        assert len(metrics) == 5
        assert all("timestamp" in metric for metric in metrics)


class TestPerformanceCollector:
    """Test cases for PerformanceCollector."""

    @pytest.fixture
    def performance_collector(self):
        """Create performance collector instance for testing."""
        return PerformanceCollector(retention_hours=1, max_points_per_device=50)

    @pytest.fixture
    def sample_metrics(self):
        """Sample performance metrics for testing."""
        return {
            "response_time": 150,
            "cpu_usage": 25.5,
            "memory_usage": 60.0,
            "network_latency": 10
        }

    @pytest.mark.asyncio
    async def test_metrics_collection(self, performance_collector, sample_metrics):
        """Test metrics collection."""
        device_id = "test_device"

        await performance_collector.collect_device_metrics(device_id, sample_metrics)

        assert device_id in performance_collector.metrics_history
        assert len(performance_collector.metrics_history[device_id]) == 1

        metric_entry = performance_collector.metrics_history[device_id][0]
        assert metric_entry["response_time"] == 150
        assert metric_entry["cpu_usage"] == 25.5
        assert "timestamp" in metric_entry
        assert metric_entry["device_id"] == device_id

    @pytest.mark.asyncio
    async def test_aggregated_metrics(self, performance_collector, sample_metrics):
        """Test aggregated metrics calculation."""
        device_id = "test_device"

        # Collect multiple metrics
        for i in range(5):
            metrics = sample_metrics.copy()
            metrics["response_time"] = 100 + i * 10
            await performance_collector.collect_device_metrics(device_id, metrics)

        aggregated = await performance_collector.get_device_performance_summary(device_id)

        assert "avg_response_time" in aggregated
        assert "max_response_time" in aggregated
        assert "total_requests" in aggregated
        assert aggregated["total_requests"] == 5

    @pytest.mark.asyncio
    async def test_metrics_retention(self, performance_collector, sample_metrics):
        """Test metrics retention policy."""
        device_id = "test_device"

        # Collect metrics
        await performance_collector.collect_device_metrics(device_id, sample_metrics)

        # Simulate old metrics by modifying timestamp
        old_time = datetime.now(timezone.utc).replace(year=2020)
        performance_collector.metrics_history[device_id][0]["timestamp"] = old_time

        # Trigger cleanup
        await performance_collector._cleanup_old_metrics()

        # Old metrics should be removed
        assert len(performance_collector.metrics_history[device_id]) == 0

    def test_performance_statistics(self, performance_collector, sample_metrics):
        """Test performance statistics."""
        device_id = "test_device"

        # Collect metrics
        asyncio.run(performance_collector.collect_device_metrics(device_id, sample_metrics))

        stats = performance_collector.get_performance_statistics()

        assert "total_devices_tracked" in stats
        assert "total_metrics_points" in stats
        assert "retention_hours" in stats
        assert stats["total_devices_tracked"] == 1


class TestWebSocketAPI:
    """Test cases for WebSocket API endpoints."""

    @pytest.fixture
    def app(self):
        """Create FastAPI app for testing."""
        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_websocket_test_page(self, client):
        """Test WebSocket test page endpoint."""
        response = client.get("/ws/test")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_websocket_health(self, client):
        """Test WebSocket health endpoint."""
        response = client.get("/ws/health")
        assert response.status_code == 200

        data = response.json()
        assert "service" in data
        assert "status" in data
        assert data["service"] == "WebSocket Real-Time Monitoring"


@pytest.mark.asyncio
async def test_integration_scenario():
    """Integration test for complete real-time monitoring workflow."""
    # Create instances
    websocket_manager = WebSocketManager()
    device_tracker = DeviceStateTracker()
    performance_collector = PerformanceCollector()

    # Mock WebSocket
    mock_websocket = Mock()
    mock_websocket.accept = AsyncMock()
    mock_websocket.send_text = AsyncMock()

    # Connect client
    await websocket_manager.connect(mock_websocket, "test_client")

    # Subscribe to device
    device_id = "test_device"
    await websocket_manager.subscribe_to_device(mock_websocket, device_id)

    # Update device state
    device_data = {
        "status": "online",
        "temperature": 25.5,
        "battery_level": 85,
        "response_time": 150,
        "error_rate": 0.02
    }

    await device_tracker.update_device_state(device_id, device_data)

    # Collect performance metrics
    performance_metrics = {
        "response_time": 150,
        "cpu_usage": 25.5,
        "memory_usage": 60.0
    }

    await performance_collector.collect_device_metrics(device_id, performance_metrics)

    # Broadcast device update
    await websocket_manager.broadcast_device_update(device_id, device_data)

    # Verify WebSocket received the update
    assert mock_websocket.send_text.call_count >= 2  # Welcome + update

    # Verify device state is tracked
    assert device_id in device_tracker.device_states
    assert device_tracker.device_states[device_id]["status"] == "online"

    # Verify performance metrics are collected
    assert device_id in performance_collector.metrics_history
    assert len(performance_collector.metrics_history[device_id]) == 1
