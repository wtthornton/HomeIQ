"""Tool handlers, one module per catalogue group. `register_all` wires every group."""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import anomalies, device_health, devices, energy, history, patterns

if TYPE_CHECKING:
    from ..backends import Backings
    from ..registry import ToolRegistry

_GROUPS = (history, devices, anomalies, patterns, energy, device_health)


def register_all(registry: ToolRegistry, backings: Backings) -> None:
    for group in _GROUPS:
        group.register(registry, backings)
