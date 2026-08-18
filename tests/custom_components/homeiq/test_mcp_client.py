"""Tests for the HomeIQ MCP JSON-RPC client (TAP-5308)."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

import pytest
from aiohttp import ClientError, ClientSession
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.homeiq.mcp_client import (
    HomeIQMcpClient,
    McpError,
    McpUnauthorizedError,
    enforce_budget,
    payload_size,
)

from .conftest import HANDSHAKE, MCP_ENDPOINT, MCP_URL, call_result, serve_mcp

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable


@pytest.fixture
def mocker() -> AiohttpClientMocker:
    """Return an aiohttp request mocker."""
    return AiohttpClientMocker()


@pytest.fixture
async def session(mocker: AiohttpClientMocker) -> AsyncGenerator[ClientSession]:
    """Return a session bound to the mocker."""
    client_session = mocker.create_session(asyncio.get_running_loop())
    yield client_session
    await client_session.close()


@pytest.fixture
def client(session: ClientSession) -> HomeIQMcpClient:
    """Return a client pointed at the mocked server."""
    return HomeIQMcpClient(session, MCP_URL, "read-token", 5)


def rpc_methods(mocker: AiohttpClientMocker) -> list[str]:
    """Return the JSON-RPC methods sent, in order."""
    return [body["method"] for _method, _url, body, _headers in mocker.mock_calls]


async def test_handshake_runs_once_before_the_first_call(
    client: HomeIQMcpClient, mocker: AiohttpClientMocker
) -> None:
    """initialize and notifications/initialized precede tools/call, once."""
    serve_mcp(mocker, HANDSHAKE | {"tools/call": call_result({"areas": []})})

    await client.async_call_tool("list_areas", {}, 8192)
    await client.async_call_tool("list_areas", {}, 8192)

    assert rpc_methods(mocker) == [
        "initialize",
        "notifications/initialized",
        "tools/call",
        "tools/call",
    ]


async def test_bearer_and_accept_headers_are_sent(
    client: HomeIQMcpClient, mocker: AiohttpClientMocker
) -> None:
    """The server requires a bearer token and both accepted encodings."""
    serve_mcp(mocker, HANDSHAKE | {"tools/call": call_result({"areas": []})})

    await client.async_call_tool("list_areas", {}, 8192)

    headers = mocker.mock_calls[0][3]
    assert headers["Authorization"] == "Bearer read-token"
    assert headers["Accept"] == "application/json, text/event-stream"


async def test_tool_arguments_are_sent_verbatim(
    client: HomeIQMcpClient, mocker: AiohttpClientMocker
) -> None:
    """tools/call carries the tool name and validated arguments."""
    serve_mcp(mocker, HANDSHAKE | {"tools/call": call_result({"points": []})})

    await client.async_call_tool("get_entity_history", {"entity_id": "sensor.x"}, 8192)

    assert mocker.mock_calls[-1][2]["params"] == {
        "name": "get_entity_history",
        "arguments": {"entity_id": "sensor.x"},
    }


async def test_structured_content_is_preferred(
    client: HomeIQMcpClient, mocker: AiohttpClientMocker
) -> None:
    """The payload comes back from structuredContent."""
    serve_mcp(mocker, HANDSHAKE | {"tools/call": call_result({"areas": ["kitchen"]})})

    assert await client.async_call_tool("list_areas", {}, 8192) == {"areas": ["kitchen"]}


async def test_text_block_is_the_fallback(
    client: HomeIQMcpClient, mocker: AiohttpClientMocker
) -> None:
    """A result without structuredContent is read from the text block."""
    payload = {"areas": ["hall"]}
    serve_mcp(
        mocker,
        HANDSHAKE | {"tools/call": {"content": [{"type": "text", "text": json.dumps(payload)}]}},
    )

    assert await client.async_call_tool("list_areas", {}, 8192) == payload


async def test_tool_error_becomes_an_mcp_error(
    client: HomeIQMcpClient, mocker: AiohttpClientMocker
) -> None:
    """isError with the server's error payload raises with its code."""
    serve_mcp(
        mocker,
        HANDSHAKE
        | {
            "tools/call": {
                "content": [{"type": "text", "text": "invalid_input: entity_id: required"}],
                "structuredContent": {
                    "error": {
                        "code": "invalid_input",
                        "message": "entity_id: required",
                        "tool": "get_entity_state",
                    }
                },
                "isError": True,
            }
        },
    )

    with pytest.raises(McpError) as err:
        await client.async_call_tool("get_entity_state", {}, 4096)

    assert err.value.code == "invalid_input"
    assert err.value.message == "entity_id: required"


