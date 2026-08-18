"""Fixtures for the HomeIQ custom integration tests."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)
from yarl import URL

from custom_components.homeiq.const import (
    CONF_AGENTFORGE_API_KEY,
    CONF_AGENTFORGE_URL,
    CONF_MCP_TOKEN,
    CONF_MCP_URL,
    DOMAIN,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from homeassistant.core import HomeAssistant

MCP_URL = "http://homeiq-mcp:8050"
MCP_ENDPOINT = f"{MCP_URL}/mcp"
AGENTFORGE_URL = "http://agentforge:8010"
AGENTFORGE_ENDPOINT = f"{AGENTFORGE_URL}/projects/homeiq/tasks/invoke"

ENTRY_DATA = {
    CONF_MCP_URL: MCP_URL,
    CONF_MCP_TOKEN: "read-token",
    CONF_AGENTFORGE_URL: AGENTFORGE_URL,
    CONF_AGENTFORGE_API_KEY: "afp_test",
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Load ``custom_components`` in every test in this package."""
    yield


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a HomeIQ config entry."""
    return MockConfigEntry(domain=DOMAIN, title="HomeIQ", data=ENTRY_DATA, options={})


@pytest.fixture
async def homeassistant_component(hass: HomeAssistant) -> None:
    """Set up the core integration the conversation component depends on."""
    assert await async_setup_component(hass, "homeassistant", {})


async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Add and set up a HomeIQ config entry."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def jsonrpc_result(result: dict[str, Any], request_id: int = 1) -> dict[str, Any]:
    """Wrap a result in a JSON-RPC envelope."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def call_result(payload: dict[str, Any]) -> dict[str, Any]:
    """Build a CallToolResult the way the HomeIQ MCP server does."""
    return {
        "content": [{"type": "text", "text": json.dumps(payload, separators=(",", ":"))}],
        "structuredContent": payload,
    }


HANDSHAKE = {"initialize": {"serverInfo": {"name": "homeiq", "version": "0.1.0"}}}


def serve_mcp(mocker: AiohttpClientMocker, results: dict[str, dict[str, Any]]) -> None:
    """Serve a fake MCP endpoint that dispatches on the JSON-RPC method."""

    async def handler(_method: str, _url: URL, data: dict[str, Any]) -> Any:
        rpc = data["method"]
        if rpc == "notifications/initialized":
            return AiohttpClientMockResponse("post", URL(MCP_ENDPOINT), status=202, text="")
        return AiohttpClientMockResponse(
            "post", URL(MCP_ENDPOINT), json=jsonrpc_result(results[rpc], data.get("id", 1))
        )

    mocker.post(MCP_ENDPOINT, side_effect=handler)


def task_response(**overrides: Any) -> dict[str, Any]:
    """Build an AgentForge TaskResponse body."""
    return {
        "result": "The kitchen light was on for 4 hours.",
        "agent_used": "homeiq-analyst",
        "is_error": False,
    } | overrides
