"""Tests for homeiq_ha package initialization and public API."""

from __future__ import annotations

import importlib


def test_package_imports() -> None:
    """Package should be importable with all public exports."""
    import homeiq_ha

    assert hasattr(homeiq_ha, "__version__")
    assert homeiq_ha.__version__ == "1.0.0"

    expected_exports = [
        "DEPLOYMENT_MODE_PRODUCTION",
        "DEPLOYMENT_MODE_TEST",
        "check_data_generation_allowed",
        "check_test_service_allowed",
        "get_deployment_mode",
        "get_health_check_info",
        "log_deployment_info",
        "validate_deployment_mode",
    ]
    for name in expected_exports:
        assert hasattr(homeiq_ha, name), f"Missing export: {name}"


def test_all_attribute() -> None:
    """__all__ should contain every public export."""
    import homeiq_ha

    assert hasattr(homeiq_ha, "__all__")
    assert len(homeiq_ha.__all__) == 8


def test_module_reimport() -> None:
    """Re-importing the package should return the cached module."""
    import homeiq_ha

    mod = importlib.import_module("homeiq_ha")
    assert mod is homeiq_ha


def test_get_deployment_mode_returns_string() -> None:
    """get_deployment_mode should return a string."""
    from homeiq_ha import get_deployment_mode

    mode = get_deployment_mode()
    assert isinstance(mode, str)
    assert mode in ("test", "production")


def test_health_check_info_returns_dict() -> None:
    """get_health_check_info should return a dictionary."""
    from homeiq_ha import get_health_check_info

    info = get_health_check_info()
    assert isinstance(info, dict)
    assert "deployment_mode" in info
    assert "is_test" in info
    assert "is_production" in info


def test_deployment_mode_constants() -> None:
    """Deployment mode constants should have expected values."""
    from homeiq_ha import DEPLOYMENT_MODE_PRODUCTION, DEPLOYMENT_MODE_TEST

    assert DEPLOYMENT_MODE_TEST == "test"
    assert DEPLOYMENT_MODE_PRODUCTION == "production"
