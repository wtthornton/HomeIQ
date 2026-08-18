"""Setup, teardown and LLM API scoping tests (TAP-5305, TAP-5306)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm

from custom_components.homeiq.const import CONF_EXPOSED_TOOLS, DOMAIN, LLM_API_ID
from custom_components.homeiq.diagnostics import async_get_config_entry_diagnostics

from .conftest import HANDSHAKE, call_result, serve_mcp, setup_entry

if TYPE_CHECKING:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

LLM_CONTEXT = llm.LLMContext(
    platform=DOMAIN,
    context=Context(),
    language="en",
    assistant="conversation",
    device_id=None,
)


@pytest.mark.usefixtures("homeassistant_component")
async def test_entry_sets_up_and_unloads(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """A config entry loads both platforms and tears them down again."""
    await setup_entry(hass, config_entry)

    assert config_entry.state is ConfigEntryState.LOADED
    assert hass.states.get("conversation.homeiq_assistant") is not None
    assert hass.states.get("ai_task.homeiq_task") is not None

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED


@pytest.mark.usefixtures("homeassistant_component")
async def test_llm_api_is_registered_and_unregistered(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """The scoped API appears while the entry is loaded and not after."""
    await setup_entry(hass, config_entry)

    assert LLM_API_ID in {api.id for api in llm.async_get_apis(hass)}

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert LLM_API_ID not in {api.id for api in llm.async_get_apis(hass)}


@pytest.mark.usefixtures("homeassistant_component")
async def test_homeiq_api_exposes_the_catalogue_tools(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Selecting the HomeIQ API yields exactly the catalogue's live tools."""
    await setup_entry(hass, config_entry)

    instance = await llm.async_get_api(hass, LLM_API_ID, LLM_CONTEXT)
    names = {tool.name for tool in instance.tools}

    assert "get_entity_history" in names
    assert "get_energy_correlations" not in names, "deferred tools must stay hidden"


@pytest.mark.usefixtures("homeassistant_component")
async def test_other_api_ids_get_no_homeiq_tools(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Home Assistant's own assist API is untouched by HomeIQ (TAP-5306)."""
    await setup_entry(hass, config_entry)

    homeiq = await llm.async_get_api(hass, LLM_API_ID, LLM_CONTEXT)
    assist = await llm.async_get_api(hass, llm.LLM_API_ASSIST, LLM_CONTEXT)

    homeiq_names = {tool.name for tool in homeiq.tools}
    assist_names = {tool.name for tool in assist.tools}

    assert homeiq_names
    assert not homeiq_names & assist_names


@pytest.mark.usefixtures("homeassistant_component")
async def test_options_can_narrow_the_exposed_tools(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Only the tools chosen in the options flow are offered."""
    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        config_entry, options={CONF_EXPOSED_TOOLS: ["list_areas"]}
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    instance = await llm.async_get_api(hass, LLM_API_ID, LLM_CONTEXT)

    assert [tool.name for tool in instance.tools] == ["list_areas"]


@pytest.mark.usefixtures("homeassistant_component")
async def test_tool_call_reaches_the_mcp_server(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A tool call is validated, dispatched and returned to the caller."""
    serve_mcp(aioclient_mock, HANDSHAKE | {"tools/call": call_result({"areas": ["hall"]})})
    await setup_entry(hass, config_entry)

    instance = await llm.async_get_api(hass, LLM_API_ID, LLM_CONTEXT)
    result = await instance.async_call_tool(llm.ToolInput(tool_name="list_areas", tool_args={}))

    assert result == {"areas": ["hall"]}


@pytest.mark.usefixtures("homeassistant_component")
async def test_tool_call_failure_becomes_a_home_assistant_error(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """An MCP failure is raised as a HomeAssistantError the chat log can catch."""
    serve_mcp(
        aioclient_mock,
        HANDSHAKE
        | {
            "tools/call": {
                "content": [{"type": "text", "text": "backing_unavailable: down"}],
                "structuredContent": {"error": {"code": "backing_unavailable", "message": "down"}},
                "isError": True,
            }
        },
    )
    await setup_entry(hass, config_entry)

    instance = await llm.async_get_api(hass, LLM_API_ID, LLM_CONTEXT)

    with pytest.raises(HomeAssistantError):
        await instance.async_call_tool(llm.ToolInput(tool_name="list_areas", tool_args={}))


@pytest.mark.usefixtures("homeassistant_component")
async def test_diagnostics_redact_credentials(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Diagnostics describe the catalogue without leaking secrets."""
    await setup_entry(hass, config_entry)

    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    assert diagnostics["entry"]["data"]["mcp_token"] == "**REDACTED**"
    assert diagnostics["entry"]["data"]["agentforge_api_key"] == "**REDACTED**"
    assert diagnostics["entry"]["data"]["mcp_url"].startswith("http://")
    assert diagnostics["catalogue_version"]
    assert all(tool["read_only"] for tool in diagnostics["tools"])
