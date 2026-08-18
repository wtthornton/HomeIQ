"""Group 1 — entity history & events (data-api `/api/v1/events*`).

data-api's `/api/v1/events` takes `start_time`/`end_time`, so the trailing
`hours` window is derived here; it has no downsampling, so
`downsample_minutes` is applied locally (first observed point per bucket).
History and state tools ask for `event_type=state_changed` only, and skip the
rare state_changed row without a new_state (HA emits one when an entity is
removed) so a single such row cannot fail the whole call.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from .projection import (
    expect_list,
    listing,
    path_segment,
    present,
    require,
    rfc3339,
    state_string,
    window,
)

if TYPE_CHECKING:
    from ..backends import Backings
    from ..registry import ToolRegistry

EVENTS = "/api/v1/events"


def _event_row(row: dict[str, Any], *, tool: str) -> dict[str, Any]:
    core = require(row, ("timestamp", "entity_id", "event_type"), tool=tool)
    out = {
        "t": rfc3339(core["timestamp"]),
        "entity_id": core["entity_id"],
        "event_type": core["event_type"],
    }
    for key in ("old_state", "new_state"):
        projected = state_string(row.get(key))
        if projected is not None:
            out[key] = projected
    return out


def _downsample(points: list[dict[str, Any]], minutes: int) -> list[dict[str, Any]]:
    if minutes <= 0:
        return points
    bucket_seconds = minutes * 60
    kept: list[dict[str, Any]] = []
    last_bucket: int | None = None
    for point in points:
        bucket = int(datetime.fromisoformat(point["t"]).timestamp() // bucket_seconds)
        if bucket != last_bucket:
            kept.append(point)
            last_bucket = bucket
    return kept


def register(registry: ToolRegistry, backings: Backings) -> None:
    data_api = backings.data_api

    @registry.register("get_entity_history", narrow_hint="hours")
    async def get_entity_history(args: dict[str, Any]) -> dict[str, Any]:
        tool = "get_entity_history"
        params: dict[str, Any] = {
            "entity_id": args["entity_id"],
            "event_type": "state_changed",
            "limit": args.get("limit", 500),
        }
        if args.get("start_time") and args.get("end_time"):
            params["start_time"], params["end_time"] = args["start_time"], args["end_time"]
        else:
            params["start_time"], params["end_time"] = window(args.get("hours", 24))
        rows = expect_list(await data_api.get_json(EVENTS, params, tool=tool), tool=tool)
        points = []
        for row in rows:
            state = state_string(row.get("new_state"))
            if state is None:
                continue
            core = require(row, ("timestamp",), tool=tool)
            points.append({"t": rfc3339(core["timestamp"]), "state": state})
        points = _downsample(points, args.get("downsample_minutes", 0))
        return listing("points", points, 500, "hours", entity_id=args["entity_id"])

    @registry.register("search_events", narrow_hint="limit")
    async def search_events(args: dict[str, Any]) -> dict[str, Any]:
        tool = "search_events"
        body = {
            "query": args["query"],
            "hours": args.get("hours", 24),
            "limit": args.get("limit", 50),
        }
        rows = expect_list(await data_api.post_json(f"{EVENTS}/search", body, tool=tool), tool=tool)
        return listing("events", [_event_row(r, tool=tool) for r in rows], 200, "limit")

    @registry.register("get_recent_events", narrow_hint="limit")
    async def get_recent_events(args: dict[str, Any]) -> dict[str, Any]:
        tool = "get_recent_events"
        start, end = window(args.get("hours", 1))
        params = {
            "limit": args.get("limit", 50),
            "offset": args.get("offset", 0),
            "start_time": start,
            "end_time": end,
            **present(args, ("entity_id", "event_type", "device_id", "area_id")),
        }
        rows = expect_list(await data_api.get_json(EVENTS, params, tool=tool), tool=tool)
        return listing(
            "events",
            [_event_row(r, tool=tool) for r in rows],
            200,
            "limit",
            offset=params["offset"],
        )

    @registry.register("trace_automation", narrow_hint="max_depth")
    async def trace_automation(args: dict[str, Any]) -> dict[str, Any]:
        tool = "trace_automation"
        max_depth = args.get("max_depth", 5)
        context_id = path_segment(args["context_id"], tool=tool, name="context_id")
        rows = expect_list(
            await data_api.get_json(
                f"{EVENTS}/automation-trace/{context_id}", {"max_depth": max_depth}, tool=tool
            ),
            tool=tool,
        )
        chain = []
        for row in rows:
            core = require(
                row, ("depth", "context_id", "timestamp", "entity_id", "event_type"), tool=tool
            )
            if int(core["depth"]) > max_depth:
                continue
            timestamp = core.pop("timestamp")
            item = {**core, "t": rfc3339(timestamp)}
            state = state_string(row.get("state"))
            if state is not None:
                item["state"] = state
            chain.append(item)
        # max_depth bounds chain LEVELS (upstream returns up to 100 events per level); the
        # byte budget, not a row cap, bounds the size — hint still names max_depth.
        return listing("chain", chain, 1000, "max_depth")

    @registry.register("get_entity_state")
    async def get_entity_state(args: dict[str, Any]) -> dict[str, Any]:
        tool = "get_entity_state"
        start, end = window(args.get("hours", 24))
        params = {
            "entity_id": args["entity_id"],
            "event_type": "state_changed",
            "limit": 1,
            "start_time": start,
            "end_time": end,
        }
        rows = expect_list(await data_api.get_json(EVENTS, params, tool=tool), tool=tool)
        newest = rows[0] if rows else None
        return {
            "entity_id": args["entity_id"],
            "state": state_string(newest.get("new_state")) if newest else None,
            "t": rfc3339(newest["timestamp"]) if newest and newest.get("timestamp") else None,
            "source": "last_observed_event",
        }
