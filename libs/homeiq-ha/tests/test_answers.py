"""Wizard answers ingestion: manifest surgery, write-only secret, idempotency (TAP-5945)."""

from __future__ import annotations

import json
import textwrap
from typing import TYPE_CHECKING

import pytest
from homeiq_ha.agent.answers import Answers, apply_answers
from homeiq_ha.agent.manifest import load_manifest

if TYPE_CHECKING:
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


@pytest.mark.asyncio
async def test_unwritable_manifest_is_a_typed_item_not_a_500(sim: SimHA, manifest_path):
    manifest_path.chmod(0o444)
    manifest_path.parent.chmod(0o555)
    try:
        result = await apply_answers(
            sim, Answers(device_areas=(("dev5", "Den"),)), list, manifest_path=manifest_path
        )
    finally:
        manifest_path.parent.chmod(0o755)
        manifest_path.chmod(0o644)
    item = next(i for i in result["items"] if i["id"] == "manifest")
    assert item["status"] == "failed"
    assert "Error" in item["evidence"]["error"]


@pytest.mark.asyncio
async def test_team_flow_first_step_create_entry_never_advances(sim: SimHA, manifest_path):
    """Verifier finding: a flow whose FIRST step is create_entry was being
    advanced anyway. Now it verifies by entity read-back and never advances;
    with no marker entity visible the item honestly reports failed."""
    sim.state["flow_first_step"] = {"type": "create_entry", "title": "VGK"}
    result = await apply_answers(
        sim, Answers(teams=({"team_id": "VGK"},)), list, manifest_path=manifest_path
    )
    item = next(i for i in result["items"] if i["id"] == "team:vgk")
    assert item["status"] == "failed"
    assert "flow_inputs" not in sim.state, "no advance on an already-created entry"


@pytest.mark.asyncio
async def test_team_flow_first_step_abort_is_a_typed_failure(sim: SimHA, manifest_path):
    sim.state["flow_first_step"] = {"type": "abort", "reason": "single_instance_allowed"}
    result = await apply_answers(
        sim, Answers(teams=({"team_id": "VGK"},)), list, manifest_path=manifest_path
    )
    item = next(i for i in result["items"] if i["id"] == "team:vgk")
    assert item["status"] == "failed"
    assert "single_instance_allowed" in item["evidence"]["error"]
    assert "flow_inputs" not in sim.state


@pytest.mark.asyncio
async def test_team_entity_matching_is_anchored(sim: SimHA, manifest_path):
    """'la' must not match team_tracker_lakers (verifier finding)."""
    sim.state["entities"].append({"entity_id": "sensor.team_tracker_lakers"})
    sim.state["flow_first_step"] = {
        "type": "form",
        "flow_id": "t2",
        "data_schema": [{"name": "team_id"}, {"name": "name"}],
    }
    result = await apply_answers(
        sim, Answers(teams=({"team_id": "LA"},)), list, manifest_path=manifest_path
    )
    item = next(i for i in result["items"] if i["id"] == "team:la")
    # The lakers entity did NOT short-circuit it; the flow ran and made team_tracker_la.
    assert item["status"] == "converged"
    assert item["evidence"]["entity_ids"] == ["sensor.team_tracker_la"]


@pytest.mark.asyncio
async def test_unknown_device_id_is_rejected_before_the_manifest_write(sim: SimHA, manifest_path):
    """A display name (or any non-registry id) posted as device_id must
    become a typed failure and leave the manifest byte-identical — a junk
    row would be sticky and could never converge (Wave 7 panel finding)."""
    before = manifest_path.read_text()
    result = await apply_answers(
        sim,
        Answers(device_areas=(("Sun", "Office"),)),
        list,
        manifest_path=manifest_path,
    )
    by_id = {i["id"]: i for i in result["items"]}
    assert by_id["device_area:Sun"]["status"] == "failed"
    assert by_id["device_area:Sun"]["evidence"]["reason"] == "unknown_device_id"
    assert by_id["manifest"]["status"] == "skipped"
    assert manifest_path.read_text() == before