async def test_unreadable_payload_is_a_contract_violation(
    client: HomeIQMcpClient, mocker: AiohttpClientMocker
) -> None:
    """A result with neither structured content nor JSON text is refused."""
    serve_mcp(mocker, HANDSHAKE | {"tools/call": {"content": [{"type": "text", "text": "oops"}]}})

    with pytest.raises(McpError) as err:
        await client.async_call_tool("list_areas", {}, 4096)

    assert err.value.code == "contract_violation"


async def test_unauthorized_is_distinct(
    client: HomeIQMcpClient, mocker: AiohttpClientMocker
) -> None:
    """A rejected bearer token raises McpUnauthorizedError, not a generic error."""
    mocker.post(MCP_ENDPOINT, status=401, json={"error": "invalid_token"})

    with pytest.raises(McpUnauthorizedError):
        await client.async_list_tools()


async def test_unreachable_server_is_distinct(
    client: HomeIQMcpClient, mocker: AiohttpClientMocker
) -> None:
    """A connection failure raises the transport-level code."""
    mocker.post(MCP_ENDPOINT, exc=ClientError("connection refused"))

    with pytest.raises(McpError) as err:
        await client.async_list_tools()

    assert err.value.code == "unreachable"


async def test_jsonrpc_error_is_surfaced(
    client: HomeIQMcpClient, mocker: AiohttpClientMocker
) -> None:
    """A JSON-RPC error envelope raises rather than returning nothing."""
    mocker.post(
        MCP_ENDPOINT,
        json={"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "nope"}},
    )

    with pytest.raises(McpError) as err:
        await client.async_list_tools()

    assert err.value.message == "nope"


async def test_list_tools_returns_the_server_list(
    client: HomeIQMcpClient, mocker: AiohttpClientMocker
) -> None:
    """tools/list is read from the result."""
    serve_mcp(mocker, HANDSHAKE | {"tools/list": {"tools": [{"name": "list_areas"}]}})

    assert await client.async_list_tools() == [{"name": "list_areas"}]


async def test_oversized_response_is_truncated(
    client: HomeIQMcpClient, mocker: AiohttpClientMocker
) -> None:
    """An over-budget payload is shrunk before it reaches the model."""
    payload = {"rows": [{"entity_id": f"sensor.s{index}"} for index in range(400)], "count": 400}
    serve_mcp(mocker, HANDSHAKE | {"tools/call": call_result(payload)})

    result = await client.async_call_tool("list_entities", {}, 2048)

    assert result["truncated"] is True
    assert result["hint"] == "limit"
    assert payload_size(result) <= 2048


def test_budget_leaves_a_small_payload_alone() -> None:
    """Under budget, nothing is changed and no flags are added."""
    assert enforce_budget({"rows": [1, 2, 3], "count": 3}, 8192, "limit") == {
        "rows": [1, 2, 3],
        "count": 3,
    }


def test_budget_recounts_and_flags() -> None:
    """Truncation updates count and records the parameter to narrow."""
    result = enforce_budget({"rows": list(range(500)), "count": 500}, 256, "limit")

    assert result["truncated"] is True
    assert result["hint"] == "limit"
    assert result["count"] == len(result["rows"])
    assert payload_size(result) <= 256


def test_budget_gives_up_when_nothing_is_left_to_drop() -> None:
    """A payload with no list rows terminates instead of looping."""
    payload = {"note": "x" * 500}

    assert enforce_budget(payload, 32, "limit") == payload


def test_budget_shrinks_the_largest_list_first() -> None:
    """The list with the most rows is the one that loses rows."""
    payload = {"rows": list(range(400)), "notes": ["kept"]}

    result = enforce_budget(payload, 256, "hours")

    assert result["notes"] == ["kept"]
    assert result["hint"] == "hours"
    assert len(result["rows"]) < 400


def test_payload_size_measures_the_wire_form() -> None:
    """Size is the compact UTF-8 serialisation, matching the server."""
    assert payload_size({"a": 1}) == len(b'{"a":1}')


@pytest.mark.parametrize("factory", [lambda: {"rows": []}, dict])
def test_budget_handles_empty_payloads(factory: Callable[[], dict[str, Any]]) -> None:
    """An empty payload is already within any budget."""
    payload = factory()

    assert enforce_budget(payload, 16, "limit") == payload
