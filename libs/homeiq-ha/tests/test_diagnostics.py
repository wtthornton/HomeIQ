"""Tests for the report-only diagnostics recipes (scene governance, mesh health)."""

from __future__ import annotations

from typing import Any

import pytest
from homeiq_ha.agent import CheckStatus
from homeiq_ha.agent.manifest import OrganizationManifest

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



def _scene_manifest() -> OrganizationManifest:
    from homeiq_ha.agent.manifest import ScenePolicyRule

    return _manifest(
        scene_policy=(
            ScenePolicyRule("hue", "bridge_owned", "Hue Bridge owns its scenes"),
        )
    )


@pytest.mark.asyncio
async def test_scene_policy_satisfied_when_all_scenes_covered(sim):
    from homeiq_ha.agent.recipes import ScenePolicyRecipe

    sim.state["entities"].extend(
        [
            {"entity_id": "scene.relax", "platform": "hue"},
            {"entity_id": "scene.energize", "platform": "hue"},
        ]
    )
    recipe = ScenePolicyRecipe(_scene_manifest())
    check = await recipe.check(sim)
    assert check.status is CheckStatus.SATISFIED
    assert check.details["covered"] == {"hue": 2}
    assert sim.writes == [], "report-only recipe must never write"


@pytest.mark.asyncio
async def test_scene_policy_blocks_on_uncovered_scene_source(sim):
    from homeiq_ha.agent.recipes import ScenePolicyRecipe

    sim.state["entities"].extend(
        [
            {"entity_id": "scene.relax", "platform": "hue"},
            {"entity_id": "scene.movie_night", "platform": "homeassistant"},
        ]
    )
    recipe = ScenePolicyRecipe(_scene_manifest())
    check = await recipe.check(sim)
    assert check.status is CheckStatus.BLOCKED_ON_HUMAN
    assert "scene.movie_night" in check.details["uncovered"]

    result = await recipe.apply(sim)
    assert result.changed == ()
    assert sim.writes == []


@pytest.mark.asyncio
async def test_scene_policy_silent_without_declared_policy(sim):
    from homeiq_ha.agent.recipes import ScenePolicyRecipe

    sim.state["entities"].append({"entity_id": "scene.relax", "platform": "hue"})
    recipe = ScenePolicyRecipe(_manifest())
    check = await recipe.check(sim)
    assert check.status is CheckStatus.SATISFIED


# --- ManifestHelpersRecipe menu/type split (TAP-5976) ------------------------


@pytest.mark.asyncio
async def test_sensor_group_helper_keeps_type_as_the_aggregation_form_field(sim):
    from homeiq_ha.agent.manifest import Helper
    from homeiq_ha.agent.recipes import ManifestHelpersRecipe

    manifest = _manifest(
        helpers=(
            Helper(
                "group",
                "backyard_temperature_group",
                "Backyard Temperature",
                {
                    "menu": "sensor",
                    "type": "mean",
                    "entities": ["sensor.backyard_hue_outdoor_motion_sensor_1_temperature"],
                },
                "outdoor temperature coverage",
            ),
        )
    )
    recipe = ManifestHelpersRecipe(manifest)
    check = await recipe.check(sim)
    assert check.status is CheckStatus.NEEDS_APPLY  # sensor.<slug> not in registry

    await recipe.apply(sim)
    assert sim.rest.writes == ["config_flow group"]
    # domain derives from the menu branch, so verify looks for sensor.<slug>
    assert ManifestHelpersRecipe._domain(manifest.helpers[0]) == "sensor"


@pytest.mark.asyncio
async def test_binary_sensor_group_helper_backward_compatible_without_menu(sim):
    from homeiq_ha.agent.manifest import Helper
    from homeiq_ha.agent.recipes import ManifestHelpersRecipe

    manifest = _manifest(
        helpers=(
            Helper(
                "group",
                "backyard_presence_group",
                "Backyard Presence",
                {"type": "binary_sensor", "entities": ["binary_sensor.x"], "all": False},
                "presence group",
            ),
        )
    )
    recipe = ManifestHelpersRecipe(manifest)
    assert ManifestHelpersRecipe._domain(manifest.helpers[0]) == "binary_sensor"
    await recipe.apply(sim)
    assert sim.rest.writes == ["config_flow group"]



class _MeshWs:
    def __init__(self, devices):
        self._devices = devices
        self.writes = []

    async def send_command(self, command_type, **_kwargs):
        if command_type == "zha/devices":
            if isinstance(self._devices, Exception):
                raise self._devices
            return self._devices
        self.writes.append(command_type)
        return None


class _MeshHA:
    def __init__(self, devices):
        self.ws = _MeshWs(devices)


@pytest.mark.asyncio
async def test_mesh_health_emits_one_row_per_device_sorted_by_lqi():
    from homeiq_ha.agent.recipes import ZigbeeMeshHealthRecipe

    ha = _MeshHA([
        {"ieee": "00:1", "name": "Coordinator", "lqi": None, "available": True, "device_type": "Coordinator"},
        {"ieee": "00:2", "name": "Strong", "lqi": 200, "available": True},
        {"ieee": "00:3", "name": "Weak", "lqi": 12, "available": True},
        {"ieee": "00:4", "name": "Dead", "lqi": 40, "available": False},
    ])
    result = await ZigbeeMeshHealthRecipe().check(ha)
    assert result.status is CheckStatus.SATISFIED
    d = result.details
    assert d["device_count"] == 4
    assert d["unavailable"] == ["00:4"]
    assert d["weak_lqi"] == ["00:3"]
    # rows sorted weakest-LQI first (None sinks to the end)
    assert [r["ieee"] for r in d["devices"]] == ["00:3", "00:4", "00:2", "00:1"]
    assert ha.ws.writes == [], "report-only: no writes"


@pytest.mark.asyncio
async def test_mesh_health_satisfied_when_no_zha_mesh():
    from homeiq_ha.agent.recipes import ZigbeeMeshHealthRecipe

    result = await ZigbeeMeshHealthRecipe().check(_MeshHA(None))
    assert result.status is CheckStatus.SATISFIED
    assert "no ZHA mesh" in result.summary


@pytest.mark.asyncio
async def test_mesh_health_degrades_on_api_error_not_crash():
    from homeiq_ha.agent.recipes import ZigbeeMeshHealthRecipe

    result = await ZigbeeMeshHealthRecipe().check(_MeshHA(RuntimeError("zha boom")))
    assert result.status is CheckStatus.SATISFIED
    assert "unavailable" in result.summary


@pytest.mark.asyncio
async def test_mesh_health_apply_is_noop():
    from homeiq_ha.agent.recipes import ZigbeeMeshHealthRecipe

    r = ZigbeeMeshHealthRecipe()
    assert (await r.apply(_MeshHA([]))).changed == ()
    assert (await r.verify(_MeshHA([]))).ok
