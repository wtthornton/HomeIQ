"""
AI Automation Service Client for HA AI Agent Service

Provides access to YAML validation via AI Automation Service.
"""

import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


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
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        logger.info(f"AI Automation Service client initialized with base_url={self.base_url}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def validate_yaml(
        self,
        yaml_content: str,
        validate_entities: bool = True,
        validate_safety: bool = True,
        context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Validate Home Assistant automation YAML.

        Args:
            yaml_content: YAML string to validate
            validate_entities: Whether to validate entities exist in HA (default: True)
            validate_safety: Whether to run safety validation (default: True)
            context: Optional context (validated entities, etc.)

        Returns:
            Dictionary with validation results:
            - valid: bool - Whether validation passed
            - errors: list[dict] - List of error objects
            - warnings: list[dict] - List of warning objects
            - stages: dict[str, bool] - Validation stage results
            - entity_results: list[dict] - Entity validation details
            - safety_score: int | None - Safety score (0-100)
            - fixed_yaml: str | None - Auto-fixed YAML if available
            - summary: str - Validation summary message

        Raises:
            httpx.HTTPError: If API request fails
        """
        try:
            payload = {
                "yaml": yaml_content,
                "validate_entities": validate_entities,
                "validate_safety": validate_safety
            }
            if context:
                payload["context"] = context

            logger.debug(f"Validating YAML via AI Automation Service (entities={validate_entities}, safety={validate_safety})")

            headers = {}
            if self.api_key:
                headers["X-HomeIQ-API-Key"] = self.api_key

            response = await self.client.post(
                f"{self.base_url}/api/v1/yaml/validate",
                json=payload,
                headers=headers
            )
            response.raise_for_status()

            result = response.json()

            logger.info(
                f"✅ YAML validation complete: valid={result.get('valid', False)}, "
                f"errors={len(result.get('errors', []))}, warnings={len(result.get('warnings', []))}"
            )

            return result

        except httpx.HTTPStatusError as e:
            error_msg = f"AI Automation Service returned {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"❌ HTTP error validating YAML: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.ConnectError as e:
            error_msg = f"Could not connect to AI Automation Service at {self.base_url}. Is the service running?"
            logger.error(f"❌ Connection error: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.TimeoutException as e:
            error_msg = "AI Automation Service request timed out after 30 seconds"
            logger.error(f"❌ Timeout error: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.HTTPError as e:
            error_msg = f"HTTP error validating YAML: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e

    async def close(self):
        """Close HTTP client connection pool"""
        await self.client.aclose()
        logger.debug("AI Automation Service client closed")

