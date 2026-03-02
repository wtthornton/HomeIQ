"""Tests for shared trace helper utilities."""

from conftest import make_span, make_trace
from utils.trace_helpers import has_errors, span_has_error, trace_wall_clock_ms


class TestHasErrors:
    def test_no_spans(self):
        trace = make_trace(spans=[])
        assert has_errors(trace) is False

    def test_no_error_tags(self, simple_trace):
        assert has_errors(simple_trace) is False

    def test_error_tag_true(self, error_trace):
        assert has_errors(error_trace) is True

    def test_error_tag_false_value(self):
        trace = make_trace(
            spans=[make_span(tags=[{"key": "error", "value": False}])]
        )
        assert has_errors(trace) is False

    def test_error_tag_empty_string(self):
        trace = make_trace(
            spans=[make_span(tags=[{"key": "error", "value": ""}])]
        )
        assert has_errors(trace) is False

    def test_multiple_spans_one_has_error(self):
        trace = make_trace(
            spans=[
                make_span(span_id="ok", tags=[]),
                make_span(span_id="bad", tags=[{"key": "error", "value": True}]),
            ]
        )
        assert has_errors(trace) is True

    def test_non_error_tags_ignored(self):
        trace = make_trace(
            spans=[make_span(tags=[{"key": "http.status_code", "value": 500}])]
        )
        assert has_errors(trace) is False


class TestSpanHasError:
    def test_clean_span(self):
        span = make_span()
        assert span_has_error(span) is False

    def test_error_span(self):
        span = make_span(tags=[{"key": "error", "value": True}])
        assert span_has_error(span) is True

    def test_error_false(self):
        span = make_span(tags=[{"key": "error", "value": False}])
        assert span_has_error(span) is False


class TestTraceWallClockMs:
    def test_empty_trace(self):
        trace = make_trace(spans=[])
        assert trace_wall_clock_ms(trace) == 0.0

    def test_single_span(self):
        # span: startTime=1000000us, duration=50000us => 50ms
        trace = make_trace(
            spans=[make_span(start_time=1000000, duration=50000)]
        )
        assert trace_wall_clock_ms(trace) == 50.0

    def test_overlapping_spans(self, multi_span_trace):
        # span1: 1000000 -> 1100000 (100ms range)
        # span2: 1020000 -> 1070000 (50ms, overlaps)
        # wall clock = (1100000 - 1000000) / 1000 = 100ms
        assert trace_wall_clock_ms(multi_span_trace) == 100.0

    def test_sequential_spans(self):
        # span1: 0 -> 50000 (50ms)
        # span2: 50000 -> 100000 (50ms)
        # wall clock = (100000 - 0) / 1000 = 100ms
        trace = make_trace(
            spans=[
                make_span(span_id="s1", start_time=0, duration=50000),
                make_span(span_id="s2", start_time=50000, duration=50000),
            ]
        )
        assert trace_wall_clock_ms(trace) == 100.0

    def test_sum_would_overcount(self):
        """Verify that overlapping spans are not double-counted."""
        trace = make_trace(
            spans=[
                make_span(span_id="s1", start_time=0, duration=100000),
                make_span(span_id="s2", start_time=10000, duration=20000),
                make_span(span_id="s3", start_time=50000, duration=80000),
            ]
        )
        # Wall clock: max(0+100000, 10000+20000, 50000+80000) - min(0, 10000, 50000)
        # = max(100000, 30000, 130000) - 0 = 130000us = 130ms
        assert trace_wall_clock_ms(trace) == 130.0
        # Sum of durations would be (100+20+80)ms = 200ms, proving wall-clock is correct
