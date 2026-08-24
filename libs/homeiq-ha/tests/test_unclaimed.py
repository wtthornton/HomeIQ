"""Tests for the unclaimed-device recipe.

The matcher fixtures below are the real ``dhcp`` blocks from Home Assistant
2026.8.2's ``ring`` and ``wled`` manifests, and the hosts are real MACs
observed on the reference network. The two Ring cases are the ones HA's own
discovery missed, and they are the whole reason this recipe exists.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeiq_ha.agent.matchers import Candidate, ManifestMatchers, MatchStrength
from homeiq_ha.agent.netobserve import ObservedHost
from homeiq_ha.agent.recipe import CheckStatus
from homeiq_ha.agent.unclaimed import FlowProbe, UnclaimedDevicesRecipe, probe_flow

# HA 2026.8.2's ring manifest: every entry ANDs hostname with a MAC prefix.
RING_DHCP = (
    {"hostname": "ring*", "macaddress": "0CAE7D*"},
    {"hostname": "ring*", "macaddress": "2CAB33*"},
    {"hostname": "ring*", "macaddress": "94E36D*"},
    {"hostname": "ring*", "macaddress": "9C7613*"},
    {"hostname": "ring*", "macaddress": "341513*"},
)

WLED_DHCP = ({"hostname": "wled*"},)


def _matchers(**domains: tuple[tuple[dict[str, Any], ...], str, str | None]) -> ManifestMatchers:
    return ManifestMatchers(entries=dict(domains))


class TestMatchStrength:
    """The two real Ring near-misses, and why each is only a near-miss."""

    def test_mac_matches_but_no_hostname_is_not_strict(self):
        """192.168.1.40 — right OUI, sent no DHCP hostname, so HA's AND fails."""
        matchers = _matchers(ring=(RING_DHCP, "Ring", "cloud_polling"))
        host = ObservedHost(mac="9C:76:13:00:00:11", ip="192.168.1.40", hostname=None)

        [candidate] = matchers.candidates_for(host)

        assert candidate.domain == "ring"
        assert candidate.strength is MatchStrength.MAC

    def test_hostname_matches_but_oui_absent_from_ha_list(self):
        """192.168.1.48 — announces RingDoorbell-22, but 90486C is not in HA's list."""
        matchers = _matchers(ring=(RING_DHCP, "Ring", "cloud_polling"))
        host = ObservedHost(mac="90:48:6C:00:00:22", ip="192.168.1.48", hostname="RingDoorbell-22")

        [candidate] = matchers.candidates_for(host)

        assert candidate.strength is MatchStrength.HOSTNAME

    def test_both_legs_match_is_strict(self):
        matchers = _matchers(ring=(RING_DHCP, "Ring", "cloud_polling"))
        host = ObservedHost(mac="9C:76:13:00:00:11", hostname="ring-doorbell")

        [candidate] = matchers.candidates_for(host)

        assert candidate.strength is MatchStrength.STRICT

    def test_unrelated_device_matches_nothing(self):
        matchers = _matchers(ring=(RING_DHCP, "Ring", "cloud_polling"))

        assert matchers.candidates_for(ObservedHost(mac="B0:4A:39:00:00:66")) == []

    def test_registered_devices_entry_cannot_claim_an_unknown_host(self):
        """``{"registered_devices": true}`` refers to devices HA already has."""
        matchers = _matchers(
            samsungtv=(({"registered_devices": True},), "Samsung", "local_polling")
        )

        assert matchers.candidates_for(ObservedHost(mac="AA:BB:CC:DD:EE:FF")) == []


