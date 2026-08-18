"""Group 4 — energy summary (data-api `/api/v1/energy/*`).

Metric definitions (lifted into the energy-truth skill under TAP-5316):
- `current_power_w`: latest whole-home smart-meter reading, watts.
- `daily_kwh`: energy since local midnight, kilowatt-hours (Wh / 1000).
- `peak_power_w` / `peak_time`: highest reading in data-api's 24 h statistics window and when.
- `average_power_w`: mean reading over that window, watts.
- `top_consumers[].average_power_on_w`: mean draw while the entity is on, watts;
  `estimated_daily_kwh`: data-api's projection from that draw (its own duty-cycle assumption).
- `carbon.grams_per_kwh`: latest grid intensity recorded in the carbon bucket (gCO2/kWh);
  omitted when data-api has no reading (404) — never fabricated. The collector that
  populated that bucket was retired, so this field is absent on new deployments.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..budget import cap_rows
from ..errors import ToolError
from .projection import expect_list, present

if TYPE_CHECKING:
    from ..backends import Backings
    from ..registry import ToolRegistry

STATS_FIELDS = ("current_power_w", "daily_kwh", "peak_power_w", "peak_time", "average_power_w")


async def _carbon(backings: Backings, *, tool: str) -> dict[str, Any] | None:
    try:
        row = await backings.data_api.get_json("/api/v1/energy/carbon-intensity/current", tool=tool)
    except ToolError as error:
        if error.code == "not_found":
            return None
        raise
    if not isinstance(row, dict) or row.get("intensity") is None:
        return None
    carbon = {"grams_per_kwh": float(row["intensity"])}
    source = row.get("grid_operator") or row.get("region")
    if source:
        carbon["source"] = str(source)
    return carbon


def register(registry: ToolRegistry, backings: Backings) -> None:
    data_api = backings.data_api

    @registry.register("get_energy_summary", narrow_hint="top_n")
    async def get_energy_summary(args: dict[str, Any]) -> dict[str, Any]:
        tool = "get_energy_summary"
        top_n = args.get("top_n", 10)
        stats = await data_api.get_json("/api/v1/energy/statistics", tool=tool)
        if not isinstance(stats, dict):
            raise ToolError(
                "contract_violation", "statistics backing returned a non-object", tool=tool
            )
        rows = expect_list(
            await data_api.get_json("/api/v1/energy/top-consumers", {"limit": top_n}, tool=tool),
            tool=tool,
        )
        consumers = [
            {
                "entity_id": r["entity_id"],
                **present(r, ("average_power_on_w", "estimated_daily_kwh")),
            }
            for r in rows
            if r.get("entity_id")
        ]
        consumers, capped = cap_rows(consumers, 20)
        out = {
            "current_power_w": stats.get("current_power_w"),
            "daily_kwh": stats.get("daily_kwh"),
            **present(stats, ("peak_power_w", "peak_time", "average_power_w")),
            "top_consumers": consumers,
            "truncated": capped,
        }
        if capped:
            out["hint"] = "top_n"
        carbon = await _carbon(backings, tool=tool)
        if carbon is not None:
            out["carbon"] = carbon
        return out
