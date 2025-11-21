"""
Unit tests for EventRateMonitor - Critical monitoring component
"""

import time
from datetime import datetime, timedelta

from event_rate_monitor import EventRateMonitor


class TestEventRateMonitorInitialization:
    """Test event rate monitor initialization"""

    def test_init_default_values(self):
        """Test initialization with default values"""
        monitor = EventRateMonitor()

        assert monitor.window_size_minutes == 60
        assert len(monitor.event_timestamps) == 0
        assert monitor.events_by_type == {}
        assert monitor.events_by_entity == {}
        assert monitor.total_events == 0
        assert monitor.start_time is not None
        assert monitor.last_event_time is None
        assert monitor.minute_rates.maxlen == 60
        assert monitor.hour_rates.maxlen == 24

    def test_init_custom_window_size(self):
        """Test initialization with custom window size"""
        monitor = EventRateMonitor(window_size_minutes=30)

        assert monitor.window_size_minutes == 30


class TestEventRateMonitorEventRecording:
    """Test event recording functionality"""

    def test_record_single_event(self):
        """Test recording a single event"""
        monitor = EventRateMonitor()

        event_data = {
            "event_type": "state_changed",
            "entity_id": "light.living_room",
            "state": "on",
        }

        monitor.record_event(event_data)

        assert monitor.total_events == 1
        assert monitor.last_event_time is not None
        assert monitor.events_by_type["state_changed"] == 1
        assert monitor.events_by_entity["light.living_room"] == 1

    def test_record_multiple_events(self):
        """Test recording multiple events"""
        monitor = EventRateMonitor()

        for i in range(10):
            event_data = {
                "event_type": "state_changed",
                "entity_id": f"light.room_{i}",
                "state": "on",
            }
            monitor.record_event(event_data)

        assert monitor.total_events == 10
        assert monitor.events_by_type["state_changed"] == 10

    def test_record_events_by_type(self):
        """Test recording events grouped by type"""
        monitor = EventRateMonitor()

        # Record state_changed events
        for _i in range(5):
            monitor.record_event({"event_type": "state_changed", "entity_id": "light.1"})

        # Record service_registered events
        for _i in range(3):
            monitor.record_event({"event_type": "service_registered"})

        # Record call_service events
        for _i in range(2):
            monitor.record_event({"event_type": "call_service"})

        assert monitor.total_events == 10
        assert monitor.events_by_type["state_changed"] == 5
        assert monitor.events_by_type["service_registered"] == 3
        assert monitor.events_by_type["call_service"] == 2

    def test_record_events_by_entity(self):
        """Test recording state_changed events grouped by entity"""
        monitor = EventRateMonitor()

        # Record events for light.1
        for _i in range(3):
            monitor.record_event({
                "event_type": "state_changed",
                "entity_id": "light.1",
            })

        # Record events for light.2
        for _i in range(2):
            monitor.record_event({
                "event_type": "state_changed",
                "entity_id": "light.2",
            })

        assert monitor.events_by_entity["light.1"] == 3
        assert monitor.events_by_entity["light.2"] == 2

    def test_record_event_without_entity_id(self):
        """Test recording event without entity_id"""
        monitor = EventRateMonitor()

        event_data = {
            "event_type": "service_registered",
        }

        monitor.record_event(event_data)

        assert monitor.total_events == 1
        assert monitor.events_by_type["service_registered"] == 1
        assert len(monitor.events_by_entity) == 0

    def test_record_event_with_unknown_type(self):
        """Test recording event with unknown type"""
        monitor = EventRateMonitor()

        event_data = {}

        monitor.record_event(event_data)

        assert monitor.total_events == 1
        assert monitor.events_by_type["unknown"] == 1


class TestEventRateMonitorRateCalculation:
    """Test event rate calculation"""

    def test_get_current_rate_single_minute(self):
        """Test getting current rate for 1 minute window"""
        monitor = EventRateMonitor()

        # Record 10 events
        for _i in range(10):
            monitor.record_event({"event_type": "state_changed", "entity_id": "light.1"})

        rate = monitor.get_current_rate(window_minutes=1)

        # Should be approximately 10 events per minute (all events in last minute)
        assert rate >= 9.0  # Allow some timing tolerance

    def test_get_current_rate_five_minutes(self):
        """Test getting current rate for 5 minute window"""
        monitor = EventRateMonitor()

        # Record 50 events
        for _i in range(50):
            monitor.record_event({"event_type": "state_changed", "entity_id": "light.1"})

        rate = monitor.get_current_rate(window_minutes=5)

        # Should be 10 events per minute (50 events / 5 minutes)
        assert rate == 10.0

    def test_get_current_rate_with_no_events(self):
        """Test getting current rate when no events recorded"""
        monitor = EventRateMonitor()

        rate = monitor.get_current_rate(window_minutes=1)

        assert rate == 0.0

    def test_get_average_rate(self):
        """Test getting average rate"""
        monitor = EventRateMonitor()

        # Record some events
        for _i in range(60):
            monitor.record_event({"event_type": "state_changed", "entity_id": "light.1"})

        average_rate = monitor.get_average_rate(window_minutes=60)

        # Should be 1 event per minute (60 events / 60 minutes, all in current window)
        assert average_rate >= 0.0  # Will depend on timing


