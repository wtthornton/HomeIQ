import json
import os

import aiohttp
import pytest
from src.clients.ha_client import HomeAssistantClient


def _get_env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_ha
async def test_conversation_create_flash_automation_request_only():
    """
    Calls Home Assistant Conversation API asking it to create an automation that
    flashes the office lights for 10 seconds and then restores the prior state.

    This test does NOT generate YAML and does NOT directly create automations.
    It simply exercises the Conversation API and prints the raw response so we
    can see whether HA can interpret and act on the request to create an automation.
    """
    ha_url = _get_env("HA_URL") or _get_env("HOME_ASSISTANT_URL")
    ha_token = _get_env("HA_TOKEN") or _get_env("HOME_ASSISTANT_TOKEN")
    office_light = _get_env("OFFICE_LIGHT_ENTITY", "")  # unused; keep natural language
    agent_id = _get_env("HA_CONVERSATION_AGENT_ID", "")  # optional

    if not ha_url or not ha_token:
        pytest.skip("HA_URL and HA_TOKEN must be set in environment/.env for this test")

    client = HomeAssistantClient(ha_url=ha_url, access_token=ha_token)

    prompts = [
        "Create an automation in Home Assistant named 'Test Flash Office' that flashes the office lights for 10 seconds and then restores their previous state. Enable it when done.",
        "Add a new automation to flash the office lights for 10 seconds, then restore their previous state.",
        "Set up an automation to flash the office lights for 10 seconds and restore the prior state.",
        "Please create a new automation called 'Test Flash Office' to flash the office lights for 10 seconds, then restore previous state.",
        "In Home Assistant, create an automation to flash the office lights for 10 seconds and then restore their previous state. Enable it.",
        "Make a new automation that flashes the office lights for 10 seconds and then sets them back to their prior settings."
    ]

    conversation_id = None
    headers = {
        "Authorization": f"Bearer {ha_token}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        for idx, prompt in enumerate(prompts, start=1):
            payload = {"text": prompt, "language": "en"}
            if agent_id:
                payload["agent_id"] = agent_id
            if conversation_id:
                payload["conversation_id"] = conversation_id

            print("\n=== Conversation API Request Variant", idx, "===\n")
            print(json.dumps(payload, indent=2, sort_keys=True))
            print("\n===================================\n")

            async with session.post(f"{ha_url.rstrip('/')}/api/conversation/process", headers=headers, json=payload) as resp:
                try:
                    result = await resp.json()
                except Exception:
                    result = {"status": resp.status, "text": await resp.text()}

            # Capture conversation_id if provided
            if isinstance(result, dict) and result.get("conversation_id"):
                conversation_id = result.get("conversation_id")

            print("\n=== Conversation API Response Variant", idx, "(raw) ===\n")
            try:
                print(json.dumps(result, indent=2, sort_keys=True))
            except Exception:
                print(result)
            print("\n====================================================\n")

            # Keep test lenient: we only assert we got something structured back
            assert isinstance(result, dict), "Expected dict response from Conversation API"


