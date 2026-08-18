"""Group 5 (part) — anomaly detection over two backings.

- `power`: data-api `GET /api/devices/power-anomalies` → `{anomalies: [{device_id, spec_power_w,
  actual_power_w, severity, timestamp, ...}]}` (route un-shadowed by TAP-6071).
- `failure_risk`: device-intelligence `GET /api/predictions/failures` → `{predictions: [{device_id,
  failure_probability (PERCENT 0-100), risk_level, recommendations: [...]}]}`; projected to a 0-1
  probability and the first recommendation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..budget import cap_rows
from .projection import expect_list, present, require, rfc3339

if TYPE_CHECKING:
    from ..backends import Backings
    from ..registry import ToolRegistry

TOOL = "detect_anomalies"


def _power_row(row: dict[str, Any]) -> dict[str, Any]:
    core = require(row, ("device_id", "actual_power_w", "severity", "timestamp"), tool=TOOL)
    out = {
        "entity_id": str(core["device_id"]),
        "t": rfc3339(core["timestamp"]),
        "observed_w": float(core["actual_power_w"]),
        "severity": str(core["severity"]),
    }
    if row.get("spec_power_w") is not None:
        out["expected_w"] = float(row["spec_power_w"])
    return out


def _prediction_row(row: dict[str, Any]) -> dict[str, Any]:
    core = require(row, ("device_id", "failure_probability", "risk_level"), tool=TOOL)
    recommendations = row.get("recommendations") or []
    return {
        "device_id": str(core["device_id"]),
        "failure_probability": round(float(core["failure_probability"]) / 100, 4),
        "risk_level": str(core["risk_level"]),
        "top_recommendation": str(recommendations[0]) if recommendations else None,
    }


async def _power(backings: Backings, limit: int) -> list[dict[str, Any]]:
    payload = await backings.data_api.get_json(
        "/api/devices/power-anomalies", {"limit": limit}, tool=TOOL
    )
    return [_power_row(r) for r in expect_list(payload, tool=TOOL, key="anomalies")]


async def _failures(backings: Backings, args: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    params = {"min_probability": args.get("min_probability", 0.5), **present(args, ("risk_level",))}
    payload = await backings.device_intelligence.get_json(
        "/api/predictions/failures", params, tool=TOOL
    )
    rows = [_prediction_row(r) for r in expect_list(payload, tool=TOOL, key="predictions")]
    return rows[:limit]


def _recount(payload: dict[str, Any]) -> None:
    payload["counts"] = {
        "power": len(payload.get("power_anomalies", [])),
        "failure_risk": len(payload.get("failure_predictions", [])),
    }


def register(registry: ToolRegistry, backings: Backings) -> None:
    @registry.register(TOOL, narrow_hint="limit", recount=_recount)
    async def detect_anomalies(args: dict[str, Any]) -> dict[str, Any]:
        kind = args.get("kind", "all")
        limit = args.get("limit", 50)
        out: dict[str, Any] = {"counts": {"power": 0, "failure_risk": 0}, "truncated": False}
        if kind in ("power", "all"):
            rows, capped = cap_rows(await _power(backings, limit), 100)
            out["power_anomalies"], out["counts"]["power"] = rows, len(rows)
            out["truncated"] |= capped
        if kind in ("failure_risk", "all"):
            rows, capped = cap_rows(await _failures(backings, args, limit), 100)
            out["failure_predictions"], out["counts"]["failure_risk"] = rows, len(rows)
            out["truncated"] |= capped
        if out["truncated"]:
            out["hint"] = "limit"
        return out
