"""Shared fixtures for cross-group integration tests.

Provides URL fixtures for all service endpoints and configures sys.path
for importing shared libraries and domain service source code.
"""

import os
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Project root and shared library paths
# ---------------------------------------------------------------------------
_project_root = Path(__file__).resolve().parents[3]

_LIB_PATHS = [
    _project_root / "libs" / "homeiq-resilience" / "src",
    _project_root / "libs" / "homeiq-data" / "src",
    _project_root / "libs" / "homeiq-observability" / "src",
    _project_root / "libs" / "homeiq-ha" / "src",
    _project_root / "libs" / "homeiq-patterns" / "src",
    _project_root / "libs" / "homeiq-memory" / "src",
]

# NOTE: Domain service src paths (zeek-network-service, proactive-agent-service)
# are NOT added globally because they share package names (models/, services/)
# which causes namespace collisions.  Each test file adds its own path via the
# ``service_src_path`` fixture below.

for p in _LIB_PATHS:
    p_str = str(p)
    if p.is_dir() and p_str not in sys.path:
        sys.path.insert(0, p_str)


# ---------------------------------------------------------------------------
# Core Platform fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def data_api_url():
    return os.environ.get("DATA_API_URL", "http://localhost:8006")


@pytest.fixture
def admin_api_url():
    return os.environ.get("ADMIN_API_URL", "http://localhost:8004")


@pytest.fixture
def postgres_url():
    return os.environ.get(
        "POSTGRES_URL",
        "postgresql+asyncpg://homeiq:homeiq_test@localhost:5432/homeiq_test",
    )


# ---------------------------------------------------------------------------
# Zeek / Data-Collectors fixtures (Story 78.2)
# ---------------------------------------------------------------------------

@pytest.fixture
def zeek_service_url():
    return os.environ.get("ZEEK_SERVICE_URL", "http://localhost:8048")


@pytest.fixture
def influxdb_url():
    return os.environ.get("INFLUXDB_URL", "http://localhost:8086")


# ---------------------------------------------------------------------------
# Agent / Automation-Core fixtures (Story 78.3)
# ---------------------------------------------------------------------------

@pytest.fixture
def ha_agent_url():
    return os.environ.get("HA_AGENT_URL", "http://localhost:8030")


@pytest.fixture
def proactive_agent_url():
    return os.environ.get("PROACTIVE_AGENT_URL", "http://localhost:8040")


@pytest.fixture
def device_control_url():
    return os.environ.get("DEVICE_CONTROL_URL", "http://localhost:8042")


# ---------------------------------------------------------------------------
# Memory Brain fixtures (Story 78.4)
# ---------------------------------------------------------------------------

@pytest.fixture
def memory_database_url():
    return os.environ.get(
        "MEMORY_DATABASE_URL",
        "postgresql+asyncpg://homeiq:homeiq_test@localhost:5432/homeiq_test",
    )
