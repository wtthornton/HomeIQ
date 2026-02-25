"""
Async SQLite feedback store for recommendation feedback.

Persists user feedback on rule recommendations so the model can
be incrementally retrained when enough new feedback accumulates.
"""

import logging
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

# Feedback types that count as positive signal for the interaction matrix
POSITIVE_FEEDBACK_TYPES = frozenset({"accepted", "created"})

# Default path for the feedback database
DEFAULT_DB_PATH = Path("/data/feedback.db")

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
VALUES (?, ?, ?, ?, ?, ?, ?)
"""

_COUNT_SQL = "SELECT COUNT(*) FROM recommendation_feedback"

_COUNT_SINCE_SQL = """
SELECT COUNT(*) FROM recommendation_feedback
WHERE created_at > COALESCE(
    (SELECT MAX(created_at) FROM model_retrain_log),
    '1970-01-01'
)
"""

_CREATE_RETRAIN_LOG_SQL = """
CREATE TABLE IF NOT EXISTS model_retrain_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
VALUES (?, ?)
"""


class FeedbackStore:
    """Async SQLite store for recommendation feedback.

    Uses lazy initialization -- the database file and tables are created
    on the first operation, not at construction time.  All public methods
    are safe to call concurrently from asyncio tasks.
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._initialized = False

    async def _ensure_initialized(self) -> aiosqlite.Connection:
        """Open connection and create tables if needed.

        Returns an *open* connection.  Callers are responsible for
        closing it (prefer ``async with`` around the returned value).
        """
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = await aiosqlite.connect(str(self._db_path))
        if not self._initialized:
            await conn.execute(_CREATE_TABLE_SQL)
            await conn.execute(_CREATE_INDEX_SQL)
            await conn.execute(_CREATE_RETRAIN_LOG_SQL)
            await conn.commit()
            self._initialized = True
            logger.info("Feedback store initialized at %s", self._db_path)
        return conn

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
        conn = await self._ensure_initialized()
        try:
            await conn.execute(
                _INSERT_SQL,
                (
                    feedback_id,
                    rule_pattern,
                    user_id,
                    feedback_type,
                    rating,
                    comment,
                    automation_id,
                ),
            )
            await conn.commit()
        except Exception:
            logger.exception("Failed to insert feedback %s", feedback_id)
            raise
        finally:
            await conn.close()

    async def count_since_last_retrain(self) -> int:
        """Return number of feedback rows added since the last retrain."""
        conn = await self._ensure_initialized()
        try:
            async with conn.execute(_COUNT_SINCE_SQL) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
        finally:
            await conn.close()

    async def total_count(self) -> int:
        """Return total feedback count."""
        conn = await self._ensure_initialized()
        try:
            async with conn.execute(_COUNT_SQL) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
        finally:
            await conn.close()

    async def get_all_feedback(
        self,
    ) -> list[dict]:
        """Return all feedback rows as dicts (for model retraining)."""
        conn = await self._ensure_initialized()
        try:
            async with conn.execute(_ALL_FEEDBACK_SQL) as cursor:
                columns = [desc[0] for desc in cursor.description]
                rows = await cursor.fetchall()
                return [dict(zip(columns, row, strict=True)) for row in rows]
        finally:
            await conn.close()

    async def log_retrain(self, feedback_count: int, status: str) -> None:
        """Record a retrain event so ``count_since_last_retrain`` resets."""
        conn = await self._ensure_initialized()
        try:
            await conn.execute(_LOG_RETRAIN_SQL, (feedback_count, status))
            await conn.commit()
        finally:
            await conn.close()
