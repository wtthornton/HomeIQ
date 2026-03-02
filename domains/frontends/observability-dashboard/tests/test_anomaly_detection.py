"""Tests for anomaly detection in real_time_monitoring."""

import sys
from unittest.mock import MagicMock

# Mock streamlit before importing the page module
_st_mock = MagicMock()
_st_mock.fragment = lambda run_every=None: (lambda f: f)  # passthrough decorator
sys.modules["streamlit"] = _st_mock

from pages.real_time_monitoring import _detect_anomalies, _trace_wall_clock_ms

from conftest import make_span, make_trace


class TestDetectAnomalies:
    def test_no_traces(self):
        assert _detect_anomalies([]) == []

    def test_no_anomalies(self):
        trace = make_trace(
            spans=[make_span(duration=500000)]  # 500ms, under 1s threshold
        )
        anomalies = _detect_anomalies([trace])
        assert anomalies == []

    def test_high_latency_detected(self):
        trace = make_trace(
            spans=[make_span(duration=2000000)]  # 2000ms, over 1s threshold
        )
        anomalies = _detect_anomalies([trace])
        assert len(anomalies) == 1
        assert anomalies[0]["Type"] == "High Latency"

    def test_error_detected_once_per_trace(self):
        """Error anomalies should be de-duplicated: one per trace, not per span."""
        trace = make_trace(
            trace_id="err123",
            spans=[
                make_span(span_id="s1", duration=10000, tags=[{"key": "error", "value": True}]),
                make_span(span_id="s2", duration=10000, tags=[]),
                make_span(span_id="s3", duration=10000, tags=[]),
            ],
        )
        anomalies = _detect_anomalies([trace])
        error_anomalies = [a for a in anomalies if a["Type"] == "Error"]
        assert len(error_anomalies) == 1

    def test_both_latency_and_error(self):
        trace = make_trace(
            trace_id="both123",
            spans=[
                make_span(
                    span_id="s1",
                    duration=2000000,  # 2s - high latency
                    tags=[{"key": "error", "value": True}],
                ),
            ],
        )
        anomalies = _detect_anomalies([trace])
        types = {a["Type"] for a in anomalies}
        assert "High Latency" in types
        assert "Error" in types

    def test_multiple_slow_spans_each_reported(self):
        trace = make_trace(
            spans=[
                make_span(span_id="s1", operation="op-a", duration=1500000),
                make_span(span_id="s2", operation="op-b", duration=2000000),
            ],
        )
        anomalies = _detect_anomalies([trace])
        latency_anomalies = [a for a in anomalies if a["Type"] == "High Latency"]
        assert len(latency_anomalies) == 2

    def test_multiple_traces_independent(self):
        t1 = make_trace(
            trace_id="t1",
            spans=[make_span(trace_id="t1", tags=[{"key": "error", "value": True}])],
        )
        t2 = make_trace(
            trace_id="t2",
            spans=[make_span(trace_id="t2", duration=1500000)],
        )
        anomalies = _detect_anomalies([t1, t2])
        assert len(anomalies) == 2  # 1 error + 1 high latency


class TestTraceWallClockMs:
    def test_delegates_correctly(self):
        trace = make_trace(
            spans=[
                make_span(start_time=0, duration=100000),
                make_span(span_id="s2", start_time=50000, duration=80000),
            ]
        )
        # max(0+100000, 50000+80000) = 130000, min = 0 => 130ms
        assert _trace_wall_clock_ms(trace) == 130.0
