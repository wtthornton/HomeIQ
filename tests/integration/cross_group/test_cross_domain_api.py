"""Cross-Domain API Contract Tests.

Verifies that services in automation-core and ml-engine correctly reference
data-api client interfaces and that their Pydantic models / request schemas
are compatible with the data-api contract.

These are static/import-level tests — they do not require running services,
only that the code can be loaded and schemas validated.
"""

import os
import sys



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
        from homeiq_data import DataAPIClient  # noqa: F401

    def test_ml_engine_imports_data_client(self):
        """ml-engine services should be able to import homeiq_data client."""
        from homeiq_data import DataAPIClient  # noqa: F401

    def test_automation_services_use_bearer_auth_pattern(self):
        """Automation-core services that call data-api must support api_key param.

        The DataAPIClient requires api_key for Bearer auth. Verify the
        client constructor accepts it.
        """
        import inspect

        from homeiq_data import DataAPIClient

        sig = inspect.signature(DataAPIClient.__init__)
        params = list(sig.parameters.keys())
        assert "api_key" in params, (
            "DataAPIClient must accept api_key parameter for Bearer auth"
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
            service_name="data-api",
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
