"""
Epic 90, Story 90.1: Backend integration test — chat → YAML round-trip.

Tests the ha-ai-agent-service /api/v1/chat endpoint directly via HTTP.
Verifies: tool_call invocation, YAML preview generation, structural correctness.

Requires: ha-ai-agent-service running at HA_AGENT_URL (default: http://localhost:8030)
          OpenAI API key configured in the service

Run: pytest tests/integration/test_ask_ai_yaml_pipeline.py -v
     pytest tests/integration/test_ask_ai_yaml_pipeline.py -v -m integration
Exclude from default: pytest -m "not integration"
"""

from __future__ import annotations

import os

import httpx
import pytest
import yaml

HA_AGENT_URL = os.environ.get("HA_AGENT_URL", "http://localhost:8030")
CHAT_ENDPOINT = f"{HA_AGENT_URL}/api/v1/chat"
TIMEOUT = 120.0  # OpenAI calls can be slow


def _parse_yaml_from_tool_call(tool_calls: list[dict]) -> dict:
    """Extract and parse automation YAML from preview tool call."""
    preview_calls = [
        tc for tc in tool_calls if tc["name"] == "preview_automation_from_prompt"
    ]
    assert len(preview_calls) >= 1, (
        f"Expected preview_automation_from_prompt tool call, "
        f"got: {[tc['name'] for tc in tool_calls]}"
    )
    yaml_content = preview_calls[0]["arguments"].get("automation_yaml", "")
    assert yaml_content, "automation_yaml argument is empty"
    parsed = yaml.safe_load(yaml_content)
    assert isinstance(parsed, dict), f"Parsed YAML is not a dict: {type(parsed)}"
    return parsed


def _assert_has_trigger(
    automation: dict, expected_platform: str | None = None
) -> list[dict]:
    """Assert automation has trigger array, optionally check platform."""
    trigger = automation.get("trigger") or automation.get("triggers", [])
    if isinstance(trigger, dict):
        trigger = [trigger]
    assert isinstance(trigger, list) and len(trigger) > 0, (
        "Automation must have at least one trigger"
    )
    if expected_platform:
        platforms = [t.get("platform", "") for t in trigger]
        assert any(expected_platform in p for p in platforms), (
            f"Expected trigger platform '{expected_platform}', got: {platforms}"
        )
    return trigger


def _assert_has_action(
    automation: dict, expected_service_fragment: str | None = None
) -> list[dict]:
    """Assert automation has action array, optionally check service."""
    action = automation.get("action") or automation.get("actions", [])
    if isinstance(action, dict):
        action = [action]
    assert isinstance(action, list) and len(action) > 0, (
        "Automation must have at least one action"
    )
    if expected_service_fragment:
        services = []
        for a in action:
            svc = a.get("service") or a.get("action", "")
            if svc:
                services.append(svc)
        assert any(expected_service_fragment in s for s in services), (
            f"Expected action service containing '{expected_service_fragment}', "
            f"got: {services}"
        )
    return action


