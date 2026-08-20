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
    normalize_model_key,
    sort_claims,
)

BASE_TIME = datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC)


def make_claim(
    evidence_class: EvidenceClass,
    claim_id: int = 1,
    fact_key: str = "param.52.effect",
    age_minutes: int = 0,
) -> DeviceKnowledgeClaim:
    """Build an unpersisted claim for precedence tests."""
    return DeviceKnowledgeClaim(
        id=claim_id,
        subject_kind=SubjectKind.MODEL.value,
        subject_key="inovelli/vzm31-sn",
        fact_key=fact_key,
        fact_value="value",
        claim_type=ClaimType.KNOWN.value,
        evidence_class=evidence_class.value,
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
