"""Group 6 — room presence roll-up (websocket-ingestion's house-status API, TAP-7588).

The backing has no per-area endpoint: `GET /api/status/rooms` returns every
area known to data-api in one roll-up (TAP-7587), so this tool fetches the
whole list and picks out the requested `area_id`. An id absent from that list
is genuinely unknown — the backing already unions data-api's area registry
with every area a presence sensor has ever reported for — so it is a
`not_found` refusal, never a fabricated or empty room.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..errors import ToolError
from .projection import expect_list, require

if TYPE_CHECKING:
    from ..backends import Backings
    from ..registry import ToolRegistry


def register(registry: ToolRegistry, backings: Backings) -> None:
    house_status = backings.house_status

    @registry.register("get_room_occupancy", narrow_hint=None)
    async def get_room_occupancy(args: dict[str, Any]) -> dict[str, Any]:
        tool = "get_room_occupancy"
        area_id = args["area_id"]
        payload = await house_status.get_json("/api/status/rooms", tool=tool)
        rows = expect_list(payload, tool=tool, key="rooms")
        for row in rows:
            if row.get("area_id") != area_id:
                continue
            core = require(row, ("area_id", "state"), tool=tool)
            return {
                **core,
                "contributing_entity_ids": list(row.get("contributing_entity_ids") or []),
                "last_changed": str(row.get("last_changed") or ""),
                "truncated": False,
            }
        raise ToolError("not_found", f"unknown area_id {area_id!r}", tool=tool)
