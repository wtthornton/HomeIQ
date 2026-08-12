"""Manifest-driven organization recipe tests.

Reuses the fixture simulator from ``test_agent_recipes`` — the shapes there
were captured from the live instance.
"""

from __future__ import annotations

from typing import Any

import pytest
from homeiq_ha.agent import CheckStatus
from homeiq_ha.agent.manifest import (
    DeviceArea,
    EntityAliases,
    EntityLabels,
    Helper,
    OrganizationManifest,
)
from homeiq_ha.agent.recipes import (
    ManifestDeviceAreasRecipe,
    ManifestEntityAliasesRecipe,
    ManifestEntityLabelsRecipe,
    ManifestHelpersRecipe,
    default_recipes,
)

from tests.test_agent_recipes import SimHA


@pytest.fixture
def sim() -> SimHA:
    return SimHA()


def _manifest(**overrides: Any) -> OrganizationManifest:
    fields: dict[str, Any] = {
        "managed_label_prefixes": ("role:", "class:", "area:"),
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
async def test_manifest_labels_match_by_slug_and_never_mint_duplicates(sim):
    # A round-tripped slug sits in the registry as its own name — the exact
    # shape that minted "<slug>_2" duplicates before admin-api commit 02b5b42a.
    sim.state["labels"].append({"label_id": "role_primary_light", "name": "role_primary_light"})
    sim.state["entities"][0]["labels"] = []
    recipe = ManifestEntityLabelsRecipe(
        _manifest(
            entity_labels=(EntityLabels("light.wled_0", ("role:primary-light",), "main light"),)
        )
    )

    await recipe.apply(sim)

    created = [c for c in sim.ws.calls if c[0] == "config/label_registry/create"]
    assert created == [], f"minted duplicate label(s): {created}"
    assert sim.state["entities"][0]["labels"] == ["role_primary_light"]
    assert (await recipe.verify(sim)).ok


@pytest.mark.asyncio
async def test_manifest_labels_reconcile_managed_set_and_keep_unmanaged(sim):
    sim.state["labels"].extend(
        [
            {"label_id": "role_presence", "name": "role:presence"},
            {"label_id": "keep_me", "name": "keep-me"},
        ]
    )
    # Entity carries a stale managed label and a personal unmanaged one.
    sim.state["entities"][0]["labels"] = ["role_presence", "keep_me"]
    recipe = ManifestEntityLabelsRecipe(
        _manifest(entity_labels=(EntityLabels("light.wled_0", ("class:diagnostic",), "telemetry"),))
    )

    first = await recipe.apply(sim)

    assert first.change_count == 2  # one label created, one entity relabelled
    labels = set(sim.state["entities"][0]["labels"])
    assert "keep_me" in labels, "unmanaged label must survive the converge"
    assert "role_presence" not in labels, "stale managed label must be removed"
    assert any("class" in label for label in labels)
    assert (await recipe.verify(sim)).ok

    second = await recipe.apply(sim)
    assert second.change_count == 0, "second apply must be a no-op"


@pytest.mark.asyncio
async def test_manifest_labels_skip_stale_entities(sim):
    recipe = ManifestEntityLabelsRecipe(
        _manifest(entity_labels=(EntityLabels("light.ghost", ("role:x",), "gone"),))
    )

    result = await recipe.check(sim)

    assert result.status is CheckStatus.SATISFIED
    assert result.details["stale_entity_ids"] == ["light.ghost"]


@pytest.mark.asyncio
async def test_manifest_aliases_add_without_clobbering(sim):
    sim.state["entities"][0]["aliases"] = ["hand-taught alias"]
    recipe = ManifestEntityAliasesRecipe(
        _manifest(
            entity_aliases=(
                EntityAliases("light.wled_0", ("office light", "hand-taught alias"), "voice"),
            )
        )
    )

    first = await recipe.apply(sim)

    assert first.change_count == 1
    assert sim.state["entities"][0]["aliases"] == ["hand-taught alias", "office light"]
    assert (await recipe.verify(sim)).ok
    assert (await recipe.apply(sim)).change_count == 0


@pytest.mark.asyncio
async def test_manifest_helpers_create_via_flow_idempotent_by_slug(sim):
    flows: list[tuple[str, list[dict[str, Any]]]] = []

    async def scripted_flow(domain: str, steps: list[dict[str, Any]], **_c: Any) -> Any:
        flows.append((domain, steps))
        sim.state["entities"].append({"entity_id": "binary_sensor.office_presence"})
        return {"type": "create_entry"}

    sim.rest.run_config_flow = scripted_flow  # type: ignore[method-assign]
    recipe = ManifestHelpersRecipe(
        _manifest(
            helpers=(
                Helper(
                    "group",
                    "office_presence",
                    "Office Presence",
                    {"type": "binary_sensor", "entities": ["binary_sensor.a"], "all": False},
                    "presence fusion",
                ),
            )
        )
    )

    assert (await recipe.check(sim)).status is CheckStatus.NEEDS_APPLY
    first = await recipe.apply(sim)

    assert first.change_count == 1
    domain, steps = flows[0]
    assert domain == "group"
    assert steps[0] == {"next_step_id": "binary_sensor"}
    assert steps[1]["name"] == "Office Presence"
    assert steps[1]["entities"] == ["binary_sensor.a"]
    assert "type" not in steps[1]
    assert (await recipe.verify(sim)).ok

    second = await recipe.apply(sim)
    assert second.change_count == 0 and len(flows) == 1


@pytest.mark.asyncio
async def test_default_recipes_include_manifest_recipes_when_given():
    manifest = _manifest(
        device_areas=(DeviceArea("dev0", "office", "r"),),
    )

    names = {recipe.name for recipe in default_recipes(manifest)}

    assert {
        "organization.device_area_assignments",
        "organization.entity_labels",
        "organization.entity_aliases",
        "helpers.manifest",
        "integrations.zha",
    } <= names
