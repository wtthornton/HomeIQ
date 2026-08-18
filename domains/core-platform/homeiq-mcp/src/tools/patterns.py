"""Group 3 — pattern detection (ai-pattern-service `/api/v1/patterns/*`, `/api/v1/synergies/*`).

Both list routes answer `{success, data: {patterns|synergies: [...], count}}`; the stats
routes answer `{success, data: {...}}`. The synergy list route has no `area` filter, so
`area` is applied here after the fetch.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from ..errors import ToolError
from .projection import expect_list, listing, present, require

if TYPE_CHECKING:
    from ..backends import Backings
    from ..registry import ToolRegistry


def _data(payload: Any, *, tool: str) -> dict[str, Any]:
    if (
        not isinstance(payload, dict)
        or not payload.get("success")
        or not isinstance(payload.get("data"), dict)
    ):
        raise ToolError(
            "contract_violation", "ai-pattern-service did not return a success envelope", tool=tool
        )
    return payload["data"]


def _text(value: Any, limit: int) -> str:
    """Bound a free-text field; upstream JSON columns may yield dicts/lists."""
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False)
    return value[:limit]


def _pattern(row: dict[str, Any], *, tool: str) -> dict[str, Any]:
    core = require(row, ("id", "pattern_type", "confidence", "occurrences"), tool=tool)
    metadata = row.get("metadata") or {}
    summary = metadata.get("summary") if isinstance(metadata, dict) else None
    return {
        "id": int(core["id"]),
        "pattern_type": str(core["pattern_type"]),
        "device_id": row.get("device_id"),
        "confidence": float(core["confidence"]),
        "occurrences": int(core["occurrences"]),
        "summary": _text(
            summary or f"{core['pattern_type']}: {core['occurrences']} occurrences", 255
        ),
    }


def _synergy(row: dict[str, Any], *, tool: str) -> dict[str, Any]:
    core = require(row, ("synergy_id", "synergy_type"), tool=tool)
    out = {
        "synergy_id": str(core["synergy_id"]),
        "synergy_type": str(core["synergy_type"]),
        "devices": [str(d) for d in (row.get("devices") or row.get("device_ids") or [])],
        "impact_score": float(row.get("impact_score") or 0.0),
        "confidence": float(row.get("confidence") or 0.0),
        **present(row, ("area", "complexity")),
    }
    explanation = row.get("explanation")
    if explanation not in (None, "", {}, []):
        out["explanation"] = _text(explanation, 1000)
    return out


def register(registry: ToolRegistry, backings: Backings) -> None:
    patterns = backings.patterns

    @registry.register("list_patterns", narrow_hint="limit")
    async def list_patterns(args: dict[str, Any]) -> dict[str, Any]:
        tool = "list_patterns"
        params = {
            "min_confidence": args.get("min_confidence", 0.5),
            "limit": args.get("limit", 50),
            **present(args, ("pattern_type", "device_id")),
        }
        rows = expect_list(
            _data(await patterns.get_json("/api/v1/patterns/list", params, tool=tool), tool=tool),
            tool=tool,
            key="patterns",
        )
        stats = _data(await patterns.get_json("/api/v1/patterns/stats", tool=tool), tool=tool)
        return listing(
            "patterns",
            [_pattern(r, tool=tool) for r in rows],
            100,
            "limit",
            stats={
                "total_patterns": int(stats.get("total_patterns") or 0),
                "avg_confidence": float(stats.get("avg_confidence") or 0.0),
                **present(stats, ("by_type", "unique_devices")),
            },
        )

    @registry.register("list_synergies", narrow_hint="limit")
    async def list_synergies(args: dict[str, Any]) -> dict[str, Any]:
        tool = "list_synergies"
        params = {
            "min_confidence": args.get("min_confidence", 0.5),
            "limit": args.get("limit", 20),
            **present(args, ("synergy_type",)),
        }
        rows = expect_list(
            _data(await patterns.get_json("/api/v1/synergies/list", params, tool=tool), tool=tool),
            tool=tool,
            key="synergies",
        )
        synergies = [_synergy(r, tool=tool) for r in rows]
        if args.get("area"):
            synergies = [s for s in synergies if s.get("area") == args["area"]]
        stats = _data(await patterns.get_json("/api/v1/synergies/statistics", tool=tool), tool=tool)
        return listing(
            "synergies",
            synergies,
            50,
            "limit",
            stats={
                "total_synergies": int(stats.get("total_synergies") or 0),
                **{
                    k: float(stats[k])
                    for k in ("avg_impact_score", "avg_confidence")
                    if stats.get(k) is not None
                },
            },
        )
