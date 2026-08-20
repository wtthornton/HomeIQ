"""Device Knowledge - provenance-aware claim store.

Enforces, server-side, the two rules that give the store its value:

1. **Provenance is mandatory and class-appropriate.** A claim that cannot say
   how it is known is refused, with a machine-readable code.
2. **A weaker claim never displaces a stronger one.** Recording an ``inferred``
   claim alongside a ``measured`` one stores it and ranks it below; only a
   strictly stronger claim supersedes.

Callers read the outcome. They do not re-derive the ordering.
"""

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.device_knowledge import (
    EVIDENCE_RANK,
    ClaimType,
    DeviceKnowledgeClaim,
    EvidenceClass,
    SubjectKind,
)

logger = logging.getLogger(__name__)

#: Provenance each evidence class must supply. A claim missing these is refused.
REQUIRED_PROVENANCE: dict[str, tuple[str, ...]] = {
    EvidenceClass.MEASURED.value: ("method",),
    EvidenceClass.UPSTREAM_SOURCE.value: ("source_ref", "source_version"),
    EvidenceClass.VENDOR_DOC.value: ("source_url",),
    EvidenceClass.COMMUNITY.value: ("source_url",),
    EvidenceClass.INFERRED.value: (),
}


class ProvenanceRequired(ValueError):
    """Raised when a claim omits the provenance its evidence class demands."""

    def __init__(self, evidence_class: str, missing: list[str]) -> None:
        self.code = "provenance_required"
        self.evidence_class = evidence_class
        self.missing = missing
        super().__init__(
            f"evidence_class '{evidence_class}' requires {', '.join(missing)}"
        )


@dataclass(frozen=True)
class RecordOutcome:
    """What the store did with a submitted claim, and why."""

    claim_id: int
    accepted: bool
    outranked_by: int | None
    superseded_ids: list[int]
    reason: str


def normalize_model_key(manufacturer: str, model: str) -> str:
    """Build the canonical subject key for a model, e.g. ``inovelli/vzm31-sn``."""
    return f"{manufacturer.strip().lower()}/{model.strip().lower()}"


def _rank(evidence_class: str) -> int:
    """Rank for an evidence class; unknown classes sort last."""
    return EVIDENCE_RANK.get(evidence_class, len(EVIDENCE_RANK))


def sort_claims(claims: list[DeviceKnowledgeClaim]) -> list[DeviceKnowledgeClaim]:
    """Strongest evidence first, then most recently recorded."""
    return sorted(
        claims,
        key=lambda claim: (_rank(claim.evidence_class), -claim.recorded_at.timestamp()),
    )


@dataclass(frozen=True)
class PrecedenceDecision:
    """What incumbent claims imply for a newly submitted one.

    Pure and side-effect free so the rule can be proven without a database.
    """

    outranked_by: DeviceKnowledgeClaim | None
    to_supersede: list[DeviceKnowledgeClaim]


def decide_precedence(
    incumbents: list[DeviceKnowledgeClaim], new_evidence_class: str
) -> PrecedenceDecision:
    """Apply evidence ordering to a new claim against the active incumbents.

    A strictly stronger incumbent outranks the newcomer and nothing is
    superseded. Otherwise every strictly weaker incumbent is superseded.
    Equal-strength claims coexist: two measurements may legitimately disagree,
    and silently dropping one would hide the disagreement.
    """
    new_rank = _rank(new_evidence_class)
    stronger = [c for c in incumbents if _rank(c.evidence_class) < new_rank]
    if stronger:
        return PrecedenceDecision(outranked_by=sort_claims(stronger)[0], to_supersede=[])
    weaker = [c for c in incumbents if _rank(c.evidence_class) > new_rank]
    return PrecedenceDecision(outranked_by=None, to_supersede=weaker)


