"""Init-agent gateway: audit and converge via the libs/homeiq-ha engine.

Thin by design — every decision (what to check, what to change, phase order,
backup gating) lives in the engine and its recipes. This module only exposes
them over HTTP and serializes the report.
"""

from __future__ import annotations

import ipaddress
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from homeiq_ha.agent import HAInitAgent
from homeiq_ha.agent.answers import Answers, apply_answers
from homeiq_ha.agent.backup import backup_taker
from homeiq_ha.agent.recipes import default_recipes
from homeiq_ha.agent.triage import DEFAULT_TRIAGE_STORE_PATH, LaterStore, apply_decision
from homeiq_ha.agent.triggers import (
    PERMIT_MAX_DURATION,
    advance_to_readiness,
    open_permit_window,
    start_hacs,
)
from homeiq_ha.agent.wizard import build_queue
from homeiq_ha.client import HAClient
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from .config import get_settings

if TYPE_CHECKING:
    from homeiq_ha.agent.engine import RunReport

logger = logging.getLogger(__name__)


def _bare_host(hostport: str) -> str:
    """The host part of a Host/Origin authority, port stripped, lowercased.

    Handles bracketed IPv6 (``[::1]:8024``); a bare multi-colon value is a
    portless IPv6 literal and passes through whole.
    """
    value = hostport.strip().lower()
    if value.startswith("["):
        return value.partition("]")[0].lstrip("[")
    if value.count(":") > 1:
        return value
    return value.rsplit(":", 1)[0]


def _host_allowed(hostport: str, extra: frozenset[str]) -> bool:
    """The DNS-rebinding policy (TAP-6035).

    A rebinding attack must present the attacker's DNS *name* in Host (the
    browser resolves evil.example to the LAN IP, but the header carries the
    name). So: IP literals and localhost always pass — they cannot be
    rebound — and any DNS name must be explicitly expected via settings.
    """
    if not hostport:
        return False
    if hostport.strip().lower() in extra:
        return True  # exact host:port entry
    host = _bare_host(hostport)
    if host in extra or host == "localhost":
        return True
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def _expected_hosts() -> frozenset[str]:
    """Operator-configured extra hosts (``EXPECTED_HOSTS``), lowered.

    A bare ``host`` entry matches that name on any port; a ``host:port``
    entry pins that exact authority only (a portless request Host will NOT
    match it — prefer bare entries unless the port matters).
    """
    raw = get_settings().expected_hosts or ""
    return frozenset(h.strip().lower() for h in raw.split(",") if h.strip())


async def same_origin_only(request: Request) -> None:
    """Refuse rebindable or cross-origin browser POSTs to init write endpoints.

    Two checks, both against the expected-host policy rather than against
    each other — comparing Origin to the request's own Host let a DNS-
    rebinding page pass with a matching-but-foreign pair (TAP-6035, Wave 7
    panel):

    1. The ``Host`` header must be an IP literal, localhost, or a
       configured expected host — a foreign DNS name is the rebinding
       shape and gets 403 whether or not Origin is present.
    2. When ``Origin`` is present (browsers attach it to fetch POSTs), its
       host must satisfy the same policy — an ordinary cross-origin
       drive-by still gets 403.

    Requests without an Origin header — curl, server-to-server — only pass
    the Host check, which IP/localhost callers satisfy by construction.
    """
    allowed = _expected_hosts()
    if not _host_allowed(request.headers.get("host", ""), allowed):
        raise HTTPException(
            status_code=403,
            detail="unexpected Host header — set EXPECTED_HOSTS to allow a DNS name",
        )
    origin = request.headers.get("origin")
    if not origin:
        return
    origin_host = origin.split("://", 1)[-1].split("/", 1)[0]
    if not _host_allowed(origin_host, allowed):
        raise HTTPException(status_code=403, detail="cross-origin request refused")


init_router = APIRouter(prefix="/api/v1/init", tags=["init-agent"])

#: State-changing endpoints hang off this router instead, so every POST
#: carries the same-origin guard without repeating it per route.
#:
#: Deliberate deferral (Wave 7 panel): these POSTs carry no API-key auth.
#: The guard closes the browser drive-by vector; a LAN host with curl can
#: still call them, matching the wizard's trust model (the page itself is
#: served unauthenticated on this LAN port and would otherwise need key
#: distribution). Revisit alongside the auth.py key gate if that changes.
write_router = APIRouter(
    prefix="/api/v1/init",
    tags=["init-agent"],
    dependencies=[Depends(same_origin_only)],
)

#: The LAN wizard page (TAP-5944) lives outside the API prefix at /setup.
page_router = APIRouter(tags=["init-agent"])

_WIZARD_PAGE = Path(__file__).parent / "static" / "setup_wizard.html"

