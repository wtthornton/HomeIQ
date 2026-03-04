"""Async HTTP client for Home Assistant REST API.

Wraps all HA interactions with circuit breaker protection and
connection pooling via httpx.AsyncClient.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from homeiq_resilience import CircuitBreaker

logger = logging.getLogger(__name__)


class HARestClient:
    """Async client for the Home Assistant REST API.

    Uses httpx with connection pooling and a circuit breaker to protect
    against HA outages cascading into this service.
    """

    def __init__(self, base_url: str, token: str, timeout: int = 15) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def startup(self) -> None:
        """Create the shared httpx client."""
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=self._timeout,
        )
        logger.info("HA REST client started (url=%s)", self._base_url)

    async def shutdown(self) -> None:
        """Close the httpx client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("HA REST client shut down")

    @property
    def is_connected(self) -> bool:
        """Return True if the HTTP client is initialized."""
        return self._client is not None

    def _require_client(self) -> httpx.AsyncClient:
        """Return the HTTP client, raising if not started."""
        if self._client is None:
            msg = "HARestClient not started -- call startup() first"
            raise RuntimeError(msg)
        return self._client

    # ------------------------------------------------------------------
    # Core API methods
    # ------------------------------------------------------------------

    async def get_states(self) -> list[dict[str, Any]]:
        """Fetch all entity states from HA."""
        client = self._require_client()
        async with self._circuit:
            resp = await client.get("/api/states")
            resp.raise_for_status()
            return resp.json()

    async def get_state(self, entity_id: str) -> dict[str, Any]:
        """Fetch state for a single entity."""
        client = self._require_client()
        async with self._circuit:
            resp = await client.get(f"/api/states/{entity_id}")
            resp.raise_for_status()
            return resp.json()

    async def call_service(
        self,
        domain: str,
        service: str,
        data: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Call an HA service (e.g. light/turn_on).

        Returns the list of affected entity states.
        """
        client = self._require_client()
        async with self._circuit:
            resp = await client.post(
                f"/api/services/{domain}/{service}",
                json=data or {},
            )
            resp.raise_for_status()
            return resp.json()

    async def render_template(self, template: str) -> str:
        """Render a Jinja2 template via the HA template API."""
        client = self._require_client()
        async with self._circuit:
            resp = await client.post(
                "/api/template",
                json={"template": template},
            )
            resp.raise_for_status()
            return resp.text

    # ------------------------------------------------------------------
    # Higher-level helpers
    # ------------------------------------------------------------------

    async def get_areas(self) -> list[str]:
        """Get all area names via the template API."""
        tpl = "{% for area in areas() %}{{ area_name(area) }}||{% endfor %}"
        raw = await self.render_template(tpl)
        return [a.strip() for a in raw.split("||") if a.strip()]

    async def get_entity_areas(self, entity_ids: list[str]) -> dict[str, str]:
        """Map entity IDs to their area names in batches of 50."""
        mapping: dict[str, str] = {}
        batch_size = 50

        for i in range(0, len(entity_ids), batch_size):
            batch = entity_ids[i : i + batch_size]
            parts = [
                f"{eid}:{{{{ area_name(area_id('{eid}')) or '' }}}}"
                for eid in batch
            ]
            template = "||".join(parts)
            try:
                raw = await self.render_template(template)
                for pair in raw.strip().split("||"):
                    if ":" in pair:
                        eid, area = pair.split(":", 1)
                        if area.strip():
                            mapping[eid.strip()] = area.strip()
            except (httpx.HTTPStatusError, httpx.RequestError):
                logger.warning("Failed to resolve areas for batch starting at %d", i)

        return mapping

    async def check_connection(self) -> bool:
        """Verify connectivity to HA by fetching the API status endpoint."""
        try:
            client = self._require_client()
            resp = await client.get("/api/")
            return resp.status_code == 200
        except Exception:
            logger.warning("HA connection check failed")
            return False