@pytest.mark.integration
@pytest.mark.asyncio
class TestAskAIYAMLPipeline:
    """Backend integration tests for chat -> YAML round-trip (Story 90.1)."""

    async def _chat(self, client: httpx.AsyncClient, message: str) -> dict:
        """Send a chat message and return the response."""
        response = await client.post(
            CHAT_ENDPOINT,
            json={"message": message, "conversation_id": None},
            timeout=TIMEOUT,
        )
        assert response.status_code == 200, (
            f"Chat failed: {response.status_code} {response.text}"
        )
        data = response.json()
        assert "tool_calls" in data, (
            f"Response missing tool_calls: {list(data.keys())}"
        )
        assert "conversation_id" in data, "Response missing conversation_id"
        return data

    # --- 5 Prompt Categories ---

    async def test_presence_based_automation(self):
        """Presence: motion detection -> light control."""
        async with httpx.AsyncClient() as client:
            data = await self._chat(
                client, "Turn on the hallway lights when motion is detected"
            )

            assert len(data["tool_calls"]) >= 1
            automation = _parse_yaml_from_tool_call(data["tool_calls"])

            triggers = _assert_has_trigger(automation, "state")
            # Trigger should reference a motion/binary_sensor entity
            trigger_entities = [t.get("entity_id", "") for t in triggers]
            assert any(
                "motion" in str(e).lower() or "binary_sensor" in str(e).lower()
                for e in trigger_entities
            ), f"Presence trigger should reference motion sensor, got: {trigger_entities}"

            _assert_has_action(automation, "light.turn_on")
            assert automation.get("alias"), "Automation must have an alias"

    async def test_time_based_automation(self):
        """Time: scheduled action at specific time."""
        async with httpx.AsyncClient() as client:
            data = await self._chat(
                client, "Turn off all lights at 11pm every night"
            )

            automation = _parse_yaml_from_tool_call(data["tool_calls"])
            _assert_has_trigger(automation, "time")
            _assert_has_action(automation, "light.turn_off")
            assert automation.get("alias"), "Automation must have an alias"

    async def test_device_state_automation(self):
        """Device-state: state change -> notification."""
        async with httpx.AsyncClient() as client:
            data = await self._chat(
                client, "Send a notification when the front door opens"
            )

            automation = _parse_yaml_from_tool_call(data["tool_calls"])
            _assert_has_trigger(automation, "state")

            # Action should be a notification service
            action = automation.get("action") or automation.get("actions", [])
            if isinstance(action, dict):
                action = [action]
            services = [
                a.get("service", "") or a.get("action", "") for a in action
            ]
            assert any(
                "notify" in s or "persistent_notification" in s for s in services
            ), f"Expected notification service, got: {services}"

    async def test_multi_domain_automation(self):
        """Multi-domain: arrival triggers multiple domain actions."""
        async with httpx.AsyncClient() as client:
            data = await self._chat(
                client,
                "When I arrive home, turn on the living room lights, "
                "set the thermostat to 72 degrees, and unlock the front door",
            )

            automation = _parse_yaml_from_tool_call(data["tool_calls"])
            _assert_has_trigger(automation)

            action = automation.get("action") or automation.get("actions", [])
            if isinstance(action, dict):
                action = [action]
            services = [
                a.get("service", "") or a.get("action", "") for a in action
            ]

            domains_found = set()
            for svc in services:
                if "light" in svc:
                    domains_found.add("light")
                if "climate" in svc:
                    domains_found.add("climate")
                if "lock" in svc:
                    domains_found.add("lock")

            assert len(domains_found) >= 2, (
                f"Multi-domain automation should span >=2 domains, "
                f"found: {domains_found} from {services}"
            )

    async def test_scene_based_automation(self):
        """Scene: device trigger -> scene activation."""
        async with httpx.AsyncClient() as client:
            data = await self._chat(
                client, "Activate the movie night scene when the TV turns on"
            )

            automation = _parse_yaml_from_tool_call(data["tool_calls"])
            _assert_has_trigger(automation, "state")

            action = automation.get("action") or automation.get("actions", [])
            if isinstance(action, dict):
                action = [action]
            services = [
                a.get("service", "") or a.get("action", "") for a in action
            ]
            assert any("scene" in s for s in services), (
                f"Scene automation should use scene service, got: {services}"
            )

    # --- API Contract Verification ---

    async def test_response_metadata_structure(self):
        """Verify response metadata contains expected fields."""
        async with httpx.AsyncClient() as client:
            data = await self._chat(
                client, "Turn on bedroom lights at sunset"
            )

            assert "metadata" in data, "Response missing metadata"
            metadata = data["metadata"]
            assert "model" in metadata, "Metadata missing model"
            assert "tokens_used" in metadata or "token_breakdown" in metadata, (
                "Metadata missing token info"
            )

    async def test_tool_call_structure(self):
        """Verify tool_call has correct shape (id, name, arguments)."""
        async with httpx.AsyncClient() as client:
            data = await self._chat(
                client, "Flash the porch light when doorbell rings"
            )

            for tc in data["tool_calls"]:
                assert "id" in tc, "Tool call missing id"
                assert "name" in tc, "Tool call missing name"
                assert "arguments" in tc, "Tool call missing arguments"

                if tc["name"] == "preview_automation_from_prompt":
                    args = tc["arguments"]
                    assert "user_prompt" in args, "Preview missing user_prompt"
                    assert "automation_yaml" in args, (
                        "Preview missing automation_yaml"
                    )
                    assert "alias" in args, "Preview missing alias"