class TestFlowProbe:
    """Automatability is decided by the flow's real schema, not the manifest.

    Every case below is the first step Home Assistant actually rendered on
    2026-08-21, captured by starting each flow and aborting it.
    """

    @pytest.mark.parametrize(
        ("domain", "kind", "required", "expected"),
        [
            # host is optional -> no required fields -> the agent can finish it
            ("tplink", "form", (), True),
            ("flux_led", "form", (), True),
            # secrets the agent must never invent
            ("ring", "form", ("username", "password"), False),
            ("roborock", "form", ("username", "region"), False),
            # OAuth redirect to login.live.com - no headless path exists
            ("xbox", "external", (), False),
        ],
    )
    def test_real_first_steps(self, domain, kind, required, expected):
        assert FlowProbe(domain, kind, required).automatable is expected

    def test_a_required_host_is_still_automatable(self):
        """An address is something the agent observed, not a secret."""
        assert FlowProbe("wled", "form", ("host",)).automatable

    def test_progress_step_is_not_automatable(self):
        assert not FlowProbe("hacs", "progress", ()).automatable

    @pytest.mark.asyncio
    async def test_probe_always_aborts_the_flow_it_started(self):
        ha = MagicMock()
        ha.rest.start_config_flow = AsyncMock(
            return_value={
                "flow_id": "abc123",
                "type": "form",
                "data_schema": [{"name": "host", "required": False}],
            }
        )
        ha.rest.classify_flow_step = MagicMock(return_value="form")
        ha.rest.abort_config_flow = AsyncMock()

        probe = await probe_flow(ha, "tplink")

        ha.rest.abort_config_flow.assert_awaited_once_with("abc123")
        assert probe.required == ()
        assert probe.automatable

    @pytest.mark.asyncio
    async def test_probe_aborts_even_when_reading_the_step_raises(self):
        """A flow left running shows up as a pending discovery in the owner's UI."""
        ha = MagicMock()
        ha.rest.start_config_flow = AsyncMock(return_value={"flow_id": "abc123"})
        ha.rest.classify_flow_step = MagicMock(side_effect=RuntimeError("boom"))
        ha.rest.abort_config_flow = AsyncMock()

        with pytest.raises(RuntimeError):
            await probe_flow(ha, "tplink")

        ha.rest.abort_config_flow.assert_awaited_once_with("abc123")


def _recipe_with(
    hosts: list[ObservedHost],
    configured: list[str],
    matchers: ManifestMatchers,
    credentials: dict[str, dict[str, str]] | None = None,
):
    observer = MagicMock()
    observer.observed_hosts = AsyncMock(return_value=hosts)
    recipe = UnclaimedDevicesRecipe(observer, credentials=credentials)

    ha = MagicMock()
    ha.rest.get_config_entries = AsyncMock(return_value=[{"domain": d} for d in configured])
    ha.ws.list_devices = AsyncMock(return_value=[])
    recipe_load = AsyncMock(return_value=matchers)
    return recipe, ha, recipe_load


class TestCheck:
    @pytest.mark.asyncio
    async def test_no_observer_is_not_applicable_not_satisfied(self):
        """An uninspected network must never report as a clean one."""
        result = await UnclaimedDevicesRecipe(None).check(MagicMock())

        assert result.status is CheckStatus.NOT_APPLICABLE
        assert "not inspected" in result.summary

    @pytest.mark.asyncio
    async def test_unclaimed_cloud_device_blocks_on_human_with_an_action(self, monkeypatch):
        matchers = _matchers(ring=(RING_DHCP, "Ring", "cloud_polling"))
        hosts = [ObservedHost("9C:76:13:00:00:11", "192.168.1.40", None, "Ring LLC")]
        recipe, ha, load = _recipe_with(hosts, configured=["hue", "zha"], matchers=matchers)
        monkeypatch.setattr(ManifestMatchers, "load", load)

        result = await recipe.check(ha)

        assert result.status is CheckStatus.BLOCKED_ON_HUMAN
        assert "ring" in result.details["integrations"]
        assert "account details" in result.human_action
        assert "Enter them when HomeIQ asks" in result.human_action
        assert "192.168.1.40" in result.human_action

    @pytest.mark.asyncio
    async def test_already_configured_domain_is_not_reported(self, monkeypatch):
        matchers = _matchers(ring=(RING_DHCP, "Ring", "cloud_polling"))
        hosts = [ObservedHost("9C:76:13:00:00:11", "192.168.1.40")]
        recipe, ha, load = _recipe_with(hosts, configured=["ring"], matchers=matchers)
        monkeypatch.setattr(ManifestMatchers, "load", load)

        result = await recipe.check(ha)

        assert result.status is CheckStatus.SATISFIED

    @pytest.mark.asyncio
    async def test_credential_free_device_needs_apply(self, monkeypatch):
        matchers = _matchers(wled=(WLED_DHCP, "WLED", "local_push"))
        hosts = [ObservedHost("FC:E8:C0:00:00:88", "192.168.1.147", "wled-000088")]
        recipe, ha, load = _recipe_with(hosts, configured=[], matchers=matchers)
        monkeypatch.setattr(ManifestMatchers, "load", load)

        result = await recipe.check(ha)

        # Even a credential-free local integration is reported, not applied.
        assert result.status is CheckStatus.BLOCKED_ON_HUMAN
        assert result.details["integrations"] == ["wled"]

    @pytest.mark.asyncio
    async def test_observer_returning_nothing_is_satisfied_not_crashing(self, monkeypatch):
        recipe, ha, load = _recipe_with([], configured=[], matchers=_matchers())
        monkeypatch.setattr(ManifestMatchers, "load", load)

        assert (await recipe.check(ha)).status is CheckStatus.SATISFIED


