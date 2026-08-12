"""Generate the org-inventory artifact from the live HA registries (read-only)."""
import asyncio
import json
import os
import sys


async def main() -> None:
    from homeiq_ha.client import HAWebSocketClient

    ws_url = os.environ["HA_WS_URL"]
    token = os.environ["HA_TOKEN"]
    async with HAWebSocketClient(ws_url, token) as client:
        areas = await client.list_areas()
        labels = await client.list_labels()
        devices = await client.list_devices()
        entities = await client.list_entities()

    inventory = {
        "areas": [{"area_id": a["area_id"], "name": a["name"]} for a in areas],
        "labels": [{"label_id": l["label_id"], "name": l["name"]} for l in labels],
        "devices": [
            {
                "device_id": d["id"],
                "name": d.get("name_by_user") or d.get("name"),
                "model": d.get("model"),
                "manufacturer": d.get("manufacturer"),
                "area_id": d.get("area_id"),
                "disabled": bool(d.get("disabled_by")),
                "entry_type": d.get("entry_type"),
            }
            for d in devices
        ],
        "entities": [
            {
                "entity_id": e["entity_id"],
                "device_id": e.get("device_id"),
                "area_id": e.get("area_id"),
                "labels": e.get("labels") or [],
                "aliases": e.get("aliases") or [],
                "name": e.get("name"),
                "original_name": e.get("original_name"),
                "disabled": bool(e.get("disabled_by")),
                "hidden": bool(e.get("hidden_by")),
            }
            for e in entities
        ],
        "helpers": sorted(
            e["entity_id"]
            for e in entities
            if e["entity_id"].split(".")[0].startswith("input_")
        ),
    }
    json.dump(inventory, sys.stdout)


asyncio.run(main())

# Usage: this must run where HA_WS_URL/HA_TOKEN exist and homeiq_ha is
# installed — in practice inside the gateway container:
#   docker exec -i homeiq-setup-service python - < scripts/generate-org-inventory.py \
#     > .tapps-mcp/org-inventory-$(date -u +%Y%m%dT%H%M%SZ).json
