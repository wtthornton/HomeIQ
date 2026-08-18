"""Tests for the HomeIQ conversation entity (TAP-5307)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from aiohttp import ClientError
from homeassistant.components import conversation
from homeassistant.core import Context, HomeAssistant

from .conftest import AGENTFORGE_ENDPOINT, setup_entry, task_response

if TYPE_CHECKING:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

ENTITY_ID = "conversation.homeiq_assistant"


async def converse(hass: HomeAssistant, text: str) -> conversation.ConversationResult:
    """Send one turn to the HomeIQ agent."""
    return await conversation.async_converse(hass, text, None, Context(), agent_id=ENTITY_ID)


def spoken(result: conversation.ConversationResult) -> str:
    """Return what the agent said."""
    return result.response.speech["plain"]["speech"]


@pytest.mark.usefixtures("homeassistant_component")
async def test_turn_is_answered_by_agentforge(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """The user's text reaches AgentForge and its answer comes back."""
    aioclient_mock.post(AGENTFORGE_ENDPOINT, json=task_response())
    await setup_entry(hass, config_entry)

    result = await converse(hass, "How long was the kitchen light on?")

    assert spoken(result) == "The kitchen light was on for 4 hours."
    assert "How long was the kitchen light on?" in aioclient_mock.mock_calls[0][2]["prompt"]


@pytest.mark.usefixtures("homeassistant_component")
async def test_scoped_tools_are_named_in_the_prompt(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """The tools taken from the chat log's scoped API are advertised."""
    aioclient_mock.post(AGENTFORGE_ENDPOINT, json=task_response())
    await setup_entry(hass, config_entry)

    await converse(hass, "what happened today?")

    prompt = aioclient_mock.mock_calls[0][2]["prompt"]
    assert "HomeIQ tools available to you:" in prompt
    assert "get_entity_history" in prompt
    assert "get_energy_correlations" not in prompt


@pytest.mark.usefixtures("homeassistant_component")
async def test_budget_refusal_is_spoken_as_a_refusal(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A budget block reaches the user as a refusal, not a crash."""
    aioclient_mock.post(
        AGENTFORGE_ENDPOINT,
        json=task_response(
            result="orchestration blocked by budget: portfolio monthly budget hard cap engaged",
            is_error=True,
        ),
    )
    await setup_entry(hass, config_entry)

    result = await converse(hass, "analyse the whole year")

    assert result.response.response_type is not conversation.intent.IntentResponseType.ERROR
    assert "stopped this request before spending more" in spoken(result)
    assert "portfolio monthly budget hard cap engaged" in spoken(result)


@pytest.mark.usefixtures("homeassistant_component")
async def test_unreachable_agentforge_is_spoken(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A transport failure becomes a sentence, not a traceback."""
    aioclient_mock.post(AGENTFORGE_ENDPOINT, exc=ClientError("no route"))
    await setup_entry(hass, config_entry)

    assert "could not reach AgentForge" in spoken(await converse(hass, "hello"))


@pytest.mark.usefixtures("homeassistant_component")
async def test_agent_is_selectable_and_read_only(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """The entity is registered as an agent and claims no control feature."""
    await setup_entry(hass, config_entry)

    info = conversation.async_get_agent_info(hass, ENTITY_ID)

    assert info is not None
    assert info.id == ENTITY_ID
    state = hass.states.get(ENTITY_ID)
    assert state.attributes["supported_features"] == 0


@pytest.mark.usefixtures("homeassistant_component")
async def test_conversation_history_is_carried_forward(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A second turn in the same conversation includes the first exchange."""
    aioclient_mock.post(AGENTFORGE_ENDPOINT, json=task_response())
    await setup_entry(hass, config_entry)

    first = await conversation.async_converse(
        hass, "first question", None, Context(), agent_id=ENTITY_ID
    )
    await conversation.async_converse(
        hass, "second question", first.conversation_id, Context(), agent_id=ENTITY_ID
    )

    prompt = aioclient_mock.mock_calls[-1][2]["prompt"]
    assert "User: first question" in prompt
    assert "Assistant: The kitchen light was on for 4 hours." in prompt
    assert "User: second question" in prompt
