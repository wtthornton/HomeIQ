"""Init-agent gateway: audit and converge via the libs/homeiq-ha engine.

Thin by design — every decision (what to check, what to change, phase order,
backup gating) lives in the engine and its recipes. This module only exposes
them over HTTP and serializes the report.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from homeiq_ha.agent import HAInitAgent
from homeiq_ha.agent.answers import Answers, apply_answers
from homeiq_ha.agent.backup import backup_taker
from homeiq_ha.agent.recipes import default_recipes
from homeiq_ha.agent.wizard import build_queue
from homeiq_ha.client import HAClient
from pydantic import BaseModel, ConfigDict, SecretStr

if TYPE_CHECKING:
    from homeiq_ha.agent.engine import RunReport

logger = logging.getLogger(__name__)

init_router = APIRouter(prefix="/api/v1/init", tags=["init-agent"])

#: The LAN wizard page (TAP-5944) lives outside the API prefix at /setup.
page_router = APIRouter(tags=["init-agent"])

_WIZARD_PAGE = Path(__file__).parent / "static" / "setup_wizard.html"


@page_router.get("/setup", include_in_schema=False)
async def setup_page() -> FileResponse:
    """The setup wizard: one self-contained page, no external assets."""
    return FileResponse(_WIZARD_PAGE, media_type="text/html")


class ConvergeRequest(BaseModel):
    """Optional narrowing of a converge run."""

    phase: int | None = None
    only: str | None = None


class DeviceAreaAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str
    area: str


class AddonOptionsAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    options: dict[str, Any]


class AnswersRequest(BaseModel):
    """The ha-human-actions-answers contract (TAP-5945).

    ``backup_password`` is a SecretStr: write-only by contract — set via
    backup/config/update, never logged, echoed, or persisted anywhere.
    An off-contract body must 422, not silently succeed as an empty
    submission — hence ``extra="forbid"`` here and on the nested answers.
    """

    model_config = ConfigDict(extra="forbid")

    device_areas: list[DeviceAreaAnswer] = []
    addon_options: list[AddonOptionsAnswer] = []
    teams: list[dict[str, str]] = []
    backup_password: SecretStr | None = None


def _serialize(report: RunReport) -> dict[str, Any]:
    return {
        "mode": report.mode.value,
        "total_changes": report.total_changes,
        "wrote_nothing": report.wrote_nothing,
        "halted_reason": report.halted_reason,
        "blocked_on_human": report.blocked_on_human,
        "read_calls": len(report.reads),
        "outcomes": [
            {
                "name": outcome.name,
                "phase": outcome.phase,
                "status": outcome.check.status.value,
                "summary": outcome.check.summary,
                "details": outcome.check.details,
                "human_action": outcome.check.human_action,
                "plan": [c.describe() for c in outcome.plan.changes] if outcome.plan else None,
                "applied": (
                    [c.describe() for c in outcome.applied.changed] if outcome.applied else None
                ),
                "verified": outcome.verified.ok if outcome.verified else None,
                "error": outcome.error,
            }
            for outcome in report.outcomes
        ],
    }


@init_router.get("/audit")
async def audit() -> dict[str, Any]:
    """Read-only audit of every recipe. Always safe to call."""
    agent = HAInitAgent(default_recipes())
    try:
        async with HAClient.from_env() as ha:
            report = await agent.audit(ha)
    except Exception as exc:
        logger.exception("init audit failed")
        raise HTTPException(status_code=502, detail=f"audit failed: {exc}") from exc
    return _serialize(report)


@init_router.get("/queue")
async def queue() -> dict[str, Any]:
    """The wizard's human-action queue: audit blocked rows + discovery flows.

    Read-only like /audit — assembly lives in homeiq_ha.agent.wizard behind
    the read-only proxy; the payload carries its read journal as evidence.
    """
    try:
        async with HAClient.from_env() as ha:
            return await build_queue(ha, default_recipes())
    except Exception as exc:
        logger.exception("init queue failed")
        raise HTTPException(status_code=502, detail=f"queue failed: {exc}") from exc


@init_router.post("/answers")
async def answers(body: AnswersRequest) -> dict[str, Any]:
    """Ingest one wizard submission, converge (backup-gated), verify by read-back.

    The manifest write lands on the repo's bind-mounted copy, so wizard
    decisions are durable and git-visible (commit them like any change).
    """
    contract = Answers(
        device_areas=tuple((d.device_id, d.area) for d in body.device_areas),
        addon_options=tuple((a.slug, a.options) for a in body.addon_options),
        teams=tuple(body.teams),
        backup_password=(
            body.backup_password.get_secret_value() if body.backup_password else None
        ),
    )
    try:
        async with HAClient.from_env() as ha:
            return await apply_answers(ha, contract, default_recipes)
    except Exception as exc:
        logger.exception("init answers failed")
        raise HTTPException(status_code=502, detail=f"answers failed: {exc}") from exc


@init_router.post("/converge")
async def converge(body: ConvergeRequest | None = None) -> dict[str, Any]:
    """Backup-gated plan+apply+verify run.

    The engine takes a backup before every phase past the gate; a converge
    without a reachable backup destination halts rather than proceeding.
    """
    body = body or ConvergeRequest()
    agent = HAInitAgent(default_recipes())
    try:
        async with HAClient.from_env() as ha:
            report = await agent.apply(
                ha, phase=body.phase, only=body.only, backup=backup_taker(ha)
            )
    except Exception as exc:
        logger.exception("init converge failed")
        raise HTTPException(status_code=502, detail=f"converge failed: {exc}") from exc
    return _serialize(report)
