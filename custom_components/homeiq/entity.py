"""Shared plumbing for the HomeIQ entities (TAP-5307, TAP-5309).

AgentForge's project invoke route is plain JSON: it has no tool-calling channel
and no SSE (its streaming endpoint is unscoped and would bypass project auth).
The scoped HomeIQ tools therefore reach the agent as a rendered manifest in the
prompt, taken from ``chat_log.llm_api.tools`` — so whichever tools the config
entry exposes are exactly the tools AgentForge is told about.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components import conversation
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from . import HomeIQConfigEntry
    from .agentforge import AgentForgeResponse

_ROLE_LABELS = {"system": "System", "user": "User", "assistant": "Assistant"}


class HomeIQEntity(Entity):
    """Base entity bound to one HomeIQ config entry."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: HomeIQConfigEntry, key: str) -> None:
        """Initialise the entity."""
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="HomeIQ",
            manufacturer="HomeIQ",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_invoke(self, prompt: str) -> AgentForgeResponse:
        """Run one AgentForge task for this entry."""
        return await self.entry.runtime_data.agentforge.async_invoke(prompt)


def render_prompt(chat_log: conversation.ChatLog) -> str:
    """Render a chat log as the single prompt string AgentForge accepts."""
    parts: list[str] = []

    system = chat_log.content[0]
    if isinstance(system, conversation.SystemContent) and system.content:
        parts.append(system.content)

    if chat_log.llm_api and chat_log.llm_api.tools:
        listing = "\n".join(f"- {tool.name}: {tool.description}" for tool in chat_log.llm_api.tools)
        parts.append(f"HomeIQ tools available to you:\n{listing}")

    transcript = [
        rendered for content in chat_log.content[1:] if (rendered := _render_content(content))
    ]
    if transcript:
        parts.append("\n".join(transcript))

    return "\n\n".join(parts)


def _render_content(content: conversation.Content) -> str | None:
    """Render one chat-log entry, or None when it carries nothing to send."""
    if isinstance(content, conversation.ToolResultContent):
        return f"Tool result ({content.tool_name}): {content.tool_result}"
    if content.content:
        return f"{_ROLE_LABELS.get(content.role, content.role)}: {content.content}"
    return None


async def assistant_delta_stream(
    text: str,
) -> AsyncGenerator[conversation.AssistantContentDeltaDict]:
    """Yield one assistant message as a chat-log delta stream.

    AgentForge answers the project invoke route in a single response, so this is
    a stream of one chunk. Using the streaming API keeps the delta listeners
    Home Assistant attaches to a chat log working, and leaves the entity ready
    for an incremental AgentForge transport without touching the caller.
    """
    yield {"role": "assistant"}
    yield {"content": text}
