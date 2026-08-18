"""HomeIQ's scoped LLM API (TAP-5306).

HomeIQ registers its tools under its own API id rather than adding them to Home
Assistant's built-in ``assist`` API. An agent therefore only sees HomeIQ tools
when it has explicitly selected the HomeIQ API: ``llm.async_get_api(hass,
"assist", ...)`` returns an instance built by the Assist API, which knows
nothing about this one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm

from .const import DOMAIN, LLM_API_ID, LLM_API_NAME
from .mcp_client import McpError

if TYPE_CHECKING:
    import voluptuous as vol
    from homeassistant.core import HomeAssistant
    from homeassistant.util.json import JsonObjectType

    from .catalogue import ToolSpec
    from .mcp_client import HomeIQMcpClient

API_PROMPT = (
    "You have read-only access to HomeIQ, the home's automation intelligence "
    "platform. Its tools answer questions about entity history, recent events, "
    "devices, areas, detected patterns, energy use and device health. None of "
    "them change the state of the home; use Home Assistant's own tools for that."
)


class HomeIQTool(llm.Tool):
    """One catalogue tool, dispatched to the HomeIQ MCP server."""

    def __init__(self, spec: ToolSpec, client: HomeIQMcpClient) -> None:
        """Initialise the tool from its catalogue entry."""
        self.name = spec.name
        self.description = spec.description
        self.parameters: vol.Schema = spec.parameters
        self._spec = spec
        self._client = client

    async def async_call(
        self,
        _hass: HomeAssistant,
        tool_input: llm.ToolInput,
        _llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Validate the arguments and run the tool on the MCP server."""
        arguments = self._spec.validate_arguments(tool_input.tool_args)
        try:
            return await self._client.async_call_tool(
                self._spec.name, arguments, self._spec.max_response_bytes
            )
        except McpError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="mcp_tool_failed",
                translation_placeholders={"tool": self._spec.name, "reason": err.message},
            ) from err


@dataclass(slots=True, kw_only=True)
class HomeIQLLMAPI(llm.API):
    """The ``homeiq`` LLM API, exposing only HomeIQ's own tools."""

    tools: list[llm.Tool] = field(default_factory=list)

    async def async_get_api_instance(self, llm_context: llm.LLMContext) -> llm.APIInstance:
        """Return an instance carrying exactly the HomeIQ tools."""
        return llm.APIInstance(
            api=self,
            api_prompt=API_PROMPT,
            llm_context=llm_context,
            tools=self.tools,
        )


def build_api(
    hass: HomeAssistant,
    specs: list[ToolSpec],
    client: HomeIQMcpClient,
) -> HomeIQLLMAPI:
    """Build the HomeIQ LLM API from catalogue specs."""
    return HomeIQLLMAPI(
        hass=hass,
        id=LLM_API_ID,
        name=LLM_API_NAME,
        tools=[HomeIQTool(spec, client) for spec in specs],
    )
