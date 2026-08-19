"""Tests for the config-checked core restart.

The case that matters is the one `check_config` cannot see: Home Assistant
disables a schema-broken automation during setup and still reports the
configuration valid, so the pre-flight passes, the core restarts, and the home
comes back with automations silently dead. RUNNING is not the same as healthy.
"""

from __future__ import annotations

from typing import Any

import pytest
from homeiq_ha.agent.core_restart import restart_core
from homeiq_ha.client.errors import HAClientError


class FakeRest:
    """Minimal stand-in for ``HARestClient``.

    ``states`` is what ``/api/states`` returns once the core is back, which is
    the surface the post-restart assertion reads.
    """

    def __init__(
        self,
        *,
        config_result: str = "valid",
        states: list[dict[str, Any]] | None = None,
    ) -> None:
        self.config_result = config_result
        self.states = states if states is not None else []
        self.calls: list[str] = []

    async def check_config(self) -> dict[str, str]:
        self.calls.append("check_config")
        return {"result": self.config_result}

    async def call_service(self, domain: str, service: str) -> None:
        self.calls.append(f"{domain}.{service}")

    async def request(self, method: str, path: str) -> Any:
        self.calls.append(f"{method} {path}")
        if path == "/api/config":
            return {"state": "RUNNING"}
        if path == "/api/states":
            return self.states
        raise AssertionError(f"unexpected request {method} {path}")


class FakeHA:
    def __init__(self, rest: FakeRest) -> None:
        self.rest = rest


def _automation(entity_id: str, state: str) -> dict[str, str]:
    return {"entity_id": entity_id, "state": state}


FAST = {"timeout": 5.0, "poll_interval": 0.01, "min_wait": 0.0}


@pytest.mark.asyncio
async def test_restart_succeeds_when_every_automation_loaded():
    rest = FakeRest(
        states=[
            _automation("automation.office_presence_lighting", "on"),
            _automation("automation.office_fan_presence_control", "off"),
            {"entity_id": "light.office", "state": "unavailable"},
        ]
    )

    await restart_core(FakeHA(rest), **FAST)

    assert "homeassistant.restart" in rest.calls
    assert "GET /api/states" in rest.calls, "post-restart health was never checked"


@pytest.mark.asyncio
async def test_restart_fails_when_an_automation_did_not_load():
    """check_config says valid, the core reaches RUNNING, and it is still broken."""
    rest = FakeRest(
        config_result="valid",
        states=[
            _automation("automation.office_presence_lighting", "unavailable"),
            _automation("automation.office_fan_presence_control", "on"),
        ],
    )

    with pytest.raises(HAClientError, match="failed to load"):
        await restart_core(FakeHA(rest), **FAST)


@pytest.mark.asyncio
async def test_failure_names_the_automations_so_the_message_is_actionable():
    rest = FakeRest(
        states=[
            _automation("automation.b_second", "unavailable"),
            _automation("automation.a_first", "unavailable"),
            _automation("automation.c_fine", "on"),
        ]
    )

    with pytest.raises(HAClientError) as excinfo:
        await restart_core(FakeHA(rest), **FAST)

    message = str(excinfo.value)
    assert "automation.a_first" in message
    assert "automation.b_second" in message
    assert "automation.c_fine" not in message
    assert message.index("a_first") < message.index("b_second"), "not sorted"


@pytest.mark.asyncio
async def test_a_light_that_is_unavailable_does_not_fail_the_restart():
    """Only automations are load-bearing here.

    An unavailable light is routine — a bulb switched off at the wall reads
    that way — and failing a restart on it would make the check unusable.
    """
    rest = FakeRest(states=[{"entity_id": "light.office_go", "state": "unavailable"}])

    await restart_core(FakeHA(rest), **FAST)


@pytest.mark.asyncio
async def test_broken_config_still_refuses_before_restarting():
    rest = FakeRest(config_result="invalid")

    with pytest.raises(HAClientError, match="refusing to restart"):
        await restart_core(FakeHA(rest), **FAST)

    assert "homeassistant.restart" not in rest.calls, "restarted despite a bad config"
