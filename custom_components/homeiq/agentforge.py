"""AgentForge invocation client for HomeIQ (TAP-5307, TAP-5309).

Every conversation turn and every AI Task is answered by AgentForge through
``POST <base>/projects/<project>/tasks/invoke`` with a project API key.
AgentForge's SSE endpoint (``POST /tasks/stream``) is unscoped and would bypass
project auth, so it is deliberately not used.

That route answers in one of two shapes. A short prompt comes back 200 with the
finished ``TaskResponse``. A longer one is *steered* onto the async queue and
comes back 202 with only ``invocation_id`` and ``status`` — no ``result``
(``invoke_steered: true``, ``steer_reason: exceeds_sync_invoke_steering_threshold``).
The answer then has to be collected from
``GET <base>/projects/<project>/invocations/<invocation_id>/result``, which
answers 404 ``"not found or not terminal"`` until the run finishes. Both shapes
are handled here, so callers always get a settled :class:`AgentForgeResponse`.

AgentForge signals a budget refusal in-band rather than with an HTTP status:
the call succeeds with ``is_error: true`` and prose in ``result``
(``backend/orchestrator/engine.py`` blocks a plan with
``"orchestration blocked by budget: <reason>"``; the per-run cap in
``backend/executor/platform_api_messages.py`` reports
``"exceeded max_budget_usd"``). Both are turned into a refusal the user can
read instead of an exception.

Like :mod:`.mcp_client`, this module imports nothing from Home Assistant.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from aiohttp import ClientError, ClientTimeout

if TYPE_CHECKING:
    from aiohttp import ClientSession

BUDGET_BLOCKED_PREFIX = "orchestration blocked by budget: "
BUDGET_EXCEEDED_MARKER = "exceeded max_budget_usd"
GATE_AWAITING = "awaiting_gate"

# Detail strings from AgentForge's project-auth middleware.
_AUTH_MESSAGES = {
    "missing-bearer": "AgentForge did not receive an API key.",
    "key-invalid-or-revoked": "AgentForge rejected the API key as invalid or revoked.",
    "cross-project-denied": "The AgentForge API key belongs to a different project.",
}


class AgentForgeError(Exception):
    """An AgentForge invocation failed at the transport or HTTP layer."""

    def __init__(self, code: str, user_message: str, detail: str = "") -> None:
        """Initialise the error."""
        super().__init__(f"{code}: {user_message}")
        self.code = code
        self.user_message = user_message
        self.detail = detail


class AgentForgeUnauthorizedError(AgentForgeError):
    """AgentForge refused the API key."""


@dataclass(frozen=True)
class AgentForgeResponse:
    """One AgentForge ``TaskResponse``, reduced to what the entities need."""

    text: str
    is_error: bool
    agent_used: str
    orchestration_state: str | None

    @property
    def refused_for_budget(self) -> bool:
        """Return whether AgentForge stopped this run on a budget gate."""
        if not self.is_error:
            return False
        return self.text.startswith(BUDGET_BLOCKED_PREFIX) or BUDGET_EXCEEDED_MARKER in self.text

    @property
    def answer_text(self) -> str:
        """Return the prose to show a person.

        Genes answer with a JSON object carrying a prose ``answer`` alongside
        the house convention fields. Showing the raw object to someone who
        asked a spoken question is never right, so the ``answer`` is unwrapped
        when present. A gene that replies in plain prose is passed through
        untouched, as is a body that is not an object.
        """
        stripped = self.text.strip()
        if not stripped.startswith("{"):
            return self.text
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return self.text
        if isinstance(parsed, dict) and isinstance(answer := parsed.get("answer"), str):
            return answer
        return self.text

    @property
    def instance_text(self) -> str:
        """Return the schema instance a structured caller asked for.

        A structured gene answers with a JSON object carrying the caller's
        instance under ``instance`` alongside its own convention fields —
        ``hiq-extract`` adds ``manifest`` and ``unsourced_fields``. An AI Task
        validates the body against the schema it supplied, so the envelope has
        to come off first or every structured task fails on the extra keys. A
        gene that replies with the bare instance, or with anything that is not
        an object, is passed through untouched.
        """
        stripped = self.text.strip()
        if not stripped.startswith("{"):
            return self.text
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return self.text
        if isinstance(parsed, dict) and "instance" in parsed:
            return json.dumps(parsed["instance"])
        return self.text

    def as_user_message(self) -> str:
        """Render this response as text a person can act on."""
        if self.refused_for_budget:
            reason = self.text.removeprefix(BUDGET_BLOCKED_PREFIX).strip() or self.text
            return (
                "HomeIQ stopped this request before spending more: "
                f"{reason}. Raise the AgentForge budget or ask for something narrower."
            )
        if self.orchestration_state == GATE_AWAITING:
            return (
                "HomeIQ paused this request for budget approval in AgentForge. "
                "Approve it there and ask again."
            )
        if self.is_error:
            detail = self.answer_text.strip() or "AgentForge reported an error with no detail."
            return f"HomeIQ could not complete that request: {detail}"
        return self.answer_text


def _http_failure(status: int, body: str) -> AgentForgeError:
    """Map an AgentForge HTTP failure onto a readable error."""
    detail = _detail_of(body)
    error_code = _error_code_of(body) or detail
    if status in (401, 403):
        return AgentForgeUnauthorizedError(
            "unauthorized",
            _AUTH_MESSAGES.get(detail, f"AgentForge refused the API key: {detail}"),
            detail,
        )
    if status == 404:
        return AgentForgeError(
            "not_found", f"AgentForge has no such project or agent: {detail}", error_code
        )
    if status == 504:
        return AgentForgeError("timeout", "AgentForge took too long to answer.", detail)
    if status == 503:
        return AgentForgeError("unavailable", f"AgentForge is unavailable: {detail}", detail)
    return AgentForgeError("http_error", f"AgentForge returned HTTP {status}: {detail}", detail)


def _decode(raw: str) -> dict[str, Any]:
    """Parse an AgentForge JSON object, or fail with a readable contract error."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as err:
        raise AgentForgeError(
            "contract_violation", "AgentForge returned a body that is not JSON."
        ) from err
    if not isinstance(parsed, dict):
        raise AgentForgeError(
            "contract_violation", "AgentForge returned a body that is not an object."
        )
    return parsed


