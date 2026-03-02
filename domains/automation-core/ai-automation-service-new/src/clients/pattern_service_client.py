"""
Pattern Service Client for AI Automation Service (cross-group: pattern-analysis)

Epic 7, Story 1: Pattern Detection Integration (Story 39.13)
Provides resilient async access to detected patterns via ai-pattern-service.

Architecture Notes:
- Patterns are queried from ai-pattern-service (port 8020)
- Uses CircuitBreaker from homeiq-resilience for graceful degradation
- Falls back to empty patterns when service is unavailable
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from homeiq_resilience import CircuitBreaker, CircuitOpenError, CrossGroupClient

from ..config import settings

logger = logging.getLogger(__name__)

# Module-level shared breaker for pattern-analysis group
_pattern_analysis_breaker = CircuitBreaker(name="pattern-analysis")


class PatternServiceClient:
    """Resilient client for ai-pattern-service (pattern-analysis group)."""

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.pattern_service_url).rstrip("/")
        self._cross_client = CrossGroupClient(
            base_url=self.base_url,
            group_name="pattern-analysis",
            timeout=15.0,
            max_retries=2,
            circuit_breaker=_pattern_analysis_breaker,
        )
        logger.info("Pattern service client initialized with base_url=%s", self.base_url)

    async def fetch_patterns(
        self,
        pattern_type: str | None = None,
        min_confidence: float | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch detected patterns from ai-pattern-service.

        Args:
            pattern_type: Optional filter by pattern type.
            min_confidence: Optional minimum confidence threshold.
            limit: Maximum patterns to return.

        Returns:
            List of pattern dictionaries.
        """
        params: dict[str, Any] = {"limit": limit}
        if pattern_type:
            params["pattern_type"] = pattern_type
        if min_confidence is not None:
            params["min_confidence"] = min_confidence

        try:
            response = await self._cross_client.call(
                "GET", "/api/v1/patterns/list", params=params,
            )
            response.raise_for_status()
            data = response.json()

            # ai-pattern-service returns {success, data: {patterns, count}, message}
            if isinstance(data, dict):
                patterns = data.get("data", {}).get("patterns", [])
            elif isinstance(data, list):
                patterns = data
            else:
                patterns = []

            logger.info("Fetched %d patterns from pattern service", len(patterns))
            return patterns

        except CircuitOpenError:
            logger.warning("AI FALLBACK: Pattern service circuit open -- returning empty patterns")
            return []
        except httpx.HTTPStatusError as e:
            logger.error("Pattern service returned %d: %s", e.response.status_code, e.response.text[:200])
            return []
        except httpx.HTTPError as e:
            logger.error("Failed to fetch patterns from pattern service: %s", e)
            return []

    async def health_check(self) -> bool:
        """Check if pattern service is healthy."""
        try:
            response = await self._cross_client.call("GET", "/health")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        """No-op -- CrossGroupClient uses per-request clients."""
        logger.debug("Pattern service client close (no-op with CrossGroupClient)")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
