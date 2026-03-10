"""Edge case tests: Jaeger unavailable, malformed data, empty responses."""

import sys
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from conftest import make_span, make_trace
from services.jaeger_client import JaegerClient, Trace

# Mock streamlit for page imports
_st_mock = MagicMock()
_st_mock.fragment = lambda run_every=None: (lambda f: f)
sys.modules.setdefault("streamlit", _st_mock)

from pages.service_performance import _calculate_service_metrics
from pages.trace_visualization import _create_dependency_graph, _create_timeline_chart


def _setup_client(client: JaegerClient, mock_get) -> None:
    client.client = AsyncMock()
    client.client.get = mock_get
    client.client.is_closed = False


@pytest.fixture
def client():
    return JaegerClient(api_url="http://unreachable:16686/api")


# ---------------------------------------------------------------------------
# Jaeger unavailable scenarios
# ---------------------------------------------------------------------------


class TestJaegerUnavailable:
    @pytest.mark.asyncio
    async def test_get_traces_connection_error(self, client):
        _setup_client(client, AsyncMock(side_effect=httpx.ConnectError("refused")))
        traces = await client.get_traces()
        assert traces == []

    @pytest.mark.asyncio
    async def test_get_trace_connection_error(self, client):
        _setup_client(client, AsyncMock(side_effect=httpx.ConnectError("refused")))
        trace = await client.get_trace("abc")
        assert trace is None

    @pytest.mark.asyncio
    async def test_get_services_connection_error(self, client):
        _setup_client(client, AsyncMock(side_effect=httpx.ConnectError("refused")))
        services = await client.get_services()
        assert services == []

    @pytest.mark.asyncio
    async def test_get_dependencies_connection_error(self, client):
        from datetime import UTC, datetime, timedelta

        _setup_client(client, AsyncMock(side_effect=httpx.ConnectError("refused")))
        now = datetime.now(UTC)
        deps = await client.get_dependencies(now - timedelta(hours=1), now)
        assert deps == []

    @pytest.mark.asyncio
    async def test_search_traces_connection_error(self, client):
        _setup_client(client, AsyncMock(side_effect=httpx.ConnectError("refused")))
        traces = await client.search_traces({"service": "x"})
        assert traces == []


# ---------------------------------------------------------------------------
# Malformed trace data handling
# ---------------------------------------------------------------------------


class TestMalformedData:
    @pytest.mark.asyncio
    async def test_get_traces_missing_data_key(self, client):
        resp = httpx.Response(200, json={}, request=httpx.Request("GET", "http://x"))
        _setup_client(client, AsyncMock(return_value=resp))
        traces = await client.get_traces()
        assert traces == []

    @pytest.mark.asyncio
    async def test_get_trace_missing_data_key(self, client):
        resp = httpx.Response(200, json={}, request=httpx.Request("GET", "http://x"))
        _setup_client(client, AsyncMock(return_value=resp))
        trace = await client.get_trace("abc")
        assert trace is None

    @pytest.mark.asyncio
    async def test_dependency_malformed_entry_skipped(self, client):
        from datetime import UTC, datetime, timedelta

        data = {
            "data": [
                {"parent": "a", "child": "b", "callCount": 1},
                {"bad": "entry"},  # missing required fields
            ]
        }
        resp = httpx.Response(200, json=data, request=httpx.Request("GET", "http://x"))
        _setup_client(client, AsyncMock(return_value=resp))
        now = datetime.now(UTC)
        deps = await client.get_dependencies(now - timedelta(hours=1), now)
        assert len(deps) == 1
        assert deps[0].parent == "a"

    def test_timeline_chart_with_unknown_process(self):
        """Span references a processID not in processes dict."""
        trace = make_trace(
            spans=[make_span(process_id="missing_p")],
            processes={},  # no matching process
        )
        fig = _create_timeline_chart([trace])
        # Should still render with "unknown" service name
        assert len(fig.data) >= 1
        assert fig.data[0].name == "unknown"

    def test_dependency_graph_non_child_of_ref_ignored(self):
        """References with refType != CHILD_OF should be ignored."""
        parent = make_span(span_id="p1", process_id="p1")
        child = make_span(
            span_id="c1",
            process_id="p2",
            references=[{"refType": "FOLLOWS_FROM", "spanID": "p1"}],
        )
        trace = make_trace(
            spans=[parent, child],
            processes={"p1": {"serviceName": "a"}, "p2": {"serviceName": "b"}},
        )
        fig = _create_dependency_graph([trace])
        # FOLLOWS_FROM is not CHILD_OF, so no dependency should be found
        assert any("No dependency data" in a.text for a in fig.layout.annotations)

    def test_service_metrics_unknown_process(self):
        """Span with processID not in processes should map to 'unknown'."""
        trace = make_trace(
            spans=[make_span(process_id="missing")],
            processes={},
        )
        metrics = _calculate_service_metrics([trace])
        assert "unknown" in metrics


# ---------------------------------------------------------------------------
# Empty response handling
# ---------------------------------------------------------------------------


class TestEmptyResponses:
    @pytest.mark.asyncio
    async def test_get_traces_empty_data_array(self, client):
        resp = httpx.Response(
            200, json={"data": []}, request=httpx.Request("GET", "http://x")
        )
        _setup_client(client, AsyncMock(return_value=resp))
        traces = await client.get_traces()
        assert traces == []

    @pytest.mark.asyncio
    async def test_get_services_empty_list(self, client):
        resp = httpx.Response(
            200, json={"data": []}, request=httpx.Request("GET", "http://x")
        )
        _setup_client(client, AsyncMock(return_value=resp))
        services = await client.get_services()
        assert services == []

    def test_timeline_chart_empty_spans_in_trace(self):
        trace = make_trace(spans=[])
        fig = _create_timeline_chart([trace])
        assert any("No trace data" in a.text for a in fig.layout.annotations)

    def test_service_metrics_empty_traces(self):
        assert _calculate_service_metrics([]) == {}
