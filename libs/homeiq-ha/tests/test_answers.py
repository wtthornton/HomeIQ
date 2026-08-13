"""Wizard answers ingestion: manifest surgery, write-only secret, idempotency (TAP-5945)."""

from __future__ import annotations

import json
import textwrap

import pytest
from homeiq_ha.agent.answers import Answers, apply_answers, merge_device_areas_into_manifest
from homeiq_ha.agent.manifest import load_manifest

from tests.simulators import SimHA

MANIFEST = textwrap.dedent(
    """\
    provenance:
      authored_by: test fixture
    # a leading comment that surgery must never disturb
    manifest:
      managed_label_prefixes: []
      areas:
      - area_id: office
        name: Office
      device_areas:
      - device_id: dev0
        area_id: office
        reason: pre-existing row
      entity_labels: []
      entity_aliases: []
      helpers: []
    design_notes: 'trailing key that marks the end of the manifest mapping'
    """
)


@pytest.fixture
def manifest_path(tmp_path):
    path = tmp_path / "manifest.yaml"
    path.write_text(MANIFEST)
    return path


def test_merge_appends_rows_and_preserves_every_other_byte(manifest_path):
    before = manifest_path.read_text()
    added = merge_device_areas_into_manifest(
        manifest_path, [("dev1", "Guest Room"), ("dev2", "Office")], reason="wizard submission 2026-08-13"
    )
    assert added == {"areas_added": ["guest_room"], "device_areas_added": ["dev1", "dev2"]}

    manifest = load_manifest(manifest_path)
    assert {a.area_id for a in manifest.areas} == {"office", "guest_room"}
    rows = {d.device_id: d for d in manifest.device_areas}
    assert rows["dev1"].area_id == "guest_room"
    assert rows["dev1"].reason == "wizard submission 2026-08-13"
    assert rows["dev2"].area_id == "office"

    after = manifest_path.read_text()
    # Everything that existed before is still there, byte-for-byte, in order.
    for line in before.splitlines():
        assert line in after
    assert "# a leading comment that surgery must never disturb" in after
    assert after.endswith("design_notes: 'trailing key that marks the end of the manifest mapping'\n")


def test_merge_is_idempotent_byte_identical(manifest_path):
    merge_device_areas_into_manifest(manifest_path, [("dev1", "Guest Room")], reason="r")
    first = manifest_path.read_text()
    added = merge_device_areas_into_manifest(manifest_path, [("dev1", "Guest Room")], reason="r")
    assert added == {"areas_added": [], "device_areas_added": []}
    assert manifest_path.read_text() == first


@pytest.mark.asyncio
async def test_apply_answers_converges_and_verifies_by_read_back(sim: SimHA, manifest_path):
    from homeiq_ha.agent.device_areas import ManifestDeviceAreasRecipe
    from homeiq_ha.agent.recipes import AreasRecipe

    answers = Answers(device_areas=(("dev1", "Guest Room"),))

    def recipes():
        manifest = load_manifest(manifest_path)
        return [
            AreasRecipe(tuple(a.name for a in manifest.areas)),
            ManifestDeviceAreasRecipe(manifest),
        ]

    result = await apply_answers(sim, answers, recipes, manifest_path=manifest_path)

    by_id = {i["id"]: i for i in result["items"]}
    assert by_id["manifest"]["status"] == "converged"
    # Verification is a live registry read-back, not the write's return value.
    assert by_id["device_area:dev1"]["status"] == "converged"
    assert by_id["device_area:dev1"]["evidence"]["live_area"] == "guest_room"

    # Second identical submission: nothing to add, nothing to change.
    again = await apply_answers(sim, answers, recipes, manifest_path=manifest_path)
    by_id = {i["id"]: i for i in again["items"]}
    assert by_id["manifest"]["status"] == "skipped"
    assert again["converge"]["wrote_nothing"] is True


@pytest.mark.asyncio
async def test_backup_password_is_write_only(sim: SimHA, manifest_path):
    answers = Answers(backup_password="hunter2-secret")
    result = await apply_answers(sim, answers, list, manifest_path=manifest_path)

    by_id = {i["id"]: i for i in result["items"]}
    assert by_id["backup_password"]["status"] == "converged"
    assert by_id["backup_password"]["evidence"] == {"encryption_key_set": True}
    # The secret appears nowhere in the response payload...
    assert "hunter2-secret" not in json.dumps(result)
    # ...but did land in the backup config via backup/config/update.
    assert sim.state["backup_config"]["create_backup"]["password"] == "hunter2-secret"

    # Second submission: already set -> skipped, never overwritten.
    again = await apply_answers(sim, answers, list, manifest_path=manifest_path)
    assert {i["id"]: i["status"] for i in again["items"]}["backup_password"] == "skipped"


@pytest.mark.asyncio
async def test_team_flow_reads_schema_and_verifies_marker_entity(sim: SimHA, manifest_path):
    sim.state["flow_first_step"] = {
        "type": "form",
        "flow_id": "tt1",
        "data_schema": [{"name": "league_id"}, {"name": "team_id"}, {"name": "name"}],
    }
    answers = Answers(teams=({"league_id": "NHL", "team_id": "VGK"},))
    result = await apply_answers(sim, answers, list, manifest_path=manifest_path)

    by_id = {i["id"]: i for i in result["items"]}
    assert by_id["team:vgk"]["status"] == "converged"
    assert by_id["team:vgk"]["evidence"]["entity_ids"] == ["sensor.team_tracker_vgk"]
    # Only schema-declared fields were sent; the marker name was defaulted in.
    assert sim.state["flow_inputs"] == [
        {"league_id": "NHL", "team_id": "VGK", "name": "team_tracker vgk"}
    ]

    # Second submission: the marker entity exists -> flow not re-driven.
    again = await apply_answers(sim, answers, list, manifest_path=manifest_path)
    assert {i["id"]: i["status"] for i in again["items"]}["team:vgk"] == "skipped"
    assert len(sim.state["flow_inputs"]) == 1


@pytest.mark.asyncio
async def test_addon_options_land_and_addon_starts(sim: SimHA, manifest_path):
    sim.state["addons"] = [{"slug": "otbr", "state": "stopped"}]
    sim.state["addon_info"] = {"otbr": {"options": {"device": None}, "state": "stopped"}}
    answers = Answers(addon_options=(("otbr", {"device": "/dev/ttyUSB0"}),))
    result = await apply_answers(sim, answers, list, manifest_path=manifest_path)

    by_id = {i["id"]: i for i in result["items"]}
    assert by_id["addon:otbr"]["status"] == "converged"
    assert sim.state["addon_info"]["otbr"]["options"]["device"] == "/dev/ttyUSB0"
    assert next(a["state"] for a in sim.state["addons"] if a["slug"] == "otbr") == "started"
