"""Tests for the HomeIQ config and options flows (TAP-5305)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from aiohttp import ClientError
from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from custom_components.homeiq.const import (
    CONF_AGENTFORGE_PROJECT,
    CONF_EXPOSED_TOOLS,
    CONF_MCP_TOKEN,
    DOMAIN,
)

from .conftest import (
    AGENTFORGE_ENDPOINT,
    ENTRY_DATA,
    HANDSHAKE,
    MCP_ENDPOINT,
    serve_mcp,
    setup_entry,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

TOOLS_LIST = {"tools/list": {"tools": [{"name": "list_areas"}]}}
MATCH_ONLY_OK = {"agent": "homeiq-analyst", "confidence": 0.9}


async def start_user_flow(hass: HomeAssistant) -> dict:
    """Submit the user step with the standard entry data."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    return await hass.config_entries.flow.async_configure(result["flow_id"], dict(ENTRY_DATA))


async def test_user_flow_creates_the_entry(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    homeassistant_component: None,
) -> None:
    """Both endpoints answer, so the entry is created."""
    serve_mcp(aioclient_mock, HANDSHAKE | TOOLS_LIST)
    aioclient_mock.post(AGENTFORGE_ENDPOINT, json=MATCH_ONLY_OK)

    result = await start_user_flow(hass)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "HomeIQ"
    assert result["data"] == ENTRY_DATA


async def test_mcp_unreachable_is_reported(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    homeassistant_component: None,
) -> None:
    """An MCP server that does not answer is named as unreachable."""
    aioclient_mock.post(MCP_ENDPOINT, exc=ClientError("connection refused"))

    result = await start_user_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "mcp_cannot_connect"}


async def test_mcp_unauthorized_is_reported(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    homeassistant_component: None,
) -> None:
    """A rejected MCP token is distinguished from an unreachable server."""
    aioclient_mock.post(MCP_ENDPOINT, status=401, json={"error": "invalid_token"})

    result = await start_user_flow(hass)

    assert result["errors"] == {"base": "mcp_invalid_auth"}


async def test_agentforge_unreachable_is_reported(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    homeassistant_component: None,
) -> None:
    """A healthy MCP server but an absent AgentForge is named separately."""
    serve_mcp(aioclient_mock, HANDSHAKE | TOOLS_LIST)
    aioclient_mock.post(AGENTFORGE_ENDPOINT, exc=ClientError("no route"))

    result = await start_user_flow(hass)

    assert result["errors"] == {"base": "agentforge_cannot_connect"}


async def test_agentforge_unauthorized_is_reported(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    homeassistant_component: None,
) -> None:
    """A rejected AgentForge key is its own error."""
    serve_mcp(aioclient_mock, HANDSHAKE | TOOLS_LIST)
    aioclient_mock.post(AGENTFORGE_ENDPOINT, status=401, json={"detail": "key-invalid-or-revoked"})

    result = await start_user_flow(hass)

    assert result["errors"] == {"base": "agentforge_invalid_auth"}


async def test_the_form_can_be_corrected_and_resubmitted(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    homeassistant_component: None,
) -> None:
    """After an error the user can fix the token and succeed."""
    aioclient_mock.post(MCP_ENDPOINT, status=401, json={"error": "invalid_token"})
    failed = await start_user_flow(hass)
    aioclient_mock.clear_requests()

    serve_mcp(aioclient_mock, HANDSHAKE | TOOLS_LIST)
    aioclient_mock.post(AGENTFORGE_ENDPOINT, json=MATCH_ONLY_OK)
    result = await hass.config_entries.flow.async_configure(
        failed["flow_id"], ENTRY_DATA | {CONF_MCP_TOKEN: "better-token"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_MCP_TOKEN] == "better-token"


async def test_only_one_entry_is_allowed(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    homeassistant_component: None,
) -> None:
    """The manifest declares a single config entry."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_reconfigure_updates_the_endpoints(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    homeassistant_component: None,
) -> None:
    """Reconfiguring validates the new endpoints before storing them."""
    await setup_entry(hass, config_entry)
    serve_mcp(aioclient_mock, HANDSHAKE | TOOLS_LIST)
    aioclient_mock.post(AGENTFORGE_ENDPOINT, json=MATCH_ONLY_OK)

    result = await config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], ENTRY_DATA | {CONF_MCP_TOKEN: "rotated"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert config_entry.data[CONF_MCP_TOKEN] == "rotated"


async def test_options_flow_stores_project_and_exposure(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    homeassistant_component: None,
) -> None:
    """The options flow offers the catalogue tools and stores the choice."""
    await setup_entry(hass, config_entry)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_AGENTFORGE_PROJECT: "homeiq", CONF_EXPOSED_TOOLS: ["list_areas"]},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_EXPOSED_TOOLS] == ["list_areas"]


@pytest.mark.parametrize("tool", ["get_energy_correlations", "get_device_energy_impact"])
async def test_options_flow_never_offers_deferred_tools(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    homeassistant_component: None,
    tool: str,
) -> None:
    """Deferred catalogue entries are not selectable."""
    await setup_entry(hass, config_entry)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    selector = result["data_schema"].schema[CONF_EXPOSED_TOOLS]

    assert tool not in [option["value"] for option in selector.config["options"]]
