"""Behavioural regression tests for the Office presence lighting automation.

Why these exist
---------------
On 2026-08-18 the office lights stopped responding to presence. The automation
was enabled, the group was correctly fused from a real mmWave sensor and a Hue
PIR, every entity resolved, and the YAML was valid. It still never fired.

The trigger read ``from: "off", to: "on"``. A binary_sensor group passes through
``unavailable`` whenever it is recreated, an integration reloads, Home Assistant
restarts, or a battery member drops off the mesh -- and the office FP300 is a
sleepy Zigbee device that flapped four times in two minutes. Presence returning
therefore arrived as ``unavailable -> on``, which does not match ``from: "off"``,
so the automation silently did nothing.

No linter could have caught that: the automation was referentially valid and
schema-valid. The defect lived in a *sequence* of states. These tests execute
the automation against synthetic state, which is the only thing that reaches it.

The first fix that comes up when searching is ``not_from: [unavailable,
unknown]``. It is wrong -- it excludes the exact transition that was broken --
and :func:`test_not_from_is_the_wrong_fix` exists to stop anyone reintroducing
it.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.components import automation
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_fire_time_changed

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

GROUP = "binary_sensor.office_presence_group"
ROOM = "light.office_office"
CLEAR_DELAY = "00:05:00"


def _automation(trigger_overrides: dict[str, Any] | None = None) -> dict:
    """The deployed Office Presence Lighting automation.

    Mirrors the live config: two triggers distinguished by ``id``, dispatched
    through a ``choose``. ``trigger_overrides`` patches only the presence-on
    trigger so a test can pin the historical shape.
    """
    presence_on: dict[str, Any] = {
        "trigger": "state",
        "entity_id": GROUP,
        "to": "on",
        "id": "presence_on",
    }
    presence_on.update(trigger_overrides or {})
    return {
        automation.DOMAIN: {
            "alias": "Office Presence Lighting",
            "triggers": [
                presence_on,
                {
                    "trigger": "state",
                    "entity_id": GROUP,
                    "to": "off",
                    "for": CLEAR_DELAY,
                    "id": "presence_clear",
                },
            ],
            "conditions": [],
            "actions": [
                {
                    "choose": [
                        {
                            "conditions": [
                                {"condition": "trigger", "id": "presence_on"}
                            ],
                            "sequence": [
                                {
                                    "action": "light.turn_on",
                                    "target": {"entity_id": ROOM},
                                }
                            ],
                        },
                        {
                            "conditions": [
                                {"condition": "trigger", "id": "presence_clear"}
                            ],
                            "sequence": [
                                {
                                    "action": "light.turn_off",
                                    "target": {"entity_id": ROOM},
                                }
                            ],
                        },
                    ]
                }
            ],
            "mode": "restart",
        }
    }


async def _load(hass: HomeAssistant, cfg: dict) -> None:
    assert await async_setup_component(hass, automation.DOMAIN, cfg)
    await hass.async_block_till_done()


async def _set(hass: HomeAssistant, state: str) -> None:
    hass.states.async_set(GROUP, state)
    await hass.async_block_till_done()


# --- the regression -------------------------------------------------------


@pytest.mark.parametrize("prior", ["off", STATE_UNAVAILABLE, STATE_UNKNOWN])
async def test_presence_lights_the_room_from_every_prior_state(
    hass: HomeAssistant, light_on: list, prior: str
) -> None:
    """The deployed trigger fires no matter what the group was before.

    ``unavailable`` is the case that was broken in production; ``unknown``
    covers a freshly created entity, which is what a restart produces.
    """
    await _set(hass, prior)
    await _load(hass, _automation())

    await _set(hass, "on")

    assert len(light_on) == 1, f"presence from {prior!r} did not light the room"
    assert light_on[0].data["entity_id"] == [ROOM]


async def test_historical_from_off_trigger_misses_unavailable(
    hass: HomeAssistant, light_on: list
) -> None:
    """Pin the original defect so its shape stays recognisable.

    This asserts the *broken* behaviour on purpose. If Home Assistant ever
    changes `from:` matching so this fires, the assertion fails loudly and the
    comment above it stops being true -- which is exactly when someone should
    re-read this file.
    """
    await _set(hass, STATE_UNAVAILABLE)
    await _load(hass, _automation({"from": "off"}))

    await _set(hass, "on")

    assert len(light_on) == 0


async def test_not_from_is_the_wrong_fix(hass: HomeAssistant, light_on: list) -> None:
    """``not_from: [unavailable, unknown]`` reintroduces the bug.

    It is the fix most commonly suggested for a trigger that misfires on
    restart, and it excludes precisely the transition that was broken here.
    """
    await _set(hass, STATE_UNAVAILABLE)
    await _load(
        hass, _automation({"not_from": [STATE_UNAVAILABLE, STATE_UNKNOWN]})
    )

    await _set(hass, "on")

    assert len(light_on) == 0, "not_from would have masked the original defect"


# --- the clear branch -----------------------------------------------------


async def test_room_goes_dark_after_the_clear_delay(
    hass: HomeAssistant, light_off: list, freezer
) -> None:
    """Five minutes of continuous vacancy turns the room off."""
    await _set(hass, "on")
    await _load(hass, _automation())

    await _set(hass, "off")
    assert len(light_off) == 0, "turned off before the delay elapsed"

    freezer.tick(timedelta(minutes=5, seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert len(light_off) == 1
    assert light_off[0].data["entity_id"] == [ROOM]


async def test_returning_presence_cancels_the_clear_timer(
    hass: HomeAssistant, light_off: list, freezer
) -> None:
    """Walking back in before the delay elapses must not leave the room dark."""
    await _set(hass, "on")
    await _load(hass, _automation())

    await _set(hass, "off")
    freezer.tick(timedelta(minutes=2))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    await _set(hass, "on")  # back in the room

    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert len(light_off) == 0, "stale timer turned the light off on an occupant"


async def test_sensor_dropout_does_not_darken_an_occupied_room(
    hass: HomeAssistant, light_off: list, freezer
) -> None:
    """A sleepy Zigbee sensor going unavailable is not the same as vacancy.

    The FP300 flapped four times in two minutes on the live mesh. Treating
    ``unavailable`` as ``off`` would switch the light off on someone sitting
    still, which is the failure the clear delay exists to prevent.
    """
    await _set(hass, "on")
    await _load(hass, _automation())

    await _set(hass, STATE_UNAVAILABLE)

    freezer.tick(timedelta(minutes=6))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert len(light_off) == 0, "an unavailable sensor was treated as vacancy"
