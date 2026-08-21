"""Decide which device models still need a knowledge lookup, and build their signature.

HomeIQ collects; genes reason. This module is the collection half of device
onboarding: it works out which models the claim store cannot yet answer for, and
assembles the protocol-native signature that `hiq-device-scout` identifies them
from. It never decides what a device *is* — that judgement lives in the gene.

**The cache is the claim store itself.** Not an ambient recall, not a side table:
the same `devices.device_knowledge_claims` rows the facts will be written to. A
hit therefore means the answer is already durable, and a lookup that would
re-establish it is pure waste. Measured on this instance, the same model costs
$0.437 and two searches cold against $0.068 and zero searches warm — a 6.4x
difference that is the whole reason this can run on every discovery pass without
being reckless.

Two entry points, both wanting the same cache discipline:

* **First-time setup** sweeps every model already on the instance, so a new
  install ends with a populated store rather than an empty one.
* **Ongoing onboarding** looks only at models discovery has not seen before, so
  the steady-state cost of a pass is zero.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

#: Facts worth having for any device. Deliberately short: each one either drives a
#: decision elsewhere in HomeIQ or answers a question a person actually asks.
#: `typical_power_watts` is here because Powercalc has no profile for televisions
#: and a stated wattage is the only way they enter energy coverage at all.
DEFAULT_WANTED_FACTS = (
    "device_type",
    "power_source",
    "typical_power_watts",
    "standby_power_watts",
    "requires_neutral",
    "zha_quirk_required",
    "known_defect",
)

#: Model strings that name no product. Home Assistant writes these when an
#: integration never learned what it found, and a search on them returns whatever
#: the web thinks the word means. The scout is built to work from a signature
#: without a model, so these are passed through as absent rather than as text.
UNINFORMATIVE_MODELS = frozenset({"", "unknown", "none", "null", "n/a", "-"})


def normalize_model_key(manufacturer: str, model: str) -> str:
    """The canonical subject key for a model, e.g. ``inovelli/vzm31-sn``.

    Mirrors device_knowledge_service.normalize_model_key. The column has no CHECK,
    so a mis-shaped key inserts cleanly and is then unreachable by the only read
    path — a write-only store that looks like success.
    """
    return f"{manufacturer.strip().lower()}/{model.strip().lower()}"


def _informative(value: str | None) -> str | None:
    """A field's value, or None when it names nothing."""
    if value is None:
        return None
    text = str(value).strip()
    return None if text.lower() in UNINFORMATIVE_MODELS else text


@dataclass(frozen=True)
class OnboardingCandidate:
    """One model that may need a knowledge lookup, with its cache already read."""

    subject_key: str
    signature: dict[str, Any]
    known: list[dict[str, Any]] = field(default_factory=list)
    wanted: tuple[str, ...] = DEFAULT_WANTED_FACTS
    device_count: int = 0

    @property
    def cached_fact_keys(self) -> set[str]:
        return {str(claim.get("fact_key")) for claim in self.known if claim.get("fact_key")}

    @property
    def gaps(self) -> tuple[str, ...]:
        """Wanted facts the cache cannot answer."""
        cached = self.cached_fact_keys
        return tuple(key for key in self.wanted if key not in cached)

    @property
    def needs_lookup(self) -> bool:
        """False when the cache already answers everything wanted.

        Checked here rather than left to the gene. A gene asked to do nothing
        still costs a model invocation; a candidate filtered out costs nothing.
        """
        return bool(self.gaps)


def build_signature(device: dict[str, Any], entity_domains: list[str]) -> dict[str, Any]:
    """Assemble the protocol-native fingerprint the scout identifies from.

    Everything here is structural: an integration slug, a model id an integration
    reported, an address burned into a radio or a NIC, the set of entity domains a
    device exposes. A friendly name is none of those and is deliberately absent —
    the scout is guardrailed against identifying from one, and the surest way to
    honour that is not to hand it over. See `.claude/rules/friendly-names.md`.
    """
    signature: dict[str, Any] = {"integration": str(device.get("integration") or "unknown")}

    for source_key, target_key in (
        ("manufacturer", "manufacturer"),
        ("model", "model"),
        ("model_id", "model_id"),
        ("sw_version", "sw_version"),
        ("hw_version", "hw_version"),
        ("zigbee_ieee", "ieee"),
    ):
        value = _informative(device.get(source_key))
        if value:
            signature[target_key] = value

    # The MAC's OUI prefix identifies the vendor even when the model does not,
    # which is how a device reporting model "MediaRenderer" is still placeable.
    for kind, value in device.get("connections") or []:
        if kind == "mac" and value:
            signature["mac"] = str(value).lower()
            break

    if entity_domains:
        signature["entity_domains"] = sorted(set(entity_domains))

    return signature