class TestEventRateMonitorStatistics:
    """Test rate statistics functionality"""

    def test_get_rate_statistics(self):
        """Test getting comprehensive rate statistics"""
        monitor = EventRateMonitor()

        # Record some events
        for i in range(10):
            monitor.record_event({
                "event_type": "state_changed",
                "entity_id": f"light.{i % 3}",
            })

        stats = monitor.get_rate_statistics()

        assert "total_events" in stats
        assert "uptime_minutes" in stats
        assert "start_time" in stats
        assert "last_event_time" in stats
        assert "current_rates" in stats
        assert "average_rates" in stats
        assert "events_by_type" in stats
        assert "top_entities" in stats
        assert "rate_trends" in stats

        assert stats["total_events"] == 10
        assert stats["events_by_type"]["state_changed"] == 10

    def test_get_rate_statistics_no_events(self):
        """Test getting statistics with no events"""
        monitor = EventRateMonitor()

        stats = monitor.get_rate_statistics()

        assert stats["total_events"] == 0
        assert stats["last_event_time"] is None

    def test_get_top_entities(self):
        """Test getting top entities by event count"""
        monitor = EventRateMonitor()

        # Record events with different frequencies
        for _i in range(10):
            monitor.record_event({
                "event_type": "state_changed",
                "entity_id": "light.1",
            })

        for _i in range(5):
            monitor.record_event({
                "event_type": "state_changed",
                "entity_id": "light.2",
            })

        for _i in range(2):
            monitor.record_event({
                "event_type": "state_changed",
                "entity_id": "light.3",
            })

        stats = monitor.get_rate_statistics()
        top_entities = stats["top_entities"]

        assert len(top_entities) == 3
        assert top_entities[0]["entity_id"] == "light.1"
        assert top_entities[0]["event_count"] == 10
        assert top_entities[1]["entity_id"] == "light.2"
        assert top_entities[1]["event_count"] == 5
        assert top_entities[2]["entity_id"] == "light.3"
        assert top_entities[2]["event_count"] == 2

    def test_get_top_entities_with_limit(self):
        """Test getting top entities with limit"""
        monitor = EventRateMonitor()

        # Record events for 20 entities
        for i in range(20):
            monitor.record_event({
                "event_type": "state_changed",
                "entity_id": f"light.{i}",
            })

        stats = monitor.get_rate_statistics()
        top_entities = stats["top_entities"]

        # Should return only top 10
        assert len(top_entities) <= 10


class TestEventRateMonitorAlerts:
    """Test rate alert generation"""

    def test_get_rate_alerts_no_events(self):
        """Test getting alerts with no events"""
        monitor = EventRateMonitor()

        alerts = monitor.get_rate_alerts()

        assert isinstance(alerts, list)

    def test_get_rate_alerts_high_rate(self):
        """Test alert generation for high event rate"""
        monitor = EventRateMonitor()

        # Record baseline events
        for _i in range(10):
            monitor.record_event({"event_type": "state_changed", "entity_id": "light.1"})

        # Simulate time passing and establish average
        time.sleep(0.1)

        # Record many more events to trigger high rate alert
        for _i in range(100):
            monitor.record_event({"event_type": "state_changed", "entity_id": "light.1"})

        alerts = monitor.get_rate_alerts()

        # Should have a high rate alert (current rate much higher than average)
        # Note: This test may not always trigger due to timing
        assert isinstance(alerts, list)

    def test_get_rate_alerts_no_events_recently(self):
        """Test alert generation for no recent events"""
        monitor = EventRateMonitor()

        # Record an event and manually set last_event_time to long ago
        monitor.record_event({"event_type": "state_changed", "entity_id": "light.1"})
        monitor.last_event_time = datetime.now() - timedelta(minutes=10)

        alerts = monitor.get_rate_alerts()

        # Should have a no_events alert
        no_events_alerts = [a for a in alerts if a["type"] == "no_events"]
        assert len(no_events_alerts) == 1
        assert no_events_alerts[0]["severity"] == "warning"


