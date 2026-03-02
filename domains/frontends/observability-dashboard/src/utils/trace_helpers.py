"""Shared trace analysis utilities used across dashboard pages."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.jaeger_client import Trace


def has_errors(trace: Trace) -> bool:
    """Check if any span in the trace has error tags."""
    for span in trace.spans:
        for tag in span.tags:
            if tag.get("key") == "error" and tag.get("value"):
                return True
    return False


def span_has_error(span) -> bool:
    """Check if a single span has error tags."""
    for tag in span.tags:
        if tag.get("key") == "error" and tag.get("value"):
            return True
    return False


def trace_wall_clock_ms(trace: Trace) -> float:
    """Calculate wall-clock duration: max(start+duration) - min(start), in milliseconds."""
    if not trace.spans:
        return 0.0
    start = min(span.startTime for span in trace.spans)
    end = max(span.startTime + span.duration for span in trace.spans)
    return (end - start) / 1000  # microseconds to ms
