"""Comment-preserving manifest surgery: appends, hostile input, idempotency (TAP-5945)."""

from __future__ import annotations

import textwrap

from homeiq_ha.agent.manifest import load_manifest
from homeiq_ha.agent.manifest_edit import merge_device_areas_into_manifest

import pytest

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
    assert added == {"areas_added": ["guest_room"], "device_areas_added": ["dev1", "dev2"], "rejected": []}

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
    assert added == {"areas_added": [], "device_areas_added": [], "rejected": []}
    assert manifest_path.read_text() == first


def test_hostile_area_names_cannot_corrupt_the_manifest(manifest_path):
    """Verifier finding: 'Kitchen: main', newlines, and anchors must either
    land as safely-quoted scalars or be rejected — never brick the file."""
    added = merge_device_areas_into_manifest(
        manifest_path,
        [("devA", "Kitchen: main"), ("devB", "two\nlines"), ("devC", "*anchor"), ("devD", "!!!")],
        reason="r",
    )
    # devD's name slugs to nothing -> rejected, not written as a null id.
    assert [r["device_id"] for r in added["rejected"]] == ["devD"]
    manifest = load_manifest(manifest_path)  # parses: nothing was corrupted
    names = {a.area_id: a.name for a in manifest.areas}
    assert names["kitchen_main"] == "Kitchen: main"
    assert names["two_lines"] == "two\nlines"
    assert names["anchor"] == "*anchor"


def test_reassignment_is_rejected_without_minting_an_orphan_area(manifest_path):
    """dev0 is mapped to office; answering Kitchen must not silently add a
    kitchen area while dropping the answer (verifier finding)."""
    before = manifest_path.read_text()
    added = merge_device_areas_into_manifest(manifest_path, [("dev0", "Kitchen")], reason="r")
    assert added["areas_added"] == [] and added["device_areas_added"] == []
    assert added["rejected"][0]["device_id"] == "dev0"
    assert "already mapped to office" in added["rejected"][0]["reason"]
    assert manifest_path.read_text() == before


def test_fresh_install_inline_empty_sections_are_extendable(tmp_path):
    path = tmp_path / "fresh.yaml"
    path.write_text(
        "manifest:\n  managed_label_prefixes: []\n  areas: []\n  device_areas: []\n"
        "  entity_labels: []\n  entity_aliases: []\n  helpers: []\n"
    )
    added = merge_device_areas_into_manifest(path, [("dev1", "Office")], reason="r")
    assert added["areas_added"] == ["office"]
    manifest = load_manifest(path)
    assert manifest.device_areas[0].device_id == "dev1"
