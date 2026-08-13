"""ManifestDeviceAreasRecipe tests: area creation + device assignment.

Reuses the fixture simulator from ``test_agent_recipes``.
"""

from __future__ import annotations

from typing import Any

import pytest
from homeiq_ha.agent import CheckStatus
from homeiq_ha.agent.manifest import Area, DeviceArea, OrganizationManifest
from homeiq_ha.agent.recipes import ManifestDeviceAreasRecipe

from tests.simulators import SimHA


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


# --- ManifestAreasRemoveRecipe (TAP-5974) ----------------------------------


def _removal_manifest(**overrides: Any) -> OrganizationManifest:
    from homeiq_ha.agent.manifest import AreaRemoval

    return _manifest(
        areas_remove=(AreaRemoval("tv", "Hue zone import artifact"),), **overrides
    )


@pytest.mark.asyncio
async def test_areas_remove_deletes_an_empty_declared_area(sim):
    from homeiq_ha.agent.recipes import ManifestAreasRemoveRecipe

    sim.state["areas"].append({"area_id": "tv", "name": "TV"})
    recipe = ManifestAreasRemoveRecipe(_removal_manifest())

    check = await recipe.check(sim)
    assert check.status is CheckStatus.NEEDS_APPLY

    result = await recipe.apply(sim)
    assert [c.target for c in result.changed] == ["area:tv"]
    assert all(a["area_id"] != "tv" for a in sim.state["areas"])

    verify = await recipe.verify(sim)
    assert verify.ok


@pytest.mark.asyncio
async def test_areas_remove_blocks_while_devices_remain(sim):
    from homeiq_ha.agent.recipes import ManifestAreasRemoveRecipe

    sim.state["areas"].append({"area_id": "tv", "name": "TV"})
    sim.state["devices"].append({"id": "devtv", "name": "TV strip", "area_id": "tv"})
    recipe = ManifestAreasRemoveRecipe(_removal_manifest())

    check = await recipe.check(sim)
    assert check.status is CheckStatus.BLOCKED_ON_HUMAN
    assert "tv" in check.details["occupied"]

    result = await recipe.apply(sim)
    assert result.changed == ()
    assert any(a["area_id"] == "tv" for a in sim.state["areas"]), "occupied area must survive"


@pytest.mark.asyncio
async def test_areas_remove_blocks_while_entities_remain(sim):
    from homeiq_ha.agent.recipes import ManifestAreasRemoveRecipe

    sim.state["areas"].append({"area_id": "tv", "name": "TV"})
    sim.state["entities"].append({"entity_id": "light.tv_strip", "area_id": "tv"})
    recipe = ManifestAreasRemoveRecipe(_removal_manifest())

    check = await recipe.check(sim)
    assert check.status is CheckStatus.BLOCKED_ON_HUMAN

    result = await recipe.apply(sim)
    assert result.changed == ()


@pytest.mark.asyncio
async def test_areas_remove_satisfied_when_already_absent(sim):
    from homeiq_ha.agent.recipes import ManifestAreasRemoveRecipe

    recipe = ManifestAreasRemoveRecipe(_removal_manifest())
    check = await recipe.check(sim)
    assert check.status is CheckStatus.SATISFIED


def test_areas_recipe_wanted_set_is_manifest_driven():
    from homeiq_ha.agent.recipes import AreasRecipe, default_recipes

    manifest = _manifest(areas=(Area("master_bedroom", "Master Bedroom"),))
    recipes = default_recipes(manifest)
    areas = next(r for r in recipes if isinstance(r, AreasRecipe))
    assert areas.wanted == ("Master Bedroom",)
    assert "Bedroom" not in areas.wanted, "hardcoded default must not resurrect removed areas"
