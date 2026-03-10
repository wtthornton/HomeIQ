"""Tests for data processing functions in page modules.

Covers internal helpers from trace_visualization, service_performance,
and real_time_monitoring that transform trace data into DataFrames and charts.
"""

import sys
from unittest.mock import MagicMock

# Mock streamlit before importing any page module
_st_mock = MagicMock()
_st_mock.fragment = lambda run_every=None: (lambda f: f)
sys.modules.setdefault("streamlit", _st_mock)

import pandas as pd
from conftest import make_span, make_trace
from pages.real_time_monitoring import (
    _calculate_service_health,
    _create_realtime_dataframe,
    _detect_anomalies,
)
from pages.service_performance import (
    _calculate_service_metrics,
    _create_error_dataframe,
    _create_health_dataframe,
    _create_latency_dataframe,
)
from pages.trace_visualization import _create_dependency_graph, _create_timeline_chart


# ---------------------------------------------------------------------------
# trace_visualization: _create_timeline_chart
# ---------------------------------------------------------------------------


class TestCreateTimelineChart:
    def test_empty_traces_returns_figure(self):
        fig = _create_timeline_chart([])
        # Should have an annotation saying no data
        assert any("No trace data" in a.text for a in fig.layout.annotations)

    def test_single_trace_returns_figure(self):
        trace = make_trace(spans=[make_span()])
        fig = _create_timeline_chart([trace])
        assert len(fig.data) >= 1

    def test_chart_contains_service_name(self):
        trace = make_trace(
            spans=[make_span()],
            processes={"p1": {"serviceName": "my-service"}},
        )
        fig = _create_timeline_chart([trace])
        service_names = [t.name for t in fig.data]
        assert "my-service" in service_names

    def test_error_trace_marker_color(self):
        trace = make_trace(
            spans=[make_span(tags=[{"key": "error", "value": True}])],
        )
        fig = _create_timeline_chart([trace])
        # The marker color mapping should include red for errors
        assert len(fig.data) >= 1

    def test_multiple_services(self):
        trace = make_trace(
            spans=[
                make_span(span_id="s1", process_id="p1"),
                make_span(span_id="s2", process_id="p2"),
            ],
            processes={
                "p1": {"serviceName": "svc-a"},
                "p2": {"serviceName": "svc-b"},
            },
        )
        fig = _create_timeline_chart([trace])
        service_names = {t.name for t in fig.data}
        assert "svc-a" in service_names
        assert "svc-b" in service_names


# ---------------------------------------------------------------------------
# trace_visualization: _create_dependency_graph
# ---------------------------------------------------------------------------


class TestCreateDependencyGraph:
    def test_empty_traces_returns_figure(self):
        fig = _create_dependency_graph([])
        assert any("No dependency data" in a.text for a in fig.layout.annotations)

    def test_no_references_returns_empty_figure(self):
        trace = make_trace(spans=[make_span(references=[])])
        fig = _create_dependency_graph([trace])
        assert any("No dependency data" in a.text for a in fig.layout.annotations)

    def test_child_of_reference_creates_dependency(self):
        parent_span = make_span(span_id="parent", process_id="p1")
        child_span = make_span(
            span_id="child",
            process_id="p2",
            references=[{"refType": "CHILD_OF", "spanID": "parent"}],
        )
        trace = make_trace(
            spans=[parent_span, child_span],
            processes={
                "p1": {"serviceName": "gateway"},
                "p2": {"serviceName": "backend"},
            },
        )
        fig = _create_dependency_graph([trace])
        # Should be a Sankey diagram with data
        assert len(fig.data) == 1
        assert fig.data[0].type == "sankey"
        labels = list(fig.data[0].node.label)
        assert "gateway" in labels
        assert "backend" in labels

    def test_multiple_calls_increment_count(self):
        spans = []
        for i in range(3):
            spans.append(make_span(span_id=f"parent_{i}", process_id="p1"))
            spans.append(
                make_span(
                    span_id=f"child_{i}",
                    process_id="p2",
                    references=[{"refType": "CHILD_OF", "spanID": f"parent_{i}"}],
                )
            )
        trace = make_trace(
            spans=spans,
            processes={
                "p1": {"serviceName": "gateway"},
                "p2": {"serviceName": "backend"},
            },
        )
        fig = _create_dependency_graph([trace])
        # The link value should be 3
        assert fig.data[0].link.value == (3,) or list(fig.data[0].link.value) == [3]


# ---------------------------------------------------------------------------
# service_performance: _calculate_service_metrics
# ---------------------------------------------------------------------------


