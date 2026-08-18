"""The HomeIQ integration (TAP-5305).

One config entry wires up three things: a client for the HomeIQ MCP server, a
client for AgentForge, and the scoped ``homeiq`` LLM API built from the MCP tool
catalogue. The conversation and AI Task platforms are set up from that same
entry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.helpers import llm
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .agentforge import AgentForgeClient
from .catalogue import load_catalogue
from .const import (
    AGENTFORGE_TIMEOUT_SECONDS,
    CONF_AGENTFORGE_API_KEY,
    CONF_AGENTFORGE_PROJECT,
    CONF_AGENTFORGE_URL,
    CONF_EXPOSED_TOOLS,
    CONF_MCP_TOKEN,
    CONF_MCP_URL,
    DEFAULT_AGENTFORGE_PROJECT,
    LOGGER,
    MCP_TIMEOUT_SECONDS,
)
from .llm_api import build_api
from .mcp_client import HomeIQMcpClient

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .catalogue import ToolSpec

PLATFORMS = (Platform.AI_TASK, Platform.CONVERSATION)


@dataclass(slots=True)
class HomeIQRuntimeData:
    """Everything the HomeIQ platforms need, built once per config entry."""

    mcp: HomeIQMcpClient
    agentforge: AgentForgeClient
    catalogue_version: str
    tools: list[ToolSpec]


HomeIQConfigEntry = ConfigEntry[HomeIQRuntimeData]


def _exposed(specs: list[ToolSpec], allowed: list[str]) -> list[ToolSpec]:
    """Narrow the catalogue to the tools the user chose to expose."""
    if not allowed:
        return specs
    return [spec for spec in specs if spec.name in allowed]


async def async_setup_entry(hass: HomeAssistant, entry: HomeIQConfigEntry) -> bool:
    """Set up HomeIQ from a config entry."""
    session = async_get_clientsession(hass)
    mcp = HomeIQMcpClient(
        session,
        entry.data[CONF_MCP_URL],
        entry.data[CONF_MCP_TOKEN],
        MCP_TIMEOUT_SECONDS,
    )
    agentforge = AgentForgeClient(
        session,
        entry.data[CONF_AGENTFORGE_URL],
        entry.data[CONF_AGENTFORGE_API_KEY],
        entry.options.get(CONF_AGENTFORGE_PROJECT, DEFAULT_AGENTFORGE_PROJECT),
        AGENTFORGE_TIMEOUT_SECONDS,
    )

    catalogue_version, specs = await hass.async_add_executor_job(load_catalogue)
    tools = _exposed(specs, entry.options.get(CONF_EXPOSED_TOOLS, []))
    LOGGER.debug(
        "HomeIQ MCP catalogue v%s: exposing %s of %s tools",
        catalogue_version,
        len(tools),
        len(specs),
    )

    entry.async_on_unload(llm.async_register_api(hass, build_api(hass, tools, mcp)))
    entry.runtime_data = HomeIQRuntimeData(
        mcp=mcp,
        agentforge=agentforge,
        catalogue_version=catalogue_version,
        tools=tools,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HomeIQConfigEntry) -> bool:
    """Unload a HomeIQ config entry.

    The LLM API is unregistered by the ``async_on_unload`` callback registered
    during setup, so no agent keeps a handle on a torn-down entry.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
