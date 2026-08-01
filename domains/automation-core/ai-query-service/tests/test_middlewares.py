"""Tests for AuthenticationMiddleware.

Focused on the source-IP bypass that used to let any peer with a private
address skip API-key validation entirely.
"""

from types import SimpleNamespace

import pytest
from src.api.middlewares import AuthenticationMiddleware
from src.config import settings


def _request(path="/api/v1/query", host="10.0.0.5", headers=None):
    """Minimal stand-in for starlette Request as the middleware uses it."""
    return SimpleNamespace(
        url=SimpleNamespace(path=path),
        client=SimpleNamespace(host=host),
        headers=headers or {},
        state=SimpleNamespace(),
    )


async def _call_next(_request):
    return "downstream"


@pytest.fixture
def middleware():
    return AuthenticationMiddleware(app=None)


class TestPrivateNetworkBypassRemoved:
    """Regression: private source IPs must not authenticate on their own."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "host",
        ["172.17.0.4", "10.0.0.5", "192.168.1.20", "127.0.0.1", "::1"],
    )
    async def test_private_ip_without_key_is_rejected(self, middleware, host):
        """A private-looking peer address grants nothing without an API key.

        request.client.host is the *immediate* peer, so behind a NAT gateway or
        sidecar this address is attacker-influenced. Treating it as proof of
        internal origin bypassed auth for the whole query API.
        """
        response = await middleware.dispatch(_request(host=host), _call_next)

        assert response.status_code == 401

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_internal_bypass_hook_remains(self, middleware):
        """The bypass helper and its prefix list must stay gone."""
        assert not hasattr(middleware, "_is_internal_request")
        assert not hasattr(middleware, "INTERNAL_NETWORK_PREFIXES")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_valid_api_key_from_private_ip_is_allowed(self, middleware, monkeypatch):
        """Internal callers still work -- they just have to present a key."""
        monkeypatch.setattr(settings, "api_keys", {"good-key"})

        request = _request(headers={"X-HomeIQ-API-Key": "good-key"})
        result = await middleware.dispatch(request, _call_next)

        assert result == "downstream"
        assert request.state.authenticated is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_path_still_exempt(self, middleware):
        """Health and docs remain unauthenticated so probes keep working."""
        result = await middleware.dispatch(_request(path="/health"), _call_next)

        assert result == "downstream"