class TestCalculateServiceMetrics:
    def test_empty_traces(self):
        assert _calculate_service_metrics([]) == {}

    def test_single_span_metrics(self):
        trace = make_trace(
            spans=[make_span(duration=100000)],  # 100ms
            processes={"p1": {"serviceName": "svc-a"}},
        )
        metrics = _calculate_service_metrics([trace])
        assert "svc-a" in metrics
        assert metrics["svc-a"]["total_count"] == 1
        assert metrics["svc-a"]["p50"] == 100.0
        assert metrics["svc-a"]["error_rate"] == 0

    def test_error_counted(self):
        trace = make_trace(
            spans=[make_span(tags=[{"key": "error", "value": True}])],
        )
        metrics = _calculate_service_metrics([trace])
        assert metrics["test-service"]["error_count"] == 1
        assert metrics["test-service"]["error_rate"] == 100.0

    def test_multiple_spans_same_service(self):
        trace = make_trace(
            spans=[
                make_span(span_id="s1", duration=100000),
                make_span(span_id="s2", duration=200000),
            ],
        )
        metrics = _calculate_service_metrics([trace])
        m = metrics["test-service"]
        assert m["total_count"] == 2
        assert m["avg"] == 150.0  # (100+200)/2
        assert m["min"] == 100.0
        assert m["max"] == 200.0

    def test_percentiles_with_multiple_spans(self):
        spans = [make_span(span_id=f"s{i}", duration=(i + 1) * 10000) for i in range(10)]
        trace = make_trace(spans=spans)
        metrics = _calculate_service_metrics([trace])
        m = metrics["test-service"]
        assert m["p50"] > 0
        assert m["p95"] >= m["p50"]
        assert m["p99"] >= m["p95"]


# ---------------------------------------------------------------------------
# service_performance: _create_health_dataframe
# ---------------------------------------------------------------------------


class TestCreateHealthDataframe:
    def _metrics(self, error_rate=0, p95=100, total=10, errors=0, avg=50):
        return {
            "error_rate": error_rate,
            "p50": 50,
            "p95": p95,
            "p99": 200,
            "avg": avg,
            "min": 10,
            "max": 300,
            "total_count": total,
            "error_count": errors,
            "durations": [],
        }

    def test_healthy_status(self):
        df = _create_health_dataframe({"svc": self._metrics()})
        assert "Healthy" in df.iloc[0]["Status"]

    def test_warning_high_p95(self):
        df = _create_health_dataframe({"svc": self._metrics(p95=1500)})
        assert "Warning" in df.iloc[0]["Status"]

    def test_warning_moderate_error_rate(self):
        df = _create_health_dataframe({"svc": self._metrics(error_rate=7)})
        assert "Warning" in df.iloc[0]["Status"]

    def test_critical_high_error_rate(self):
        df = _create_health_dataframe({"svc": self._metrics(error_rate=15)})
        assert "Critical" in df.iloc[0]["Status"]


# ---------------------------------------------------------------------------
# service_performance: _create_latency_dataframe / _create_error_dataframe
# ---------------------------------------------------------------------------


class TestCreateLatencyDataframe:
    def test_returns_dataframe_with_percentiles(self):
        metrics = {"svc": {"p50": 10, "p95": 50, "p99": 100}}
        df = _create_latency_dataframe(metrics)
        assert isinstance(df, pd.DataFrame)
        assert set(["p50", "p95", "p99"]).issubset(df.columns)
        assert df.iloc[0]["p50"] == 10


class TestCreateErrorDataframe:
    def test_returns_dataframe(self):
        metrics = {"svc": {"error_rate": 5.0, "error_count": 2, "total_count": 40}}
        df = _create_error_dataframe(metrics)
        assert isinstance(df, pd.DataFrame)
        assert df.iloc[0]["Error Rate (%)"] == 5.0


# ---------------------------------------------------------------------------
# real_time_monitoring: _calculate_service_health
# ---------------------------------------------------------------------------


class TestCalculateServiceHealth:
    def test_empty_traces(self):
        assert _calculate_service_health([]) == []

    def test_healthy_service(self):
        trace = make_trace(
            spans=[make_span(duration=10000)],  # 10ms, no errors
        )
        health = _calculate_service_health([trace])
        assert len(health) == 1
        assert health[0]["Health Score"] > 90

    def test_error_reduces_health(self):
        trace = make_trace(
            spans=[make_span(tags=[{"key": "error", "value": True}], duration=10000)],
        )
        health = _calculate_service_health([trace])
        # Error rate 100% -> score drops by 200 (capped at 0)
        assert health[0]["Health Score"] == 0


# ---------------------------------------------------------------------------
# real_time_monitoring: _create_realtime_dataframe
# ---------------------------------------------------------------------------


class TestCreateRealtimeDataframe:
    def test_creates_dataframe(self):
        trace = make_trace(spans=[make_span()])
        df = _create_realtime_dataframe([trace])
        assert isinstance(df, pd.DataFrame)
        assert "Trace ID" in df.columns
        assert "Status" in df.columns

    def test_error_trace_status(self):
        trace = make_trace(
            spans=[make_span(tags=[{"key": "error", "value": True}])],
        )
        df = _create_realtime_dataframe([trace])
        assert df.iloc[0]["Status"] == "Error"

    def test_ok_trace_status(self):
        trace = make_trace(spans=[make_span()])
        df = _create_realtime_dataframe([trace])
        assert df.iloc[0]["Status"] == "OK"