#: "later" triage deferrals (TAP-5947) — durable on the bind-mounted config/.
_TRIAGE_STORE = LaterStore(DEFAULT_TRIAGE_STORE_PATH)


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
async def queue(show_all: bool = False) -> dict[str, Any]:
    """The wizard's human-action queue: audit blocked rows + discovery flows.

    Read-only like /audit — assembly lives in homeiq_ha.agent.wizard behind
    the read-only proxy; the payload carries its read journal as evidence.
    Items deferred with a ``later`` decision (TAP-5947) are hidden by
    default and included with ``?show_all=true``.
    """
    try:
        async with HAClient.from_env() as ha:
            payload = await build_queue(ha, default_recipes())
        # Inside the envelope: a hand-corrupted store file must surface as
        # a diagnosable 502, not an anonymous 500.
        deferred = _TRIAGE_STORE.keys()
    except Exception as exc:
        logger.exception("init queue failed")
        raise HTTPException(status_code=502, detail=f"queue failed: {exc}") from exc
    if not show_all and deferred:
        kept = [i for i in payload["items"] if i.get("triage_key") not in deferred]
        payload["deferred_count"] = len(payload["items"]) - len(kept)
        payload["items"] = kept
    return payload


@write_router.post("/answers")
async def answers(body: AnswersRequest) -> dict[str, Any]:
    """Ingest one wizard submission, converge (backup-gated), verify by read-back.

    The manifest write lands on the repo's bind-mounted copy, so wizard
    decisions are durable and git-visible (commit them like any change).
    """
    contract = Answers(
        device_areas=tuple((d.device_id, d.area) for d in body.device_areas),
        addon_options=tuple((a.slug, a.options) for a in body.addon_options),
        teams=tuple(body.teams),
        backup_password=(body.backup_password.get_secret_value() if body.backup_password else None),
    )
    try:
        async with HAClient.from_env() as ha:
            return await apply_answers(ha, contract, default_recipes)
    except Exception as exc:
        logger.exception("init answers failed")
        raise HTTPException(status_code=502, detail=f"answers failed: {exc}") from exc


class PermitRequest(BaseModel):
    """TAP-5946: explicit, bounded join-window length (upstream range 0-254).

    ``duration`` is always forwarded explicitly — the window's length is
    stated, never inherited from a server default. 0 closes an open window.
    """

    model_config = ConfigDict(extra="forbid")

    duration: int = Field(default=60, ge=0, le=PERMIT_MAX_DURATION)


@write_router.post("/pairing/permit")
async def pairing_permit(body: PermitRequest | None = None) -> dict[str, Any]:
    """Open a bounded ZHA join window; the response states when it closes.

    Idempotent-safe: re-triggering restarts the window with the new
    duration (upstream ZHA behaviour) — an extend, never an error.
    """
    body = body or PermitRequest()
    try:
        async with HAClient.from_env() as ha:
            return await open_permit_window(ha, duration=body.duration)
    except Exception as exc:
        logger.exception("pairing permit failed")
        raise HTTPException(status_code=502, detail=f"permit failed: {exc}") from exc


@write_router.post("/flows/{flow_id}/start")
async def flow_start(flow_id: str) -> dict[str, Any]:
    """Advance a readiness flow to its human-readable step (PIN, code).

    Readiness-gated: only handlers in the wizard's readiness map are
    advanced; any other flow is returned untouched with
    ``reason: not_a_readiness_flow`` (its confirm submission would be the
    completing step — that is the triage ``add`` decision, TAP-5947).
    """
    try:
        async with HAClient.from_env() as ha:
            return await advance_to_readiness(ha, flow_id)
    except Exception as exc:
        logger.exception("flow start failed")
        raise HTTPException(status_code=502, detail=f"flow start failed: {exc}") from exc


class DecisionRequest(BaseModel):
    """TAP-5947: one triage decision for one discovered flow."""

    model_config = ConfigDict(extra="forbid")

    decision: Literal["add", "ignore", "later"]


@write_router.post("/flows/{flow_id}/decision")
async def flow_decision(flow_id: str, body: DecisionRequest) -> dict[str, Any]:
    """Apply one add / ignore / later decision; outcomes are read-back verified.

    ``add`` completes confirm-style flows (PIN flows route to the readiness
    triggers instead); ``ignore`` dismisses via HA's ignore mechanism so the
    flow stays gone across restarts; ``later`` defers durably and hides the
    item from the default queue view.
    """
    try:
        async with HAClient.from_env() as ha:
            return await apply_decision(ha, flow_id, body.decision, _TRIAGE_STORE)
    except Exception as exc:
        logger.exception("flow decision failed")
        raise HTTPException(status_code=502, detail=f"decision failed: {exc}") from exc


@write_router.post("/hacs/start")
async def hacs_start() -> dict[str, Any]:
    """Begin HACS onboarding, surfacing the GitHub device code and URL."""
    try:
        async with HAClient.from_env() as ha:
            return await start_hacs(ha)
    except Exception as exc:
        logger.exception("hacs start failed")
        raise HTTPException(status_code=502, detail=f"hacs start failed: {exc}") from exc


@write_router.post("/converge")
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
