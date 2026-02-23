"""Shared circuit breakers for proactive-agent-service cross-group calls.

Module-level breakers ensure all client instances share a single circuit
per target service group.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    _project_root = str(Path(__file__).resolve().parents[4])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
except IndexError:
    pass  # Docker: PYTHONPATH already includes /app

from shared.resilience import CircuitBreaker

# data-api, sports-data, carbon-intensity all live in core-platform (Group 1)
core_platform_breaker = CircuitBreaker(name="core-platform")

# weather-api lives in data-collectors (Group 2)
data_collectors_breaker = CircuitBreaker(name="data-collectors")
