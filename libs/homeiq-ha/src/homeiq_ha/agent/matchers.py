"""Match observed LAN devices against Home Assistant's own discovery matchers.

The matcher table is read from the live instance at audit time
(``integration/descriptions`` for the domain list, then ``manifest/get`` per
domain — about a second for ~1200 domains), so the mapping from hardware to
integration is always whatever the installed HA version says it is. There is
no vendor table in HomeIQ to rot.

What differs from HA is only *strictness*. HA requires every key of one
matcher entry to match at once, and on the reference instance that missed both
Ring devices: one had the right OUI but sent no DHCP hostname, the other
announced ``RingDoorbell-22`` but from an OUI absent from HA's five-prefix
list. Neither ever produced a discovery flow. This module scores each leg
separately and records which one hit — see :class:`MatchStrength`, whose
ordering decides whether a device may be configured automatically.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeiq_ha.client import HAClient

    from .netobserve import ObservedHost


class MatchStrength(IntEnum):
    """How firmly an observed device is tied to an integration domain.

    Ordered deliberately, and the ordering decides autonomy:

    ``STRICT``
        Every key of one manifest matcher entry matched — the same bar Home
        Assistant itself applies. Eligible for automatic configuration when
        the integration also needs no account.
    ``MAC``
        The OUI matched but the entry's other keys did not. A MAC prefix is
        protocol-native identity: it survives a rename and is assigned by
        IEEE, so this is real evidence, just not HA's own bar. Reported to a
        person, never auto-applied.
    ``HOSTNAME``
        Only the DHCP hostname matched. A hostname is a *name* — the owner can
        change it, and a rename would erase the "evidence" entirely
        (.claude/rules/friendly-names.md). It is recorded so a human can see
        why the device was flagged, and it confers nothing on its own.
    """

    HOSTNAME = 1
    MAC = 2
    STRICT = 3


@dataclass(frozen=True)
class Candidate:
    """An integration domain that plausibly owns an observed device."""

    domain: str
    title: str
    host: ObservedHost
    strength: MatchStrength
    iot_class: str | None = None

    @property
    def needs_account(self) -> bool:
        """True when the config flow will demand credentials from a person.

        ``iot_class`` of ``cloud_polling`` / ``cloud_push`` means the
        integration talks to a vendor cloud, which means an account login and
        usually a second factor. No amount of automation gets past that, and
        pretending otherwise produces a flow that errors instead of a device
        that works.
        """
        return not self.iot_class or self.iot_class.startswith("cloud")

    @property
    def auto_applicable(self) -> bool:
        return self.strength is MatchStrength.STRICT and not self.needs_account

    def describe(self) -> str:
        who = self.host.hostname or self.host.ip or self.host.mac
        return f"{self.title} ({self.domain}) — {who} at {self.host.mac} [{self.strength.name}]"


@dataclass
class ManifestMatchers:
    """HA's own discovery matchers, read from the live instance.

    Built once per run. ``integration/descriptions`` lists every installed
    domain; ``manifest/get`` returns each one's ``dhcp`` block. Both are
    read-only websocket commands, so this is safe inside ``check``.
    """

    #: domain -> (matcher entries, title, iot_class)
    entries: dict[str, tuple[tuple[dict[str, Any], ...], str, str | None]] = field(
        default_factory=dict
    )

    @classmethod
    async def load(cls, ha: HAClient) -> ManifestMatchers:
        descriptions = await ha.ws.send_command("integration/descriptions") or {}
        domains = _domains_from_descriptions(descriptions)

        matchers: dict[str, tuple[tuple[dict[str, Any], ...], str, str | None]] = {}
        for domain in domains:
            manifest = await _safe_manifest(ha, domain)
            dhcp = manifest.get("dhcp") if manifest else None
            if dhcp:
                matchers[domain] = (
                    tuple(dhcp),
                    manifest.get("name") or domain,
                    manifest.get("iot_class"),
                )
        return cls(entries=matchers)

    def candidates_for(self, host: ObservedHost) -> list[Candidate]:
        """Return every domain whose matchers touch this host, best match first."""
        found: dict[str, Candidate] = {}
        for domain, (dhcp_entries, title, iot_class) in self.entries.items():
            strength = _match_strength(dhcp_entries, host)
            if strength is None:
                continue
            existing = found.get(domain)
            if existing is None or strength > existing.strength:
                found[domain] = Candidate(domain, title, host, strength, iot_class)
        return sorted(found.values(), key=lambda c: -c.strength)


def _domains_from_descriptions(descriptions: dict[str, Any]) -> list[str]:
    """Flatten ``integration/descriptions`` into a flat domain list.

    The payload nests two ways: a domain maps either to its own metadata, or —
    for a brand such as Amazon — to an ``integrations`` dict of the real
    domains underneath it. ``alexa_devices`` only exists in the second form,
    so a reader that skips brands misses it entirely.
    """
    domains: set[str] = set()
    for section in ("core", "custom"):
        for domain, meta in (descriptions.get(section) or {}).get("integration", {}).items():
            if not isinstance(meta, dict):
                continue
            nested = meta.get("integrations")
            if isinstance(nested, dict):
                domains.update(nested)
            if not meta.get("supported_by"):
                domains.add(domain)
    return sorted(domains)


async def _safe_manifest(ha: HAClient, domain: str) -> dict[str, Any]:
    """``manifest/get`` for one domain; empty dict when HA does not know it."""
    try:
        return await ha.ws.send_command("manifest/get", integration=domain) or {}
    except Exception:  # noqa: BLE001 — one unknown domain must not end the audit
        return {}


def _glob(pattern: str | None, value: str | None) -> bool:
    if not pattern or not value:
        return False
    return fnmatch.fnmatch(value.upper(), pattern.upper())


def _match_strength(
    dhcp_entries: tuple[dict[str, Any], ...], host: ObservedHost
) -> MatchStrength | None:
    """Score one host against one integration's DHCP matchers.

    Home Assistant ANDs the keys within an entry and ORs across entries. This
    keeps that as ``STRICT`` but also reports the near-misses, because on the
    reference instance every real Ring device was a near-miss.
    """
    best: MatchStrength | None = None
    for entry in dhcp_entries:
        mac_pattern = entry.get("macaddress")
        hostname_pattern = entry.get("hostname")
        if not mac_pattern and not hostname_pattern:
            # e.g. {"registered_devices": true} — refers to devices HA already
            # has, so it can never identify an unclaimed one.
            continue

        mac_hit = _glob(mac_pattern, host.mac_digits)
        hostname_hit = _glob(hostname_pattern, host.hostname)

        required = [
            hit
            for pattern, hit in ((mac_pattern, mac_hit), (hostname_pattern, hostname_hit))
            if pattern
        ]
        if all(required):
            return MatchStrength.STRICT
        if mac_hit:
            best = max(best or MatchStrength.MAC, MatchStrength.MAC)
        elif hostname_hit and best is None:
            best = MatchStrength.HOSTNAME
    return best


__all__ = ["Candidate", "ManifestMatchers", "MatchStrength"]