def _is_supplied(value: Any) -> bool:
    """True when a provenance field carries real content.

    Whitespace does not count: a blank source URL is an unbacked claim wearing
    the costume of a cited one.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _validate_provenance(evidence_class: str, fields: dict[str, Any]) -> None:
    """Refuse a claim whose evidence class is unbacked by the required fields."""
    required = REQUIRED_PROVENANCE.get(evidence_class, ())
    missing = [name for name in required if not _is_supplied(fields.get(name))]
    if missing:
        raise ProvenanceRequired(evidence_class, missing)


class DeviceKnowledgeService:
    """Session-bound access to the device knowledge claim store."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _active_claims_for_fact(
        self, subject_kind: str, subject_key: str, fact_key: str
    ) -> list[DeviceKnowledgeClaim]:
        """Every non-superseded claim competing for one fact key."""
        stmt = select(DeviceKnowledgeClaim).where(
            DeviceKnowledgeClaim.subject_kind == subject_kind,
            DeviceKnowledgeClaim.subject_key == subject_key,
            DeviceKnowledgeClaim.fact_key == fact_key,
            DeviceKnowledgeClaim.superseded_by.is_(None),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def record(self, **fields: Any) -> RecordOutcome:
        """Store a claim, applying evidence precedence.

        The claim is always persisted. What varies is whether it supersedes the
        incumbents, is outranked by them, or stands alone.
        """
        evidence_class = fields["evidence_class"]
        _validate_provenance(evidence_class, fields)

        incumbents = await self._active_claims_for_fact(
            fields["subject_kind"], fields["subject_key"], fields["fact_key"]
        )
        decision = decide_precedence(incumbents, evidence_class)

        claim = DeviceKnowledgeClaim(**fields)
        self.session.add(claim)
        await self.session.flush()

        if decision.outranked_by is not None:
            best = decision.outranked_by
            await self.session.commit()
            return RecordOutcome(
                claim_id=claim.id,
                accepted=True,
                outranked_by=best.id,
                superseded_ids=[],
                reason=(
                    f"stored, but outranked by claim {best.id} "
                    f"({best.evidence_class} beats {evidence_class})"
                ),
            )

        for incumbent in decision.to_supersede:
            incumbent.superseded_by = claim.id
            incumbent.superseded_reason = (
                f"superseded by stronger evidence: {evidence_class}"
            )
        await self.session.commit()

        superseded = [c.id for c in decision.to_supersede]
        return RecordOutcome(
            claim_id=claim.id,
            accepted=True,
            outranked_by=None,
            superseded_ids=superseded,
            reason=(
                f"superseded {len(superseded)} weaker claim(s)" if superseded else "recorded"
            ),
        )

    async def claims_for_subject(
        self, subject_kind: str, subject_key: str, include_superseded: bool = False
    ) -> list[DeviceKnowledgeClaim]:
        """All claims about one subject, strongest evidence first."""
        stmt = select(DeviceKnowledgeClaim).where(
            DeviceKnowledgeClaim.subject_kind == subject_kind,
            DeviceKnowledgeClaim.subject_key == subject_key,
        )
        if not include_superseded:
            stmt = stmt.where(DeviceKnowledgeClaim.superseded_by.is_(None))
        result = await self.session.execute(stmt)
        return sort_claims(list(result.scalars().all()))

    async def resolve_for_device(
        self,
        manufacturer: str | None,
        model: str | None,
        instance_key: str | None,
    ) -> dict[str, Any]:
        """Merge model knowledge with instance measurements for one device.

        Instance claims win on a fact-key collision: a measurement of *this*
        hardware beats a general statement about the model.
        """
        model_claims: list[DeviceKnowledgeClaim] = []
        if manufacturer and model:
            model_claims = await self.claims_for_subject(
                SubjectKind.MODEL.value, normalize_model_key(manufacturer, model)
            )

        instance_claims: list[DeviceKnowledgeClaim] = []
        if instance_key:
            instance_claims = await self.claims_for_subject(
                SubjectKind.INSTANCE.value, instance_key
            )

        instance_fact_keys = {claim.fact_key for claim in instance_claims}
        shadowed = [c for c in model_claims if c.fact_key in instance_fact_keys]

        return {
            "instance_claims": instance_claims,
            "model_claims": [c for c in model_claims if c.fact_key not in instance_fact_keys],
            "shadowed_model_claims": shadowed,
            "not_claimed": [
                c
                for c in (instance_claims + model_claims)
                if c.claim_type == ClaimType.NOT_CLAIMED.value
            ],
        }
