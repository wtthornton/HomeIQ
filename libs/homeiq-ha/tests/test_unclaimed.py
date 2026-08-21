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
from homeiq_ha.agent.unclaimed import UnclaimedDevicesRecipe

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


class TestReportOnly:
    """The recipe never drives a config flow, whatever the match says.

    iot_class does not answer "does this need credentials". Roborock is
    local_polling and still requires a Roborock account plus a mailed
    verification code, per HA's own docs. No manifest field distinguishes the
    two, so nothing here is auto-applied.
    """

    @pytest.mark.asyncio
    async def test_apply_is_a_no_op_even_for_a_strict_local_match(self):
        ha = MagicMock()
        ha.rest.run_config_flow = AsyncMock()
        recipe = UnclaimedDevicesRecipe(MagicMock())

        result = await recipe.apply(ha)

        ha.rest.run_config_flow.assert_not_called()
        assert result.change_count == 0
        assert result.summary == "report-only"

    @pytest.mark.asyncio
    async def test_plan_is_always_empty(self):
        assert (await UnclaimedDevicesRecipe(MagicMock()).plan(MagicMock())).is_empty

    def test_candidate_carries_no_autonomy_verdict(self):
        """The removed heuristic must not come back by accident."""
        candidate = Candidate(
            "roborock",
            "Roborock",
            ObservedHost("B0:4A:39:00:00:66"),
            MatchStrength.STRICT,
            "local_polling",
        )

        assert not hasattr(candidate, "auto_applicable")
        assert not hasattr(candidate, "needs_account")


def _recipe_with(hosts: list[ObservedHost], configured: list[str], matchers: ManifestMatchers):
    observer = MagicMock()
    observer.observed_hosts = AsyncMock(return_value=hosts)
    recipe = UnclaimedDevicesRecipe(observer)

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
        assert "Add Integration" in result.human_action
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
