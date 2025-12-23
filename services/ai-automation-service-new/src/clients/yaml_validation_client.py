"""
YAML Validation Service Client for AI Automation Service

Epic 51, Story 51.6: Integrate Validation Service with Automation Service

Provides access to comprehensive YAML validation via the new yaml-validation-service.
"""

import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class YAMLValidationClient:
    """Client for YAML validation via yaml-validation-service"""

    def __init__(self, base_url: str = "http://yaml-validation-service:8026", api_key: str | None = None):
        """
        Initialize YAML Validation Service client.

        Args:
            base_url: Base URL for YAML Validation Service (default: http://yaml-validation-service:8026)
            api_key: API key for authentication (optional)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        logger.info(f"YAML Validation Service client initialized with base_url={self.base_url}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def validate_yaml(
        self,
        yaml_content: str,
        normalize: bool = True,
        validate_entities: bool = True,
        validate_services: bool = False
    ) -> dict[str, Any]:
        """
        Validate Home Assistant automation YAML.

        Args:
            yaml_content: YAML string to validate
            normalize: Whether to normalize YAML to canonical format (default: True)
            validate_entities: Whether to validate entities exist (default: True)
            validate_services: Whether to validate services exist (default: False)

        Returns:
            Dictionary with validation results:
            - valid: bool - Whether validation passed
            - errors: list[str] - List of error messages
            - warnings: list[str] - List of warning messages
            - score: float - Quality score (0-100)
            - fixed_yaml: str | None - Normalized/fixed YAML if available
            - fixes_applied: list[str] - List of fixes applied

        Raises:
            httpx.HTTPError: If API request fails
        """
        try:
            payload = {
                "yaml_content": yaml_content,
                "normalize": normalize,
                "validate_entities": validate_entities,
                "validate_services": validate_services
            }

            logger.debug(
                f"Validating YAML via YAML Validation Service "
                f"(normalize={normalize}, entities={validate_entities}, services={validate_services})"
            )

            headers = {}
            if self.api_key:
                headers["X-HomeIQ-API-Key"] = self.api_key

            response = await self.client.post(
                f"{self.base_url}/api/v1/validation/validate",
                json=payload,
                headers=headers
            )
            response.raise_for_status()

            result = response.json()

            logger.info(
                f"✅ YAML validation complete: valid={result.get('valid', False)}, "
                f"errors={len(result.get('errors', []))}, warnings={len(result.get('warnings', []))}, "
                f"score={result.get('score', 0)}"
            )

            return result

        except httpx.HTTPStatusError as e:
            error_msg = f"YAML Validation Service returned {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"❌ HTTP error validating YAML: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.ConnectError as e:
            error_msg = f"Could not connect to YAML Validation Service at {self.base_url}. Is the service running?"
            logger.error(f"❌ Connection error: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.TimeoutException as e:
            error_msg = "YAML Validation Service request timed out after 30 seconds"
            logger.error(f"❌ Timeout error: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.HTTPError as e:
            error_msg = f"HTTP error validating YAML: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e

    async def normalize_yaml(self, yaml_content: str) -> dict[str, Any]:
        """
        Normalize YAML to canonical format.

        Args:
            yaml_content: YAML string to normalize

        Returns:
            Dictionary with normalized YAML and fixes applied
        """
        result = await self.validate_yaml(
            yaml_content=yaml_content,
            normalize=True,
            validate_entities=False,
            validate_services=False
        )
        return {
            "normalized_yaml": result.get("fixed_yaml") or yaml_content,
            "fixes_applied": result.get("fixes_applied", [])
        }

    async def close(self):
        """Close HTTP client connection pool"""
        await self.client.aclose()
        logger.debug("YAML Validation Service client closed")