def plan_onboarding(
    devices: list[dict[str, Any]],
    domains_by_device: dict[str, list[str]],
    claims_by_subject: dict[str, list[dict[str, Any]]],
    *,
    wanted: tuple[str, ...] = DEFAULT_WANTED_FACTS,
    only_subjects: set[str] | None = None,
) -> list[OnboardingCandidate]:
    """Which models need a lookup, cache already applied.

    One candidate per distinct (manufacturer, model), not per device: twenty Hue
    downlights are one model and one lookup. A device whose manufacturer or model
    names nothing is skipped rather than searched on the word "Unknown".

    `only_subjects` narrows the sweep to models discovery has just seen for the
    first time, which is what makes the ongoing path cost nothing in steady state.
    """
    by_subject: dict[str, OnboardingCandidate] = {}
    counts: dict[str, int] = {}

    for device in devices:
        # Home Assistant's own answer to "is this a physical device?". Hue Room
        # and Zone groups, add-ons and service integrations are registered as
        # services: there is no product to look up, and "Signify Netherlands
        # B.V. / Room" is a search that can only return something misleading.
        if str(device.get("entry_type") or "").lower() == "service":
            continue

        manufacturer = _informative(device.get("manufacturer"))
        model = _informative(device.get("model"))
        if not manufacturer or not model:
            # Nothing to key a model-scoped claim on. The device is still
            # discoverable; it simply has no model identity to research.
            continue

        subject_key = normalize_model_key(manufacturer, model)
        if only_subjects is not None and subject_key not in only_subjects:
            continue

        counts[subject_key] = counts.get(subject_key, 0) + 1
        if subject_key in by_subject:
            continue

        by_subject[subject_key] = OnboardingCandidate(
            subject_key=subject_key,
            signature=build_signature(device, domains_by_device.get(str(device.get("id")), [])),
            known=list(claims_by_subject.get(subject_key) or []),
            wanted=wanted,
        )

    candidates = [
        OnboardingCandidate(
            subject_key=candidate.subject_key,
            signature=candidate.signature,
            known=candidate.known,
            wanted=candidate.wanted,
            device_count=counts.get(candidate.subject_key, 0),
        )
        for candidate in by_subject.values()
    ]

    needing = [candidate for candidate in candidates if candidate.needs_lookup]
    logger.info(
        "Device onboarding: %d distinct model(s), %d already answered by the claim "
        "store, %d needing a lookup",
        len(candidates),
        len(candidates) - len(needing),
        len(needing),
    )
    # Biggest populations first: a fact about the model behind twenty devices is
    # worth more than one behind a single device, and a budget that runs out
    # should run out on the long tail.
    return sorted(needing, key=lambda c: (-c.device_count, c.subject_key))


#: How many newly-seen models one discovery pass may dispatch. New models are rare
#: in steady state — a home gains a device, not a catalogue — so this bounds the
#: one case that is not rare: a first sight of an unfamiliar home, where every
#: model is new at once. The remainder is not dropped; it is left for the next
#: pass and for the setup sweep, which is bounded the same way.
MAX_DISPATCH_PER_PASS = 3


def newly_seen_models(
    current: set[str],
    previously_seen: set[str] | None,
) -> set[str]:
    """Model subject keys appearing for the first time.

    `previously_seen` is None on the first pass after a restart, when everything
    looks new because nothing has been seen yet. Returning empty there is
    deliberate: a restart is not a home full of new devices, and treating it as
    one would re-dispatch the whole catalogue every time the service bounces.
    The setup sweep exists for the genuine first-run case and is explicit about
    what it will cost.
    """
    if previously_seen is None:
        return set()
    return current - previously_seen
