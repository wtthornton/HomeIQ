"""Shared fixtures for observability dashboard tests."""

import sys
from pathlib import Path

import pytest

# Add src directory to path so tests can import application modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.jaeger_client import Trace, TraceSpan


def make_span(
    *,
    trace_id: str = "abc123",
    span_id: str = "span1",
    operation: str = "GET /api",
    start_time: int = 1000000,
    duration: int = 50000,
    process_id: str = "p1",
    tags: list | None = None,
    references: list | None = None,
) -> TraceSpan:
    """Helper to create a TraceSpan with defaults."""
    return TraceSpan(
        traceID=trace_id,
        spanID=span_id,
        operationName=operation,
        startTime=start_time,
        duration=duration,
        tags=tags or [],
        logs=[],
        references=references or [],
        processID=process_id,
    )


def make_trace(
    *,
    trace_id: str = "abc123",
    spans: list[TraceSpan] | None = None,
    processes: dict | None = None,
) -> Trace:
    """Helper to create a Trace with defaults."""
    return Trace(
        traceID=trace_id,
        spans=spans or [],
        processes=processes or {"p1": {"serviceName": "test-service"}},
    )


@pytest.fixture
def simple_trace() -> Trace:
    """A simple trace with one OK span."""
    return make_trace(
        spans=[make_span()],
    )


@pytest.fixture
def error_trace() -> Trace:
    """A trace with an error tag."""
    return make_trace(
        trace_id="err456",
        spans=[
            make_span(
                trace_id="err456",
                tags=[{"key": "error", "value": True}],
            ),
        ],
    )


@pytest.fixture
def multi_span_trace() -> Trace:
    """A trace with multiple spans (overlapping times)."""
    return make_trace(
        trace_id="multi789",
        spans=[
            make_span(
                trace_id="multi789",
                span_id="s1",
                operation="parent-op",
                start_time=1000000,
                duration=100000,
                process_id="p1",
            ),
            make_span(
                trace_id="multi789",
                span_id="s2",
                operation="child-op",
                start_time=1020000,
                duration=50000,
                process_id="p1",
            ),
        ],
        processes={"p1": {"serviceName": "svc-a"}},
    )
