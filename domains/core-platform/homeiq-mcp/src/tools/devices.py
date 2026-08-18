"""Group 2 — devices, entities, areas and automation stats (data-api).

data-api wraps its lists: `/api/devices` → `{devices, count, limit}`,
`/api/entities` → `{entities, count, limit}`, `/api/areas` → `{areas, count}`,
`/api/entities/by-device/{id}` → `{entities, count, ...}`, and the
`/api/v1/automations*` routes → `{count, automations}`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..budget import cap_rows
from ..errors import ToolError
from .projection import expect_list, listing, path_segment, present, require

if TYPE_CHECKING:
    from ..backends import Backings
    from ..registry import ToolRegistry

_DEVICE_OPTIONAL = ("manufacturer", "model", "area_id", "integration")
_ENTITY_OPTIONAL = ("device_id", "area_id", "friendly_name", "device_class")
_AUTOMATION_OPTIONAL = ("alias", "success_rate", "avg_duration_seconds", "last_triggered")
_STATS_PATHS = {
    "list": "/api/v1/automations",
    "errors": "/api/v1/automations/stats/errors",
    "slow": "/api/v1/automations/stats/slow",
    "inactive": "/api/v1/automations/stats/inactive",
}


def _entity(row: dict[str, Any], *, tool: str) -> dict[str, Any]:
    core = require(row, ("entity_id", "domain"), tool=tool)
    return {**core, "disabled": bool(row.get("disabled", False)), **present(row, ("device_class",))}


def _automation(row: dict[str, Any], *, tool: str) -> dict[str, Any]:
    core = require(row, ("automation_id",), tool=tool)
    return {
        **core,
        "enabled": bool(row.get("enabled", True)),
        "total_executions": int(row.get("total_executions") or 0),
        "total_errors": int(row.get("total_errors") or 0),
        **present(row, _AUTOMATION_OPTIONAL),
    }


def register(registry: ToolRegistry, backings: Backings) -> None:
    data_api = backings.data_api

    @registry.register("list_devices", narrow_hint="limit")
    async def list_devices(args: dict[str, Any]) -> dict[str, Any]:
        tool = "list_devices"
        params = {
            "limit": args.get("limit", 100),
            **present(args, ("manufacturer", "model", "area_id", "platform", "device_category")),
        }
        rows = expect_list(
            await data_api.get_json("/api/devices", params, tool=tool), tool=tool, key="devices"
        )
        devices = [
            {
                **require(r, ("device_id", "name"), tool=tool),
                "entity_count": int(r.get("entity_count") or 0),
                **present(r, _DEVICE_OPTIONAL),
            }
            for r in rows
        ]
        return listing("devices", devices, 300, "limit")

    def _recount_device(payload: dict[str, Any]) -> None:
        payload["entity_count"] = len(payload["entities"])

    @registry.register("get_device", narrow_hint=None, recount=_recount_device)
    async def get_device(args: dict[str, Any]) -> dict[str, Any]:
        tool = "get_device"
        device_id = path_segment(args["device_id"], tool=tool, name="device_id")
        row = await data_api.get_json(f"/api/devices/{device_id}", tool=tool)
        if not isinstance(row, dict):
            raise ToolError("contract_violation", "device backing returned a non-object", tool=tool)
        entities_payload = await data_api.get_json(
            f"/api/entities/by-device/{device_id}", tool=tool
        )
        rows = expect_list(entities_payload, tool=tool, key="entities")
        entities = [_entity(r, tool=tool) for r in rows]
        device = {
            **require(row, ("device_id", "name"), tool=tool),
            **present(row, (*_DEVICE_OPTIONAL, "sw_version", "labels")),
        }
        entities, capped = cap_rows(entities, 500)
        out = {
            "device": device,
            "entities": entities,
            "entity_count": len(entities),
            "truncated": capped,
        }
        if capped:
            out["hint"] = "device_id"
        return out

    @registry.register("list_entities", narrow_hint="limit")
    async def list_entities(args: dict[str, Any]) -> dict[str, Any]:
        tool = "list_entities"
        params = {
            "limit": args.get("limit", 200),
            **present(args, ("domain", "area_id", "device_id", "label")),
        }
        rows = expect_list(
            await data_api.get_json("/api/entities", params, tool=tool), tool=tool, key="entities"
        )
        entities = [{**_entity(r, tool=tool), **present(r, _ENTITY_OPTIONAL)} for r in rows]
        return listing("entities", entities, 500, "limit")

    @registry.register("list_areas", narrow_hint=None)
    async def list_areas(_args: dict[str, Any]) -> dict[str, Any]:
        tool = "list_areas"
        rows = expect_list(await data_api.get_json("/api/areas", tool=tool), tool=tool, key="areas")
        areas = [
            {
                "area_id": require(r, ("area_id",), tool=tool)["area_id"],
                "name": r.get("display_name") or r.get("name") or r["area_id"],
                "entity_count": int(r.get("entity_count") or 0),
                "domains": list(r.get("domains") or []),
            }
            for r in rows
        ]
        return listing("areas", areas, 100, None)

    @registry.register("get_automation_stats", narrow_hint="limit")
    async def get_automation_stats(args: dict[str, Any]) -> dict[str, Any]:
        tool = "get_automation_stats"
        view = args.get("view", "overview")
        if view == "overview":
            row = await data_api.get_json("/api/v1/automations/stats/overview", tool=tool)
            if not isinstance(row, dict):
                raise ToolError(
                    "contract_violation", "overview backing returned a non-object", tool=tool
                )
            return {
                "view": view,
                "overview": {
                    "total_automations": int(row.get("total_automations") or 0),
                    "total_executions": int(row.get("total_executions") or 0),
                    "error_rate_percent": float(row.get("error_rate_percent") or 0),
                    "avg_success_rate": float(row.get("avg_success_rate") or 0),
                },
                "truncated": False,
            }
        limit = args.get("limit", 25)
        if args.get("automation_id"):
            automation_id = path_segment(args["automation_id"], tool=tool, name="automation_id")
            row = await data_api.get_json(f"/api/v1/automations/{automation_id}", tool=tool)
            rows = [row] if isinstance(row, dict) else expect_list(row, tool=tool)
        else:
            payload = await data_api.get_json(_STATS_PATHS[view], {"limit": limit}, tool=tool)
            # stats/inactive ignores limit upstream; apply it here for every view.
            rows = expect_list(payload, tool=tool, key="automations")[:limit]
        return {
            **listing("automations", [_automation(r, tool=tool) for r in rows], 100, "limit"),
            "view": view,
        }
