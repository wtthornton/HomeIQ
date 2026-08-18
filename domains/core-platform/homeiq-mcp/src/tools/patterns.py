"""Tool handlers for pattern detection and synergy analysis (TAP-5295)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..budget import cap_rows
from ..errors import ToolError

if TYPE_CHECKING:
    from ..backends import Backings
    from ..registry import ToolRegistry


async def _list_patterns_handler(args: dict[str, Any]) -> dict[str, Any]:
    """
    List detected behavioral patterns with confidence filters; stats rollup included.
    """
    handler = _list_patterns_handler
    backings = handler._backings  # type: ignore[union-attr]

    params = {
        "pattern_type": args.get("pattern_type"),
        "device_id": args.get("device_id"),
        "min_confidence": args.get("min_confidence", 0.5),
        "limit": args.get("limit", 50),
    }

    try:
        # Call patterns endpoint
        patterns_resp = await backings.patterns.get_json(
            "/api/v1/patterns/list", params=params, tool="list_patterns"
        )
        stats_resp = await backings.patterns.get_json(
            "/api/v1/patterns/stats", params={}, tool="list_patterns"
        )
    except ToolError:
        raise

    # Extract patterns from the success response
    if not patterns_resp.get("success"):
        raise ToolError(
            "contract_violation",
            "Upstream patterns endpoint returned success=false",
            tool="list_patterns",
        )

    patterns_data = patterns_resp.get("data", {})
    upstream_patterns = patterns_data.get("patterns", [])

    # Extract stats
    if not stats_resp.get("success"):
        raise ToolError(
            "contract_violation",
            "Upstream patterns/stats endpoint returned success=false",
            tool="list_patterns",
        )
    stats_data = stats_resp.get("data", {})

    # Project patterns: extract summary from metadata
    projected_patterns = []
    for p in upstream_patterns:
        metadata = p.get("metadata", {})
        summary = metadata.get("summary", "")
        if not summary and metadata:
            # Build a basic summary if not present
            summary = f"{p.get('pattern_type', 'unknown')}: {p.get('occurrences', 0)} occurrences"

        projected_patterns.append(
            {
                "id": p.get("id"),
                "pattern_type": p.get("pattern_type"),
                "device_id": p.get("device_id"),
                "confidence": p.get("confidence", 0),
                "occurrences": p.get("occurrences", 0),
                "summary": summary[:255],  # Max 255 chars
            }
        )

    # Apply row cap
    capped_patterns, was_capped = cap_rows(projected_patterns, 100)

    # Build stats object from upstream stats
    stats_output = {
        "total_patterns": stats_data.get("total_patterns", 0),
        "avg_confidence": stats_data.get("avg_confidence", 0.0),
    }

    # Add optional fields if present
    by_type = stats_data.get("by_type", {})
    if by_type:
        stats_output["by_type"] = by_type

    unique_devices = stats_data.get("unique_devices")
    if unique_devices is not None:
        stats_output["unique_devices"] = unique_devices

    return {
        "patterns": capped_patterns,
        "stats": stats_output,
        "count": len(capped_patterns),
        "truncated": was_capped,
    }


async def _list_synergies_handler(args: dict[str, Any]) -> dict[str, Any]:
    """
    Cross-device automation opportunities (rule-based graph analysis).
    """
    handler = _list_synergies_handler
    backings = handler._backings  # type: ignore[union-attr]

    params = {
        "synergy_type": args.get("synergy_type"),
        "min_confidence": args.get("min_confidence", 0.5),
        "area": args.get("area"),
        "limit": args.get("limit", 20),
    }

    try:
        # Call synergies list endpoint
        synergies_resp = await backings.patterns.get_json(
            "/api/v1/synergies/list", params=params, tool="list_synergies"
        )
        stats_resp = await backings.patterns.get_json(
            "/api/v1/synergies/statistics", params={}, tool="list_synergies"
        )
    except ToolError:
        raise

    # Extract synergies from the success response
    if not synergies_resp.get("success"):
        raise ToolError(
            "contract_violation",
            "Upstream synergies endpoint returned success=false",
            tool="list_synergies",
        )

    synergies_data = synergies_resp.get("data", {})
    upstream_synergies = synergies_data.get("synergies", [])

    # Extract stats
    if not stats_resp.get("success"):
        raise ToolError(
            "contract_violation",
            "Upstream synergies/statistics endpoint returned success=false",
            tool="list_synergies",
        )
    stats_data = stats_resp.get("data", {})

    # Project synergies: extract required fields, default optional ones
    projected_synergies = []
    for s in upstream_synergies:
        synergy_obj = {
            "synergy_id": s.get("synergy_id", f"synergy_{s.get('id')}"),
            "synergy_type": s.get("synergy_type"),
            "devices": s.get("device_ids", s.get("devices", [])),
            "impact_score": s.get("impact_score", 0),
            "confidence": s.get("confidence", 0),
        }

        # Optional fields
        if "area" in s and s["area"]:
            synergy_obj["area"] = s["area"]

        # complexity can be string or int; keep as-is
        if "complexity" in s:
            synergy_obj["complexity"] = s["complexity"]

        # Explanation
        explanation = s.get("explanation", "")
        if not explanation:
            explanation = (
                f"{s.get('synergy_type', 'synergy')}: impact score {s.get('impact_score', 0)}"
            )
        synergy_obj["explanation"] = explanation[:1000]

        projected_synergies.append(synergy_obj)

    # Apply row cap
    capped_synergies, was_capped = cap_rows(projected_synergies, 50)

    # Build stats object from upstream stats
    stats_output = {
        "total_synergies": stats_data.get("total_synergies", 0),
    }

    # Add optional fields if present
    avg_impact = stats_data.get("avg_impact_score")
    if avg_impact is not None:
        stats_output["avg_impact_score"] = float(avg_impact)

    avg_confidence = stats_data.get("avg_confidence")
    if avg_confidence is not None:
        stats_output["avg_confidence"] = float(avg_confidence)

    return {
        "synergies": capped_synergies,
        "stats": stats_output,
        "count": len(capped_synergies),
        "truncated": was_capped,
    }


def register(registry: ToolRegistry, backings: Backings) -> None:
    """Register patterns and synergies tools."""
    # Attach backings to handlers so they can access them
    _list_patterns_handler._backings = backings  # type: ignore[attr-defined]
    _list_synergies_handler._backings = backings  # type: ignore[attr-defined]

    @registry.register("list_patterns")
    async def list_patterns(args: dict[str, Any]) -> dict[str, Any]:
        return await _list_patterns_handler(args)

    @registry.register("list_synergies")
    async def list_synergies(args: dict[str, Any]) -> dict[str, Any]:
        return await _list_synergies_handler(args)
