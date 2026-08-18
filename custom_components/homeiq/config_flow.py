"""Config and options flows for HomeIQ (TAP-5305)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, OptionsFlowWithReload
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .agentforge import AgentForgeClient, AgentForgeError, AgentForgeUnauthorizedError
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
    DOMAIN,
    LOGGER,
    MCP_TIMEOUT_SECONDS,
)
from .mcp_client import HomeIQMcpClient, McpError, McpUnauthorizedError

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigFlowResult
    from homeassistant.core import HomeAssistant

    from . import HomeIQConfigEntry

_URL = TextSelector(TextSelectorConfig(type=TextSelectorType.URL))
_SECRET = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MCP_URL, default="http://homeiq-mcp:8050"): _URL,
        vol.Required(CONF_MCP_TOKEN): _SECRET,
        vol.Required(CONF_AGENTFORGE_URL, default="http://localhost:8010"): _URL,
        vol.Required(CONF_AGENTFORGE_API_KEY): _SECRET,
    }
)


async def async_validate_endpoints(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    """Probe both endpoints, returning config-flow errors keyed by ``base``.

    Both probes are real authenticated calls — ``tools/list`` on the MCP server
    and a ``match_only`` invoke on AgentForge — so a wrong token fails here
    rather than on the first conversation turn.
    """
    session = async_get_clientsession(hass)

    mcp = HomeIQMcpClient(session, data[CONF_MCP_URL], data[CONF_MCP_TOKEN], MCP_TIMEOUT_SECONDS)
    try:
        await mcp.async_list_tools()
    except McpUnauthorizedError:
        return {"base": "mcp_invalid_auth"}
    except McpError as err:
        LOGGER.debug("HomeIQ MCP probe failed: %s", err)
        return {"base": "mcp_cannot_connect"}

    agentforge = AgentForgeClient(
        session,
        data[CONF_AGENTFORGE_URL],
        data[CONF_AGENTFORGE_API_KEY],
        data.get(CONF_AGENTFORGE_PROJECT, DEFAULT_AGENTFORGE_PROJECT),
        AGENTFORGE_TIMEOUT_SECONDS,
    )
    try:
        await agentforge.async_verify()
    except AgentForgeUnauthorizedError:
        return {"base": "agentforge_invalid_auth"}
    except AgentForgeError as err:
        LOGGER.debug("AgentForge probe failed: %s", err)
        return {"base": "agentforge_cannot_connect"}

    return {}


class HomeIQConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the HomeIQ config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Collect the HomeIQ endpoints and verify them."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = await async_validate_endpoints(self.hass, user_input)
            if not errors:
                return self.async_create_entry(title="HomeIQ", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(STEP_USER_DATA_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the endpoints or credentials of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = await async_validate_endpoints(self.hass, user_input)
            if not errors:
                return self.async_update_reload_and_abort(entry, data_updates=user_input)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, user_input or dict(entry.data)
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(_config_entry: HomeIQConfigEntry) -> HomeIQOptionsFlow:
        """Return the options flow."""
        return HomeIQOptionsFlow()


class HomeIQOptionsFlow(OptionsFlowWithReload):
    """Choose the AgentForge project and which HomeIQ tools are exposed."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show and store the HomeIQ options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        _, specs = await self.hass.async_add_executor_job(load_catalogue)
        schema = vol.Schema(
            {
                vol.Required(CONF_AGENTFORGE_PROJECT, default=DEFAULT_AGENTFORGE_PROJECT): str,
                vol.Optional(CONF_EXPOSED_TOOLS, default=[]): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=spec.name, label=spec.name) for spec in specs
                        ],
                        multiple=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                schema, dict(self.config_entry.options)
            ),
        )
