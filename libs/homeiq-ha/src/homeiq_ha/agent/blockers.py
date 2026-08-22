"""Catalogue of things HomeIQ cannot configure for you, and why.

Every entry here was hit on a real instance, not imagined. They are structural
— any Home Assistant install with the same hardware meets the same wall — so
they ship with the product rather than living in one operator's notes.

The catalogue is the *taxonomy*; which of these a given instance is actually
hitting is recorded per-domain in ``devices.integration_blockers`` by
ha-setup-service, and served from ``GET /api/v1/init/blockers``.

Adding an entry is a claim that something is un-automatable. Before adding one,
check it is not merely *unimplemented* — those are issues, not blockers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from .flow_credentials import credentials_for
from .matchers import MatchStrength

if TYPE_CHECKING:
    from .flow_probe import FlowProbe
    from .matchers import Candidate


class BlockerKind(StrEnum):
    """Why an integration cannot be configured unattended."""

    OAUTH_EXTERNAL = "oauth_external"
    SECOND_FACTOR = "second_factor"
    CREDENTIALS_MISSING = "credentials_missing"
    NO_DISCOVERY_MATCHER = "no_discovery_matcher"
    MATCHER_TOO_NARROW = "matcher_too_narrow"
    HOSTNAME_GLOB_COLLISION = "hostname_glob_collision"
    WEAK_EVIDENCE_FOR_ADDRESS_FLOW = "weak_evidence_for_address_flow"
    YAML_ONLY_INTEGRATION = "yaml_only_integration"
    CUSTOM_REPOSITORY = "custom_repository"
    RANDOMIZED_MAC = "randomized_mac"
    NOT_OBSERVED = "not_observed"
    BEHIND_BRIDGE = "behind_bridge"


@dataclass(frozen=True)
class Blocker:
    """One reason automation stops, with the manual step that gets past it."""

    kind: BlockerKind
    title: str
    #: What the software actually encounters.
    detection: str
    #: Why no amount of engineering removes it.
    why: str
    #: What a person does instead.
    workaround: str
    #: True when a future release could plausibly automate it anyway.
    resolvable: bool = False
    #: Concrete instance seen on the reference install, for recognisability.
    example: str = ""


CATALOGUE: tuple[Blocker, ...] = (
    Blocker(
        kind=BlockerKind.OAUTH_EXTERNAL,
        title="Config flow redirects to a browser login",
        detection="The flow's first step returns type 'external' with a login URL.",
        why=(
            "OAuth deliberately requires a user agent the vendor controls, so the "
            "consent screen cannot be replayed by a server. There is no headless "
            "path, by design, and any that appeared would be a vendor bug."
        ),
        workaround=(
            "Open Settings > Devices & Services > Add Integration and complete the "
            "sign-in in your browser. One time; the token then refreshes itself."
        ),
        example="xbox -> login.live.com via account-link.nabucasa.com",
    ),
    Blocker(
        kind=BlockerKind.SECOND_FACTOR,
        title="A one-time code arrives out of band",
        detection=(
            "The flow accepts the credential form, then renders a second form "
            "asking for a code sent by email, SMS, or an authenticator app."
        ),
        why=(
            "The code is delivered on a channel HomeIQ does not hold and is valid "
            "for minutes. Automating it means granting the agent your inbox, which "
            "is a much larger authority than 'add an integration'."
        ),
        workaround=(
            "Supply the credentials via HOMEIQ_INTEGRATION_* so the flow gets past "
            "step one, then enter the code when prompted. One interaction rather "
            "than the whole wizard."
        ),
        resolvable=True,
        example="ring 2FA code; roborock emailed verification code",
    ),
    Blocker(
        kind=BlockerKind.CREDENTIALS_MISSING,
        title="Account details not supplied",
        detection="The flow's first step requires fields that are not addresses.",
        why=(
            "The agent must never invent an account. This is not a wall so much as "
            "a fact the owner has not stated yet."
        ),
        workaround=(
            "Set HOMEIQ_INTEGRATION_<DOMAIN>_<FIELD> in .env for every required "
            "field, then run POST /api/v1/init/converge. All-or-nothing per domain: "
            "a half-filled form errors identically to a wrong password."
        ),
        resolvable=True,
        example="HOMEIQ_INTEGRATION_RING_USERNAME / _PASSWORD",
    ),
    Blocker(
        kind=BlockerKind.NO_DISCOVERY_MATCHER,
        title="Integration declares no discovery matcher at all",
        detection="manifest/get returns no dhcp, zeroconf, ssdp or bluetooth block.",
        why=(
            "Home Assistant can only auto-discover what an integration asks to be "
            "matched on. An integration with no matcher is manual-only by its "
            "author's decision, so no survey — HA's or HomeIQ's — can ever reach it."
        ),
        workaround=(
            "Add it by hand. HomeIQ still reports the devices under "
            "'identified but unmatched' so you know they exist."
        ),
        example="alexa_devices on HA 2026.8.2 — nine Amazon devices unreachable",
    ),
    Blocker(
        kind=BlockerKind.MATCHER_TOO_NARROW,
        title="Matcher exists but excludes the hardware you own",
        detection=(
            "The device's OUI or hostname matches part of a manifest entry, never "
            "all of it. HomeIQ reports this as MAC or HOSTNAME strength."
        ),
        why=(
            "Manifest matchers are hand-maintained lists that lag real product "
            "lines, and each entry ANDs every key it declares. A vendor shipping a "
            "new OUI, or a device that sends no DHCP hostname, silently fails."
        ),
        workaround=(
            "Add the integration manually; it will find the device through your "
            "account or a local scan. Consider reporting the missing prefix upstream."
        ),
        resolvable=True,
        example=(
            "ring needs hostname ring* AND one of five OUIs — one doorbell sent no "
            "hostname, the other's OUI (90486C) is not listed. lg_thinq lists only "
            "34E6E6*; real LG units are LG Innotek. solaredge needs hostname 'target'."
        ),
    ),
    Blocker(
        kind=BlockerKind.HOSTNAME_GLOB_COLLISION,
        title="Hostname pattern matches an unrelated device",
        detection="Only the hostname leg of a matcher hit; the OUI did not.",
        why=(
            "Hostname globs are broad and a hostname is a name: the owner can "
            "change it, so it is not identity. HomeIQ refuses to write on a "
            "name match, which means a real device behind a name-only match also "
            "goes unconfigured. That is the safe side of the trade."
        ),
        workaround="Confirm what the device is, then add the integration manually.",
        example="flux_led glob [hba][flk]* claims HL_CAM4-… , which is a camera",
    ),
    Blocker(
        kind=BlockerKind.WEAK_EVIDENCE_FOR_ADDRESS_FLOW,
        title="OUI match is not enough to configure an address-based integration",
        detection=(
            "The flow needs only a host/IP, but the match is MAC strength rather than STRICT."
        ),
        why=(
            "An address flow writes the match itself into Home Assistant, so a "
            "wrong match creates a wrong device. A vendor OUI says the hardware is "
            "that vendor's; it does not say the integration supports this model."
        ),
        workaround="Add it manually and give it the IP HomeIQ reported.",
        example="tplink refused for RE815X — a range extender, not a Kasa plug",
    ),
    Blocker(
        kind=BlockerKind.YAML_ONLY_INTEGRATION,
        title="Integration has no config flow",
        detection="manifest/get reports config_flow false or null.",
        why=(
            "There is no flow API to drive. Setup is a configuration.yaml edit and "
            "a Home Assistant restart."
        ),
        workaround="Edit configuration.yaml on the HA host and restart Home Assistant.",
        example="solaredge_local — local Modbus, config_flow null",
    ),
    Blocker(
        kind=BlockerKind.CUSTOM_REPOSITORY,
        title="Only a custom (HACS) integration covers this device",
        detection="No core integration matches; a HACS repository does.",
        why=(
            "HACS integrations are third-party code that runs inside Home "
            "Assistant with full access. Installing one is a supply-chain decision "
            "that belongs to the owner, not to an agent."
        ),
        workaround=(
            "Review the repository yourself, then install through HACS. Once "
            "installed its matchers join the survey automatically — HomeIQ reads "
            "both the core and custom sections of integration/descriptions."
        ),
        example="huesyncbox (mvdwetering) — no core equivalent exists",
    ),
    Blocker(
        kind=BlockerKind.RANDOMIZED_MAC,
        title="Device uses a private (randomized) MAC",
        detection="The MAC's locally-administered bit is set; no IEEE assignment exists.",
        why=(
            "MAC randomization is a privacy feature working correctly. There is no "
            "vendor to look up, and the address changes, so it is not an identity "
            "either."
        ),
        workaround=(
            "Usually a phone or laptop with nothing to integrate. If it is a device "
            "you care about, disable private-address mode for this network on it."
        ),
        example="9 of 54 observed MACs on the reference network",
    ),
    Blocker(
        kind=BlockerKind.NOT_OBSERVED,
        title="Device present but never seen taking a DHCP lease",
        detection="Visible in ARP or on the network, absent from the fingerprint store.",
        why=(
            "Observation is passive and DHCP-based. A device that has not renewed "
            "its lease inside the capture window has produced no record to read, so "
            "an empty result means 'not observed', never 'not present'."
        ),
        workaround=(
            "Power-cycle the device to force a DHCP request, or wait for its lease "
            "to renew. The one-time backfill covers rotated logs already on disk."
        ),
        resolvable=True,
        example="a third Ring (b0:09:da:…) is in ARP with no address-bearing DHCP record",
    ),
    Blocker(
        kind=BlockerKind.BEHIND_BRIDGE,
        title="Device has no LAN presence to observe",
        detection="Present in HA's device registry with no MAC in its connections.",
        why=(
            "Zigbee, Z-Wave, Thread and Hue-bridge devices speak a radio protocol, "
            "not IP. Network observation is structurally blind to them — and it "
            "does not need to see them, because they already have an integration."
        ),
        workaround="None needed; these are already configured.",
        example="50 of 93 HA devices on the reference install expose no MAC",
    ),
)

BY_KIND: dict[BlockerKind, Blocker] = {b.kind: b for b in CATALOGUE}


def describe(kind: BlockerKind | str) -> Blocker | None:
    """Look up one catalogue entry, tolerating a raw string kind."""
    try:
        return BY_KIND[BlockerKind(kind)]
    except ValueError:
        return None


def classify_blocker(candidate: Candidate, probe: FlowProbe) -> BlockerKind | None:
    """Which catalogue entry explains why this domain is not configured.

    ``None`` means nothing is blocking it — the flow is fillable now. Order
    matters: a hostname-only match is refused before its flow shape is even
    considered, because no flow shape would make a name safe.
    """
    if probe.kind != "form":
        return BlockerKind.OAUTH_EXTERNAL
    if candidate.strength is MatchStrength.HOSTNAME:
        return BlockerKind.HOSTNAME_GLOB_COLLISION
    if probe.automatable:
        if candidate.strength is not MatchStrength.STRICT:
            return BlockerKind.WEAK_EVIDENCE_FOR_ADDRESS_FLOW
        return None if candidate.host.ip else BlockerKind.NOT_OBSERVED
    if credentials_for(candidate.domain, probe.required) is None:
        return BlockerKind.CREDENTIALS_MISSING
    return None


__all__ = ["BY_KIND", "CATALOGUE", "Blocker", "BlockerKind", "classify_blocker", "describe"]