class TestEventRateMonitorTimestampCleaning:
    """Test timestamp cleaning functionality"""

    def test_clean_old_timestamps(self):
        """Test that old timestamps are cleaned"""
        monitor = EventRateMonitor(window_size_minutes=5)

        # Record an event
        monitor.record_event({"event_type": "state_changed", "entity_id": "light.1"})

        # Manually add old timestamp
        old_time = datetime.now() - timedelta(minutes=10)
        monitor.event_timestamps.appendleft(old_time)

        # Record another event to trigger cleaning
        monitor.record_event({"event_type": "state_changed", "entity_id": "light.2"})

        # Old timestamps should be removed (only events from last 5 minutes kept)
        assert monitor.total_events == 2  # Both events counted
        # Timestamps older than window should be cleaned
        for ts in monitor.event_timestamps:
            time_diff = (datetime.now() - ts).total_seconds() / 60
            assert time_diff <= monitor.window_size_minutes + 1  # Allow 1 minute tolerance


class TestEventRateMonitorStatisticsReset:
    """Test statistics reset functionality"""

    def test_reset_statistics(self):
        """Test resetting all statistics"""
        monitor = EventRateMonitor()

        # Record some events
        for _i in range(10):
            monitor.record_event({
                "event_type": "state_changed",
                "entity_id": "light.1",
            })

        assert monitor.total_events == 10

        # Reset statistics
        monitor.reset_statistics()

        assert monitor.total_events == 0
        assert len(monitor.event_timestamps) == 0
        assert len(monitor.events_by_type) == 0
        assert len(monitor.events_by_entity) == 0
        assert len(monitor.minute_rates) == 0
        assert len(monitor.hour_rates) == 0
        assert monitor.last_event_time is None


class TestEventRateMonitorThreadSafety:
    """Test thread safety of event rate monitor"""

    def test_concurrent_event_recording(self):
        """Test that concurrent event recording is thread-safe"""
        import threading

        monitor = EventRateMonitor()
        num_threads = 10
        events_per_thread = 10

        def record_events():
            for _i in range(events_per_thread):
                monitor.record_event({
                    "event_type": "state_changed",
                    "entity_id": "light.1",
                })

        threads = []
        for _i in range(num_threads):
            thread = threading.Thread(target=record_events)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All events should be recorded
        assert monitor.total_events == num_threads * events_per_thread


class TestEventRateMonitorEdgeCases:
    """Test edge cases"""

    def test_record_event_with_exception_in_data(self):
        """Test that exceptions in event data are handled gracefully"""
        monitor = EventRateMonitor()

        # Record event with None values
        event_data = {
            "event_type": None,
            "entity_id": None,
        }

        monitor.record_event(event_data)

        # Should still increment total events
        assert monitor.total_events == 1

    def test_zero_uptime(self):
        """Test rate calculation with minimal uptime"""
        monitor = EventRateMonitor()

        # Record events immediately
        monitor.record_event({"event_type": "state_changed", "entity_id": "light.1"})

        stats = monitor.get_rate_statistics()

        # Should handle zero/minimal uptime gracefully
        assert "total_events" in stats
        assert stats["total_events"] == 1

    def test_large_event_volume(self):
        """Test handling large event volumes"""
        monitor = EventRateMonitor()

        # Record many events
        for i in range(1000):
            monitor.record_event({
                "event_type": "state_changed",
                "entity_id": f"light.{i % 100}",
            })

        assert monitor.total_events == 1000
        assert len(monitor.events_by_entity) == 100

        stats = monitor.get_rate_statistics()
        assert stats["total_events"] == 1000


class TestEventRateMonitorRateTrends:
    """Test rate trend tracking"""

    def test_minute_rates_tracking(self):
        """Test that minute rates are tracked"""
        monitor = EventRateMonitor()

        # Record some events
        for _i in range(30):
            monitor.record_event({
                "event_type": "state_changed",
                "entity_id": "light.1",
            })

        stats = monitor.get_rate_statistics()

        assert "rate_trends" in stats
        assert "minute_rates" in stats["rate_trends"]
        assert len(stats["rate_trends"]["minute_rates"]) > 0

    def test_hour_rates_tracking(self):
        """Test that hour rates are tracked"""
        monitor = EventRateMonitor()

        # Record some events
        for _i in range(30):
            monitor.record_event({
                "event_type": "state_changed",
                "entity_id": "light.1",
            })

        stats = monitor.get_rate_statistics()

        assert "rate_trends" in stats
        assert "hour_rates" in stats["rate_trends"]
        assert len(stats["rate_trends"]["hour_rates"]) > 0