class TestIdentifiedButUnmatched:
    """The Amazon case: identified hardware that no matcher can ever claim."""

    @pytest.mark.asyncio
    async def test_known_vendor_with_no_matcher_is_reported(self, monkeypatch):
        """alexa_devices declares no dhcp/zeroconf/ssdp block on HA 2026.8.2."""
        hosts = [
            ObservedHost(
                "C0:8D:51:00:00:44",
                "192.168.1.43",
                "Amazon-Smart-Thermostat",
                "Amazon Technologies Inc.",
            ),
            ObservedHost("40:F6:BC:00:00:55", "192.168.1.229", None, "Amazon Technologies Inc."),
        ]
        recipe, ha, load = _recipe_with(hosts, configured=[], matchers=_matchers())
        monkeypatch.setattr(ManifestMatchers, "load", load)

        result = await recipe.check(ha)

        assert result.status is CheckStatus.BLOCKED_ON_HUMAN
        assert result.details["identified_but_unmatched"]["Amazon Technologies Inc."] == [
            "Amazon-Smart-Thermostat (192.168.1.43)",
            "40:F6:BC:00:00:55 (192.168.1.229)",
        ]
        assert "never discover them on its own" in result.human_action

    @pytest.mark.asyncio
    async def test_unresolved_vendor_is_not_reported(self, monkeypatch):
        """A randomized privacy MAC has no IEEE assignment and asserts nothing."""
        hosts = [ObservedHost("2E:15:29:00:00:99", "192.168.1.133", None, "Unknown")]
        recipe, ha, load = _recipe_with(hosts, configured=[], matchers=_matchers())
        monkeypatch.setattr(ManifestMatchers, "load", load)

        assert (await recipe.check(ha)).status is CheckStatus.SATISFIED

    @pytest.mark.asyncio
    async def test_device_already_in_ha_registry_is_not_unclaimed(self, monkeypatch):
        """Adoption is judged on registry MAC connections, never on names."""
        hosts = [ObservedHost("9C:76:13:00:00:11", "192.168.1.40", None, "Ring LLC")]
        recipe, ha, load = _recipe_with(
            hosts, configured=[], matchers=_matchers(ring=(RING_DHCP, "Ring", "cloud_polling"))
        )
        monkeypatch.setattr(ManifestMatchers, "load", load)
        ha.ws.list_devices = AsyncMock(
            return_value=[{"connections": [["mac", "9c:76:13:00:00:11"]]}]
        )

        assert (await recipe.check(ha)).status is CheckStatus.SATISFIED


