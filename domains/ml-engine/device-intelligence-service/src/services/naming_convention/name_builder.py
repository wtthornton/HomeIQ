"""The one place a convention name is composed (TAP-6231).

Three call sites used to build names with their own ad hoc string joins
(`name_generator`, `hygiene_analyzer`, `naming_router`), and they disagreed —
one of them shipped manufacturer-prefixed names the shared rubric itself
penalizes (TAP-6234). The composition policy lives here, next to the rubric
that scores it (`convention_rules`):

- area first, then an optional position, then the device descriptor
- Title Case throughout
- NEVER a brand or manufacturer word — `convention_rules._BRAND_NAMES` docks
  them, and a generator must not emit names its own scorer flags
"""

from __future__ import annotations

from .convention_rules import _BRAND_NAMES

#: Domain -> customer-facing device type label. Shared by every composer so
#: "binary_sensor" never renders three different ways.
DEVICE_TYPE_LABELS = {
    "light": "Light",
    "switch": "Switch",
    "sensor": "Sensor",
    "binary_sensor": "Sensor",
    "climate": "Thermostat",
    "cover": "Cover",
    "lock": "Lock",
    "fan": "Fan",
    "camera": "Camera",
    "media_player": "Media Player",
    "vacuum": "Vacuum",
    "automation": "Automation",
    "script": "Script",
    "scene": "Scene",
}


def device_type_label(domain: str | None, device_class: str | None = None) -> str:
    """The customer-facing label for a domain/device_class pair."""
    label = DEVICE_TYPE_LABELS.get(domain or "")
    if not label and device_class:
        label = device_class.replace("_", " ").title()
    if not label:
        label = domain.replace("_", " ").title() if domain else "Device"
    return label


def strip_brands(text: str | None) -> str:
    """Drop every token the rubric's brand list would dock points for.

    The no-brand rule is enforced here, not documented and hoped for: a
    composer that lets 'Hue' through generates a name the system's own
    scorer flags (TAP-6234 — 30 of 93 live devices have a brand-first model).
    """
    if not text:
        return ""
    kept = [token for token in text.split() if token.lower() not in _BRAND_NAMES]
    return " ".join(kept)


def compose_name(
    area_name: str | None,
    descriptor: str,
    position: str | None = None,
) -> str:
    """Compose a convention-compliant friendly name.

    Brand tokens are stripped from every part (TAP-6234) — the contract is
    code, not a docstring.
    """
    parts = [strip_brands(part) for part in (area_name, position, descriptor)]
    parts = [part for part in parts if part]
    return " ".join(parts) if parts else "Device"
