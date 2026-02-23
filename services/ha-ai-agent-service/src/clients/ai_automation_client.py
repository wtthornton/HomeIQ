"""
AI Automation Service Client for HA AI Agent Service

Provides access to YAML validation via AI Automation Service.
Uses CrossGroupClient for circuit-breaker protection and automatic retries.
"""

import logging
from typing import Any

import httpx

from shared.resilience import CircuitBreaker, CrossGroupClient
from shared.resilience.circuit_breaker import CircuitOpenError

logger = logging.getLogger(__name__)

_automation_breaker = CircuitBreaker(name="automation-intelligence")


class AIAutomationClient:
    """Client for YAML validation via AI Automation Service"""

    def __init__(self, base_url: str = "http://ai-automation-service:8000", api_key: str | None = None):
        """
        Initialize AI Automation Service client.

        Args:
            base_url: Base URL for AI Automation Service (default: http://ai-automation-service:8000)
            api_key: API key for authentication (optional)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self._auth_headers = {"X-HomeIQ-API-Key": api_key} if api_key else {}
        self._cross_client = CrossGroupClient(
            base_url=self.base_url,
            group_name="automation-intelligence",
            timeout=30.0,
            max_retries=3,
            circuit_breaker=_automation_breaker,
        )
        logger.info(f"AI Automation Service client initialized with base_url={self.base_url}")

    async def validate_yaml(
        self,
        yaml_content: str,
        validate_entities: bool = True,
        validate_safety: bool = True,
        _context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Validate Home Assistant automation YAML via unified endpoint.

        Args:
            yaml_content: YAML string to validate
            validate_entities: Whether to validate entities exist in HA (default: True)
            validate_safety: Whether to run safety validation (default: True, maps to validate_services)
            _context: Optional context (unused by unified endpoint, kept for compatibility)

        Returns:
            Dictionary with validation results.

        Raises:
            Exception: If API request fails or circuit breaker is open
        """
        try:
            payload = {
                "yaml_content": yaml_content,
                "normalize": True,
                "validate_entities": validate_entities,
                "validate_services": validate_safety,
            }

            logger.debug(
                f"Validating YAML via AI Automation Service unified endpoint "
                f"(entities={validate_entities}, services={validate_safety})"
            )

            response = await self._cross_client.call(
                "POST", "/api/v1/automations/validate",
                json=payload, headers=self._auth_headers,
            )
            response.raise_for_status()

            result = response.json()

            logger.info(
                f"YAML validation complete: valid={result.get('valid', False)}, "
                f"errors={len(result.get('errors', []))}, warnings={len(result.get('warnings', []))}"
            )

            return result

        except CircuitOpenError as e:
            error_msg = f"AI Automation Service circuit breaker open: {e}"
            logger.error(f"Circuit open: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.HTTPStatusError as e:
            error_msg = f"AI Automation Service returned {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"HTTP error validating YAML: {error_msg}")
            raise Exception(error_msg) from e
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError) as e:
            error_msg = f"Error validating YAML: {e}"
            logger.error(error_msg)
            raise Exception(error_msg) from e

    async def close(self):
        """No-op — CrossGroupClient uses per-request clients."""
        logger.debug("AI Automation Service client close called (no-op with CrossGroupClient)")