def _error_code_of(body: str) -> str | None:
    """Return AgentForge's structured ``error_code``, when the body carries one."""
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return None
    detail = parsed.get("detail") if isinstance(parsed, dict) else None
    if isinstance(detail, dict) and (code := detail.get("error_code")):
        return str(code)
    return None


def _detail_of(body: str) -> str:
    """Pull the human-readable part out of a FastAPI error body."""
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return body.strip() or "no detail"
    detail = parsed.get("detail") if isinstance(parsed, dict) else None
    if isinstance(detail, dict):
        return str(detail.get("detail") or detail.get("error_code") or detail)
    if isinstance(detail, str):
        return detail
    return body.strip() or "no detail"


class AgentForgeClient:
    """Invokes HomeIQ tasks on AgentForge."""

    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        api_key: str,
        project: str,
        timeout: float,
        poll_interval: float = 3.0,
        async_wait: float = 180.0,
    ) -> None:
        """Initialise the client."""
        self._session = session
        root = f"{base_url.rstrip('/')}/projects/{project}"
        self._endpoint = f"{root}/tasks/invoke"
        self._result_endpoint = f"{root}/invocations/{{invocation_id}}/result"
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        self._timeout = ClientTimeout(total=timeout)
        self._poll_interval = poll_interval
        self._async_wait = async_wait

    async def _post(self, body: dict[str, Any]) -> str:
        """Send one invocation and return the raw response body."""
        try:
            response = await self._session.post(
                self._endpoint, json=body, headers=self._headers, timeout=self._timeout
            )
            async with response:
                raw = await response.text()
                if response.status >= 400:
                    raise _http_failure(response.status, raw)
                return raw
        except (TimeoutError, ClientError, OSError) as err:
            raise AgentForgeError(
                "unreachable", f"HomeIQ could not reach AgentForge: {err}"
            ) from err

    async def _fetch_result(self, invocation_id: str) -> dict[str, Any] | None:
        """Return the terminal payload for an invocation, or ``None`` if still running.

        AgentForge uses 404 for both "no such invocation" and "not finished
        yet", so a 404 is a signal to keep waiting rather than an error. Every
        other failing status is a real failure and is raised.
        """
        url = self._result_endpoint.format(invocation_id=invocation_id)
        try:
            response = await self._session.get(url, headers=self._headers, timeout=self._timeout)
            async with response:
                raw = await response.text()
                if response.status == 404:
                    return None
                if response.status >= 400:
                    raise _http_failure(response.status, raw)
        except (TimeoutError, ClientError, OSError) as err:
            raise AgentForgeError(
                "unreachable", f"HomeIQ could not reach AgentForge: {err}"
            ) from err
        return _decode(raw)

    async def _await_result(self, invocation_id: str) -> dict[str, Any]:
        """Poll until the steered invocation settles, or give up with a readable error."""
        deadline = time.monotonic() + self._async_wait
        while True:
            payload = await self._fetch_result(invocation_id)
            if payload is not None:
                return payload
            if time.monotonic() + self._poll_interval >= deadline:
                raise AgentForgeError(
                    "timeout",
                    "AgentForge is still working on that request. "
                    "It was queued rather than answered directly; try again shortly.",
                    invocation_id,
                )
            await asyncio.sleep(self._poll_interval)

    async def async_verify(self) -> None:
        """Confirm the endpoint answers and accepts the API key.

        Uses ``match_only`` so AgentForge resolves the project and the key
        without spawning an agent. ``AGENT_NOT_FOUND`` still proves the project
        exists and the key was accepted, so it is not treated as a failure; an
        unknown project is.
        """
        try:
            await self._post({"prompt": "HomeIQ connectivity check", "match_only": True})
        except AgentForgeError as err:
            if err.code == "not_found" and err.detail == "AGENT_NOT_FOUND":
                return
            raise

    async def async_invoke(
        self, prompt: str, *, config_hint: str | None = None
    ) -> AgentForgeResponse:
        """Run one task and return AgentForge's answer."""
        body: dict[str, Any] = {"prompt": prompt}
        if config_hint:
            body["config_hint"] = config_hint
        parsed = _decode(await self._post(body))

        # A steered invoke carries an id instead of an answer; collect the answer.
        if parsed.get("result") is None:
            invocation_id = parsed.get("invocation_id")
            if not invocation_id:
                raise AgentForgeError(
                    "contract_violation",
                    "AgentForge returned neither a result nor an invocation to follow.",
                    ",".join(sorted(parsed)),
                )
            parsed = await self._await_result(str(invocation_id))

        return AgentForgeResponse(
            text=str(parsed.get("result") or ""),
            is_error=bool(parsed.get("is_error", False)),
            agent_used=str(parsed.get("agent_used", "")),
            orchestration_state=parsed.get("orchestration_state"),
        )
