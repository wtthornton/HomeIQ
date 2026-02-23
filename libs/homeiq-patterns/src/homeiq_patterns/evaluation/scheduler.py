"""
Agent Evaluation Framework — Evaluation Scheduler

Orchestrates automated evaluation runs based on each agent's priority
matrix.  Frequencies (every_session, hourly, daily, weekly, monthly) are
checked against last-run timestamps to decide which evaluations are due.

Usage::

    scheduler = EvaluationScheduler(registry=registry)
    scheduler.register_agent(config, session_source=source)
    reports = await scheduler.check_and_run()
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from .config import AgentEvalConfig
from .models import BatchReport, SessionTrace
from .registry import EvaluationRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Session source protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class SessionSource(Protocol):
    """Protocol for objects that can provide recent sessions."""

    async def get_recent(
        self, agent_name: str, count: int
    ) -> list[SessionTrace]:
        """Return the most recent *count* sessions for the given agent."""
        ...  # pragma: no cover


class InMemorySessionSource:
    """In-memory session source for testing."""

    def __init__(self, sessions: list[SessionTrace] | None = None):
        self._sessions: list[SessionTrace] = sessions or []

    def add(self, session: SessionTrace) -> None:
        self._sessions.append(session)

    def add_many(self, sessions: list[SessionTrace]) -> None:
        self._sessions.extend(sessions)

    async def get_recent(
        self, agent_name: str, count: int
    ) -> list[SessionTrace]:
        matching = [
            s for s in self._sessions if s.agent_name == agent_name
        ]
        # Most recent first (by timestamp)
        matching.sort(key=lambda s: s.timestamp, reverse=True)
        return matching[:count]


# ---------------------------------------------------------------------------
# Frequency helpers
# ---------------------------------------------------------------------------

# Map frequency string → seconds between runs
_FREQUENCY_SECONDS: dict[str, float] = {
    "every_session": 0,  # Always run (every check_and_run call)
    "hourly": 3600,
    "daily": 86400,
    "weekly": 604800,
    "monthly": 2592000,  # 30 days
}


def _is_due(
    last_run: float | None,
    frequency: str,
    now: float,
) -> bool:
    """Check if an evaluation is due based on frequency and last run time."""
    if frequency == "every_session":
        return True
    interval = _FREQUENCY_SECONDS.get(frequency)
    if interval is None:
        logger.warning("Unknown frequency '%s' — treating as due", frequency)
        return True
    if last_run is None:
        return True
    return (now - last_run) >= interval


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


class _ScheduledAgent:
    """Internal: tracked agent with config and session source."""

    __slots__ = ("config", "session_source")

    def __init__(
        self,
        config: AgentEvalConfig,
        session_source: SessionSource,
    ):
        self.config = config
        self.session_source = session_source


class EvaluationScheduler:
    """
    Schedules and runs evaluations based on agent priority matrices.

    Usage::

        scheduler = EvaluationScheduler(registry=registry)
        scheduler.register_agent(config, session_source=src)
        reports = await scheduler.check_and_run()
    """

    def __init__(
        self,
        registry: EvaluationRegistry,
        batch_size: int = 20,
    ):
        self._registry = registry
        self._batch_size = batch_size
        self._agents: dict[str, _ScheduledAgent] = {}
        # Track last run per (agent, priority): float timestamp
        self._last_runs: dict[str, float] = {}

    @property
    def registered_agents(self) -> list[str]:
        """List of registered agent names."""
        return list(self._agents.keys())

    @property
    def batch_size(self) -> int:
        return self._batch_size

    @batch_size.setter
    def batch_size(self, value: int) -> None:
        self._batch_size = max(1, value)

    def register_agent(
        self,
        config: AgentEvalConfig,
        session_source: SessionSource,
    ) -> None:
        """Register an agent for scheduled evaluation."""
        # Also register in the evaluation registry if not already
        if config.agent_name not in self._registry.registered_agents:
            self._registry.register_agent(config)

        self._agents[config.agent_name] = _ScheduledAgent(
            config=config,
            session_source=session_source,
        )
        logger.info("Scheduler registered agent '%s'", config.agent_name)

    async def check_and_run(self) -> dict[str, BatchReport]:
        """
        Check all agents for due evaluations and run them.

        Returns a dict mapping agent_name → BatchReport for agents that
        were evaluated.
        """
        now = time.time()
        results: dict[str, BatchReport] = {}

        for agent_name, entry in self._agents.items():
            due_priorities = self._get_due_priorities(agent_name, now)
            if not due_priorities:
                logger.debug("No evaluations due for '%s'", agent_name)
                continue

            report = await self._run_agent_evaluation(agent_name, entry, now)
            if report is not None:
                results[agent_name] = report

            # Update last-run timestamps for all due priorities
            for priority in due_priorities:
                key = f"{agent_name}:{priority}"
                self._last_runs[key] = now

        return results

    async def run_agent(
        self, agent_name: str
    ) -> BatchReport | None:
        """
        Manually trigger evaluation for a specific agent.

        Ignores frequency checks — runs all evaluators immediately.
        """
        entry = self._agents.get(agent_name)
        if entry is None:
            logger.error("Agent '%s' not registered in scheduler", agent_name)
            return None

        now = time.time()
        report = await self._run_agent_evaluation(agent_name, entry, now)

        # Update all priority timestamps
        if report is not None:
            priorities = {p.priority for p in entry.config.priority_matrix}
            for priority in priorities:
                self._last_runs[f"{agent_name}:{priority}"] = now

        return report

    async def get_due_evaluations(self) -> list[dict[str, Any]]:
        """
        Return list of evaluations that are currently due.

        Each entry: {"agent": str, "priority": str, "metrics": [str]}
        """
        now = time.time()
        due: list[dict[str, Any]] = []

        for agent_name, entry in self._agents.items():
            due_by_priority: dict[str, list[str]] = {}
            for pe in entry.config.priority_matrix:
                key = f"{agent_name}:{pe.priority}"
                last = self._last_runs.get(key)
                if _is_due(last, pe.frequency, now):
                    due_by_priority.setdefault(pe.priority, []).append(pe.metric)

            for priority, metrics in due_by_priority.items():
                due.append({
                    "agent": agent_name,
                    "priority": priority,
                    "metrics": metrics,
                })

        return due

    def get_last_run(self, agent_name: str, priority: str) -> float | None:
        """Get the last run timestamp for an agent+priority combination."""
        return self._last_runs.get(f"{agent_name}:{priority}")

    # -- internals ---------------------------------------------------------

    def _get_due_priorities(
        self, agent_name: str, now: float
    ) -> list[str]:
        """Return list of priorities that are due for evaluation."""
        entry = self._agents.get(agent_name)
        if entry is None:
            return []

        due: set[str] = set()
        for pe in entry.config.priority_matrix:
            key = f"{agent_name}:{pe.priority}"
            last = self._last_runs.get(key)
            if _is_due(last, pe.frequency, now):
                due.add(pe.priority)
        return sorted(due)

    async def _run_agent_evaluation(
        self,
        agent_name: str,
        entry: _ScheduledAgent,
        now: float,
    ) -> BatchReport | None:
        """Run evaluation for a single agent."""
        start = time.monotonic()

        # Get recent sessions
        sessions = await entry.session_source.get_recent(
            agent_name, self._batch_size
        )

        if not sessions:
            logger.warning(
                "No sessions available for '%s' — skipping evaluation",
                agent_name,
            )
            return BatchReport(
                agent_name=agent_name,
                sessions_evaluated=0,
                total_evaluations=0,
            )

        # Run evaluation
        report = await self._registry.evaluate_batch(sessions)

        duration = time.monotonic() - start
        logger.info(
            "Evaluated '%s': %d sessions, %d evaluations, %.2fs, %d alerts",
            agent_name,
            report.sessions_evaluated,
            report.total_evaluations,
            duration,
            len(report.alerts),
        )

        return report
