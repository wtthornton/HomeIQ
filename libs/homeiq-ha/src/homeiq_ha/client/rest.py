"""Home Assistant REST client.

Covers the surface that genuinely is REST: config-entry flows, service calls,
and the automation/script/scene config endpoints. Registries are not here —
they are WebSocket-only, see :mod:`homeiq_ha.client.ws`.
"""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING, Any

import aiohttp

from .errors import HAClientError, HAFlowError, HAHumanGateRequired
from .redaction import redact

if TYPE_CHECKING:
    from types import TracebackType

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30.0

#: Flow step types a client may act on without a person.
_ADVANCEABLE = frozenset({"form", "menu"})
#: Flow step types that end the flow.
_TERMINAL = frozenset({"create_entry", "abort"})
#: Flow step types Home Assistant core refuses to let a client advance.
_HUMAN_GATED = frozenset({"external", "progress"})


class HARestClient:
    """Authenticated REST access to Home Assistant."""

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        session: aiohttp.ClientSession | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session = session
        self._owns_session = session is None

    async def __aenter__(self) -> HARestClient:
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        if self._session is not None and self._owns_session:
            await self._session.close()
            self._session = None

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        url = f"{self._base_url}/{path.lstrip('/')}"
        async with self._session.request(method, url, headers=self._headers, **kwargs) as response:
            body: Any
            try:
                body = await response.json()
            except (aiohttp.ContentTypeError, ValueError):
                body = await response.text()
            if response.status >= 400:
                raise HAClientError(f"{method.upper()} {path} -> {response.status}: {redact(body)}")
            return body

    # -- services ----------------------------------------------------------

    async def call_service(self, domain: str, service: str, **data: Any) -> Any:
        return await self.request("POST", f"/api/services/{domain}/{service}", json=data)

    async def check_config(self) -> dict[str, Any]:
        """Validate the configuration. Always run this before a restart."""
        return await self.request("POST", "/api/config/core/check_config")

    async def get_states(self) -> list[dict[str, Any]]:
        return await self.request("GET", "/api/states")

    async def get_config_entries(self) -> list[dict[str, Any]]:
        return await self.request("GET", "/api/config/config_entries/entry")

    async def get_supervisor_logs(self, endpoint: str = "/core/logs") -> str:
        """Supervisor-managed logs as text, via the core's ``/api/hassio`` proxy.

        The supported log path (TAP-5984, verified live 2026-08-13 on
        HA 2026.8.1): the WS ``supervisor/api`` passthrough JSON-decodes
        every Supervisor response, so text log endpoints (``/core/logs``,
        ``/supervisor/logs``, ``/addons/<slug>/logs``) always fail there
        with an opaque ``unknown_error``. The REST proxy forwards the
        journald text untouched (ANSI color codes included — strip them
        before machine-parsing), and :meth:`request` already returns
        non-JSON bodies as ``str``.

        Args:
            endpoint: Supervisor log path, e.g. ``/core/logs`` or
                ``/addons/core_ssh/logs``.
        """
        body = await self.request("GET", f"/api/hassio/{endpoint.lstrip('/')}")
        return body if isinstance(body, str) else str(body)

    # -- config flows ------------------------------------------------------

    async def start_config_flow(self, domain: str, **context: Any) -> dict[str, Any]:
        """Begin a config-entry flow and return its first step."""
        return await self.request(
            "POST",
            "/api/config/config_entries/flow",
            json={"handler": domain, "show_advanced_options": True, **context},
        )

    async def advance_config_flow(self, flow_id: str, user_input: dict[str, Any]) -> dict[str, Any]:
        """Submit one step of a running flow."""
        return await self.request(
            "POST", f"/api/config/config_entries/flow/{flow_id}", json=user_input
        )

    async def get_config_flow(self, flow_id: str) -> dict[str, Any]:
        """Re-render a running flow's current step without submitting it.

        HA core's ``FlowManagerResourceView.get`` calls
        ``async_configure(flow_id)`` with no user input, which re-invokes the
        current step handler in show-form mode — nothing advances.
        """
        return await self.request("GET", f"/api/config/config_entries/flow/{flow_id}")

    async def abort_config_flow(self, flow_id: str) -> None:
        await self.request("DELETE", f"/api/config/config_entries/flow/{flow_id}")

    @staticmethod
    def classify_flow_step(step: dict[str, Any]) -> str:
        """Return the step's ``type``, defaulting to ``form``.

        Gating on this rather than assuming every step is a form is what makes
        ``external`` (OAuth) and ``progress`` (HACS device authorization) steps
        *surface* instead of failing with a confusing schema error.
        """
        return str(step.get("type") or "form")

    async def run_config_flow(
        self,
        domain: str,
        steps: list[dict[str, Any]],
        **context: Any,
    ) -> dict[str, Any]:
        """Drive a config flow to completion.

        ``steps`` supplies the user input for each successive form, in order.

        Raises:
            HAHumanGateRequired: the flow needs a person — either an
                ``external`` / ``progress`` step Home Assistant refuses to let
                a client advance, or a form whose input was not supplied
                (a 2FA code, a mailed verification code). **The flow is left
                running** in all these cases, because the whole point is that
                someone completes it via ``/api/v1/init/flow/{flow_id}``. The
                exception carries the step, so the queue can render the
                remaining fields and the URL or device code.
            HAFlowError: the flow aborted, or reached a step this client
                cannot drive. The flow is torn down first, since nothing can
                resume it.

        A form that runs out of input is a **human gate, not an error**. Getting
        that wrong is expensive: ``HAFlowError`` propagates out of a recipe's
        ``apply`` as a plain failure, and ``engine`` halts the entire converge
        run on the first failed recipe (`if not outcome.ok: return report`).
        One missing 2FA code would therefore abandon every later recipe *and*
        strand the flow. As a gate it becomes ``BLOCKED_ON_HUMAN``, which the
        engine records and steps over.
        """
        step = await self.start_config_flow(domain, **context)
        remaining = list(steps)

        while True:
            step_type = self.classify_flow_step(step)
            logger.debug("config flow %s step: %s", domain, redact(step))

            if step_type in _HUMAN_GATED:
                # Left running on purpose: the resume route needs this flow_id.
                raise HAHumanGateRequired(
                    f"{domain} config flow needs a person at a {step_type!r} step",
                    step,
                )

            if step_type == "create_entry":
                return step

            if step_type == "abort":
                # Home Assistant already tore this one down.
                raise HAFlowError(
                    f"{domain} config flow aborted: {step.get('reason', 'unknown')}",
                    step,
                )

            if step_type not in _ADVANCEABLE:
                await self._discard_flow(step)
                raise HAFlowError(
                    f"{domain} config flow returned an unsupported step type {step_type!r}",
                    step,
                )

            if not remaining:
                # Also left running: this is exactly the 2FA case, and the
                # owner answers it through the human-decision queue.
                raise HAHumanGateRequired(
                    f"{domain} config flow needs input for step "
                    f"{step.get('step_id')!r} that was not supplied — "
                    f"answer it at /api/v1/init/flow/{step.get('flow_id')}",
                    step,
                )

            flow_id = step.get("flow_id")
            if not flow_id:
                raise HAFlowError(f"{domain} config flow step has no flow_id", step)
            step = await self.advance_config_flow(str(flow_id), remaining.pop(0))

    async def _discard_flow(self, step: dict[str, Any]) -> None:
        """Abort a flow nothing can resume, so it leaves no pending discovery."""
        flow_id = step.get("flow_id")
        if not flow_id:
            return
        with suppress(Exception):
            await self.abort_config_flow(str(flow_id))
