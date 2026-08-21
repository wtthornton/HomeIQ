"""Find devices that are on the network but claimed by no Home Assistant integration.

Home Assistant discovers cloud-polling brands through its ``dhcp`` component,
which matches observed DHCP traffic against per-integration matchers declared
in each integration's manifest. That mechanism is **passive and lossy**, and on
the reference instance it missed every Ring and Amazon device in the house:

- ``9c:76:13:00:00:11`` carries an OUI that *is* in HA's ``ring`` matcher, but
  sent no DHCP hostname. HA's matcher entry requires ``hostname: "ring*"``
  **and** the MAC prefix, so a missing hostname fails the whole entry.
- ``90:48:6c:00:00:22`` announced itself as ``RingDoorbell-22`` — but its OUI
  (``90486C``, Ring LLC) is absent from HA's five-prefix list, so that entry
  failed too.

Neither device ever produced a discovery flow. Two Ring doorbells and nine
Amazon devices sat on the LAN, invisible, while HA reported 93 healthy devices.
(A third Ring is visible in ARP but sent no DHCP record carrying an address, so
it is outside this recipe's reach — see the coverage note in
docs/operations/init-gateway.md.)

This recipe closes that gap without duplicating HA's knowledge. The matcher
table is read **from Home Assistant's own manifests** at audit time
(``integration/descriptions`` for the domain list, then ``manifest/get`` per
domain — about a second for ~1200 domains on the reference instance), so the
mapping from hardware to integration stays whatever the installed HA version
says it is. There is no vendor table in this file to rot.

What differs from HA is only the *strictness*: HA needs every key in a matcher
entry to match at once; this recipe scores each leg separately and records
which one hit. See :class:`MatchStrength` for why that distinction decides
whether a device may be configured automatically or must go to a person.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .matchers import Candidate, ManifestMatchers
from .recipe import (
    PHASE_INTEGRATIONS,
    ApplyResult,
    Change,
    CheckResult,
    CheckStatus,
    Plan,
    Recipe,
    VerifyResult,
)

if TYPE_CHECKING:
    from homeiq_ha.client import HAClient

    from .netobserve import NetworkObserver, ObservedHost


def _identified_vendor(host: ObservedHost) -> str:
    """The host's IEEE vendor, or "" when the OUI did not resolve.

    A randomized privacy MAC has no IEEE assignment; ``oui_lookup`` reports
    those as ``"Unknown"``, which asserts nothing and must not be listed as a
    vendor a person could go looking for an integration for.
    """
    vendor = (host.vendor or "").strip()
    return "" if vendor.lower() == "unknown" else vendor


def _where(host: ObservedHost) -> str:
    """How a person locates this device: its name if it has one, else its MAC."""
    return f"{host.hostname or host.mac} ({host.ip or 'no lease seen'})"


class UnclaimedDevicesRecipe(Recipe):
    """Report LAN devices no configured integration owns; configure the safe ones.

    Human-gated by default. A device is configured automatically only when the
    match meets Home Assistant's own strictness *and* the integration needs no
    account — everything else becomes a ``blocked_on_human`` row naming the
    device, because a Ring or Alexa config flow cannot be completed without the
    owner's credentials and a second factor.
    """

    name = "integrations.unclaimed_devices"
    phase = PHASE_INTEGRATIONS
    description = "Every LAN device is claimed by a configured integration"

    def __init__(self, observer: NetworkObserver | None = None) -> None:
        self._observer = observer

    @staticmethod
    async def _adopted_macs(ha: HAClient) -> set[str]:
        """MACs Home Assistant already has in its device registry.

        Read from ``connections`` — protocol-native identity — never from
        device names. A device HA already owns is not unclaimed no matter what
        a matcher says about it.
        """
        macs: set[str] = set()
        for device in await ha.ws.list_devices() or []:
            for kind, value in device.get("connections") or []:
                if kind == "mac" and value:
                    macs.add(str(value).upper().replace(":", "").replace("-", ""))
        return macs

    async def _survey(self, ha: HAClient) -> tuple[list[Candidate], dict[str, list[ObservedHost]]]:
        """Return (unclaimed candidates, identified-but-unmatched hosts by vendor).

        The second bucket exists because a matcher-based survey has a floor
        that is not its own fault: an integration that declares no ``dhcp``,
        ``zeroconf`` or ``ssdp`` block can never be matched to anything.
        ``alexa_devices`` is exactly that — manual-only on HA 2026.8.2 — so
        nine Amazon devices on the reference network match no matcher in
        existence. Reporting only what matched would have rendered them as
        "nothing found", which is the failure this recipe exists to end.
        """
        hosts = await self._observer.observed_hosts() if self._observer else []
        if not hosts:
            return [], {}

        entries = await ha.rest.get_config_entries() or []
        configured = {e.get("domain") for e in entries if e.get("domain")}
        adopted = await self._adopted_macs(ha)
        matchers = await ManifestMatchers.load(ha)

        unclaimed: list[Candidate] = []
        unmatched: dict[str, list[ObservedHost]] = {}
        for host in hosts:
            if host.mac_digits in adopted:
                continue
            candidates = matchers.candidates_for(host)
            if candidates:
                unclaimed.extend(c for c in candidates if c.domain not in configured)
            elif _identified_vendor(host):
                unmatched.setdefault(_identified_vendor(host), []).append(host)
        return unclaimed, unmatched

    async def _unclaimed(self, ha: HAClient) -> list[Candidate]:
        candidates, _ = await self._survey(ha)
        return candidates

    @staticmethod
    def _human_action(
        blocked: list[Candidate], unmatched: dict[str, list[ObservedHost]] | None = None
    ) -> str:
        lines: list[str] = []

        by_domain: dict[str, list[Candidate]] = {}
        for candidate in blocked:
            by_domain.setdefault(candidate.domain, []).append(candidate)

        if by_domain:
            lines.append(
                "Add these in Settings > Devices & Services > Add Integration. "
                "Each needs an account login the agent must not attempt:"
            )
            for domain, group in sorted(by_domain.items()):
                where = ", ".join(_where(c.host) for c in group)
                lines.append(f"  - {group[0].title} [{domain}]: {len(group)} device(s) — {where}")

        if unmatched:
            if lines:
                lines.append("")
            lines.append(
                "These are on the network and identified by IEEE OUI, but NO installed "
                "integration declares a dhcp/zeroconf/ssdp matcher for them, so Home "
                "Assistant can never discover them on its own:"
            )
            lines.append(
                "Whether an integration covers any of them is a judgement this "
                "agent will not guess: a vendor's legal name is not its Home "
                "Assistant brand name (Signify ships as 'Philips Hue', D&M as "
                "'Denon'), and phones and laptops appear here with no "
                "integration to add at all. Listed most devices first:"
            )
            for vendor, hosts in sorted(unmatched.items(), key=lambda t: (-len(t[1]), t[0])):
                where = ", ".join(_where(h) for h in hosts)
                lines.append(f"  - {vendor}: {len(hosts)} device(s) — {where}")

        return "\n".join(lines)

    #: Returned when no sensor is wired up. Deliberately not SATISFIED.
    _NO_OBSERVER = CheckResult(
        CheckStatus.NOT_APPLICABLE,
        "no network observer configured; LAN was not inspected",
        {
            "reason": (
                "Set HOMEIQ_NETWORK_OBSERVER_URL to the zeek-network-service "
                "endpoint. Without it this recipe cannot see the network and "
                "will not pretend the network is clean."
            )
        },
    )

    @staticmethod
    def _details(
        unclaimed: list[Candidate],
        auto: list[Candidate],
        blocked: list[Candidate],
        unmatched: dict[str, list[ObservedHost]],
    ) -> dict[str, Any]:
        return {
            "unclaimed": [c.describe() for c in unclaimed],
            "auto_applicable": [c.domain for c in auto],
            "needs_credentials": sorted({c.domain for c in blocked}),
            "identified_but_unmatched": {
                vendor: [_where(h) for h in hosts] for vendor, hosts in sorted(unmatched.items())
            },
        }

    async def check(self, ha: HAClient) -> CheckResult:
        if self._observer is None:
            return self._NO_OBSERVER

        unclaimed, unmatched = await self._survey(ha)
        if not unclaimed and not unmatched:
            return CheckResult(
                CheckStatus.SATISFIED, "every observed LAN device maps to a configured integration"
            )

        auto = [c for c in unclaimed if c.auto_applicable]
        blocked = [c for c in unclaimed if not c.auto_applicable]
        details = self._details(unclaimed, auto, blocked, unmatched)

        if not blocked and not unmatched:
            return CheckResult(
                CheckStatus.NEEDS_APPLY,
                f"{len(auto)} unclaimed device(s) can be configured without credentials",
                details,
            )

        unmatched_count = sum(len(hosts) for hosts in unmatched.values())
        return CheckResult(
            CheckStatus.BLOCKED_ON_HUMAN,
            f"{len(unclaimed)} unclaimed device(s) across "
            f"{len({c.domain for c in unclaimed})} integration(s); "
            f"{unmatched_count} identified device(s) match no integration",
            details,
            human_action=self._human_action(blocked, unmatched),
        )

    async def plan(self, ha: HAClient) -> Plan:
        auto = [c for c in await self._unclaimed(ha) if c.auto_applicable]
        return Plan(
            tuple(
                Change("configure integration", c.domain, after="loaded")
                for c in _unique_by_domain(auto)
            )
        )

    async def apply(self, ha: HAClient) -> ApplyResult:
        auto = _unique_by_domain([c for c in await self._unclaimed(ha) if c.auto_applicable])
        if not auto:
            return ApplyResult((), "nothing to configure without credentials")

        changed: list[Change] = []
        for candidate in auto:
            await ha.rest.run_config_flow(candidate.domain, [{}])
            changed.append(Change("configure integration", candidate.domain, after="loaded"))
        return ApplyResult(tuple(changed), f"configured {len(changed)} integration(s)")

    async def verify(self, ha: HAClient) -> VerifyResult:
        remaining = await self._unclaimed(ha)
        auto_left = [c for c in remaining if c.auto_applicable]
        return VerifyResult(
            not auto_left,
            f"{len(remaining)} unclaimed device(s) remain; {len(auto_left)} still auto-applicable",
            {"remaining": [c.describe() for c in remaining]},
        )


def _unique_by_domain(candidates: list[Candidate]) -> list[Candidate]:
    seen: dict[str, Candidate] = {}
    for candidate in candidates:
        seen.setdefault(candidate.domain, candidate)
    return list(seen.values())


__all__ = ["UnclaimedDevicesRecipe"]
