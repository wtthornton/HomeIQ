"""Tests for homeiq_patterns package initialization and public API."""

from __future__ import annotations

import importlib


def test_package_imports() -> None:
    """All public symbols should be importable from the top-level package."""
    import homeiq_patterns

    expected_exports = [
        "RAGContextService",
        "RAGContextRegistry",
        "UnifiedValidationRouter",
        "ValidationBackend",
        "ValidationRequest",
        "ValidationResponse",
        "ValidationSubsection",
        "categorize_errors",
        "get_error_domain_hints",
        "PostActionVerifier",
        "VerificationResult",
        "VerificationResultStore",
        "VerificationWarning",
    ]
    for name in expected_exports:
        assert hasattr(homeiq_patterns, name), f"Missing export: {name}"


def test_all_attribute() -> None:
    """__all__ should contain every public export plus __version__."""
    import homeiq_patterns

    assert hasattr(homeiq_patterns, "__all__")
    assert "__version__" in homeiq_patterns.__all__
    assert len(homeiq_patterns.__all__) == 14


def test_version_attribute() -> None:
    """Package should expose a __version__ string."""
    import homeiq_patterns

    assert hasattr(homeiq_patterns, "__version__")
    assert isinstance(homeiq_patterns.__version__, str)


def test_module_reimport() -> None:
    """Re-importing the package should return the cached module."""
    import homeiq_patterns

    mod = importlib.import_module("homeiq_patterns")
    assert mod is homeiq_patterns
