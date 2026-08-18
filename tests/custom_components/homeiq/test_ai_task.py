"""Tests for the HomeIQ AI Task entity (TAP-5309)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
import voluptuous as vol
from aiohttp import ClientError
from homeassistant.components import ai_task
from homeassistant.exceptions import HomeAssistantError

from .conftest import AGENTFORGE_ENDPOINT, setup_entry, task_response

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

ENTITY_ID = "ai_task.homeiq_task"

STRUCTURE = vol.Schema(
    {
        vol.Required("busiest_room"): str,
        vol.Required("events"): int,
    }
)


async def generate(
    hass: HomeAssistant, instructions: str, structure: vol.Schema | None = None
) -> ai_task.GenDataTaskResult:
    """Run a generate-data task on the HomeIQ entity."""
    return await ai_task.async_generate_data(
        hass,
        task_name="homeiq test",
        entity_id=ENTITY_ID,
        instructions=instructions,
        structure=structure,
    )


@pytest.mark.usefixtures("homeassistant_component")
async def test_plain_task_returns_text(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Without a structure the agent's text is the data."""
    aioclient_mock.post(AGENTFORGE_ENDPOINT, json=task_response(result="all quiet"))
    await setup_entry(hass, config_entry)

    result = await generate(hass, "summarise the day")

    assert result.data == "all quiet"
    assert "summarise the day" in aioclient_mock.mock_calls[0][2]["prompt"]


@pytest.mark.usefixtures("homeassistant_component")
async def test_structured_task_conforms_to_the_request(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A structured task returns data validated against the requested schema."""
    aioclient_mock.post(
        AGENTFORGE_ENDPOINT,
        json=task_response(result=json.dumps({"busiest_room": "kitchen", "events": 42})),
    )
    await setup_entry(hass, config_entry)

    result = await generate(hass, "which room was busiest?", STRUCTURE)

    assert result.data == {"busiest_room": "kitchen", "events": 42}
    prompt = aioclient_mock.mock_calls[0][2]["prompt"]
    assert "Reply with JSON only" in prompt
    assert '"busiest_room"' in prompt


@pytest.mark.usefixtures("homeassistant_component")
async def test_structured_task_tolerates_a_code_fence(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A fenced JSON answer is still parsed."""
    fenced = '```json\n{"busiest_room": "hall", "events": 7}\n```'
    aioclient_mock.post(AGENTFORGE_ENDPOINT, json=task_response(result=fenced))
    await setup_entry(hass, config_entry)

    result = await generate(hass, "which room was busiest?", STRUCTURE)

    assert result.data == {"busiest_room": "hall", "events": 7}


@pytest.mark.usefixtures("homeassistant_component")
async def test_structured_task_rejects_non_json(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Prose where JSON was demanded fails loudly."""
    aioclient_mock.post(AGENTFORGE_ENDPOINT, json=task_response(result="the kitchen, I think"))
    await setup_entry(hass, config_entry)

    with pytest.raises(HomeAssistantError, match="did not return JSON"):
        await generate(hass, "which room was busiest?", STRUCTURE)


@pytest.mark.usefixtures("homeassistant_component")
async def test_structured_task_rejects_a_mismatched_shape(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """JSON that does not match the declared structure is refused."""
    aioclient_mock.post(
        AGENTFORGE_ENDPOINT, json=task_response(result=json.dumps({"busiest_room": "hall"}))
    )
    await setup_entry(hass, config_entry)

    with pytest.raises(HomeAssistantError, match="did not match the requested structure"):
        await generate(hass, "which room was busiest?", STRUCTURE)


@pytest.mark.usefixtures("homeassistant_component")
async def test_budget_refusal_fails_the_task_readably(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """An automation sees a readable refusal rather than a silent success."""
    aioclient_mock.post(
        AGENTFORGE_ENDPOINT,
        json=task_response(
            result="orchestration blocked by budget: "
            "plan low estimate exceeds remaining portfolio budget",
            is_error=True,
        ),
    )
    await setup_entry(hass, config_entry)

    with pytest.raises(HomeAssistantError, match="stopped this request before spending more"):
        await generate(hass, "analyse everything")


@pytest.mark.usefixtures("homeassistant_component")
async def test_unreachable_agentforge_fails_the_task(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A transport failure surfaces as a task error."""
    aioclient_mock.post(AGENTFORGE_ENDPOINT, exc=ClientError("no route"))
    await setup_entry(hass, config_entry)

    with pytest.raises(HomeAssistantError, match="could not reach AgentForge"):
        await generate(hass, "summarise the day")


@pytest.mark.usefixtures("homeassistant_component")
async def test_entity_supports_generate_data(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """The entity advertises the generate-data feature automations look for."""
    await setup_entry(hass, config_entry)

    state = hass.states.get(ENTITY_ID)

    assert state.attributes["supported_features"] == ai_task.AITaskEntityFeature.GENERATE_DATA
