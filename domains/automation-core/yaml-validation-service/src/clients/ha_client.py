"""Home Assistant API client for service validation."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class HAServiceClient:
    """Client to fetch available services from Home Assistant.

    Queries the HA REST API to retrieve the list of registered services,
    then exposes helpers that the validation pipeline uses to check whether
    a ``domain.service`` call actually exists on the target instance.

    The service list is cached for the lifetime of the client so that
    multiple validation calls within the same request do not trigger
    repeated HTTP round-trips.
    """

    def __init__(self, ha_url: str, ha_token: str) -> None:
        self._ha_url = ha_url.rstrip("/")
        self._ha_token = ha_token
        self._services: dict[str, set[str]] | None = None
        self._client = httpx.AsyncClient(
            timeout=10.0,
            headers={"Authorization": f"Bearer {ha_token}"},
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_services(self) -> dict[str, set[str]]:
        """Fetch available services from the HA REST API.

        Returns a mapping of ``{domain: {service_name, ...}}``.
        Results are cached after the first successful call.
        """
        if self._services is not None:
            return self._services

        try:
            response = await self._client.get(f"{self._ha_url}/api/services")
            response.raise_for_status()
            raw: list[dict[str, Any]] = response.json()

            services: dict[str, set[str]] = {}
            for entry in raw:
                domain = entry.get("domain", "")
                svc_map = entry.get("services", {})
                if domain and isinstance(svc_map, dict):
                    services[domain] = set(svc_map.keys())

            self._services = services
            logger.info(
                "Fetched %d service domains from Home Assistant",
                len(services),
            )
            return services

        except httpx.TimeoutException:
            logger.warning(
                "Timeout connecting to Home Assistant at %s", self._ha_url
            )
            return {}
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Home Assistant returned HTTP %d when fetching services",
                exc.response.status_code,
            )
            return {}
        except Exception:
            logger.exception("Unexpected error fetching HA services")
            return {}

    async def validate_service(self, service_call: str) -> bool:
        """Check whether a ``domain.service`` call exists in HA.

        Args:
            service_call: Fully-qualified service name, e.g. ``light.turn_on``.

        Returns:
            ``True`` if the service is known to HA, ``False`` otherwise.
        """
        if "." not in service_call:
            return False

        domain, service_name = service_call.split(".", 1)
        services = await self.get_services()

        domain_services = services.get(domain)
        if domain_services is None:
            return False

        return service_name in domain_services

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()
