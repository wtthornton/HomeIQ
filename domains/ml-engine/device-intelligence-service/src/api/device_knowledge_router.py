"""Device Knowledge API.

Endpoints:
    POST /api/device-knowledge/claims          Record a provenance-bearing claim
    GET  /api/device-knowledge/models/{mfr}/{model}   Claims about a device model
    GET  /api/device-knowledge/resolve         Merged model + instance view

See ``docs/architecture/adr-device-knowledge-provenance.md``.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db_session
from ..models.device_knowledge import (
    ClaimType,
    DeviceKnowledgeClaim,
    EvidenceClass,
    SubjectKind,
)
from ..services.device_knowledge_service import (
    REQUIRED_PROVENANCE,
    DeviceKnowledgeService,
    ProvenanceRequired,
    normalize_model_key,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/device-knowledge", tags=["Device Knowledge"])


# ---------------------------------------------------------------- Request Models


class ClaimRequest(BaseModel):
    """A single claim about a device model or instance."""

    subject_kind: SubjectKind
    subject_key: str = Field(min_length=1, max_length=255)
    fact_key: str = Field(min_length=1, max_length=255)
    fact_value: str = Field(min_length=1)
    evidence_class: EvidenceClass
    claim_type: ClaimType = ClaimType.KNOWN

    caveat: str | None = None
    source_url: str | None = None
    source_ref: str | None = None
    source_version: str | None = Field(default=None, max_length=255)
    source_quote: str | None = None
    method: str | None = Field(default=None, max_length=255)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    firmware_min: str | None = Field(default=None, max_length=32)
    firmware_max: str | None = Field(default=None, max_length=32)
    recorded_by: str = Field(min_length=1, max_length=128)


# --------------------------------------------------------------- Response Models


class RecordResponse(BaseModel):
    """Outcome of recording a claim, including whether it was outranked."""

    claim_id: int
    accepted: bool
    outranked_by: int | None
    superseded_ids: list[int]
    reason: str


class ClaimResponse(BaseModel):
    """A stored claim as returned to callers."""

    id: int
    subject_kind: str
    subject_key: str
    fact_key: str
    fact_value: str
    claim_type: str
    evidence_class: str
    evidence_rank: int
    caveat: str | None
    source_url: str | None
    source_ref: str | None
    source_version: str | None
    source_quote: str | None
    method: str | None
    confidence: float | None
    firmware_min: str | None
    firmware_max: str | None
    recorded_by: str
    superseded_by: int | None


class SubjectClaimsResponse(BaseModel):
    """Claims about one subject, strongest evidence first."""

    subject_kind: str
    subject_key: str
    claims: list[ClaimResponse]
    count: int


class ResolveResponse(BaseModel):
    """Instance measurements layered over model knowledge."""

    instance_claims: list[ClaimResponse]
    model_claims: list[ClaimResponse]
    shadowed_model_claims: list[ClaimResponse]
    not_claimed: list[ClaimResponse]


def _serialize(claim: DeviceKnowledgeClaim) -> ClaimResponse:
    """Project an ORM claim onto its wire shape."""
    return ClaimResponse(
        id=claim.id,
        subject_kind=claim.subject_kind,
        subject_key=claim.subject_key,
        fact_key=claim.fact_key,
        fact_value=claim.fact_value,
        claim_type=claim.claim_type,
        evidence_class=claim.evidence_class,
        evidence_rank=claim.evidence_rank,
        caveat=claim.caveat,
        source_url=claim.source_url,
        source_ref=claim.source_ref,
        source_version=claim.source_version,
        source_quote=claim.source_quote,
        method=claim.method,
        confidence=claim.confidence,
        firmware_min=claim.firmware_min,
        firmware_max=claim.firmware_max,
        recorded_by=claim.recorded_by,
        superseded_by=claim.superseded_by,
    )


@router.post("/claims", response_model=RecordResponse, status_code=status.HTTP_201_CREATED)
async def record_claim(
    payload: ClaimRequest,
    session: AsyncSession = Depends(get_db_session),
) -> RecordResponse:
    """Record a claim. Refused when its evidence class lacks required provenance."""
    service = DeviceKnowledgeService(session)
    try:
        outcome = await service.record(**payload.model_dump())
    except ProvenanceRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": exc.code,
                "evidence_class": exc.evidence_class,
                "missing": exc.missing,
                "required_by_class": {k: list(v) for k, v in REQUIRED_PROVENANCE.items()},
            },
        ) from exc

    return RecordResponse(
        claim_id=outcome.claim_id,
        accepted=outcome.accepted,
        outranked_by=outcome.outranked_by,
        superseded_ids=outcome.superseded_ids,
        reason=outcome.reason,
    )


@router.get("/models/{manufacturer}/{model}", response_model=SubjectClaimsResponse)
async def get_model_claims(
    manufacturer: str,
    model: str,
    include_superseded: bool = Query(default=False),
    session: AsyncSession = Depends(get_db_session),
) -> SubjectClaimsResponse:
    """Everything known about a device model, strongest evidence first."""
    subject_key = normalize_model_key(manufacturer, model)
    service = DeviceKnowledgeService(session)
    claims = await service.claims_for_subject(
        SubjectKind.MODEL.value, subject_key, include_superseded=include_superseded
    )
    return SubjectClaimsResponse(
        subject_kind=SubjectKind.MODEL.value,
        subject_key=subject_key,
        claims=[_serialize(c) for c in claims],
        count=len(claims),
    )


@router.get("/resolve", response_model=ResolveResponse)
async def resolve_device_knowledge(
    manufacturer: str | None = Query(default=None),
    model: str | None = Query(default=None),
    instance_key: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> ResolveResponse:
    """Merge instance measurements over model knowledge for one device."""
    if not instance_key and not (manufacturer and model):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="supply instance_key, or both manufacturer and model",
        )

    service = DeviceKnowledgeService(session)
    resolved = await service.resolve_for_device(manufacturer, model, instance_key)
    return ResolveResponse(
        instance_claims=[_serialize(c) for c in resolved["instance_claims"]],
        model_claims=[_serialize(c) for c in resolved["model_claims"]],
        shadowed_model_claims=[_serialize(c) for c in resolved["shadowed_model_claims"]],
        not_claimed=[_serialize(c) for c in resolved["not_claimed"]],
    )
