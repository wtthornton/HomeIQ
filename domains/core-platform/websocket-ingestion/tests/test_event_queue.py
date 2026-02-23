"""
Tests for Event Queue
"""

import os
import tempfile

import pytest
from src.event_queue import EventQueue


class TestEventQueue:
    """Test cases for EventQueue class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.queue = EventQueue(maxsize=100)

    def test_initialization(self):
        """Test queue initialization"""
        assert self.queue.maxsize == 100
        assert self.queue.queue.maxsize == 100
        assert self.queue.total_events_received == 0
        assert self.queue.total_events_processed == 0
        assert self.queue.total_events_dropped == 0
        assert self.queue.overflow_events == 0

    @pytest.mark.asyncio
    async def test_put_get_event(self):
        """Test putting and getting events"""
        event_data = {"event_type": "state_changed", "entity_id": "sensor.test"}

        # Put event
        success = await self.queue.put(event_data)
        assert success

        # Get event
        retrieved_event = await self.queue.get()
        assert retrieved_event is not None
        assert retrieved_event["data"] == event_data
        assert "timestamp" in retrieved_event
        assert "id" in retrieved_event

    @pytest.mark.asyncio
    async def test_put_get_nowait(self):
        """Test putting and getting events without waiting"""
        event_data = {"event_type": "state_changed", "entity_id": "sensor.test"}

        # Put event
        success = await self.queue.put(event_data)
        assert success

        # Get event without waiting
        retrieved_event = await self.queue.get_nowait()
        assert retrieved_event is not None
        assert retrieved_event["data"] == event_data

    @pytest.mark.asyncio
    async def test_queue_overflow(self):
        """Test queue overflow handling"""
        # Create a small queue
        small_queue = EventQueue(maxsize=2)

        # Fill the queue
        for i in range(3):
            event_data = {"event_type": "state_changed", "entity_id": f"sensor.test{i}"}
            success = await small_queue.put(event_data)

            if i < 2:
                assert success  # First two should succeed
            else:
                assert not success  # Third should fail due to overflow

        assert small_queue.overflow_events == 1

    @pytest.mark.asyncio
    async def test_priority_events(self):
        """Test event priority handling"""
        # Put events with different priorities
        await self.queue.put({"event_type": "low_priority"}, priority=1)
        await self.queue.put({"event_type": "high_priority"}, priority=10)
        await self.queue.put({"event_type": "medium_priority"}, priority=5)

        # Get events and check priorities
        events = []
        for _ in range(3):
            event = await self.queue.get()
            if event:
                events.append(event)

        # Should have 3 events
        assert len(events) == 3

        # Check that priority is preserved
        priorities = [event["priority"] for event in events]
        assert 1 in priorities
        assert 5 in priorities
        assert 10 in priorities

    @pytest.mark.asyncio
    async def test_queue_statistics(self):
        """Test queue statistics"""
        # Put some events
        for i in range(5):
            event_data = {"event_type": "state_changed", "entity_id": f"sensor.test{i}"}
            await self.queue.put(event_data)

        # Get some events
        for _ in range(3):
            await self.queue.get()

        # Get statistics
        stats = self.queue.get_queue_statistics()

        assert stats["total_events_received"] == 5
        assert stats["total_events_processed"] == 3
        assert stats["queue_size"] == 2
        assert stats["queue_maxsize"] == 100
        assert stats["overflow_queue_size"] == 0
        assert stats["overflow_events"] == 0
        assert stats["drop_rate_percent"] == 0

    @pytest.mark.asyncio
    async def test_health_status(self):
        """Test queue health status"""
        # Test healthy status
        health = self.queue.get_health_status()
        assert health["status"] == "healthy"
        assert health["queue_size"] == 0
        assert health["utilization_percent"] == 0

        # Fill queue to warning level
        for i in range(75):  # 75% utilization
            event_data = {"event_type": "state_changed", "entity_id": f"sensor.test{i}"}
            await self.queue.put(event_data)

        health = self.queue.get_health_status()
        assert health["status"] == "warning"
        assert health["utilization_percent"] >= 70

        # Fill queue to critical level
        for i in range(25):  # 100% utilization
            event_data = {"event_type": "state_changed", "entity_id": f"sensor.test{i}"}
            await self.queue.put(event_data)

        health = self.queue.get_health_status()
        assert health["status"] == "critical"
        assert health["utilization_percent"] >= 90

    @pytest.mark.asyncio
    async def test_persistence(self):
        """Test queue persistence"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create queue with persistence
            persistent_queue = EventQueue(maxsize=2, persistence_path=temp_dir)

            # Fill queue to cause overflow
            for i in range(3):
                event_data = {"event_type": "state_changed", "entity_id": f"sensor.test{i}"}
                await persistent_queue.put(event_data)

            # Check that overflow event was persisted
            assert persistent_queue.overflow_events == 1

            # Check that persistence file was created
            persistence_files = list(os.listdir(temp_dir))
            assert len(persistence_files) > 0
            assert any(f.startswith("overflow_events_") for f in persistence_files)

    @pytest.mark.asyncio
    async def test_recover_overflow_events(self):
        """Test recovering overflow events"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create queue with persistence
            persistent_queue = EventQueue(maxsize=2, persistence_path=temp_dir)

            # Fill queue to cause overflow
            for i in range(3):
                event_data = {"event_type": "state_changed", "entity_id": f"sensor.test{i}"}
                await persistent_queue.put(event_data)

            # Create new queue and recover events
            new_queue = EventQueue(maxsize=100, persistence_path=temp_dir)
            recovered_count = await new_queue.recover_overflow_events()

            assert recovered_count == 1
            assert len(new_queue.overflow_queue) == 1

    def test_configure_maxsize(self):
        """Test configuring queue maxsize"""
        self.queue.configure_maxsize(200)
        assert self.queue.maxsize == 200

    def test_configure_maxsize_invalid(self):
        """Test configuring invalid maxsize"""
        with pytest.raises(ValueError):
            self.queue.configure_maxsize(0)

        with pytest.raises(ValueError):
            self.queue.configure_maxsize(-1)

    def test_configure_persistence(self):
        """Test configuring persistence"""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.queue.configure_persistence(temp_dir)
            assert self.queue.persistence_path == temp_dir

            self.queue.configure_persistence(None)
            assert self.queue.persistence_path is None

    def test_reset_statistics(self):
        """Test resetting statistics"""
        # Set some statistics
        self.queue.total_events_received = 10
        self.queue.total_events_processed = 8
        self.queue.total_events_dropped = 2

        # Reset statistics
        self.queue.reset_statistics()

        assert self.queue.total_events_received == 0
        assert self.queue.total_events_processed == 0
        assert self.queue.total_events_dropped == 0
        assert self.queue.overflow_events == 0
        assert len(self.queue.queue_size_history) == 0
        assert len(self.queue.processing_rate_history) == 0
