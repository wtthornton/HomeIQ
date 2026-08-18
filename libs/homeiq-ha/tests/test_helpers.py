"""ManifestHelpersRecipe tests split out for the slug-identity contract (TAP-5431)."""

from __future__ import annotations

from typing import Any

import pytest
from homeiq_ha.agent import CheckStatus
from homeiq_ha.agent.manifest import Helper, OrganizationManifest
from homeiq_ha.agent.recipes import ManifestHelpersRecipe

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
async def test_manifest_utility_meter_helper_keys_existence_on_sensor_domain(sim):
    """A utility_meter entry creates sensor.<slug>, not utility_meter.<slug>.

    Keying existence on the flow-handler domain would re-create the helper
    every converge (TAP-5431).
    """
    recipe = ManifestHelpersRecipe(
        _manifest(
            helpers=(
                Helper(
                    "utility_meter",
                    "daily_energy",
                    "Daily Energy",
                    {"source": "sensor.a_energy", "cycle": "daily"},
                    "alias",
                ),
            )
        )
    )
    sim.state["entities"].append({"entity_id": "sensor.daily_energy"})

    assert (await recipe.check(sim)).status is CheckStatus.SATISFIED
    assert (await recipe.apply(sim)).change_count == 0


@pytest.mark.asyncio
async def test_manifest_helper_adopts_a_source_named_entity_by_rename(sim):
    """utility_meter keys the object id on the SOURCE entity, not the name.

    An existing platform+name match is renamed to the slug identity instead
    of creating a duplicate config entry (TAP-5431, observed live).
    """
    recipe = ManifestHelpersRecipe(
        _manifest(
            helpers=(
                Helper(
                    "utility_meter",
                    "daily_energy",
                    "Daily Energy",
                    {"source": "sensor.a_energy", "cycle": "daily"},
                    "alias",
                ),
            )
        )
    )
    sim.state["entities"].append(
        {
            "entity_id": "sensor.living_room_a_daily_energy",
            "platform": "utility_meter",
            "original_name": "Daily Energy",
        }
    )

    result = await recipe.apply(sim)

    assert result.changed[0].action == "rename"
    assert not any(w.startswith("flow") for w in sim.rest.writes)
    ids = {e["entity_id"] for e in sim.state["entities"]}
    assert "sensor.daily_energy" in ids
    assert (await recipe.verify(sim)).ok
    assert (await recipe.apply(sim)).change_count == 0


@pytest.mark.asyncio
async def test_manifest_helper_repairs_a_drifted_created_entity_id(sim):
    recipe = ManifestHelpersRecipe(
        _manifest(
            helpers=(
                Helper(
                    "utility_meter",
                    "daily_energy",
                    "Daily Energy",
                    {"source": "sensor.a_energy", "cycle": "daily"},
                    "alias",
                ),
            )
        )
    )

    async def scripted_flow(_domain: str, _steps: list[dict[str, Any]], **_c: Any) -> Any:
        sim.state["entities"].append(
            {"entity_id": "sensor.somewhere_else_daily_energy", "config_entry_id": "um1"}
        )
        return {"type": "create_entry", "result": {"entry_id": "um1"}}

    sim.rest.run_config_flow = scripted_flow  # type: ignore[method-assign]

    result = await recipe.apply(sim)

    assert result.change_count == 1
    ids = {e["entity_id"] for e in sim.state["entities"]}
    assert "sensor.daily_energy" in ids
    assert (await recipe.verify(sim)).ok
