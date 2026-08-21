"""Device-knowledge onboarding: what still needs looking up, and dispatching it.

Two entry points onto the same cache-first plan, because setup and steady state
want the same discipline for different reasons:

* ``GET /api/onboarding/plan`` — what a lookup would cost right now, and why.
  Read-only and free. The setup routine calls this to show a person the bill
  before anything is spent.
* ``POST /api/onboarding/run`` — dispatch the lookups. Bounded by ``limit`` so a
  first-time sweep over an unfamiliar home cannot run away.

The gene is not asked to decide whether it should run. `plan_onboarding` applies
the cache first, because a gene invoked only to report `cache_hits` still costs a
model call. On this instance that filter is most of the work: of 40 candidate
models, 14 are Home Assistant service entries with no product to look up and the
rest are increasingly answered by the store as it fills.
"""

# No `from __future__ import annotations` here, deliberately: FastAPI resolves
# Depends annotations at runtime, so AsyncSession must stay a runtime import.
# The other routers in this service are written the same way.

import logging
import os
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db_session
from ..services.device_onboarding import (
    DEFAULT_WANTED_FACTS,
    OnboardingCandidate,
    plan_onboarding,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["Device Onboarding"])


class CandidateOut(BaseModel):
    subject_key: str
    device_count: int
    gaps: list[str]
    cached_facts: int
    signature: dict[str, Any]


class PlanOut(BaseModel):
    models_total: int
    models_answered: int
    models_needing_lookup: int
    wanted_facts: list[str]
    candidates: list[CandidateOut]


async def _load_plan(
    session: AsyncSession,
    *,
    only_subjects: set[str] | None = None,
) -> tuple[list[OnboardingCandidate], int]:
    """Read devices, their entity domains and the claim store, then plan."""
    devices = [
        dict(row._mapping)
        for row in await session.execute(
            text(
                "SELECT id, manufacturer, model, integration, zigbee_ieee, entry_type FROM devices"
            )
        )
    ]

    domains: dict[str, list[str]] = {}
    for row in await session.execute(
        text(
            "SELECT device_id, split_part(entity_id, '.', 1) AS domain "
            "FROM device_entities WHERE device_id IS NOT NULL "
            "AND (entity_category IS NULL OR entity_category NOT IN ('diagnostic','config'))"
        )
    ):
        domains.setdefault(str(row.device_id), []).append(str(row.domain))

    claims: dict[str, list[dict[str, Any]]] = {}
    for row in await session.execute(
        text(
            "SELECT subject_key, fact_key, fact_value, evidence_class "
            "FROM device_knowledge_claims "
            "WHERE subject_kind = 'model' AND superseded_by IS NULL"
        )
    ):
        claims.setdefault(str(row.subject_key), []).append(
            {
                "fact_key": row.fact_key,
                "fact_value": row.fact_value,
                "evidence_class": row.evidence_class,
            }
        )

    candidates = plan_onboarding(devices, domains, claims, only_subjects=only_subjects)
    return candidates, len(claims)


@router.get("/plan", response_model=PlanOut)
async def get_onboarding_plan(
    session: AsyncSession = Depends(get_db_session),
) -> PlanOut:
    """What still needs a knowledge lookup, and what the cache already answers.

    Read-only and free. Nothing here invokes a gene; the point is to know the
    bill before deciding to pay it.
    """
    candidates, answered = await _load_plan(session)
    return PlanOut(
        models_total=answered + len(candidates),
        models_answered=answered,
        models_needing_lookup=len(candidates),
        wanted_facts=list(DEFAULT_WANTED_FACTS),
        candidates=[
            CandidateOut(
                subject_key=c.subject_key,
                device_count=c.device_count,
                gaps=list(c.gaps),
                cached_facts=len(c.cached_fact_keys),
                signature=c.signature,
            )
            for c in candidates
        ],
    )


class DispatchedOut(BaseModel):
    subject_key: str
    run_id: str | None
    gaps: list[str]
    error: str | None = None


class RunOut(BaseModel):
    dispatched: list[DispatchedOut]
    models_needing_lookup: int
    limit: int


AGENTFORGE_URL = os.environ.get("AGENTFORGE_URL", "http://172.17.0.1:8010")
ONBOARD_WORKFLOW = "device-onboard"


async def _dispatch(client: httpx.AsyncClient, candidate: OnboardingCandidate) -> DispatchedOut:
    """Kick off one onboarding run, without waiting for it.

    `kickoff: async` because a run takes about a minute and executes on
    agentforge-main rather than on the replica that accepts the call. Blocking a
    request handler on work happening elsewhere would buy nothing.
    """
    try:
        response = await client.post(
            f"/projects/homeiq/workflows/{ONBOARD_WORKFLOW}/run",
            json={
                "inputs": {
                    "signature": candidate.signature,
                    "subject_key": candidate.subject_key,
                    "known": candidate.known,
                    "wanted": list(candidate.gaps),
                },
                "kickoff": "async",
            },
        )
        response.raise_for_status()
        return DispatchedOut(
            subject_key=candidate.subject_key,
            run_id=response.json().get("run_id"),
            gaps=list(candidate.gaps),
        )
    except Exception as exc:
        # One model failing to dispatch must not abandon the rest of the sweep.
        logger.warning("Could not dispatch onboarding for %s: %s", candidate.subject_key, exc)
        return DispatchedOut(
            subject_key=candidate.subject_key,
            run_id=None,
            gaps=list(candidate.gaps),
            error=str(exc),
        )


@router.post("/run", response_model=RunOut)
async def run_onboarding(
    limit: int = Query(default=5, ge=1, le=50),
    session: AsyncSession = Depends(get_db_session),
) -> RunOut:
    """Dispatch lookups for the models the cache cannot answer.

    Bounded by `limit` on purpose. A first-time sweep over an unfamiliar home
    faces every model at once, and the honest default is to do a few, let a
    person look at what came back, and continue — rather than discover the size
    of the bill afterwards.

    Ordered biggest-population-first, so a budget that runs out runs out on the
    long tail rather than on the model behind twenty devices.

    Each run ends at hiq-device-kb-curator. Its `approved` array is the complete
    set of claim bodies that may be written, and the relay that posts them adds no
    judgement of its own — the write path is an approval chokepoint, not a network
    one.
    """
    candidates, _ = await _load_plan(session)
    selected = candidates[:limit]
    if not selected:
        return RunOut(dispatched=[], models_needing_lookup=0, limit=limit)

    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("AGENTFORGE_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient(base_url=AGENTFORGE_URL, headers=headers, timeout=30.0) as client:
        dispatched = [await _dispatch(client, candidate) for candidate in selected]

    logger.info(
        "Device onboarding: dispatched %d of %d model(s) needing a lookup",
        sum(1 for d in dispatched if d.run_id),
        len(candidates),
    )
    return RunOut(dispatched=dispatched, models_needing_lookup=len(candidates), limit=limit)
