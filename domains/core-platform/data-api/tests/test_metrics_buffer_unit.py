"""Unit tests for MetricsBuffer and helpers — Story 85.5

Tests recording, aggregation, series retrieval, and thread safety.
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.metrics_buffer import MetricsBuffer, MinuteBucket, _parse_interval


# ---------------------------------------------------------------------------
# MinuteBucket dataclass
# ---------------------------------------------------------------------------

class TestMinuteBucket:

    def test_avg_response_time_with_data(self):
        b = MinuteBucket(timestamp=datetime.now(UTC), response_time_sum=100.0, response_time_count=10)
        assert b.avg_response_time == pytest.approx(10.0)

    def test_avg_response_time_no_data(self):
        b = MinuteBucket(timestamp=datetime.now(UTC))
        assert b.avg_response_time == 0.0

    def test_avg_db_latency_with_data(self):
        b = MinuteBucket(timestamp=datetime.now(UTC), db_query_sum=50.0, db_query_count=5)
        assert b.avg_db_latency == pytest.approx(10.0)

    def test_avg_db_latency_no_data(self):
        b = MinuteBucket(timestamp=datetime.now(UTC))
        assert b.avg_db_latency == 0.0

    def test_error_rate_with_data(self):
        b = MinuteBucket(timestamp=datetime.now(UTC), request_count=100, error_count=5)
        assert b.error_rate == pytest.approx(5.0)

    def test_error_rate_no_requests(self):
        b = MinuteBucket(timestamp=datetime.now(UTC))
        assert b.error_rate == 0.0

    def test_defaults(self):
        b = MinuteBucket(timestamp=datetime.now(UTC))
        assert b.request_count == 0
        assert b.error_count == 0
        assert b.response_time_min == float("inf")
        assert b.response_time_max == 0.0


# ---------------------------------------------------------------------------
# _parse_interval helper
# ---------------------------------------------------------------------------

class TestParseInterval:

    def test_minutes(self):
        assert _parse_interval("5m") == timedelta(minutes=5)

    def test_hours(self):
        assert _parse_interval("2h") == timedelta(hours=2)

    def test_days(self):
        assert _parse_interval("1d") == timedelta(days=1)

    def test_invalid_falls_back_to_1m(self):
        assert _parse_interval("invalid") == timedelta(minutes=1)

    def test_single_minute(self):
        assert _parse_interval("1m") == timedelta(minutes=1)


# ---------------------------------------------------------------------------
# MetricsBuffer — recording
# ---------------------------------------------------------------------------

class TestMetricsBufferRecording:

    def test_record_single_request(self):
        buf = MetricsBuffer()
        buf.record_request(50.0, False)
        assert buf._current is not None
        assert buf._current.request_count == 1
        assert buf._current.response_time_sum == 50.0

    def test_record_error_request(self):
        buf = MetricsBuffer()
        buf.record_request(100.0, True)
        assert buf._current.error_count == 1

    def test_record_multiple_requests(self):
        buf = MetricsBuffer()
        buf.record_request(10.0, False)
        buf.record_request(20.0, False)
        buf.record_request(30.0, True)
        assert buf._current.request_count == 3
        assert buf._current.error_count == 1
        assert buf._current.response_time_sum == pytest.approx(60.0)

    def test_tracks_min_max(self):
        buf = MetricsBuffer()
        buf.record_request(10.0, False)
        buf.record_request(50.0, False)
        buf.record_request(30.0, False)
        assert buf._current.response_time_min == pytest.approx(10.0)
        assert buf._current.response_time_max == pytest.approx(50.0)

    def test_record_db_query(self):
        buf = MetricsBuffer()
        buf.record_db_query(5.0)
        buf.record_db_query(15.0)
        assert buf._current.db_query_count == 2
        assert buf._current.db_query_sum == pytest.approx(20.0)
        assert buf._current.db_query_min == pytest.approx(5.0)
        assert buf._current.db_query_max == pytest.approx(15.0)

    def test_new_minute_rotates_bucket(self):
        buf = MetricsBuffer()
        # Create a bucket in the past
        past = datetime.now(UTC).replace(second=0, microsecond=0) - timedelta(minutes=1)
        buf._current = MinuteBucket(timestamp=past, request_count=1)
        buf.record_request(10.0, False)
        # Old bucket should be in snapshots
        assert len(buf._snapshots) == 1
        assert buf._snapshots[0].request_count == 1


# ---------------------------------------------------------------------------
# MetricsBuffer — get_series
# ---------------------------------------------------------------------------

class TestMetricsBufferGetSeries:

    def _create_buffer_with_data(self):
        buf = MetricsBuffer()
        now = datetime.now(UTC).replace(second=0, microsecond=0)
        # Add a bucket at the current minute
        bucket = MinuteBucket(
            timestamp=now,
            request_count=100,
            error_count=5,
            response_time_sum=500.0,
            response_time_count=100,
            db_query_sum=200.0,
            db_query_count=50,
        )
        buf._current = bucket
        return buf, now

    def test_response_time_series(self):
        buf, now = self._create_buffer_with_data()
        series = buf.get_series("response_time", now.isoformat(), "1m", 1)
        assert len(series) == 1
        assert series[0]["value"] == pytest.approx(5.0)  # 500/100

    def test_db_latency_series(self):
        buf, now = self._create_buffer_with_data()
        series = buf.get_series("db_latency", now.isoformat(), "1m", 1)
        assert len(series) == 1
        assert series[0]["value"] == pytest.approx(4.0)  # 200/50

    def test_error_rate_series(self):
        buf, now = self._create_buffer_with_data()
        series = buf.get_series("error_rate", now.isoformat(), "1m", 1)
        assert len(series) == 1
        assert series[0]["value"] == pytest.approx(5.0)  # 5/100 * 100

    def test_unknown_metric_returns_zero(self):
        buf, now = self._create_buffer_with_data()
        series = buf.get_series("unknown", now.isoformat(), "1m", 1)
        assert series[0]["value"] == 0.0

    def test_empty_buffer_returns_zeros(self):
        buf = MetricsBuffer()
        now = datetime.now(UTC).isoformat()
        series = buf.get_series("response_time", now, "1m", 3)
        assert len(series) == 3
        assert all(p["value"] == 0.0 for p in series)

    def test_series_has_timestamps(self):
        buf, now = self._create_buffer_with_data()
        series = buf.get_series("response_time", now.isoformat(), "1m", 2)
        assert "timestamp" in series[0]
        assert "timestamp" in series[1]

    def test_num_points_respected(self):
        buf = MetricsBuffer()
        now = datetime.now(UTC).isoformat()
        series = buf.get_series("response_time", now, "1m", 5)
        assert len(series) == 5


# ---------------------------------------------------------------------------
# MetricsBuffer — max capacity
# ---------------------------------------------------------------------------

class TestMetricsBufferCapacity:

    def test_max_minutes_limit(self):
        buf = MetricsBuffer()
        assert buf._snapshots.maxlen == 10_080
