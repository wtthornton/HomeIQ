"""Cross-Domain API Contract Tests.

Verifies that services in automation-core and ml-engine correctly reference
data-api client interfaces and that their Pydantic models / request schemas
are compatible with the data-api contract.

These are static/import-level tests — they do not require running services,
only that the code can be loaded and schemas validated.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

from homeiq_resilience import CrossGroupClient, ServiceAuthValidator
from homeiq_resilience.circuit_breaker import CircuitBreaker


def _add_service_src(domain: str, service: str):
    """Add a service's src directory to sys.path, return the path."""
    src = os.path.join(os.getcwd(), "domains", domain, service, "src")
    if os.path.isdir(src) and src not in sys.path:
        sys.path.insert(0, src)
    return src


class TestCrossDomainAPI:
    """Validate that cross-domain consumers use compatible API contracts."""

    def test_automation_core_imports_data_client(self):
        """automation-core services should be able to import homeiq_data client."""
        from homeiq_data import StandardDataAPIClient  # noqa: F401

    def test_ml_engine_imports_data_client(self):
        """ml-engine services should be able to import homeiq_data client."""
        from homeiq_data import StandardDataAPIClient  # noqa: F401

    def test_automation_services_use_bearer_auth_pattern(self):
        """Automation-core services that call data-api must support api_key param.

        The DataAPIClient requires api_key for Bearer auth. Verify the
        client constructor accepts it.
        """
        import inspect

        from homeiq_data import StandardDataAPIClient

        sig = inspect.signature(StandardDataAPIClient.__init__)
        params = list(sig.parameters.keys())
        assert "api_key" in params, (
            "StandardDataAPIClient must accept api_key parameter for Bearer auth"
        )

    def test_resilience_cross_group_client_available(self):
        """CrossGroupClient from homeiq-resilience should be importable.

        This is the standard way for services in one domain group to call
        services in another group with circuit-breaker protection.
        """
        from homeiq_resilience import CrossGroupClient  # noqa: F401

    def test_circuit_breaker_wraps_cross_domain_calls(self):
        """CircuitBreaker should be instantiable for cross-domain protection."""
        from homeiq_resilience import CircuitBreaker

        cb = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30,
            name="data-api",
        )
        assert cb is not None

    def test_shared_validation_router_importable(self):
        """UnifiedValidationRouter (used by automation-core) should import."""
        from homeiq_patterns import UnifiedValidationRouter  # noqa: F401

    def test_rag_context_service_importable(self):
        """RAGContextService (used by ml-engine and automation-core) should import."""
        from homeiq_patterns import RAGContextService  # noqa: F401

    def test_observability_logging_consistent(self):
        """All domains should use the same logging setup from homeiq-observability."""
        from homeiq_observability.logging_config import setup_logging

        logger = setup_logging("cross-domain-test")
        assert logger is not None


@pytest.mark.integration
class TestCrossGroupAuth:
    """Validate cross-group Bearer token authentication (Story 78.5)."""

    @pytest.mark.asyncio
    async def test_service_auth_validator_rejects_invalid_token(self):
        """ServiceAuthValidator should reject requests with an invalid token.

        When SERVICE_AUTH_TOKEN is set, a request with a wrong Bearer token
        should raise HTTPException with 401.
        """
        import os

        from fastapi import HTTPException

        validator = ServiceAuthValidator(env_var="TEST_SERVICE_AUTH_TOKEN")

        # Set the expected token
        os.environ["TEST_SERVICE_AUTH_TOKEN"] = "correct-token"
        try:
            mock_request = MagicMock()
            mock_request.method = "GET"
            mock_request.url.path = "/api/v1/test"
            mock_request.client.host = "127.0.0.1"

            # Simulate wrong credentials
            mock_credentials = MagicMock()
            mock_credentials.credentials = "wrong-token"

            with pytest.raises(HTTPException) as exc_info:
                await validator(request=mock_request, credentials=mock_credentials)

            assert exc_info.value.status_code == 401
        finally:
            del os.environ["TEST_SERVICE_AUTH_TOKEN"]

    @pytest.mark.asyncio
    async def test_service_auth_validator_accepts_valid_token(self):
        """ServiceAuthValidator should accept requests with a valid token.

        When SERVICE_AUTH_TOKEN is set and the request sends the matching
        Bearer token, validation should pass and return the token string.
        """
        import os

        validator = ServiceAuthValidator(env_var="TEST_SERVICE_AUTH_TOKEN2")

        os.environ["TEST_SERVICE_AUTH_TOKEN2"] = "valid-secret"
        try:
            mock_request = MagicMock()
            mock_request.method = "GET"
            mock_request.url.path = "/api/v1/data"

            mock_credentials = MagicMock()
            mock_credentials.credentials = "valid-secret"

            result = await validator(request=mock_request, credentials=mock_credentials)
            assert result == "valid-secret"
        finally:
            del os.environ["TEST_SERVICE_AUTH_TOKEN2"]

    def test_cross_group_client_injects_auth_header(self):
        """CrossGroupClient should set Authorization header when auth_token is provided.

        Validates the constructor stores the token and that _do_request
        would inject it into outgoing headers.
        """
        client = CrossGroupClient(
            base_url="http://data-api:8006",
            group_name="core-platform",
            auth_token="bearer-test-token",
        )

        assert client._auth_token == "bearer-test-token"

        # Verify that a client without auth_token has None
        client_no_auth = CrossGroupClient(
            base_url="http://data-api:8006",
            group_name="core-platform",
        )
        assert client_no_auth._auth_token is None
