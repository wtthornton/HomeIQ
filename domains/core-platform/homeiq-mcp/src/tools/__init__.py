"""Tool handlers, one module per catalogue group. `register_all` wires every group."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backends import Backings
    from ..registry import ToolRegistry


def register_all(registry: ToolRegistry, backings: Backings) -> None:
    # Groups land per story: TAP-5294 (history/events/devices/entities/areas/state/stats/anomalies),
    # TAP-5295 (patterns/synergies/energy summary/device health).
    del registry, backings
