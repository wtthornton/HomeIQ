"""Group-aware health check utilities.

Provides a structured health-check endpoint builder so every service can
report its own status **and** the reachability of its upstream dependencies.

Example response::

    {
        "status": "degraded",
        "group": "automation-intelligence",
        "version": "1.2.3",
        "uptime_seconds": 3600,
        "dependencies": {
            "data-api": {"status": "healthy", "latency_ms": 12},
            "ai-core-service": {
                "status": "unreachable",
                "last_seen": "2026-02-22T10:00:00Z"
            }
        },
        "degraded_features": []
    }
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class DependencyStatus:
    """Health snapshot of a single upstream dependency."""

    name: str
    status: str = "unknown"  # healthy | unhealthy | unreachable
    latency_ms: float | None = None
    last_seen: str | None = None  # ISO-8601 timestamp


class GroupHealthCheck:
    """Builder for group-aware ``/health`` responses.

    Parameters
    ----------
    group_name:
        Logical group this service belongs to (e.g. ``core-platform``).
    version:
        Application version string (e.g. ``1.0.0``).
    """

    def __init__(self, group_name: str, version: str = "0.0.0") -> None:
        self._group_name = group_name
        self._version = version
        self._start_time = time.monotonic()
        self._dependencies: dict[str, str] = {}  # name -> health URL
        self._degraded_features: list[str] = []

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def register_dependency(self, name: str, url: str) -> None:
        """Register an upstream dependency to monitor.

        Parameters
        ----------
        name:
            Human-readable dependency name (e.g. ``data-api``).
        url:
            Base URL of the dependency.  ``/health`` is appended
            automatically when probing.
        """
        self._dependencies[name] = url.rstrip("/")

    def add_degraded_feature(self, feature: str) -> None:
        """Mark a feature as degraded (shown in the health response)."""
        if feature not in self._degraded_features:
            self._degraded_features.append(feature)

    def remove_degraded_feature(self, feature: str) -> None:
        """Remove a previously-degraded feature."""
        if feature in self._degraded_features:
            self._degraded_features.remove(feature)

    # ------------------------------------------------------------------
    # Probing
    # ------------------------------------------------------------------

    async def check_all(self) -> list[DependencyStatus]:
        """Probe every registered dependency and return their statuses."""
        results: list[DependencyStatus] = []
        for name, base_url in self._dependencies.items():
            result = await self._probe(name, base_url)
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Response builder
    # ------------------------------------------------------------------

    async def to_dict(self) -> dict[str, Any]:
        """Build the structured health response dictionary."""
        dep_statuses = await self.check_all()

        overall = self._compute_overall_status(dep_statuses)

        dependencies_dict: dict[str, dict[str, Any]] = {}
        for dep in dep_statuses:
            entry: dict[str, Any] = {"status": dep.status}
            if dep.latency_ms is not None:
                entry["latency_ms"] = round(dep.latency_ms, 1)
            if dep.last_seen is not None:
                entry["last_seen"] = dep.last_seen
            dependencies_dict[dep.name] = entry

        return {
            "status": overall,
            "group": self._group_name,
            "version": self._version,
            "uptime_seconds": round(time.monotonic() - self._start_time),
            "dependencies": dependencies_dict,
            "degraded_features": list(self._degraded_features),
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    async def _probe(name: str, base_url: str) -> DependencyStatus:
        """Ping a single dependency's ``/health`` endpoint."""
        try:
            start = time.monotonic()
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                resp = await client.get(f"{base_url}/health")
            elapsed_ms = (time.monotonic() - start) * 1000

            now_iso = datetime.now(timezone.utc).isoformat()

            if resp.status_code == 200:
                return DependencyStatus(
                    name=name,
                    status="healthy",
                    latency_ms=elapsed_ms,
                    last_seen=now_iso,
                )
            return DependencyStatus(
                name=name,
                status="unhealthy",
                latency_ms=elapsed_ms,
                last_seen=now_iso,
            )

        except (httpx.ConnectError, httpx.TimeoutException, OSError) as exc:
            logger.warning("Dependency '%s' unreachable: %s", name, exc)
            return DependencyStatus(name=name, status="unreachable")

    @staticmethod
    def _compute_overall_status(deps: list[DependencyStatus]) -> str:
        """Derive the aggregate status from individual dependency statuses.

        Rules:
        - No dependencies registered -> ``healthy``
        - All healthy -> ``healthy``
        - All unhealthy/unreachable -> ``unhealthy``
        - Mixed -> ``degraded``
        """
        if not deps:
            return "healthy"

        healthy_count = sum(1 for d in deps if d.status == "healthy")

        if healthy_count == len(deps):
            return "healthy"
        if healthy_count == 0:
            return "unhealthy"
        return "degraded"
