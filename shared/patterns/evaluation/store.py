"""
Agent Evaluation Framework — Evaluation History Storage

Dual-write evaluation results to InfluxDB (time-series scores) and
SQLite (session-level details).  Provides query methods for trends,
historical scores, and latest reports.

Usage::

    store = EvaluationStore(influxdb_client=client, sqlite_path=":memory:")
    await store.initialize()
    await store.store_batch_report(report)
    scores = await store.get_scores("ha-ai-agent", period="7d")
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Protocol, runtime_checkable

import aiosqlite

from .models import BatchReport, EvalLevel, EvaluationReport, EvaluationResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# InfluxDB writer protocol (decoupled from influxdb-client library)
# ---------------------------------------------------------------------------


@runtime_checkable
class InfluxDBWriter(Protocol):
    """Protocol for writing points to InfluxDB."""

    def write_points(self, points: list[dict[str, Any]]) -> None:
        """Write a list of point dicts to InfluxDB."""
        ...  # pragma: no cover


class NullInfluxDBWriter:
    """No-op writer when InfluxDB is not available."""

    def write_points(self, points: list[dict[str, Any]]) -> None:
        logger.debug("NullInfluxDBWriter: %d points discarded", len(points))


# ---------------------------------------------------------------------------
# EvaluationStore
# ---------------------------------------------------------------------------

# Default retention periods
_DEFAULT_INFLUXDB_RETENTION_DAYS = 90
_DEFAULT_SQLITE_RETENTION_DAYS = 30

_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS evaluation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    run_timestamp TEXT NOT NULL,
    sessions_evaluated INTEGER NOT NULL DEFAULT 0,
    total_evaluations INTEGER NOT NULL DEFAULT 0,
    alerts_triggered INTEGER NOT NULL DEFAULT 0,
    summary_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS evaluation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    session_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    evaluator_name TEXT NOT NULL,
    level TEXT NOT NULL,
    score REAL NOT NULL,
    label TEXT DEFAULT '',
    explanation TEXT DEFAULT '',
    timestamp TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES evaluation_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_results_agent ON evaluation_results(agent_name);
CREATE INDEX IF NOT EXISTS idx_results_run ON evaluation_results(run_id);
CREATE INDEX IF NOT EXISTS idx_runs_agent ON evaluation_runs(agent_name);
"""