class TestApplyConfiguresOnlyWhatItCan:
    """apply() drives flows it can finish, and leaves the rest alone."""

    @staticmethod
    def _strict(domain, title, host):
        """A STRICT match — the only strength allowed to authorise a write."""
        return _matchers(
            **{domain: ((({"macaddress": host.mac_digits[:6] + "*"}),), title, "local_polling")}
        )

    @pytest.mark.asyncio
    async def test_configures_an_address_only_flow_with_the_observed_ip(self, monkeypatch):
        host = ObservedHost("1C:61:B4:00:00:AA", "192.168.1.45", "TL-Office", "TP-Link")
        recipe, ha, load = _recipe_with(
            [host], configured=[], matchers=self._strict("tplink", "TP-Link", host)
        )
        monkeypatch.setattr(ManifestMatchers, "load", load)
        monkeypatch.setattr(
            "homeiq_ha.agent.unclaimed.probe_flow",
            AsyncMock(return_value=FlowProbe("tplink", "form", ())),
        )
        ha.rest.run_config_flow = AsyncMock()

        result = await recipe.apply(ha)

        ha.rest.run_config_flow.assert_awaited_once_with("tplink", [{"host": "192.168.1.45"}])
        assert result.change_count == 1

    @pytest.mark.asyncio
    async def test_uses_owner_credentials_when_supplied(self, monkeypatch):
        """The whole point: the owner sets the secret once, the agent does the rest."""
        host = ObservedHost("9C:76:13:00:00:11", "192.168.1.40", None, "Ring LLC")
        recipe, ha, load = _recipe_with(
            [host],
            configured=[],
            matchers=self._strict("ring", "Ring", host),
            credentials={"ring": {"username": "owner@example.com", "password": "hunter2"}},
        )
        monkeypatch.setattr(ManifestMatchers, "load", load)
        monkeypatch.setattr(
            "homeiq_ha.agent.unclaimed.probe_flow",
            AsyncMock(return_value=FlowProbe("ring", "form", ("username", "password"))),
        )
        ha.rest.run_config_flow = AsyncMock()

        result = await recipe.apply(ha)

        ha.rest.run_config_flow.assert_awaited_once_with(
            "ring", [{"username": "owner@example.com", "password": "hunter2"}]
        )
        assert result.change_count == 1

    @pytest.mark.asyncio
    async def test_partial_credentials_are_refused(self, monkeypatch):
        """Half a form renders a validation error indistinguishable from a bad password."""
        host = ObservedHost("9C:76:13:00:00:11", "192.168.1.40", None, "Ring LLC")
        recipe, ha, load = _recipe_with(
            [host],
            configured=[],
            matchers=self._strict("ring", "Ring", host),
            credentials={"ring": {"username": "owner@example.com"}},
        )
        monkeypatch.setattr(ManifestMatchers, "load", load)
        monkeypatch.setattr(
            "homeiq_ha.agent.unclaimed.probe_flow",
            AsyncMock(return_value=FlowProbe("ring", "form", ("username", "password"))),
        )
        ha.rest.run_config_flow = AsyncMock()

        result = await recipe.apply(ha)

        ha.rest.run_config_flow.assert_not_called()
        assert result.change_count == 0

    @pytest.mark.asyncio
    async def test_never_drives_an_oauth_flow_even_with_credentials(self, monkeypatch):
        host = ObservedHost("68:6C:E6:00:00:DD", "192.168.1.101", "XBOX", "Microsoft")
        recipe, ha, load = _recipe_with(
            [host],
            configured=[],
            matchers=self._strict("xbox", "Xbox", host),
            credentials={"xbox": {"username": "someone"}},
        )
        monkeypatch.setattr(ManifestMatchers, "load", load)
        monkeypatch.setattr(
            "homeiq_ha.agent.unclaimed.probe_flow",
            AsyncMock(return_value=FlowProbe("xbox", "external", ())),
        )
        ha.rest.run_config_flow = AsyncMock()

        await recipe.apply(ha)

        ha.rest.run_config_flow.assert_not_called()

    @pytest.mark.asyncio
    async def test_a_hostname_only_match_is_never_written(self, monkeypatch):
        """flux_led's glob [hba][flk]* claims HL_CAM4-..., a camera. A name authorises nothing."""
        host = ObservedHost(
            "80:48:2C:00:00:CC", "192.168.1.235", "HL_CAM4-80482C0000CC", "Hangzhou"
        )
        matchers = _matchers(
            flux_led=(
                (({"hostname": "[hba][flk]*", "macaddress": "18B905*"}),),
                "Magic Home",
                "local_polling",
            )
        )
        recipe, ha, load = _recipe_with([host], configured=[], matchers=matchers)
        monkeypatch.setattr(ManifestMatchers, "load", load)
        probe = AsyncMock(return_value=FlowProbe("flux_led", "form", ()))
        monkeypatch.setattr("homeiq_ha.agent.unclaimed.probe_flow", probe)
        ha.rest.run_config_flow = AsyncMock()

        result = await recipe.apply(ha)

        probe.assert_not_called()  # gated before the flow is even probed
        ha.rest.run_config_flow.assert_not_called()
        assert result.change_count == 0

    @pytest.mark.asyncio
    async def test_check_still_never_probes(self, monkeypatch):
        """check() is read-only; starting a flow there would trip the audit proxy."""
        host = ObservedHost("1C:61:B4:00:00:AA", "192.168.1.45", "TL-Office", "TP-Link")
        recipe, ha, load = _recipe_with(
            [host], configured=[], matchers=self._strict("tplink", "TP-Link", host)
        )
        monkeypatch.setattr(ManifestMatchers, "load", load)
        ha.rest.start_config_flow = AsyncMock()

        await recipe.check(ha)

        ha.rest.start_config_flow.assert_not_called()


