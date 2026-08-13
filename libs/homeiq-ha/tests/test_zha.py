"""integrations.zha recipe tests: formation guard and flow driver.

Reuses the fixture simulator from ``test_agent_recipes`` — the shapes there
were captured from the live instance.
"""

from __future__ import annotations

from typing import Any

import pytest
from homeiq_ha.agent import CheckStatus, HAInitAgent
from homeiq_ha.agent.recipes import (
    ZHAFormationRefused,
    ZHARecipe,
)

from tests.simulators import SimHA


@pytest.fixture
def sim() -> SimHA:
    return SimHA()


ZHA_PATH = "socket://192.168.1.121:6638"


def _loaded_zha_entry() -> dict[str, Any]:
    return {"entry_id": "zha1", "domain": "zha", "state": "loaded"}


class ZHAFlowScript:
    """REST half scripting the captured first-install ZHA flow.

    Mirrors the transcript from the live install (2026-08-11): serial-port
    form → radio verification form → strategy menu → ``form_new_network``
    progress step polled twice → ``create_entry``.
    """

    def __init__(self, state: dict[str, Any], progress_polls: int = 2) -> None:
        self.state = state
        self.calls: list[tuple[str, Any]] = []
        self._progress_left = progress_polls

    @staticmethod
    def classify_flow_step(step: dict[str, Any]) -> str:
        return str(step.get("type") or "form")

    async def get_config_entries(self) -> list[dict[str, Any]]:
        return self.state["config_entries"]

    async def start_config_flow(self, domain: str, **_context: Any) -> dict[str, Any]:
        self.calls.append(("start", domain))
        return {
            "type": "form",
            "flow_id": "f1",
            "step_id": "choose_serial_port",
            "data_schema": [{"name": "path"}],
        }

    async def advance_config_flow(self, flow_id: str, user_input: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("advance", dict(user_input)))
        step = len([c for c in self.calls if c[0] == "advance"])
        if step == 1:
            assert user_input == {"path": ZHA_PATH}
            return {
                "type": "form",
                "flow_id": flow_id,
                "step_id": "verify_radio",
                "data_schema": [],
            }
        if step == 2:
            return {"type": "menu", "flow_id": flow_id, "step_id": "choose_setup_strategy"}
        if step == 3:
            assert user_input == {"next_step_id": "setup_strategy_recommended"}
            return {"type": "progress", "flow_id": flow_id, "step_id": "form_new_network"}
        if self._progress_left > 0:
            assert user_input == {}
            self._progress_left -= 1
            if self._progress_left:
                return {"type": "progress", "flow_id": flow_id, "step_id": "form_new_network"}
        self.state["config_entries"].append(_loaded_zha_entry())
        return {"type": "create_entry", "flow_id": flow_id}


@pytest.mark.asyncio
async def test_zha_check_is_satisfied_on_a_loaded_entry(sim):
    sim.state["config_entries"].append(_loaded_zha_entry())

    result = await ZHARecipe(ZHA_PATH).check(sim)

    assert result.status is CheckStatus.SATISFIED


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["loaded", "setup_retry", "not_loaded"])
async def test_zha_apply_refuses_formation_when_any_entry_exists(sim, state):
    sim.state["config_entries"].append({"entry_id": "zha1", "domain": "zha", "state": state})
    recipe = ZHARecipe(ZHA_PATH)

    async def tripwire(*_a: object, **_kw: object) -> None:
        raise AssertionError("flow call issued despite existing zha entry")

    sim.rest.start_config_flow = tripwire  # type: ignore[attr-defined]

    with pytest.raises(ZHAFormationRefused):
        await recipe.apply(sim)


@pytest.mark.asyncio
async def test_engine_never_applies_zha_over_a_loaded_entry(sim):
    sim.state["config_entries"].append(_loaded_zha_entry())
    script = ZHAFlowScript(sim.state)
    sim.rest = script  # type: ignore[assignment]
    agent = HAInitAgent([ZHARecipe(ZHA_PATH)])

    async def backup(_label: str) -> None:
        return None

    report = await agent.apply(sim, only="integrations.zha", backup=backup)

    assert report.total_changes == 0
    assert [c for c in script.calls if c[0] == "start"] == [], (
        "engine must not open a config flow when the entry is already loaded"
    )


@pytest.mark.asyncio
async def test_zha_apply_forms_network_on_a_fresh_instance(sim):
    script = ZHAFlowScript(sim.state)
    sim.rest = script  # type: ignore[assignment]
    recipe = ZHARecipe(ZHA_PATH, formation_timeout=5.0, poll_interval=0.0)

    result = await recipe.apply(sim)

    assert result.change_count == 1
    assert ("start", "zha") in script.calls
    # The progress step was polled with empty POSTs, never raised as a gate.
    assert [c for c in script.calls if c[1] == {}][0][0] == "advance"
    verified = await recipe.verify(sim)
    assert verified.ok, verified.summary