class EvaluationStore:
    """
    Dual-write evaluation storage: InfluxDB for time-series, SQLite for details.

    Supports degraded mode: if InfluxDB is unavailable, writes only to SQLite.
    """

    def __init__(
        self,
        influxdb_writer: InfluxDBWriter | None = None,
        sqlite_path: str = ":memory:",
        influxdb_retention_days: int = _DEFAULT_INFLUXDB_RETENTION_DAYS,
        sqlite_retention_days: int = _DEFAULT_SQLITE_RETENTION_DAYS,
    ):
        self._influx = influxdb_writer or NullInfluxDBWriter()
        self._sqlite_path = sqlite_path
        self._influx_retention = influxdb_retention_days
        self._sqlite_retention = sqlite_retention_days
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Create SQLite tables if they don't exist."""
        self._db = await aiosqlite.connect(self._sqlite_path)
        await self._db.executescript(_CREATE_TABLES_SQL)
        await self._db.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    async def store_batch_report(self, report: BatchReport) -> int:
        """
        Store a BatchReport: write scores to InfluxDB and details to SQLite.

        Returns the evaluation_runs.id for the stored run.
        """
        if self._db is None:
            await self.initialize()
        assert self._db is not None

        # 1. Write to InfluxDB (time-series scores)
        self._write_influxdb_points(report)

        # 2. Write run record to SQLite
        run_id = await self._write_run_record(report)

        # 3. Write individual results to SQLite
        await self._write_result_records(run_id, report)

        return run_id

    async def get_scores(
        self,
        agent_name: str,
        evaluator: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Query historical scores from SQLite."""
        if self._db is None:
            return []

        query = """
            SELECT er.evaluator_name, er.level, er.score, er.label, er.timestamp
            FROM evaluation_results er
            JOIN evaluation_runs r ON er.run_id = r.id
            WHERE er.agent_name = ?
        """
        params: list[Any] = [agent_name]

        if evaluator:
            query += " AND er.evaluator_name = ?"
            params.append(evaluator)
        if start:
            query += " AND er.timestamp >= ?"
            params.append(start.isoformat())
        if end:
            query += " AND er.timestamp <= ?"
            params.append(end.isoformat())

        query += " ORDER BY er.timestamp DESC"

        async with self._db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        return [
            {
                "evaluator_name": row[0],
                "level": row[1],
                "score": row[2],
                "label": row[3],
                "timestamp": row[4],
            }
            for row in rows
        ]

    async def get_trends(
        self,
        agent_name: str,
        period: str = "7d",
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Get aggregated score trends over time.

        Returns dict keyed by evaluator_name, each with a list of
        {timestamp, score} entries.
        """
        if self._db is None:
            return {}

        days = _parse_period(period)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        query = """
            SELECT er.evaluator_name, r.run_timestamp, AVG(er.score) as avg_score
            FROM evaluation_results er
            JOIN evaluation_runs r ON er.run_id = r.id
            WHERE er.agent_name = ? AND r.run_timestamp >= ?
            GROUP BY er.evaluator_name, r.run_timestamp
            ORDER BY r.run_timestamp ASC
        """

        async with self._db.execute(query, [agent_name, cutoff]) as cursor:
            rows = await cursor.fetchall()

        trends: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            evaluator = row[0]
            trends.setdefault(evaluator, []).append({
                "timestamp": row[1],
                "score": round(row[2], 4),
            })

        return trends

    async def get_latest_report(
        self, agent_name: str
    ) -> dict[str, Any] | None:
        """Get the most recent evaluation run summary."""
        if self._db is None:
            return None

        query = """
            SELECT id, agent_name, run_timestamp, sessions_evaluated,
                   total_evaluations, alerts_triggered, summary_json
            FROM evaluation_runs
            WHERE agent_name = ?
            ORDER BY run_timestamp DESC
            LIMIT 1
        """

        async with self._db.execute(query, [agent_name]) as cursor:
            row = await cursor.fetchone()

        if row is None:
            return None

        return {
            "run_id": row[0],
            "agent_name": row[1],
            "run_timestamp": row[2],
            "sessions_evaluated": row[3],
            "total_evaluations": row[4],
            "alerts_triggered": row[5],
            "summary": json.loads(row[6]) if row[6] else {},
        }

    async def get_run_count(self, agent_name: str) -> int:
        """Get the total number of evaluation runs for an agent."""
        if self._db is None:
            return 0
        async with self._db.execute(
            "SELECT COUNT(*) FROM evaluation_runs WHERE agent_name = ?",
            [agent_name],
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else 0

    async def cleanup_expired(self) -> int:
        """
        Remove expired data from SQLite.

        Returns the number of deleted rows.
        """
        if self._db is None:
            return 0

        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=self._sqlite_retention)
        ).isoformat()

        # Delete results first (FK constraint)
        await self._db.execute(
            """
            DELETE FROM evaluation_results
            WHERE run_id IN (
                SELECT id FROM evaluation_runs WHERE run_timestamp < ?
            )
            """,
            [cutoff],
        )
        cursor = await self._db.execute(
            "DELETE FROM evaluation_runs WHERE run_timestamp < ?",
            [cutoff],
        )
        deleted = cursor.rowcount
        await self._db.commit()

        if deleted:
            logger.info("Cleaned up %d expired evaluation runs", deleted)
        return deleted

    # -- internals ---------------------------------------------------------

    def _write_influxdb_points(self, report: BatchReport) -> None:
        """Write evaluation scores to InfluxDB as points."""
        points: list[dict[str, Any]] = []
        ts = report.timestamp.isoformat()

        for session_report in report.reports:
            for result in session_report.results:
                points.append({
                    "measurement": "agent_evaluation",
                    "tags": {
                        "agent_name": report.agent_name,
                        "evaluator_name": result.evaluator_name,
                        "level": result.level.value,
                    },
                    "fields": {
                        "score": float(result.score),
                        "label": result.label,
                        "passed": 1 if result.passed else 0,
                    },
                    "time": ts,
                })

        if points:
            try:
                self._influx.write_points(points)
            except Exception:
                logger.warning(
                    "InfluxDB write failed — scores only in SQLite",
                    exc_info=True,
                )

    async def _write_run_record(self, report: BatchReport) -> int:
        """Insert an evaluation_runs record and return its ID."""
        assert self._db is not None
        summary = json.dumps(report.aggregate_scores or {})
        cursor = await self._db.execute(
            """
            INSERT INTO evaluation_runs
                (agent_name, run_timestamp, sessions_evaluated,
                 total_evaluations, alerts_triggered, summary_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                report.agent_name,
                report.timestamp.isoformat(),
                report.sessions_evaluated,
                report.total_evaluations,
                len(report.alerts),
                summary,
            ],
        )
        await self._db.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    async def _write_result_records(
        self, run_id: int, report: BatchReport
    ) -> None:
        """Insert evaluation_results records for all session results."""
        assert self._db is not None
        rows = []
        for session_report in report.reports:
            for result in session_report.results:
                rows.append((
                    run_id,
                    session_report.session_id,
                    report.agent_name,
                    result.evaluator_name,
                    result.level.value,
                    result.score,
                    result.label,
                    result.explanation,
                    report.timestamp.isoformat(),
                ))

        if rows:
            await self._db.executemany(
                """
                INSERT INTO evaluation_results
                    (run_id, session_id, agent_name, evaluator_name, level,
                     score, label, explanation, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            await self._db.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_period(period: str) -> int:
    """Parse a period string like '7d', '30d', '90d' into days."""
    period = period.strip().lower()
    if period.endswith("d"):
        try:
            return int(period[:-1])
        except ValueError:
            pass
    # Default mappings
    mapping = {"7d": 7, "30d": 30, "90d": 90, "1w": 7, "1m": 30, "3m": 90}
    return mapping.get(period, 7)
