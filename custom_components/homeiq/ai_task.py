"""AI Task support for HomeIQ (TAP-5309)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import ai_task, conversation
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.json import json_loads
from voluptuous_openapi import convert

from .agentforge import AgentForgeError
from .const import DOMAIN
from .entity import HomeIQEntity, render_prompt

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
    """Set up the HomeIQ AI Task entity."""
    async_add_entities([HomeIQTaskEntity(config_entry)])


class HomeIQTaskEntity(ai_task.AITaskEntity, HomeIQEntity):
    """Generates data from automations, scripts and templates via AgentForge."""

    _attr_supported_features = ai_task.AITaskEntityFeature.GENERATE_DATA

    def __init__(self, entry: HomeIQConfigEntry) -> None:
        """Initialise the entity."""
        super().__init__(entry, "ai_task_data")

    async def _async_generate_data(
        self,
        task: ai_task.GenDataTask,
        chat_log: conversation.ChatLog,
    ) -> ai_task.GenDataTaskResult:
        """Run a generate-data task and return output matching the request."""
        prompt = render_prompt(chat_log)
        if task.structure is not None:
            prompt = f"{prompt}\n\n{_structure_instruction(task.structure)}"

        try:
            response = await self.async_invoke(prompt)
        except AgentForgeError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="agentforge_error",
                translation_placeholders={"reason": err.user_message},
            ) from err

        if response.is_error:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="agentforge_error",
                translation_placeholders={"reason": response.as_user_message()},
            )

        chat_log.async_add_assistant_content_without_tools(
            conversation.AssistantContent(agent_id=self.entity_id, content=response.text)
        )

        data: Any = response.text
        if task.structure is not None:
            data = _structured_data(task.structure, response.text)

        return ai_task.GenDataTaskResult(conversation_id=chat_log.conversation_id, data=data)


def _structure_instruction(structure: vol.Schema) -> str:
    """Describe the requested output structure to AgentForge."""
    schema = json.dumps(convert(structure), separators=(",", ":"))
    return (
        "Reply with JSON only — no prose and no code fence — matching this JSON "
        f"schema exactly: {schema}"
    )


def _structured_data(structure: vol.Schema, text: str) -> Any:
    """Parse and validate AgentForge's answer against the requested structure."""
    try:
        parsed = json_loads(_strip_code_fence(text))
    except ValueError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="structure_not_json",
            translation_placeholders={"response": text},
        ) from err

    try:
        return structure(parsed)
    except vol.Invalid as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="structure_mismatch",
            translation_placeholders={"reason": str(err)},
        ) from err


def _strip_code_fence(text: str) -> str:
    """Remove a surrounding markdown code fence, which models add unbidden."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    body = stripped.removeprefix("```")
    newline = body.find("\n")
    if newline == -1:
        return stripped
    return body[newline + 1 :].removesuffix("```").strip()