class TestEvidenceBarByFlowKind:
    """An address flow writes the match; an account flow writes the account."""

    @pytest.mark.asyncio
    async def test_mac_match_is_enough_for_an_account_flow(self, monkeypatch):
        """Ring enumerates its own devices from the cloud; the match is only a trigger."""
        host = ObservedHost("9C:76:13:00:00:11", "192.168.1.40", None, "Ring LLC")
        recipe, ha, load = _recipe_with(
            [host],
            configured=[],
            matchers=_matchers(ring=(RING_DHCP, "Ring", "cloud_polling")),
            credentials={"ring": {"username": "owner@example.com", "password": "hunter2"}},
        )
        monkeypatch.setattr(ManifestMatchers, "load", load)
        monkeypatch.setattr(
            "homeiq_ha.agent.unclaimed.probe_flow",
            AsyncMock(return_value=FlowProbe("ring", "form", ("username", "password"))),
        )
        ha.rest.run_config_flow = AsyncMock()

        result = await recipe.apply(ha)

        # MAC strength, not STRICT — and that is sufficient here.
        ha.rest.run_config_flow.assert_awaited_once()
        assert result.change_count == 1

    @pytest.mark.asyncio
    async def test_mac_match_is_not_enough_for_an_address_flow(self, monkeypatch):
        """A TP-Link OUI does not mean the tplink integration supports the device."""
        host = ObservedHost("1C:61:B4:00:00:AA", "192.168.1.126", "RE815X", "TP-Link")
        matchers = _matchers(
            tplink=(
                (({"hostname": "e[sp]*", "macaddress": "1C61B4*"}),),
                "TP-Link",
                "local_polling",
            )
        )
        recipe, ha, load = _recipe_with([host], configured=[], matchers=matchers)
        monkeypatch.setattr(ManifestMatchers, "load", load)
        monkeypatch.setattr(
            "homeiq_ha.agent.unclaimed.probe_flow",
            AsyncMock(return_value=FlowProbe("tplink", "form", ())),
        )
        ha.rest.run_config_flow = AsyncMock()

        result = await recipe.apply(ha)

        ha.rest.run_config_flow.assert_not_called()
        assert result.change_count == 0

    def test_dedup_keeps_the_strongest_evidence_for_a_domain(self):
        """Two Ring devices: one HOSTNAME, one MAC. The domain is MAC."""
        from homeiq_ha.agent.unclaimed import _unique_by_domain

        weak = Candidate("ring", "Ring", ObservedHost("90:48:6C:00:00:22"), MatchStrength.HOSTNAME)
        strong = Candidate("ring", "Ring", ObservedHost("9C:76:13:00:00:11"), MatchStrength.MAC)

        [only] = _unique_by_domain([weak, strong])

        assert only.strength is MatchStrength.MAC
