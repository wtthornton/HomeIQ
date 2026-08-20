"""Tests for the device knowledge precedence rules.

These exercise the guarantee the store exists to provide: a weaker claim never
displaces a stronger one. The logic under test is pure, so no database is
required and the guarantee is provable in isolation.
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.models.device_knowledge import (
    EVIDENCE_ORDER,
    EVIDENCE_RANK,
    ClaimType,
    DeviceKnowledgeClaim,
    EvidenceClass,
    SubjectKind,
)
from src.services.device_knowledge_service import (
    REQUIRED_PROVENANCE,
    ProvenanceRequired,
    _validate_provenance,
    decide_precedence,
    firmware_ranges_overlap,
    normalize_model_key,
    sort_claims,
)

BASE_TIME = datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC)


def make_claim(
    evidence_class: EvidenceClass,
    claim_id: int = 1,
    fact_key: str = "param.52.effect",
    age_minutes: int = 0,
    claim_type: ClaimType = ClaimType.KNOWN,
    firmware_min: str | None = None,
    firmware_max: str | None = None,
) -> DeviceKnowledgeClaim:
    """Build an unpersisted claim for precedence tests."""
    return DeviceKnowledgeClaim(
        id=claim_id,
        subject_kind=SubjectKind.MODEL.value,
        subject_key="inovelli/vzm31-sn",
        fact_key=fact_key,
        fact_value="value",
        claim_type=claim_type.value,
        evidence_class=evidence_class.value,
        firmware_min=firmware_min,
        firmware_max=firmware_max,
        recorded_by="test",
        recorded_at=BASE_TIME - timedelta(minutes=age_minutes),
    )


class TestEvidenceOrdering:
    """The ordering itself must be total and stable."""

    def test_every_evidence_class_is_ranked(self):
        assert set(EVIDENCE_RANK) == {member.value for member in EvidenceClass}

    def test_ranks_are_unique_and_dense(self):
        assert sorted(EVIDENCE_RANK.values()) == list(range(len(EvidenceClass)))

    def test_measured_is_strongest_and_inferred_weakest(self):
        assert EVIDENCE_ORDER[0] is EvidenceClass.MEASURED
        assert EVIDENCE_ORDER[-1] is EvidenceClass.INFERRED

    def test_sort_puts_strongest_first(self):
        claims = [
            make_claim(EvidenceClass.INFERRED, 1),
            make_claim(EvidenceClass.MEASURED, 2),
            make_claim(EvidenceClass.VENDOR_DOC, 3),
        ]
        assert [c.id for c in sort_claims(claims)] == [2, 3, 1]

    def test_equal_evidence_breaks_tie_on_recency(self):
        older = make_claim(EvidenceClass.MEASURED, 1, age_minutes=60)
        newer = make_claim(EvidenceClass.MEASURED, 2, age_minutes=0)
        assert [c.id for c in sort_claims([older, newer])] == [2, 1]


class TestPrecedence:
    """The rule that would have prevented the Inovelli episode."""

    def test_inference_never_displaces_a_measurement(self):
        measured = make_claim(EvidenceClass.MEASURED, 1)
        decision = decide_precedence([measured], EvidenceClass.INFERRED.value)
        assert decision.outranked_by is measured
        assert decision.to_supersede == []

    def test_measurement_supersedes_an_inference(self):
        inferred = make_claim(EvidenceClass.INFERRED, 1)
        decision = decide_precedence([inferred], EvidenceClass.MEASURED.value)
        assert decision.outranked_by is None
        assert decision.to_supersede == [inferred]

    def test_first_claim_stands_alone(self):
        decision = decide_precedence([], EvidenceClass.VENDOR_DOC.value)
        assert decision.outranked_by is None
        assert decision.to_supersede == []

    def test_equal_strength_claims_coexist(self):
        incumbent = make_claim(EvidenceClass.MEASURED, 1)
        decision = decide_precedence([incumbent], EvidenceClass.MEASURED.value)
        assert decision.outranked_by is None
        assert decision.to_supersede == []

    def test_only_strictly_weaker_incumbents_are_superseded(self):
        stronger = make_claim(EvidenceClass.UPSTREAM_SOURCE, 1)
        weaker = make_claim(EvidenceClass.COMMUNITY, 2)
        decision = decide_precedence(
            [stronger, weaker], EvidenceClass.VENDOR_DOC.value
        )
        assert decision.outranked_by is stronger
        assert decision.to_supersede == []

    def test_supersedes_all_weaker_when_nothing_is_stronger(self):
        weak_a = make_claim(EvidenceClass.COMMUNITY, 1)
        weak_b = make_claim(EvidenceClass.INFERRED, 2)
        decision = decide_precedence(
            [weak_a, weak_b], EvidenceClass.UPSTREAM_SOURCE.value
        )
        assert decision.outranked_by is None
        assert {c.id for c in decision.to_supersede} == {1, 2}

    @pytest.mark.parametrize("evidence", list(EvidenceClass))
    def test_unknown_incumbent_class_sorts_last_and_never_outranks(self, evidence):
        rogue = make_claim(EvidenceClass.MEASURED, 9)
        rogue.evidence_class = "not_a_real_class"
        decision = decide_precedence([rogue], evidence.value)
        assert decision.outranked_by is None


class TestProvenanceEnforcement:
    """A claim that cannot say how it is known is refused."""

    def test_measured_requires_a_method(self):
        with pytest.raises(ProvenanceRequired) as exc:
            _validate_provenance(EvidenceClass.MEASURED.value, {})
        assert exc.value.code == "provenance_required"
        assert exc.value.missing == ["method"]

    def test_upstream_source_requires_ref_and_version(self):
        with pytest.raises(ProvenanceRequired) as exc:
            _validate_provenance(
                EvidenceClass.UPSTREAM_SOURCE.value, {"source_ref": "a.py:1"}
            )
        assert exc.value.missing == ["source_version"]

    def test_vendor_doc_requires_a_url(self):
        with pytest.raises(ProvenanceRequired):
            _validate_provenance(EvidenceClass.VENDOR_DOC.value, {"source_ref": "x"})

    def test_inferred_needs_no_source(self):
        _validate_provenance(EvidenceClass.INFERRED.value, {})

    def test_blank_string_does_not_satisfy_a_requirement(self):
        with pytest.raises(ProvenanceRequired):
            _validate_provenance(EvidenceClass.VENDOR_DOC.value, {"source_url": "  "})

    def test_every_evidence_class_declares_its_requirements(self):
        assert set(REQUIRED_PROVENANCE) == {member.value for member in EvidenceClass}


class TestRefusalPrecedence:
    """`not_claimed` is a first-class refusal — never displaced by a guess,
    never displacing knowledge (ADR section 3)."""

    def test_a_refusal_never_supersedes_a_known_claim(self):
        # The erasure bug: a measured "we could not determine this" used to
        # supersede a cited vendor_doc statement of the fact.
        documented = make_claim(EvidenceClass.VENDOR_DOC, 1)
        decision = decide_precedence(
            [documented],
            EvidenceClass.MEASURED.value,
            ClaimType.NOT_CLAIMED.value,
        )
        assert decision.to_supersede == []
        assert decision.outranked_by is None  # orthogonal, so also not outranked

    def test_a_known_claim_at_equal_evidence_resolves_a_refusal(self):
        refusal = make_claim(
            EvidenceClass.MEASURED, 1, claim_type=ClaimType.NOT_CLAIMED
        )
        decision = decide_precedence([refusal], EvidenceClass.MEASURED.value)
        assert decision.to_supersede == [refusal]

    def test_a_weaker_known_claim_is_blocked_by_a_stronger_refusal(self):
        # Filling the gap with less evidence than it took to declare the gap
        # is exactly the invention the store exists to prevent.
        refusal = make_claim(
            EvidenceClass.MEASURED, 1, claim_type=ClaimType.NOT_CLAIMED
        )
        decision = decide_precedence([refusal], EvidenceClass.INFERRED.value)
        assert decision.outranked_by is refusal
        assert decision.to_supersede == []

    def test_refusals_compete_with_each_other_on_evidence(self):
        weak_refusal = make_claim(
            EvidenceClass.INFERRED, 1, claim_type=ClaimType.NOT_CLAIMED
        )
        decision = decide_precedence(
            [weak_refusal],
            EvidenceClass.MEASURED.value,
            ClaimType.NOT_CLAIMED.value,
        )
        assert decision.to_supersede == [weak_refusal]


class TestFirmwareBoundaries:
    """Precedence never crosses a provably disjoint firmware range."""

    def test_disjoint_ranges_do_not_overlap(self):
        assert not firmware_ranges_overlap("3.00", None, None, "1.9")
        assert not firmware_ranges_overlap(None, "1.9", "3.00", None)

    def test_adjacent_and_intersecting_ranges_overlap(self):
        assert firmware_ranges_overlap("1.0", "2.0", "2.0", "3.0")
        assert firmware_ranges_overlap("1.0", "2.5", "2.0", "3.0")

    def test_unbounded_ranges_overlap_everything(self):
        assert firmware_ranges_overlap(None, None, "1.0", "1.5")
        assert firmware_ranges_overlap(None, None, None, None)

    def test_versions_compare_numerically_not_lexically(self):
        # "10.0" < "2.0" as strings; must not be treated as disjoint that way.
        assert firmware_ranges_overlap("10.0", None, None, "9.0") is False
        assert firmware_ranges_overlap("2.0", None, None, "10.0") is True

    def test_unparseable_versions_cannot_prove_disjointness(self):
        assert firmware_ranges_overlap("beta", None, None, "1.0")

    def test_record_scenario_measurement_on_new_firmware_spares_old_claim(self):
        """The cross-firmware supersession bug, as decide_precedence sees it
        after record() filters to overlapping ranges: the pre-3.00 vendor_doc
        claim is not comparable with a 3.00+ measurement, so it survives."""
        old_fw_doc = make_claim(EvidenceClass.VENDOR_DOC, 1, firmware_max="1.9")
        comparable = [
            c
            for c in [old_fw_doc]
            if firmware_ranges_overlap("3.00", None, c.firmware_min, c.firmware_max)
        ]
        assert comparable == []
        decision = decide_precedence(comparable, EvidenceClass.MEASURED.value)
        assert decision.to_supersede == []


class TestModelKeyNormalization:
    """Model keys must collapse case and spacing so lookups do not miss."""

    @pytest.mark.parametrize(
        "manufacturer,model",
        [("Inovelli", "VZM31-SN"), ("inovelli", "vzm31-sn"), ("  Inovelli ", " VZM31-SN ")],
    )
    def test_variants_collapse_to_one_key(self, manufacturer, model):
        assert normalize_model_key(manufacturer, model) == "inovelli/vzm31-sn"

    def test_distinct_models_do_not_collide(self):
        assert normalize_model_key("Inovelli", "VZM31-SN") != normalize_model_key(
            "Inovelli", "VZM35-SN"
        )
