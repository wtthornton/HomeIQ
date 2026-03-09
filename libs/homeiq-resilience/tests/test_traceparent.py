"""Tests for OpenTelemetry trace-context propagation in CrossGroupClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from homeiq_resilience.cross_group_client import CrossGroupClient


@pytest.fixture
def client():
    return CrossGroupClient(
        base_url="http://data-api:8006",
        group_name="core-platform",
        timeout=5.0,
        max_retries=1,
    )


# ------------------------------------------------------------------
# OTel available
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_traceparent_injected_when_otel_available(client):
    """When OpenTelemetry is installed, traceparent header is injected."""
    mock_inject = MagicMock()
    mock_span = MagicMock()
    mock_span.is_recording.return_value = True

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200

    with (
        patch("homeiq_resilience.cross_group_client._OTEL_AVAILABLE", True),
        patch("homeiq_resilience.cross_group_client.otel_inject", mock_inject),
        patch("homeiq_resilience.cross_group_client.trace") as mock_trace,
        patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=mock_response),
    ):
        mock_trace.get_current_span.return_value = mock_span

        await client.call("GET", "/api/entities")

        # otel_inject was called with the headers dict
        mock_inject.assert_called_once()
        headers_arg = mock_inject.call_args[0][0]
        assert isinstance(headers_arg, dict)

        # span attribute was set
        mock_span.set_attribute.assert_called_once_with(
            "homeiq.target_group", "core-platform"
        )


@pytest.mark.asyncio
async def test_traceparent_sets_group_attribute(client):
    """The homeiq.target_group span attribute matches the client group_name."""
    mock_span = MagicMock()
    mock_span.is_recording.return_value = True

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200

    with (
        patch("homeiq_resilience.cross_group_client._OTEL_AVAILABLE", True),
        patch("homeiq_resilience.cross_group_client.otel_inject", MagicMock()),
        patch("homeiq_resilience.cross_group_client.trace") as mock_trace,
        patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=mock_response),
    ):
        mock_trace.get_current_span.return_value = mock_span

        await client.call("GET", "/health")

        mock_span.set_attribute.assert_called_with(
            "homeiq.target_group", "core-platform"
        )


# ------------------------------------------------------------------
# OTel not available
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_error_when_otel_unavailable(client):
    """When OpenTelemetry is NOT installed, no error is raised."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200

    with (
        patch("homeiq_resilience.cross_group_client._OTEL_AVAILABLE", False),
        patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=mock_response),
    ):
        response = await client.call("GET", "/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_no_traceparent_when_otel_unavailable(client):
    """When OTel unavailable, no traceparent header is injected."""
    captured_headers = {}

    async def capture_request(self, _method, _url, *, headers=None, **_kwargs):  # noqa: ARG001
        captured_headers.update(headers or {})
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        return mock_resp

    with (
        patch("homeiq_resilience.cross_group_client._OTEL_AVAILABLE", False),
        patch("httpx.AsyncClient.request", capture_request),
    ):
        await client.call("GET", "/health")
        assert "traceparent" not in captured_headers


# ------------------------------------------------------------------
# Auth header preserved alongside OTel headers
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auth_header_preserved_with_otel():
    """Bearer auth and OTel headers coexist without conflicts."""
    authed_client = CrossGroupClient(
        base_url="http://data-api:8006",
        group_name="core-platform",
        auth_token="test-token-123",
        max_retries=1,
    )

    captured_headers = {}

    async def capture_request(self, _method, _url, *, headers=None, **_kwargs):  # noqa: ARG001
        captured_headers.update(headers or {})
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        return mock_resp

    def fake_inject(carrier):
        carrier["traceparent"] = "00-abc-def-01"

    with (
        patch("homeiq_resilience.cross_group_client._OTEL_AVAILABLE", True),
        patch("homeiq_resilience.cross_group_client.otel_inject", fake_inject),
        patch("homeiq_resilience.cross_group_client.trace") as mock_trace,
        patch("httpx.AsyncClient.request", capture_request),
    ):
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_trace.get_current_span.return_value = mock_span

        await authed_client.call("GET", "/api/entities")

        assert captured_headers["Authorization"] == "Bearer test-token-123"
        assert captured_headers["traceparent"] == "00-abc-def-01"
