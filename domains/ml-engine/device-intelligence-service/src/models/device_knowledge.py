"""Device Knowledge - Database Models.

A claim-oriented store for what is known about a device *model* (vendor facts)
or a device *instance* (measurements taken on this home's hardware).

Every claim carries an explicit evidence class. The classes are ordered, and a
weaker claim never silently displaces a stronger one for the same fact key.
See ``docs/architecture/adr-device-knowledge-provenance.md``.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .database import Base


class SubjectKind(StrEnum):
    """What a claim is about.

    Conflating these two is the failure this table exists to prevent:
    "P21 is read-only" is a property of the model, while "P21 reads false on
    the Office dimmer" is a measurement of one instance.
    """

    MODEL = "model"
    INSTANCE = "instance"


class EvidenceClass(StrEnum):
    """How a claim is known. Ordered strongest to weakest by :data:`EVIDENCE_ORDER`."""

    MEASURED = "measured"
    UPSTREAM_SOURCE = "upstream_source"
    VENDOR_DOC = "vendor_doc"
    COMMUNITY = "community"
    INFERRED = "inferred"


#: Strongest first. The single definition of precedence in this service.
EVIDENCE_ORDER: tuple[EvidenceClass, ...] = (
    EvidenceClass.MEASURED,
    EvidenceClass.UPSTREAM_SOURCE,
    EvidenceClass.VENDOR_DOC,
    EvidenceClass.COMMUNITY,
    EvidenceClass.INFERRED,
)

#: Rank lookup derived from :data:`EVIDENCE_ORDER`; lower rank wins.
EVIDENCE_RANK: dict[str, int] = {
    evidence.value: rank for rank, evidence in enumerate(EVIDENCE_ORDER)
}


class ClaimType(StrEnum):
    """Whether the claim asserts knowledge or records a deliberate refusal.

    ``NOT_CLAIMED`` exists because a store that can only hold knowledge invites
    the next reader to invent the gaps.
    """

    KNOWN = "known"
    NOT_CLAIMED = "not_claimed"


def _values(enum_cls: type[StrEnum]) -> str:
    """Render an enum as a SQL ``IN`` list for a CHECK constraint."""
    return ", ".join(f"'{member.value}'" for member in enum_cls)


class DeviceKnowledgeClaim(Base):
    """One provenance-bearing claim about a device model or instance."""

    __tablename__ = "device_knowledge_claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Subject
    subject_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    subject_key: Mapped[str] = mapped_column(String(255), nullable=False)

    # Claim
    fact_key: Mapped[str] = mapped_column(String(255), nullable=False)
    fact_value: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ClaimType.KNOWN.value
    )
    caveat: Mapped[str | None] = mapped_column(Text)

    # Provenance
    evidence_class: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_ref: Mapped[str | None] = mapped_column(Text)
    source_version: Mapped[str | None] = mapped_column(String(255))
    source_quote: Mapped[str | None] = mapped_column(Text)
    method: Mapped[str | None] = mapped_column(String(255))
    confidence: Mapped[float | None] = mapped_column(Float)

    # Applicability. A fact without its firmware predicate misleads across versions.
    firmware_min: Mapped[str | None] = mapped_column(String(32))
    firmware_max: Mapped[str | None] = mapped_column(String(32))

    # Lifecycle
    recorded_by: Mapped[str] = mapped_column(String(128), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), index=True
    )
    superseded_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("device_knowledge_claims.id", ondelete="SET NULL"),
        index=True,
    )
    superseded_reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            f"subject_kind IN ({_values(SubjectKind)})",
            name="chk_dk_subject_kind",
        ),
        CheckConstraint(
            f"evidence_class IN ({_values(EvidenceClass)})",
            name="chk_dk_evidence_class",
        ),
        CheckConstraint(
            f"claim_type IN ({_values(ClaimType)})",
            name="chk_dk_claim_type",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)",
            name="chk_dk_confidence_range",
        ),
        Index("idx_dk_subject", "subject_kind", "subject_key"),
        Index("idx_dk_subject_fact", "subject_kind", "subject_key", "fact_key"),
    )

    @property
    def evidence_rank(self) -> int:
        """Sort key; lower wins. Unknown classes sort last rather than raising."""
        return EVIDENCE_RANK.get(self.evidence_class, len(EVIDENCE_ORDER))

    @property
    def is_active(self) -> bool:
        """True when this claim has not been superseded."""
        return self.superseded_by is None

    def __repr__(self) -> str:
        return f"<DeviceKnowledgeClaim {self.subject_key} {self.fact_key} [{self.evidence_class}]>"
