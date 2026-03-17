"""Cross-service security feed — pushes events to proactive-agent and ai-pattern.

Sends security events (anomalies, new devices, beaconing alerts) to
downstream consumers via HTTP. Uses fire-and-forget with circuit-breaker
pattern to avoid blocking the main service on feed failures.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from homeiq_observability.logging_config import setup_logging

logger = setup_logging("zeek-security-feed")

# Endpoints for downstream services
_PROACTIVE_AGENT_PATH = "/api/v1/security-events"
_AI_PATTERN_PATH = "/api/v1/network-patterns"


class SecurityFeed:
    """Pushes security events to proactive-agent-service and ai-pattern-service."""

    def __init__(
        self,
        data_api_url: str,
        api_key: str | None = None,
        proactive_agent_url: str = "http://proactive-agent-service:8046",
        ai_pattern_url: str = "http://ai-pattern-service:8040",
    ) -> None:
        self._data_api_url = data_api_url
        self._api_key = api_key
        self._proactive_agent_url = proactive_agent_url
        self._ai_pattern_url = ai_pattern_url
        self._client: httpx.AsyncClient | None = None

        # Stats
        self.events_sent: int = 0
        self.events_failed: int = 0
        self._consecutive_failures: int = 0
        self._circuit_open: bool = False
        self._circuit_open_until: datetime | None = None

    async def initialize(self) -> None:
        """Create HTTP client."""
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            headers=headers,
        )
        logger.info("SecurityFeed initialized")

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()

    async def send_security_event(self, event: dict[str, Any]) -> None:
        """Send a security event to proactive-agent-service.

        Events include: new_device, beaconing, dga_domain, dns_tunneling,
        protocol_violation, expired_certificate, weak_tls.
        """
        if not self._client or self._is_circuit_open():
            return

        payload = {
            "source": "zeek-network-service",
            "timestamp": datetime.now(UTC).isoformat(),
            **event,
        }

        try:
            resp = await self._client.post(
                f"{self._proactive_agent_url}{_PROACTIVE_AGENT_PATH}",
                json=payload,
            )
            if resp.status_code < 300:
                self.events_sent += 1
                self._consecutive_failures = 0
            else:
                self._record_failure(
                    f"proactive-agent returned {resp.status_code}"
                )
        except httpx.HTTPError as e:
            self._record_failure(f"proactive-agent unreachable: {e}")

    async def send_network_pattern(self, pattern: dict[str, Any]) -> None:
        """Send network behavioral pattern to ai-pattern-service.

        Patterns include: DNS profiles, connection graphs, device behaviors.
        """
        if not self._client or self._is_circuit_open():
            return

        payload = {
            "source": "zeek-network-service",
            "pattern_type": "network_behavior",
            "timestamp": datetime.now(UTC).isoformat(),
            **pattern,
        }

        try:
            resp = await self._client.post(
                f"{self._ai_pattern_url}{_AI_PATTERN_PATH}",
                json=payload,
            )
            if resp.status_code < 300:
                self.events_sent += 1
                self._consecutive_failures = 0
            else:
                self._record_failure(
                    f"ai-pattern returned {resp.status_code}"
                )
        except httpx.HTTPError as e:
            self._record_failure(f"ai-pattern unreachable: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Return feed statistics."""
        return {
            "events_sent": self.events_sent,
            "events_failed": self.events_failed,
            "circuit_open": self._circuit_open,
        }

    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open (skip requests)."""
        if not self._circuit_open:
            return False
        if (
            self._circuit_open_until
            and datetime.now(UTC) > self._circuit_open_until
        ):
            self._circuit_open = False
            self._consecutive_failures = 0
            logger.info("SecurityFeed circuit breaker closed (recovery)")
            return False
        return True

    def _record_failure(self, msg: str) -> None:
        """Record a failure and open circuit breaker after 3 consecutive failures."""
        self.events_failed += 1
        self._consecutive_failures += 1
        logger.warning("SecurityFeed failure (%d): %s", self._consecutive_failures, msg)

        if self._consecutive_failures >= 3 and not self._circuit_open:
            from datetime import timedelta

            self._circuit_open = True
            self._circuit_open_until = datetime.now(UTC) + timedelta(seconds=60)
            logger.warning("SecurityFeed circuit breaker OPEN (60s cooldown)")
