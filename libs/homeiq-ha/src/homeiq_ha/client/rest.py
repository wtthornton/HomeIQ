"""Home Assistant REST client.

Covers the surface that genuinely is REST: config-entry flows, service calls,
and the automation/script/scene config endpoints. Registries are not here —
they are WebSocket-only, see :mod:`homeiq_ha.client.ws`.
"""

from __future__ import annotations

import logging
from types import TracebackType
from typing import Any

import aiohttp

from .errors import HAClientError, HAFlowError, HAHumanGateRequired
from .redaction import redact

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
        async with self._session.request(
            method, url, headers=self._headers, **kwargs
        ) as response:
            body: Any
            try:
                body = await response.json()
            except (aiohttp.ContentTypeError, ValueError):
                body = await response.text()
            if response.status >= 400:
                raise HAClientError(
                    f"{method.upper()} {path} -> {response.status}: {redact(body)}"
                )
            return body

    # -- services ----------------------------------------------------------

    async def call_service(
        self, domain: str, service: str, **data: Any
    ) -> Any:
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

    async def advance_config_flow(
        self, flow_id: str, user_input: dict[str, Any]
    ) -> dict[str, Any]:
        """Submit one step of a running flow."""
        return await self.request(
            "POST", f"/api/config/config_entries/flow/{flow_id}", json=user_input
        )

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
            HAHumanGateRequired: the flow reached an ``external`` or
                ``progress`` step. The exception carries the URL and any
                ``description_placeholders`` (HACS puts its GitHub device code
                there) so the caller can prompt a person and resume.
            HAFlowError: the flow aborted, or ran out of supplied input.
        """
        step = await self.start_config_flow(domain, **context)
        remaining = list(steps)

        while True:
            step_type = self.classify_flow_step(step)
            logger.debug("config flow %s step: %s", domain, redact(step))

            if step_type in _HUMAN_GATED:
                raise HAHumanGateRequired(
                    f"{domain} config flow needs a person at a {step_type!r} step",
                    step,
                )

            if step_type == "create_entry":
                return step

            if step_type == "abort":
                raise HAFlowError(
                    f"{domain} config flow aborted: {step.get('reason', 'unknown')}",
                    step,
                )

            if step_type not in _ADVANCEABLE:
                raise HAFlowError(
                    f"{domain} config flow returned an unsupported step type "
                    f"{step_type!r}",
                    step,
                )

            if not remaining:
                raise HAFlowError(
                    f"{domain} config flow needs input for step "
                    f"{step.get('step_id')!r} but none was supplied",
                    step,
                )

            flow_id = step.get("flow_id")
            if not flow_id:
                raise HAFlowError(f"{domain} config flow step has no flow_id", step)
            step = await self.advance_config_flow(str(flow_id), remaining.pop(0))
