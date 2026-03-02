"""Tests for JaegerClient with mocked HTTP responses."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import httpx
import pytest

from services.jaeger_client import JaegerClient


def _ok_response(json_data: dict) -> httpx.Response:
    """Create a 200 httpx.Response with a request so raise_for_status works."""
    return httpx.Response(
        200,
        json=json_data,
        request=httpx.Request("GET", "http://test-jaeger:16686/api/traces"),
    )


@pytest.fixture
def client():
    return JaegerClient(api_url="http://test-jaeger:16686/api")


@pytest.fixture
def mock_traces_data():
    return {
        "data": [
            {
                "traceID": "abc123",
                "spans": [
                    {
                        "traceID": "abc123",
                        "spanID": "span1",
                        "operationName": "GET /health",
                        "startTime": 1000000,
                        "duration": 50000,
                        "tags": [],
                        "logs": [],
                        "references": [],
                        "processID": "p1",
                    }
                ],
                "processes": {"p1": {"serviceName": "test-service"}},
            }
        ]
    }


@pytest.fixture
def mock_services_data():
    return {"data": ["service-a", "service-b"]}


@pytest.fixture
def mock_operations_data():
    return {"data": ["GET /health", "POST /data"]}


def _setup_client(client, mock_get):
    """Replace client's httpx client with a mock."""
    client.client = AsyncMock()
    client.client.get = mock_get
    client.client.is_closed = False


class TestGetTraces:
    @pytest.mark.asyncio
    async def test_returns_traces(self, client, mock_traces_data):
        _setup_client(client, AsyncMock(return_value=_ok_response(mock_traces_data)))

        traces = await client.get_traces(service="test-service")

        assert len(traces) == 1
        assert traces[0].traceID == "abc123"
        assert traces[0].spans[0].operationName == "GET /health"

    @pytest.mark.asyncio
    async def test_returns_empty_on_http_error(self, client):
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

        traces = await client.get_traces()
        assert traces == []

    @pytest.mark.asyncio
    async def test_default_time_range(self, client, mock_traces_data):
        mock_get = AsyncMock(return_value=_ok_response(mock_traces_data))
        _setup_client(client, mock_get)

        await client.get_traces()

        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs.get("params", {})
        assert "start" in params
        assert "end" in params

    @pytest.mark.asyncio
    async def test_skips_malformed_traces(self, client):
        response_data = {
            "data": [
                {"traceID": "good", "spans": [], "processes": {}},
                {"bad": "data"},  # malformed
            ]
        }
        _setup_client(client, AsyncMock(return_value=_ok_response(response_data)))

        traces = await client.get_traces()
        assert len(traces) == 1
        assert traces[0].traceID == "good"


class TestGetTrace:
    @pytest.mark.asyncio
    async def test_get_single_trace(self, client, mock_traces_data):
        _setup_client(client, AsyncMock(return_value=_ok_response(mock_traces_data)))

        trace = await client.get_trace("abc123")
        assert trace is not None
        assert trace.traceID == "abc123"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, client):
        _setup_client(client, AsyncMock(return_value=_ok_response({"data": []})))

        trace = await client.get_trace("nonexistent")
        assert trace is None


class TestGetServices:
    @pytest.mark.asyncio
    async def test_returns_services(self, client, mock_services_data, mock_operations_data):
        responses = [
            _ok_response(mock_services_data),
            _ok_response(mock_operations_data),
            _ok_response(mock_operations_data),
        ]
        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            resp = responses[min(call_count, len(responses) - 1)]
            call_count += 1
            return resp

        _setup_client(client, mock_get)

        services = await client.get_services()
        assert len(services) == 2
        assert services[0].name == "service-a"
        assert services[0].operations == ["GET /health", "POST /data"]

    @pytest.mark.asyncio
    async def test_cache_hit(self, client, mock_services_data, mock_operations_data):
        responses = [
            _ok_response(mock_services_data),
            _ok_response(mock_operations_data),
            _ok_response(mock_operations_data),
        ]
        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            resp = responses[min(call_count, len(responses) - 1)]
            call_count += 1
            return resp

        _setup_client(client, mock_get)

        # First call populates cache
        services1 = await client.get_services()
        # Second call should use cache (no additional HTTP calls)
        services2 = await client.get_services()

        assert services1 == services2
        assert call_count == 3  # Only the 3 calls from the first request


class TestGetDependencies:
    @pytest.mark.asyncio
    async def test_returns_dependencies(self, client):
        mock_data = {
            "data": [
                {"parent": "service-a", "child": "service-b", "callCount": 42}
            ]
        }
        _setup_client(client, AsyncMock(return_value=_ok_response(mock_data)))

        now = datetime.utcnow()
        deps = await client.get_dependencies(
            start_time=now - timedelta(hours=1),
            end_time=now,
        )
        assert len(deps) == 1
        assert deps[0].parent == "service-a"
        assert deps[0].child == "service-b"
        assert deps[0].callCount == 42


class TestClose:
    @pytest.mark.asyncio
    async def test_close(self, client):
        client.client = AsyncMock()
        client.client.is_closed = False
        client.client.aclose = AsyncMock()

        await client.close()
        client.client.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_already_closed(self, client):
        client.client = AsyncMock()
        client.client.is_closed = True
        client.client.aclose = AsyncMock()

        await client.close()
        client.client.aclose.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        async with JaegerClient(api_url="http://test:16686/api") as c:
            assert c.api_url == "http://test:16686/api"
        assert c.client.is_closed
