"""ManifestDeviceAreasRecipe tests: area creation + device assignment.

Reuses the fixture simulator from ``test_agent_recipes``.
"""

from __future__ import annotations

from typing import Any

import pytest
from homeiq_ha.agent import CheckStatus
from homeiq_ha.agent.manifest import Area, DeviceArea, OrganizationManifest
from homeiq_ha.agent.recipes import ManifestDeviceAreasRecipe

from tests.test_agent_recipes import SimHA


@pytest.fixture
def sim() -> SimHA:
    return SimHA()


def _manifest(**overrides: Any) -> OrganizationManifest:
    fields: dict[str, Any] = {
        "managed_label_prefixes": ("role:", "class:", "area:"),
        "areas": (),
        "device_areas": (),
        "entity_labels": (),
        "entity_aliases": (),
        "helpers": (),
    }
    fields.update(overrides)
    return OrganizationManifest(**fields)


@pytest.mark.asyncio
async def test_manifest_device_areas_converge_and_are_idempotent(sim):
    manifest = _manifest(device_areas=(DeviceArea("dev0", "living_room", "name says so"),))
    recipe = ManifestDeviceAreasRecipe(manifest)

    assert (await recipe.check(sim)).status is CheckStatus.NEEDS_APPLY

    first = await recipe.apply(sim)
    assert first.change_count == 1
    assert (await recipe.verify(sim)).ok
    assert next(d for d in sim.state["devices"] if d["id"] == "dev0")["area_id"] == "living_room"

    second = await recipe.apply(sim)
    assert second.change_count == 0
    assert (await recipe.check(sim)).status is CheckStatus.SATISFIED


@pytest.mark.asyncio
async def test_manifest_device_areas_skip_stale_ids_without_crashing(sim):
    recipe = ManifestDeviceAreasRecipe(
        _manifest(device_areas=(DeviceArea("ghost", "office", "gone"),))
    )

    result = await recipe.check(sim)

    assert result.status is CheckStatus.SATISFIED
    assert result.details["stale_device_ids"] == ["ghost"]
    assert (await recipe.apply(sim)).change_count == 0


@pytest.mark.asyncio
async def test_manifest_areas_are_created_before_assignment(sim):
    """Owner rule 2026-08-12: a device name that names a room is the answer —
    the recipe creates the missing area, then assigns."""
    sim.state["devices"].append({"id": "tv1", "name": "Guest Room TV", "area_id": None})
    recipe = ManifestDeviceAreasRecipe(
        _manifest(
            areas=(Area("guest_room", "Guest Room"),),
            device_areas=(DeviceArea("tv1", "guest_room", "name names the room"),),
        )
    )

    assert (await recipe.check(sim)).status is CheckStatus.NEEDS_APPLY
    first = await recipe.apply(sim)

    assert first.change_count == 2  # area created + device assigned
    assert any(a["area_id"] == "guest_room" for a in sim.state["areas"])
    assert next(d for d in sim.state["devices"] if d["id"] == "tv1")["area_id"] == "guest_room"
    assert (await recipe.verify(sim)).ok

    second = await recipe.apply(sim)
    assert second.change_count == 0
