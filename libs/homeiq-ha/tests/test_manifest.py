"""Manifest schema: the switch-gesture catalogue (TAP-5987).

The catalogue is an owner-selection surface, not a deployment: these tests
pin that parsing works, that ``selected`` defaults to ``None``, and that the
committed manifest ships every gesture unselected — no recipe may wire a
gesture without the owner writing a selection into the manifest first.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from homeiq_ha.agent.manifest import SwitchGesture, load_manifest

#: The committed manifest, located from this file so the test is CWD-proof.
COMMITTED_MANIFEST = Path(__file__).parents[3] / "config" / "ha-organization-manifest.yaml"


def test_switch_gestures_parse_with_selected_defaulting_to_none(tmp_path):
    doc = textwrap.dedent(
        """
        manifest:
          managed_label_prefixes: []
          areas: []
          device_areas: []
          entity_labels: []
          entity_aliases: []
          helpers: []
          switch_gestures:
          - device_id: abc123
            device_name: Office Light Dimmer
            gesture: remote_button_double_press/Up
            options: [bright work mode, everything on]
          - device_id: abc123
            device_name: Office Light Dimmer
            gesture: remote_button_double_press/Down
            options: [wind-down]
            selected: wind-down
        """
    )
    path = tmp_path / "manifest.yaml"
    path.write_text(doc)
    m = load_manifest(path)
    assert m.switch_gestures == (
        SwitchGesture(
            "abc123",
            "Office Light Dimmer",
            "remote_button_double_press/Up",
            ("bright work mode", "everything on"),
            None,
        ),
        SwitchGesture(
            "abc123",
            "Office Light Dimmer",
            "remote_button_double_press/Down",
            ("wind-down",),
            "wind-down",
        ),
    )


def test_switch_gestures_absent_means_empty_tuple(tmp_path):
    path = tmp_path / "manifest.yaml"
    path.write_text("manifest: {}\n")
    assert load_manifest(path).switch_gestures == ()


def test_committed_catalogue_covers_all_three_switches_and_wires_nothing():
    """The live catalogue: 3 switches x (double..quintuple) x (Up/Down), all
    awaiting owner sign-off. If a selection lands, a recipe may act on it —
    until then every row must stay unselected."""
    manifest = load_manifest(COMMITTED_MANIFEST)
    gestures = manifest.switch_gestures
    assert {g.device_name for g in gestures} == {
        "Office Light Dimmer",
        "Office Fan Switch",
        "Bar Light Dimmer",
    }
    multiplicities = {
        "remote_button_double_press",
        "remote_button_triple_press",
        "remote_button_quadruple_press",
        "remote_button_quintuple_press",
    }
    for name in ("Office Light Dimmer", "Office Fan Switch", "Bar Light Dimmer"):
        rows = [g for g in gestures if g.device_name == name]
        assert {g.gesture.split("/")[0] for g in rows} == multiplicities
        assert {g.gesture.split("/")[1] for g in rows} == {"Up", "Down"}
        assert all(g.options for g in rows), f"{name}: every gesture lists candidates"
    assert all(g.selected is None for g in gestures), (
        "catalogue rows must ship unselected; owner sign-off happens by "
        "editing `selected` in config/ha-organization-manifest.yaml"
    )
