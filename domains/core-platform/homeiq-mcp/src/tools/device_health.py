"""Group 5 (part) — device health from device-intelligence-service.

- fleet: `GET /api/health/scores?skip&limit&min_score&health_status` →
  `{health_scores: [{device_id, overall_score, health_status, factor_scores, ...}], summary, ...}`
- one device: `GET /api/health/scores/{id}` (same row shape) and, on request,
  `GET /api/health/trends/{id}?days` → `{trends: [{timestamp, overall_score, ...}], ...}`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..errors import ToolError
from .projection import expect_list, listing, path_segment, present, require, rfc3339

if TYPE_CHECKING:
    from ..backends import Backings
    from ..registry import ToolRegistry

TOOL = "get_device_health"
STATUSES = ("healthy", "degraded", "critical")


def _score_row(row: dict[str, Any]) -> dict[str, Any]:
    core = require(row, ("device_id", "overall_score", "health_status"), tool=TOOL)
    return {**core, "overall_score": float(core["overall_score"])}


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [r["overall_score"] for r in rows]
    summary: dict[str, Any] = {
        "total": len(rows),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0.0,
    }
    for status in STATUSES:
        summary[status] = sum(1 for r in rows if r["health_status"] == status)
    return summary


async def _trend(backings: Backings, device_id: str, days: int) -> list[dict[str, Any]]:
    payload = await backings.device_intelligence.get_json(
        f"/api/health/trends/{path_segment(device_id, tool=TOOL, name='device_id')}",
        {"days": days},
        tool=TOOL,
    )
    points = []
    for row in expect_list(payload, tool=TOOL, key="trends"):
        core = require(row, ("timestamp", "overall_score"), tool=TOOL)
        points.append({"t": rfc3339(core["timestamp"]), "score": float(core["overall_score"])})
    return points[-30:]


def _recount(payload: dict[str, Any]) -> None:
    if "devices" in payload:
        payload["summary"] = _summary(payload["devices"])


def register(registry: ToolRegistry, backings: Backings) -> None:
    @registry.register(TOOL, narrow_hint="limit", recount=_recount)
    async def get_device_health(args: dict[str, Any]) -> dict[str, Any]:
        device_id = args.get("device_id")
        if device_id:
            safe_id = path_segment(device_id, tool=TOOL, name="device_id")
            row = await backings.device_intelligence.get_json(
                f"/api/health/scores/{safe_id}", tool=TOOL
            )
            if not isinstance(row, dict):
                raise ToolError(
                    "contract_violation", "health backing returned a non-object", tool=TOOL
                )
            device = {**_score_row(row), **present(row, ("factor_scores",))}
            if args.get("include_trend", False):
                device["trend"] = await _trend(backings, device_id, args.get("trend_days", 7))
            return {"device": device, "truncated": False}

        params = {
            "skip": 0,
            "limit": args.get("limit", 50),
            **present(args, ("min_score", "health_status")),
        }
        payload = await backings.device_intelligence.get_json(
            "/api/health/scores", params, tool=TOOL
        )
        rows = [_score_row(r) for r in expect_list(payload, tool=TOOL, key="health_scores")]
        return {**listing("devices", rows, 100, "limit", count=False), "summary": _summary(rows)}
