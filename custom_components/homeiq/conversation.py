"""Conversation support for HomeIQ (TAP-5307)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from homeassistant.components import conversation
from homeassistant.const import MATCH_ALL

from .agentforge import AgentForgeError
from .const import CONVERSATION_AGENT, DOMAIN, LLM_API_ID
from .entity import HomeIQEntity, assistant_delta_stream, render_prompt

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from . import HomeIQConfigEntry

PARALLEL_UPDATES = 0


async def async_setup_entry(
    _hass: HomeAssistant,
    config_entry: HomeIQConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the HomeIQ conversation entity."""
    async_add_entities([HomeIQConversationEntity(config_entry)])


class HomeIQConversationEntity(
    conversation.ConversationEntity,
    conversation.AbstractConversationAgent,
    HomeIQEntity,
):
    """A selectable conversation agent that answers through AgentForge."""

    # AgentForge's project invoke route returns one complete response, so there
    # is nothing to stream incrementally.
    _attr_supports_streaming = False

    def __init__(self, entry: HomeIQConfigEntry) -> None:
        """Initialise the agent."""
        super().__init__(entry, "conversation")

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return the languages this agent accepts."""
        return MATCH_ALL

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Answer one turn through AgentForge."""
        try:
            await chat_log.async_provide_llm_data(
                user_input.as_llm_context(DOMAIN),
                LLM_API_ID,
                None,
                user_input.extra_system_prompt,
            )
        except conversation.ConverseError as err:
            return err.as_conversation_result()

        try:
            response = await self.async_invoke(
                render_prompt(chat_log), config_hint=CONVERSATION_AGENT
            )
        except AgentForgeError as err:
            # A refusal or an unreachable AgentForge is something the user needs
            # to hear, not a traceback in the log.
            text = err.user_message
        else:
            text = response.as_user_message()

        async for _content in chat_log.async_add_delta_content_stream(
            self.entity_id, assistant_delta_stream(text)
        ):
            pass

        return conversation.async_get_result_from_chat_log(user_input, chat_log)
