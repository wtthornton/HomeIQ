"""Fixtures for behavioural automation tests.

These run a real Home Assistant core in-process via
``pytest-homeassistant-custom-component``, which pins the exact HA release the
live instance runs. They need no Home Assistant instance, no network and no
hardware: a full boot plus a dozen scenarios completes in under a second.

Unlike the rest of the suite these tests execute the automation rather than
inspecting its YAML, which is the only way to reach defects that live in a
*sequence* of states rather than in the document.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@pytest.fixture
def light_on(hass: HomeAssistant) -> list:
    """Capture and intercept ``light.turn_on`` calls."""
    return async_mock_service(hass, "light", "turn_on")


@pytest.fixture
def light_off(hass: HomeAssistant) -> list:
    """Capture and intercept ``light.turn_off`` calls."""
    return async_mock_service(hass, "light", "turn_off")


@pytest.fixture
def fan_off(hass: HomeAssistant) -> list:
    """Capture and intercept ``fan.turn_off`` calls."""
    return async_mock_service(hass, "fan", "turn_off")
