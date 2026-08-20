"""Device Knowledge - provenance-aware claim store.

Enforces, server-side, the rules that give the store its value:

1. **Provenance is mandatory and class-appropriate.** A claim that cannot say
   how it is known is refused, with a machine-readable code.
2. **A weaker claim never displaces a stronger one.** Recording an ``inferred``
   claim alongside a ``measured`` one stores it and ranks it below; only a
   strictly stronger claim supersedes.
3. **Precedence stays inside a firmware boundary.** Claims whose firmware
   ranges are provably disjoint describe different populations of devices, so
   neither supersedes nor outranks the other — "P52 forces full-wave" on 3.00+
   does not displace the pre-3.00 statement (see the ADR's consequences
   section).
4. **A refusal is not displaced by a guess.** ``not_claimed`` records "we
   deliberately do not know X". Knowledge and refusals are orthogonal: a
   refusal never supersedes a ``known`` claim, and only a ``known`` claim at
   equal-or-stronger evidence resolves a refusal. A weaker known claim is
   blocked by the refusal — filling the gap with less evidence than it took to
   declare the gap is exactly the invention the ADR forbids.

Callers read the outcome. They do not re-derive the ordering.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select, text
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


def _version_key(version: str) -> tuple[int, ...] | None:
    """Numeric components of a firmware version, or None when unparseable.

    "2.19" -> (2, 19); "v3.00-beta1" -> (3, 0, 1). Tuple comparison then gives
    the ordering a naive string compare gets wrong ("10.0" < "2.0").
    """
    numbers = re.findall(r"\d+", version)
    return tuple(int(n) for n in numbers) if numbers else None


def firmware_ranges_overlap(
    a_min: str | None,
    a_max: str | None,
    b_min: str | None,
    b_max: str | None,
) -> bool:
    """True unless the two firmware ranges are PROVABLY disjoint.

    None bounds are unbounded, and an unparseable version cannot prove
    disjointness — both err toward overlap, because treating two claims as
    comparable is the pre-existing behaviour while wrongly splitting them
    would let contradictory active claims accumulate unranked.
    """

    def provably_before(hi: str | None, lo: str | None) -> bool:
        if hi is None or lo is None:
            return False
        hi_key, lo_key = _version_key(hi), _version_key(lo)
        if hi_key is None or lo_key is None:
            return False
        return hi_key < lo_key

    return not (provably_before(a_max, b_min) or provably_before(b_max, a_min))


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
    incumbents: list[DeviceKnowledgeClaim],
    new_evidence_class: str,
    new_claim_type: str = ClaimType.KNOWN.value,
) -> PrecedenceDecision:
    """Apply evidence ordering to a new claim against the active incumbents.

    Callers pass only incumbents the newcomer is comparable with (same fact
    key, overlapping firmware range — see :func:`firmware_ranges_overlap`).

    Among ``known`` claims: a strictly stronger incumbent outranks the
    newcomer and nothing is superseded; otherwise every strictly weaker
    incumbent is superseded. Equal-strength claims coexist: two measurements
    may legitimately disagree, and silently dropping one would hide the
    disagreement.

    ``not_claimed`` refusals are orthogonal to knowledge. A refusal competes
    only with other refusals — it never supersedes or outranks a ``known``
    claim, however strong its evidence, because "we could not determine X"
    does not falsify a cited statement of X. A ``known`` newcomer resolves a
    refusal at equal-or-stronger evidence; against a strictly stronger
    refusal it is stored but outranked, since filling a gap with less
    evidence than it took to declare the gap is invention.
    """
    new_rank = _rank(new_evidence_class)
    refusals = [c for c in incumbents if c.claim_type == ClaimType.NOT_CLAIMED.value]

    if new_claim_type == ClaimType.NOT_CLAIMED.value:
        stronger = [c for c in refusals if _rank(c.evidence_class) < new_rank]
        if stronger:
            return PrecedenceDecision(
                outranked_by=sort_claims(stronger)[0], to_supersede=[]
            )
        weaker = [c for c in refusals if _rank(c.evidence_class) > new_rank]
        return PrecedenceDecision(outranked_by=None, to_supersede=weaker)

    known = [c for c in incumbents if c.claim_type != ClaimType.NOT_CLAIMED.value]
    blockers = [c for c in known if _rank(c.evidence_class) < new_rank]
    blockers += [c for c in refusals if _rank(c.evidence_class) < new_rank]
    if blockers:
        return PrecedenceDecision(outranked_by=sort_claims(blockers)[0], to_supersede=[])
    to_supersede = [c for c in known if _rank(c.evidence_class) > new_rank]
    to_supersede += [c for c in refusals if _rank(c.evidence_class) >= new_rank]
    return PrecedenceDecision(outranked_by=None, to_supersede=to_supersede)


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

        # Serialize concurrent records for the same fact. Without this, two
        # simultaneous inserts each read an empty incumbent set and both land
        # active with the weaker one never marked superseded. The advisory
        # lock is transaction-scoped, so the commit below releases it.
        bind = self.session.get_bind()
        if bind is not None and bind.dialect.name == "postgresql":
            lock_key = ":".join(
                (fields["subject_kind"], fields["subject_key"], fields["fact_key"])
            )
            await self.session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                {"key": lock_key},
            )

        incumbents = await self._active_claims_for_fact(
            fields["subject_kind"], fields["subject_key"], fields["fact_key"]
        )
        # Claims for provably disjoint firmware ranges describe different
        # devices; they neither block nor get superseded by this one.
        comparable = [
            c
            for c in incumbents
            if firmware_ranges_overlap(
                fields.get("firmware_min"),
                fields.get("firmware_max"),
                c.firmware_min,
                c.firmware_max,
            )
        ]
        claim_type = fields.get("claim_type") or ClaimType.KNOWN.value
        decision = decide_precedence(comparable, evidence_class, claim_type)

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
            if incumbent.claim_type == ClaimType.NOT_CLAIMED.value:
                incumbent.superseded_reason = (
                    f"refusal resolved by known claim at equal-or-stronger "
                    f"evidence: {evidence_class}"
                )
            else:
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
