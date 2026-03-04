"""
Async feedback store for recommendation feedback.

Persists user feedback on rule recommendations so the model can
be incrementally retrained when enough new feedback accumulates.
Uses SQLAlchemy async with PostgreSQL.
"""

import logging
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)

# Feedback types that count as positive signal for the interaction matrix
POSITIVE_FEEDBACK_TYPES = frozenset({"accepted", "created"})

# Default PostgreSQL URL
DEFAULT_DB_URL = os.environ.get(
    "POSTGRES_URL",
    os.environ.get("DATABASE_URL", "postgresql+asyncpg://homeiq:homeiq@localhost:5432/homeiq"),
)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS recommendation_feedback (
    id TEXT PRIMARY KEY,
    rule_pattern TEXT NOT NULL,
    user_id TEXT,
    feedback_type TEXT NOT NULL,
    rating INTEGER,
    comment TEXT,
    automation_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_feedback_pattern
    ON recommendation_feedback (rule_pattern)
"""

_INSERT_SQL = """
INSERT INTO recommendation_feedback
    (id, rule_pattern, user_id, feedback_type, rating, comment, automation_id)
VALUES (:id, :rule_pattern, :user_id, :feedback_type, :rating, :comment, :automation_id)
"""

_COUNT_SQL = "SELECT COUNT(*) FROM recommendation_feedback"

_COUNT_SINCE_SQL = """
SELECT COUNT(*) FROM recommendation_feedback
WHERE created_at > COALESCE(
    (SELECT MAX(created_at) FROM model_retrain_log),
    '1970-01-01'::timestamp
)
"""

_CREATE_RETRAIN_LOG_SQL = """
CREATE TABLE IF NOT EXISTS model_retrain_log (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    feedback_count INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'started'
)
"""

_ALL_FEEDBACK_SQL = """
SELECT id, rule_pattern, user_id, feedback_type, rating, comment,
       automation_id, created_at
FROM recommendation_feedback
ORDER BY created_at
"""

_LOG_RETRAIN_SQL = """
INSERT INTO model_retrain_log (feedback_count, status)
VALUES (:feedback_count, :status)
"""


class FeedbackStore:
    """Async store for recommendation feedback.

    Uses lazy initialization -- the database connection and tables are created
    on the first operation, not at construction time.  All public methods
    are safe to call concurrently from asyncio tasks.
    """

    def __init__(self, db_url: str | None = None) -> None:
        self._db_url = db_url or DEFAULT_DB_URL
        self._engine = None
        self._session_maker = None
        self._initialized = False

    async def _ensure_initialized(self) -> async_sessionmaker:
        """Create engine and tables if needed.

        Returns a session maker.
        """
        if not self._initialized:
            self._engine = create_async_engine(self._db_url, echo=False)
            self._session_maker = async_sessionmaker(
                self._engine, class_=AsyncSession, expire_on_commit=False
            )
            async with self._engine.begin() as conn:
                await conn.execute(text(_CREATE_TABLE_SQL))
                await conn.execute(text(_CREATE_INDEX_SQL))
                await conn.execute(text(_CREATE_RETRAIN_LOG_SQL))
            self._initialized = True
            logger.info("Feedback store initialized at %s", self._db_url)
        return self._session_maker

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def insert(
        self,
        *,
        feedback_id: str,
        rule_pattern: str,
        user_id: str | None,
        feedback_type: str,
        rating: int | None,
        comment: str | None,
        automation_id: str | None,
    ) -> None:
        """Persist a single feedback record."""
        session_maker = await self._ensure_initialized()
        try:
            async with session_maker() as session:
                await session.execute(
                    text(_INSERT_SQL),
                    {
                        "id": feedback_id,
                        "rule_pattern": rule_pattern,
                        "user_id": user_id,
                        "feedback_type": feedback_type,
                        "rating": rating,
                        "comment": comment,
                        "automation_id": automation_id,
                    },
                )
                await session.commit()
        except Exception:
            logger.exception("Failed to insert feedback %s", feedback_id)
            raise

    async def count_since_last_retrain(self) -> int:
        """Return number of feedback rows added since the last retrain."""
        session_maker = await self._ensure_initialized()
        async with session_maker() as session:
            result = await session.execute(text(_COUNT_SINCE_SQL))
            row = result.fetchone()
            return row[0] if row else 0

    async def total_count(self) -> int:
        """Return total feedback count."""
        session_maker = await self._ensure_initialized()
        async with session_maker() as session:
            result = await session.execute(text(_COUNT_SQL))
            row = result.fetchone()
            return row[0] if row else 0

    async def get_all_feedback(
        self,
    ) -> list[dict]:
        """Return all feedback rows as dicts (for model retraining)."""
        session_maker = await self._ensure_initialized()
        async with session_maker() as session:
            result = await session.execute(text(_ALL_FEEDBACK_SQL))
            columns = list(result.keys())
            rows = result.fetchall()
            return [dict(zip(columns, row, strict=True)) for row in rows]

    async def log_retrain(self, feedback_count: int, status: str) -> None:
        """Record a retrain event so ``count_since_last_retrain`` resets."""
        session_maker = await self._ensure_initialized()
        async with session_maker() as session:
            await session.execute(
                text(_LOG_RETRAIN_SQL),
                {"feedback_count": feedback_count, "status": status},
            )
            await session.commit()
