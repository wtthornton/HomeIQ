"""Expanded tests for JaegerClient — covers search_traces, cache TTL,
model validation edge cases, and _get_service_operations."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import httpx
import pytest
from services.jaeger_client import (
    Dependency,
    JaegerClient,
    Service,
    Trace,
    TraceSpan,
)


def _ok_response(json_data: dict, url: str = "http://test/api") -> httpx.Response:
    return httpx.Response(200, json=json_data, request=httpx.Request("GET", url))


def _error_response(status: int = 500, url: str = "http://test/api") -> httpx.Response:
    resp = httpx.Response(status, request=httpx.Request("GET", url))
    return resp


def _setup_client(client: JaegerClient, mock_get) -> None:
    client.client = AsyncMock()
    client.client.get = mock_get
    client.client.is_closed = False


@pytest.fixture
def client():
    return JaegerClient(api_url="http://test-jaeger:16686/api")


# ---------------------------------------------------------------------------
# search_traces
# ---------------------------------------------------------------------------


class TestSearchTraces:
    @pytest.mark.asyncio
    async def test_returns_traces(self, client):
        data = {
            "data": [
                {
                    "traceID": "search1",
                    "spans": [],
                    "processes": {},
                }
            ]
        }
        _setup_client(client, AsyncMock(return_value=_ok_response(data)))

        traces = await client.search_traces({"service": "svc", "limit": 10})
        assert len(traces) == 1
        assert traces[0].traceID == "search1"

    @pytest.mark.asyncio
    async def test_empty_data(self, client):
        _setup_client(client, AsyncMock(return_value=_ok_response({"data": []})))
        traces = await client.search_traces({"service": "x"})
        assert traces == []

    @pytest.mark.asyncio
    async def test_http_error_returns_empty(self, client):
        _setup_client(
            client,
            AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "500",
                    request=httpx.Request("GET", "http://x"),
                    response=httpx.Response(500),
                )
            ),
        )
        traces = await client.search_traces({"service": "svc"})
        assert traces == []

    @pytest.mark.asyncio
    async def test_unexpected_error_returns_empty(self, client):
        _setup_client(client, AsyncMock(side_effect=RuntimeError("boom")))
        traces = await client.search_traces({})
        assert traces == []

    @pytest.mark.asyncio
    async def test_skips_malformed_trace_data(self, client):
        data = {
            "data": [
                {"traceID": "good", "spans": [], "processes": {}},
                {"missing": "fields"},
            ]
        }
        _setup_client(client, AsyncMock(return_value=_ok_response(data)))
        traces = await client.search_traces({})
        assert len(traces) == 1

    @pytest.mark.asyncio
    async def test_custom_params_forwarded(self, client):
        mock_get = AsyncMock(return_value=_ok_response({"data": []}))
        _setup_client(client, mock_get)

        await client.search_traces({"service": "foo", "tags": '{"env":"prod"}'})
        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["params"]["tags"] == '{"env":"prod"}'


# ---------------------------------------------------------------------------
# Cache TTL expiry
# ---------------------------------------------------------------------------


class TestCacheTTL:
    @pytest.mark.asyncio
    async def test_cache_expires_after_ttl(self, client):
        services_data = {"data": ["svc-a"]}
        ops_data = {"data": ["op1"]}
        call_count = 0

        async def mock_get(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count in (1, 3):
                return _ok_response(services_data)
            return _ok_response(ops_data)

        _setup_client(client, mock_get)

        # First call populates cache
        await client.get_services()
        first_call_count = call_count

        # Expire the cache manually
        client._services_cache_time = datetime.now(UTC) - timedelta(minutes=10)

        # Second call should re-fetch
        await client.get_services()
        assert call_count > first_call_count

    @pytest.mark.asyncio
    async def test_force_refresh_bypasses_cache(self, client):
        services_data = {"data": ["svc-a"]}
        ops_data = {"data": ["op1"]}
        call_count = 0

        async def mock_get(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count in (1, 3):
                return _ok_response(services_data)
            return _ok_response(ops_data)

        _setup_client(client, mock_get)

        await client.get_services()
        first_call_count = call_count

        await client.get_services(force_refresh=True)
        assert call_count > first_call_count


# ---------------------------------------------------------------------------
# Pydantic model validation edge cases
# ---------------------------------------------------------------------------


class TestModelValidation:
    def test_trace_span_minimal(self):
        span = TraceSpan(
            traceID="t1",
            spanID="s1",
            operationName="op",
            startTime=0,
            duration=0,
            tags=[],
            logs=[],
            references=[],
            processID="p1",
        )
        assert span.warnings is None

    def test_trace_span_with_warnings(self):
        span = TraceSpan(
            traceID="t1",
            spanID="s1",
            operationName="op",
            startTime=0,
            duration=0,
            tags=[],
            logs=[],
            references=[],
            processID="p1",
            warnings=["clock skew"],
        )
        assert span.warnings == ["clock skew"]

    def test_trace_span_missing_required_field(self):
        with pytest.raises(Exception):
            TraceSpan(traceID="t1", spanID="s1")  # missing many fields

    def test_service_without_operations(self):
        svc = Service(name="test-svc")
        assert svc.operations is None

    def test_service_with_operations(self):
        svc = Service(name="test-svc", operations=["GET /", "POST /data"])
        assert len(svc.operations) == 2

    def test_dependency_model(self):
        dep = Dependency(parent="a", child="b", callCount=5)
        assert dep.parent == "a"
        assert dep.callCount == 5

    def test_trace_empty_spans_and_processes(self):
        trace = Trace(traceID="t1", spans=[], processes={})
        assert trace.spans == []
        assert trace.processes == {}


# ---------------------------------------------------------------------------
# _get_service_operations
# ---------------------------------------------------------------------------


class TestGetServiceOperations:
    @pytest.mark.asyncio
    async def test_returns_operations(self, client):
        _setup_client(
            client,
            AsyncMock(return_value=_ok_response({"data": ["op1", "op2"]})),
        )
        ops = await client._get_service_operations("svc")
        assert ops == ["op1", "op2"]

    @pytest.mark.asyncio
    async def test_http_error_returns_empty(self, client):
        _setup_client(
            client,
            AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "500",
                    request=httpx.Request("GET", "http://x"),
                    response=httpx.Response(500),
                )
            ),
        )
        ops = await client._get_service_operations("svc")
        assert ops == []

    @pytest.mark.asyncio
    async def test_unexpected_error_returns_empty(self, client):
        _setup_client(client, AsyncMock(side_effect=ValueError("bad")))
        ops = await client._get_service_operations("svc")
        assert ops == []
