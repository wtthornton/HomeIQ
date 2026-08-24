"""Tests for the non-automatable-issue catalogue.

The catalogue ships with the product and other installs read it, so the
invariants worth pinning are about completeness and honesty rather than
behaviour: every kind is described, every entry says what to do instead, and
the classifier maps live findings onto it without inventing a kind.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeiq_ha.agent.blockers import (
    BY_KIND,
    CATALOGUE,
    BlockerKind,
    classify_blocker,
    describe,
)
from homeiq_ha.agent.matchers import Candidate, MatchStrength
from homeiq_ha.agent.netobserve import ObservedHost
from homeiq_ha.agent.unclaimed import FlowProbe, UnclaimedDevicesRecipe


class TestCatalogueCompleteness:
    def test_every_kind_has_an_entry(self):
        """A classifier returning a kind with no entry would render as a blank row."""
        assert set(BY_KIND) == set(BlockerKind)

    def test_no_duplicate_kinds(self):
        assert len({entry.kind for entry in CATALOGUE}) == len(CATALOGUE)

    @pytest.mark.parametrize("entry", CATALOGUE, ids=lambda e: e.kind.value)
    def test_entry_tells_a_person_what_to_do(self, entry):
        """An entry that only says 'cannot' is a complaint, not documentation."""
        assert entry.workaround.strip()
        assert entry.why.strip()
        assert entry.detection.strip()

    @pytest.mark.parametrize("entry", CATALOGUE, ids=lambda e: e.kind.value)
    def test_entry_carries_a_concrete_example(self, entry):
        assert entry.example.strip(), f"{entry.kind} has no observed example"

    def test_describe_tolerates_a_raw_string(self):
        assert describe("oauth_external") is BY_KIND[BlockerKind.OAUTH_EXTERNAL]

    def test_describe_returns_none_for_an_unknown_kind(self):
        assert describe("not_a_real_kind") is None


def _candidate(strength: MatchStrength, ip: str | None = "192.168.1.10") -> Candidate:
    return Candidate("d", "D", ObservedHost("AA:BB:CC:00:00:01", ip), strength, "local_polling")


class TestClassifier:
    """Each branch maps to a catalogue kind, measured against real flow shapes."""

    def test_external_step_is_oauth(self):
        kind = classify_blocker(_candidate(MatchStrength.STRICT), FlowProbe("xbox", "external", ()))
        assert kind is BlockerKind.OAUTH_EXTERNAL

    def test_hostname_match_is_a_glob_collision(self):
        kind = classify_blocker(
            _candidate(MatchStrength.HOSTNAME), FlowProbe("flux_led", "form", ())
        )
        assert kind is BlockerKind.HOSTNAME_GLOB_COLLISION

    def test_hostname_match_outranks_the_flow_shape(self):
        """No flow shape makes a name safe, so the name check comes first."""
        kind = classify_blocker(
            _candidate(MatchStrength.HOSTNAME), FlowProbe("ring", "form", ("username",))
        )
        assert kind is BlockerKind.HOSTNAME_GLOB_COLLISION

    def test_mac_match_on_an_address_flow_is_weak_evidence(self):
        kind = classify_blocker(_candidate(MatchStrength.MAC), FlowProbe("tplink", "form", ()))
        assert kind is BlockerKind.WEAK_EVIDENCE_FOR_ADDRESS_FLOW

    def test_strict_address_flow_with_no_ip_is_not_observed(self):
        kind = classify_blocker(
            _candidate(MatchStrength.STRICT, ip=None), FlowProbe("wled", "form", ())
        )
        assert kind is BlockerKind.NOT_OBSERVED

    def test_account_flow_without_secrets_is_credentials_missing(self):
        kind = classify_blocker(
            _candidate(MatchStrength.MAC), FlowProbe("d", "form", ("username",)), None
        )
        assert kind is BlockerKind.CREDENTIALS_MISSING

    def test_nothing_blocks_a_fillable_address_flow(self):
        assert (
            classify_blocker(_candidate(MatchStrength.STRICT), FlowProbe("wled", "form", ()))
            is None
        )

    def test_nothing_blocks_an_account_flow_once_secrets_exist(self):
        assert (
            classify_blocker(
                _candidate(MatchStrength.MAC),
                FlowProbe("d", "form", ("username",)),
                {"username": "owner@example.com"},
            )
            is None
        )

    def test_every_returned_kind_is_in_the_catalogue(self):
        """The classifier must never emit a kind the catalogue cannot explain."""
        probes = [
            FlowProbe("d", "external", ()),
            FlowProbe("d", "progress", ()),
            FlowProbe("d", "form", ()),
            FlowProbe("d", "form", ("username",)),
            FlowProbe("d", "form", ("host",)),
        ]
        for strength in MatchStrength:
            for ip in ("192.168.1.10", None):
                for probe in probes:
                    kind = classify_blocker(_candidate(strength, ip), probe)
                    assert kind is None or kind in BY_KIND


class TestBlockerRows:
    @pytest.mark.asyncio
    async def test_row_names_the_fields_a_person_must_supply(self, monkeypatch):
        from homeiq_ha.agent.matchers import ManifestMatchers

        recipe = UnclaimedDevicesRecipe(MagicMock(), credentials={})
        host = ObservedHost("9C:76:13:00:00:11", "192.168.1.40", None, "Ring LLC")
        monkeypatch.setattr(
            UnclaimedDevicesRecipe,
            "_survey",
            AsyncMock(return_value=([Candidate("ring", "Ring", host, MatchStrength.MAC)], {})),
        )
        monkeypatch.setattr(
            "homeiq_ha.agent.unclaimed.probe_flow",
            AsyncMock(return_value=FlowProbe("ring", "form", ("username", "password"))),
        )
        assert ManifestMatchers  # imported for symmetry with the recipe's deps

        [row] = await recipe.blockers(MagicMock())

        assert row["blocker"] == BlockerKind.CREDENTIALS_MISSING.value
        assert row["required_fields"] == ["username", "password"]
        assert row["evidence"] == "MAC"
