"""Comment-preserving manifest edits for wizard answers (TAP-5945).

The committed manifest carries a provenance block and inline comments that a
YAML round-trip would destroy, so wizard-driven appends are text surgery on
exactly two block-list sections. Wizard input is untrusted: every scalar is
YAML-dumped, the result is re-parsed after writing (or rolled back), and
reassignments are refused — an append-only surface cannot edit history.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from .manifest import load_manifest

if TYPE_CHECKING:
    from collections.abc import Sequence


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _scalar(value: str) -> str:
    """One YAML-safe scalar. Wizard input is untrusted: a name like
    'Kitchen: main' or an anchor/newline must not be able to corrupt the
    committed manifest (verifier finding, TAP-5945)."""
    return yaml.safe_dump(value, default_flow_style=True).strip().removesuffix("...").strip()


def _append_block_list_rows(text: str, section: str, rows: list[str]) -> str:
    """Insert formatted rows at the end of one 2-space-indented block list.

    Locates ``  <section>:`` under ``manifest:`` and inserts before the next
    sibling key (or top-level key), leaving every other byte — comments,
    provenance, formatting — untouched.
    """
    if not text.endswith("\n"):
        text += "\n"  # EOF without newline would glue the first row onto it
    # Fresh-install shape: an inline empty list becomes a block list.
    text = text.replace(f"  {section}: []\n", f"  {section}:\n", 1)
    lines = text.splitlines(keepends=True)
    start = next(
        (i for i, line in enumerate(lines) if line.rstrip("\n") == f"  {section}:"),
        None,
    )
    if start is None:
        raise ValueError(f"manifest has no '  {section}:' section to extend")
    end = len(lines)
    for i in range(start + 1, len(lines)):
        stripped = lines[i].rstrip("\n")
        # Next sibling ('  key:') or top-level ('key:') line ends the section;
        # list items ('  - ') and their continuations are deeper-indented.
        if stripped and not stripped.startswith(("  -", "    ", "#", "  #")):
            end = i
            break
    return "".join(lines[:end]) + "".join(rows) + "".join(lines[end:])


def merge_device_areas_into_manifest(
    path: str | Path, device_areas: Sequence[tuple[str, str]], *, reason: str
) -> dict[str, Any]:
    """Append wizard-chosen areas + device_areas rows; skip rows already present.

    Returns what was added so the caller can report it. Zero additions leaves
    the file byte-identical (idempotency).
    """
    path = Path(path)
    manifest = load_manifest(path)
    known_areas = {a.area_id for a in manifest.areas}
    device_rows = {d.device_id: d.area_id for d in manifest.device_areas}

    new_area_rows: list[str] = []
    new_device_rows: list[str] = []
    added_areas: list[str] = []
    added_devices: list[str] = []
    rejected: list[dict[str, str]] = []
    for device_id, area_name in device_areas:
        area_id = _slugify(area_name)
        if not area_id:
            rejected.append({"device_id": device_id, "reason": f"unusable area name {area_name!r}"})
            continue
        if device_id in device_rows:
            if device_rows[device_id] != area_id:
                # Reassignment is a manifest EDIT, not an append — refuse
                # loudly rather than silently dropping the answer while
                # still minting an orphan area (verifier finding).
                rejected.append(
                    {
                        "device_id": device_id,
                        "reason": f"already mapped to {device_rows[device_id]}; "
                        "reassignment needs a manifest edit, not the wizard",
                    }
                )
            continue
        if area_id not in known_areas:
            known_areas.add(area_id)
            added_areas.append(area_id)
            new_area_rows.append(
                f"  - area_id: {_scalar(area_id)}\n    name: {_scalar(area_name)}\n"
            )
        device_rows[device_id] = area_id
        added_devices.append(device_id)
        new_device_rows.append(
            f"  - device_id: {_scalar(device_id)}\n"
            f"    area_id: {_scalar(area_id)}\n"
            f"    reason: {_scalar(reason)}\n"
        )

    if new_area_rows or new_device_rows:
        original = path.read_text()
        text = original
        if new_area_rows:
            text = _append_block_list_rows(text, "areas", new_area_rows)
        if new_device_rows:
            text = _append_block_list_rows(text, "device_areas", new_device_rows)
        path.write_text(text)
        try:
            load_manifest(path)  # re-parse or roll back: never leave it bricked
        except Exception:
            path.write_text(original)
            raise
    return {
        "areas_added": added_areas,
        "device_areas_added": added_devices,
        "rejected": rejected,
    }


__all__ = ["merge_device_areas_into_manifest"]
