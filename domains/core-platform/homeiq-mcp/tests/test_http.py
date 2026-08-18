"""HTTP surface: /health, bearer auth on /mcp, and a JSON-RPC round trip."""

from __future__ import annotations

import httpx
import respx
from starlette.testclient import TestClient

from tests.conftest import READ_TOKEN, WRITE_TOKEN

INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "pytest", "version": "0"},
    },
}
MCP_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


def _client(app):
    # No redirect following: a 307 from /mcp would hide a mount/route mistake from real clients.
    return TestClient(
        app.build_http_app(), base_url="http://homeiq-mcp:8050", follow_redirects=False
    )


def _bearer(token: str) -> dict[str, str]:
    return {**MCP_HEADERS, "Authorization": f"Bearer {token}"}


@respx.mock
def test_health_reports_backings_and_tools(app, registry):
    respx.get("http://data-api.test:8006/health").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )
    respx.get("http://patterns.test:8020/health").mock(side_effect=httpx.ConnectError("down"))
    respx.get("http://devint.test:8028/health").mock(return_value=httpx.Response(503))

    with _client(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "homeiq-mcp"
    assert body["catalogue_version"] == registry.catalogue.version
    by_name = {b["name"]: b for b in body["backings"]}
    assert by_name["data-api"]["ok"] is True
    assert (
        by_name["ai-pattern-service"]["ok"] is False
        and by_name["ai-pattern-service"]["detail"] == "ConnectError"
    )
    assert by_name["device-intelligence-service"]["ok"] is False
    assert "get_entity_state" in body["tools_pending"]
    assert "get_energy_correlations" not in body["tools_pending"]


@respx.mock
def test_health_is_503_when_data_api_down(app):
    respx.get("http://data-api.test:8006/health").mock(side_effect=httpx.ConnectError("down"))
    respx.get("http://patterns.test:8020/health").mock(return_value=httpx.Response(200))
    respx.get("http://devint.test:8028/health").mock(return_value=httpx.Response(200))
    with _client(app) as client:
        response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"


def test_mcp_requires_bearer(app):
    with _client(app) as client:
        assert client.post("/mcp", json=INIT, headers=MCP_HEADERS).status_code == 401
        assert (
            client.post(
                "/mcp", json=INIT, headers={**MCP_HEADERS, "Authorization": "Bearer wrong"}
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/mcp", json=INIT, headers={**MCP_HEADERS, "Authorization": "Basic abc"}
            ).status_code
            == 401
        )
        assert client.get("/health").status_code in (200, 503)


def test_health_needs_no_token(app):
    with _client(app) as client:
        assert client.get("/health").status_code in (200, 503)


def _initialize_and_list(client, token):
    init = client.post("/mcp", json=INIT, headers=_bearer(token))
    assert init.status_code == 200, init.text
    assert init.json()["result"]["serverInfo"]["name"] == "homeiq"
    client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        headers=_bearer(token),
    )
    listed = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        headers=_bearer(token),
    )
    assert listed.status_code == 200, listed.text
    return listed.json()["result"]["tools"]


def test_json_rpc_round_trip_lists_registered_tools(app, registry, catalogue):
    @registry.register("get_entity_state")
    async def _handler(args):
        return {
            "entity_id": args["entity_id"],
            "state": "on",
            "t": None,
            "source": "last_observed_event",
        }

    with _client(app) as client:
        tools = _initialize_and_list(client, READ_TOKEN)
        assert [t["name"] for t in tools] == ["get_entity_state"]
        assert tools[0]["inputSchema"] == catalogue.tools["get_entity_state"].input_schema
        assert tools[0]["annotations"]["readOnlyHint"] is True

        call = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "get_entity_state", "arguments": {"entity_id": "light.office"}},
            },
            headers=_bearer(READ_TOKEN),
        )
        assert call.status_code == 200, call.text
        result = call.json()["result"]
        assert result.get("isError") is not True
        assert result["structuredContent"]["state"] == "on"

        bad = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "get_entity_state", "arguments": {"hours": 1}},
            },
            headers=_bearer(READ_TOKEN),
        )
        result = bad.json()["result"]
        assert result["isError"] is True
        assert result["structuredContent"]["error"]["code"] == "invalid_input"


def test_write_token_also_reads(app, registry):
    @registry.register("list_areas")
    async def _handler(args):
        return {"areas": [], "count": 0, "truncated": False}

    with _client(app) as client:
        tools = _initialize_and_list(client, WRITE_TOKEN)
        assert [t["name"] for t in tools] == ["list_areas"]


def test_dns_rebinding_host_is_rejected(app):
    with TestClient(
        app.build_http_app(), base_url="http://evil.example", follow_redirects=False
    ) as client:
        response = client.post("/mcp", json=INIT, headers=_bearer(READ_TOKEN))
    assert response.status_code == 421


def test_mcp_path_is_exact_and_never_redirects(app):
    with _client(app) as client:
        assert client.post("/mcp", json=INIT, headers=MCP_HEADERS).status_code == 401
        assert client.post("/mcp/", json=INIT, headers=MCP_HEADERS).status_code == 404
