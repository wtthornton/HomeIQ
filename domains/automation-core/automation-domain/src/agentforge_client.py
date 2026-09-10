"""AgentForge workflow client for automation-domain (TAP-7275).

Every LLM call this domain used to make with a provider API key is now a
workflow run on AgentForge. HomeIQ keeps the data and CRUD slice; the model
call, its prompt, and its credential live in AgentForge.

The contract is ``POST <base>/projects/<slug>/workflows/<name>/run`` with a
project bearer, body ``{"inputs": {...}, "dry_run": bool}``. It answers with a
terminal run record: ``{"run_id", "state", "output", "node_outputs", ...}``.
``output`` is the terminal node's payload serialised as a JSON *string*, so a
caller that wants an object has to parse it -- ``run_workflow_json`` does.

Two refusal shapes matter to callers and are surfaced as typed errors rather
than as a generic exception:

* ``422`` -- the inputs disagree with the published spec (``missing_inputs``
  for an absent required input, ``undeclared_inputs`` for a key the spec never
  declares). This is a *publishing* bug, not a runtime one: the workflow YAML
  in ``agentforge/projects/homeiq/workflows/`` and this caller have drifted.
* ``409`` -- the workflow exists but has no active version, i.e. it was never
  published. ``scripts/af.sh publish`` is the fix; retrying is not.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_PROJECT_SLUG = "homeiq"

#: States a run can be in while it is still going.
PENDING_STATES = frozenset({"pending", "running", "queued"})

#: Seconds between polls of a run that came back not-yet-terminal.
POLL_INTERVAL_SECONDS = 2.0


class AgentForgeError(Exception):
    """An AgentForge workflow run failed at the transport or HTTP layer."""

    def __init__(self, code: str, message: str, detail: str = "") -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.detail = detail


class AgentForgeUnauthorizedError(AgentForgeError):
    """AgentForge refused the project key."""


class AgentForgeNotPublishedError(AgentForgeError):
    """The workflow is unknown (404) or has no active version (409)."""


class AgentForgeInputMismatchError(AgentForgeError):
    """The inputs sent disagree with the published spec (422)."""


class AgentForgeRunFailedError(AgentForgeError):
    """The run reached a terminal state that is not ``complete``."""

    def __init__(self, message: str, state: str, failed_nodes: list[Any]) -> None:
        super().__init__("run-failed", message)
        self.state = state
        self.failed_nodes = failed_nodes


class AgentForgeClient:
    """Runs published AgentForge workflows for the homeiq project."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        project_slug: str = DEFAULT_PROJECT_SLUG,
        timeout: float = 180.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = (api_key or "").strip()
        self.project_slug = project_slug
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def configured(self) -> bool:
        """Whether a project key is present.

        A missing key is not an error at construction time -- it is reported by
        ``/health`` and raised at the first call, so a container without a key
        starts and says so instead of crash-looping.
        """
        return bool(self.api_key)

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def run_workflow(
        self,
        name: str,
        inputs: dict[str, Any],
        *,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Run ``name`` to a terminal state and return the run record."""
        if not self.configured:
            raise AgentForgeError(
                "missing-key",
                "AGENTFORGE_API_KEY is not set; automation-domain cannot reach AgentForge.",
            )
        url = f"{self.base_url}/projects/{self.project_slug}/workflows/{name}/run"
        body = {"inputs": inputs, "dry_run": dry_run}
        try:
            response = await self._http().post(
                url,
                json=body,
                headers=self._headers(),
                params={"kickoff": "sync"},
            )
        except httpx.HTTPError as exc:
            raise AgentForgeError(
                "transport", f"AgentForge unreachable at {self.base_url}: {exc}"
            ) from exc

        if response.status_code in (401, 403):
            raise AgentForgeUnauthorizedError(
                "key-invalid-or-revoked",
                "AgentForge refused the project API key.",
                response.text[:400],
            )
        if response.status_code in (404, 409):
            raise AgentForgeNotPublishedError(
                "not-published",
                f"AgentForge workflow '{name}' is not published for project "
                f"'{self.project_slug}' (HTTP {response.status_code}). "
                "Run scripts/af.sh publish.",
                response.text[:400],
            )
        if response.status_code == 422:
            raise AgentForgeInputMismatchError(
                "input-mismatch",
                f"AgentForge rejected the inputs for '{name}'; the caller and the "
                "published spec have drifted.",
                response.text[:800],
            )
        if response.status_code >= 400:
            raise AgentForgeError(
                "http-error",
                f"AgentForge returned HTTP {response.status_code} for '{name}'.",
                response.text[:400],
            )

        record: dict[str, Any] = response.json()
        # `kickoff=sync` is a request, not a guarantee. AgentForge steers a run
        # onto its async queue when it exceeds the sync threshold and answers
        # 202 with `state: pending` and no output -- measured on
        # `suggestion-describe`, which came back 202 while eight sibling
        # workflows came back 200. Treating that as a failure would have made
        # this client flaky in exactly the way that is hardest to reproduce, so
        # a non-terminal state is polled to completion here.
        if record.get("state") in PENDING_STATES:
            record = await self._await_terminal(record, name)

        state = record.get("state", "")
        if state not in ("complete", "dry_run"):
            raise AgentForgeRunFailedError(
                f"AgentForge run {record.get('run_id')} for '{name}' ended in state '{state}'.",
                state=state,
                failed_nodes=record.get("failed_nodes") or [],
            )
        return record

    async def _await_terminal(self, record: dict[str, Any], name: str) -> dict[str, Any]:
        """Poll a steered run until it settles or the client timeout elapses."""
        run_id = record.get("run_id")
        if not run_id:
            raise AgentForgeError(
                "no-run-id",
                f"AgentForge steered '{name}' onto its async queue but returned no run_id.",
            )
        deadline = asyncio.get_running_loop().time() + self.timeout
        url = f"{self.base_url}/workflows/runs/{run_id}"
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            try:
                response = await self._http().get(url, headers=self._headers())
            except httpx.HTTPError as exc:
                raise AgentForgeError(
                    "transport", f"AgentForge unreachable while polling {run_id}: {exc}"
                ) from exc
            if response.status_code >= 400:
                raise AgentForgeError(
                    "http-error",
                    f"AgentForge returned HTTP {response.status_code} polling run {run_id}.",
                    response.text[:400],
                )
            body = response.json()
            # The poll route wraps the run record under "run"; the kickoff route
            # returns it bare. Accept both rather than depending on which one
            # answered.
            run = body.get("run") if isinstance(body.get("run"), dict) else body
            if run.get("state") not in PENDING_STATES:
                return run
        raise AgentForgeError(
            "timeout",
            f"AgentForge run {run_id} for '{name}' did not settle within {self.timeout:.0f}s.",
        )

    async def run_workflow_json(
        self,
        name: str,
        inputs: dict[str, Any],
        *,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Run ``name`` and return the terminal node's output as an object.

        ``output`` comes back as a JSON string. A gene that answers in prose
        rather than an object is returned as ``{"answer": <prose>}`` so callers
        never have to branch on the serialisation.
        """
        record = await self.run_workflow(name, inputs, dry_run=dry_run)
        return parse_workflow_output(record)


def parse_workflow_output(record: dict[str, Any]) -> dict[str, Any]:
    """Turn a run record's ``output`` into a dict.

    Kept as a module function so tests can drive it from a real run record
    captured from AgentForge, without a live HTTP client in the way.
    """
    raw = record.get("output")
    if isinstance(raw, dict):
        return raw
    if raw is None:
        return {}
    text = str(raw).strip()
    if not text.startswith("{"):
        return {"answer": text}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"answer": text}
    if isinstance(parsed, dict):
        return parsed
    return {"answer": text}
