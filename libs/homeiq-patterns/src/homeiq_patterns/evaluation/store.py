"""
Agent Evaluation Framework — Evaluation History Storage

Dual-write evaluation results to InfluxDB (time-series scores) and
a PostgreSQL database (session-level details).  Provides query methods for
trends, historical scores, and latest reports.

Usage::

    store = EvaluationStore(influxdb_writer=client, db_url="postgresql+asyncpg://...")
    await store.initialize()
    await store.store_batch_report(report)
    scores = await store.get_scores("ha-ai-agent", period="7d")
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, runtime_checkable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import BatchReport

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
_DEFAULT_DB_RETENTION_DAYS = 30

_CREATE_TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS evaluation_runs (
        id SERIAL PRIMARY KEY,
        agent_name TEXT NOT NULL,
        run_timestamp TEXT NOT NULL,
        sessions_evaluated INTEGER NOT NULL DEFAULT 0,
        total_evaluations INTEGER NOT NULL DEFAULT 0,
        alerts_triggered INTEGER NOT NULL DEFAULT 0,
        summary_json TEXT DEFAULT '{}'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS evaluation_results (
        id SERIAL PRIMARY KEY,
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
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_results_agent ON evaluation_results(agent_name)",
    "CREATE INDEX IF NOT EXISTS idx_results_run ON evaluation_results(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_runs_agent ON evaluation_runs(agent_name)",
]


class EvaluationStore:
    """
    Dual-write evaluation storage: InfluxDB for time-series, PostgreSQL for details.

    Supports degraded mode: if InfluxDB is unavailable, writes only to PostgreSQL.
    """

    def __init__(
        self,
        influxdb_writer: InfluxDBWriter | None = None,
        db_url: str | None = None,
        _db_path: str | None = None,
        influxdb_retention_days: int = _DEFAULT_INFLUXDB_RETENTION_DAYS,
        db_retention_days: int = _DEFAULT_DB_RETENTION_DAYS,
    ):
        self._influx = influxdb_writer or NullInfluxDBWriter()
        self._db_url = (
            db_url
            or os.environ.get("POSTGRES_URL")
            or os.environ.get("DATABASE_URL")
            or "postgresql+asyncpg://homeiq:homeiq@localhost:5432/homeiq"
        )
        self._influx_retention = influxdb_retention_days
        self._db_retention = db_retention_days
        self._engine = None
        self._session_maker: async_sessionmaker | None = None

    async def initialize(self) -> None:
        """Create database tables if they don't exist."""
        self._engine = create_async_engine(self._db_url, echo=False)
        self._session_maker = async_sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
        async with self._engine.begin() as conn:
            for sql in _CREATE_TABLES_SQL:
                await conn.execute(text(sql))

    async def close(self) -> None:
        """Close the database connection."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_maker = None

    async def store_batch_report(self, report: BatchReport) -> int:
        """
        Store a BatchReport: write scores to InfluxDB and details to PostgreSQL.

        Returns the evaluation_runs.id for the stored run.
        """
        if self._session_maker is None:
            await self.initialize()
        assert self._session_maker is not None

        # 1. Write to InfluxDB (time-series scores)
        self._write_influxdb_points(report)

        # 2. Write run record to PostgreSQL
        run_id = await self._write_run_record(report)

        # 3. Write individual results
        await self._write_result_records(run_id, report)

        return run_id

    async def get_scores(
        self,
        agent_name: str,
        evaluator: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Query historical scores from PostgreSQL."""
        if self._session_maker is None:
            return []

        query = """
            SELECT er.evaluator_name, er.level, er.score, er.label, er.timestamp
            FROM evaluation_results er
            JOIN evaluation_runs r ON er.run_id = r.id
            WHERE er.agent_name = :agent_name
        """
        params: dict[str, Any] = {"agent_name": agent_name}

        if evaluator:
            query += " AND er.evaluator_name = :evaluator"
            params["evaluator"] = evaluator
        if start:
            query += " AND er.timestamp >= :start"
            params["start"] = start.isoformat()
        if end:
            query += " AND er.timestamp <= :end"
            params["end"] = end.isoformat()

        query += " ORDER BY er.timestamp DESC"

        async with self._session_maker() as session:
            result = await session.execute(text(query), params)
            rows = result.fetchall()

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
        if self._session_maker is None:
            return {}

        days = _parse_period(period)
        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()

        query = """
            SELECT er.evaluator_name, r.run_timestamp, AVG(er.score) as avg_score
            FROM evaluation_results er
            JOIN evaluation_runs r ON er.run_id = r.id
            WHERE er.agent_name = :agent_name AND r.run_timestamp >= :cutoff
            GROUP BY er.evaluator_name, r.run_timestamp
            ORDER BY r.run_timestamp ASC
        """

        async with self._session_maker() as session:
            result = await session.execute(text(query), {"agent_name": agent_name, "cutoff": cutoff})
            rows = result.fetchall()

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
        if self._session_maker is None:
            return None

        query = """
            SELECT id, agent_name, run_timestamp, sessions_evaluated,
                   total_evaluations, alerts_triggered, summary_json
            FROM evaluation_runs
            WHERE agent_name = :agent_name
            ORDER BY run_timestamp DESC
            LIMIT 1
        """

        async with self._session_maker() as session:
            result = await session.execute(text(query), {"agent_name": agent_name})
            row = result.fetchone()

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
        if self._session_maker is None:
            return 0
        async with self._session_maker() as session:
            result = await session.execute(
                text("SELECT COUNT(*) FROM evaluation_runs WHERE agent_name = :agent_name"),
                {"agent_name": agent_name},
            )
            row = result.fetchone()
        return row[0] if row else 0

    async def cleanup_expired(self) -> int:
        """
        Remove expired data from PostgreSQL.

        Returns the number of deleted rows.
        """
        if self._session_maker is None:
            return 0

        cutoff = (
            datetime.now(UTC) - timedelta(days=self._db_retention)
        ).isoformat()

        async with self._session_maker() as session:
            # Delete results first (FK constraint)
            await session.execute(
                text("""
                DELETE FROM evaluation_results
                WHERE run_id IN (
                    SELECT id FROM evaluation_runs WHERE run_timestamp < :cutoff
                )
                """),
                {"cutoff": cutoff},
            )
            result = await session.execute(
                text("DELETE FROM evaluation_runs WHERE run_timestamp < :cutoff"),
                {"cutoff": cutoff},
            )
            deleted = result.rowcount
            await session.commit()

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
                    "InfluxDB write failed — scores only in PostgreSQL",
                    exc_info=True,
                )

    async def _write_run_record(self, report: BatchReport) -> int:
        """Insert an evaluation_runs record and return its id."""
        assert self._session_maker is not None
        summary = json.dumps(report.aggregate_scores or {})
        async with self._session_maker() as session:
            result = await session.execute(
                text("""
                INSERT INTO evaluation_runs
                    (agent_name, run_timestamp, sessions_evaluated,
                     total_evaluations, alerts_triggered, summary_json)
                VALUES (:agent_name, :run_timestamp, :sessions_evaluated,
                        :total_evaluations, :alerts_triggered, :summary_json)
                RETURNING id
                """),
                {
                    "agent_name": report.agent_name,
                    "run_timestamp": report.timestamp.isoformat(),
                    "sessions_evaluated": report.sessions_evaluated,
                    "total_evaluations": report.total_evaluations,
                    "alerts_triggered": len(report.alerts),
                    "summary_json": summary,
                },
            )
            run_id = result.scalar()
            await session.commit()
        return run_id

    async def _write_result_records(
        self, run_id: int, report: BatchReport
    ) -> None:
        """Insert evaluation_results records for all session results."""
        assert self._session_maker is not None
        async with self._session_maker() as session:
            for session_report in report.reports:
                for result in session_report.results:
                    await session.execute(
                        text("""
                        INSERT INTO evaluation_results
                            (run_id, session_id, agent_name, evaluator_name, level,
                             score, label, explanation, timestamp)
                        VALUES (:run_id, :session_id, :agent_name, :evaluator_name,
                                :level, :score, :label, :explanation, :timestamp)
                        """),
                        {
                            "run_id": run_id,
                            "session_id": session_report.session_id,
                            "agent_name": report.agent_name,
                            "evaluator_name": result.evaluator_name,
                            "level": result.level.value,
                            "score": result.score,
                            "label": result.label,
                            "explanation": result.explanation,
                            "timestamp": report.timestamp.isoformat(),
                        },
                    )
            await session.commit()


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
