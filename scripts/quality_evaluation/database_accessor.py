"""
Database Accessor for Quality Evaluation

Handles database connections and queries for patterns and synergies.
Uses PostgreSQL via psycopg2.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

# PostgreSQL connection URL
POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://homeiq:homeiq@localhost:5432/homeiq")


class DatabaseAccessor:
    """Handles database access for patterns and synergies."""

    def __init__(self, pg_url: str = POSTGRES_URL):
        """
        Initialize database connection.

        Args:
            pg_url: PostgreSQL connection URL
        """
        self.pg_url = pg_url
        self.conn: Optional[psycopg2.extensions.connection] = None
        logger.info(f"Initialized database accessor for PostgreSQL")

    def _table_exists(self, table_name: str, schema: str = "patterns") -> bool:
        """Check if a table exists in the database."""
        if self.conn is None:
            self.conn = psycopg2.connect(self.pg_url)

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
                (schema, table_name)
            )
            return cursor.fetchone() is not None
        except psycopg2.Error:
            return False

    async def get_all_patterns(
        self,
        pattern_type: Optional[str] = None,
        device_id: Optional[str] = None,
        min_confidence: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all patterns with optional filters.

        Args:
            pattern_type: Filter by pattern type
            device_id: Filter by device ID
            min_confidence: Minimum confidence threshold

        Returns:
            List of pattern dictionaries
        """
        if self.conn is None:
            self.conn = psycopg2.connect(self.pg_url)

        # Check if table exists
        if not self._table_exists('patterns', 'patterns'):
            logger.warning("Table 'patterns.patterns' does not exist in database")
            return []

        query = "SELECT * FROM patterns.patterns WHERE 1=1"
        params = []

        if pattern_type:
            query += " AND pattern_type = %s"
            params.append(pattern_type)

        if device_id:
            query += " AND device_id = %s"
            params.append(device_id)

        if min_confidence is not None:
            query += " AND confidence >= %s"
            params.append(min_confidence)

        query += " ORDER BY confidence DESC"

        try:
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, params)
            rows = cursor.fetchall()

            patterns = []
            for row in rows:
                pattern = dict(row)
                # Parse JSON fields
                if 'pattern_metadata' in pattern and pattern['pattern_metadata']:
                    try:
                        if isinstance(pattern['pattern_metadata'], str):
                            pattern['pattern_metadata'] = json.loads(pattern['pattern_metadata'])
                    except (json.JSONDecodeError, TypeError):
                        pattern['pattern_metadata'] = {}

                patterns.append(pattern)

            logger.info(f"Retrieved {len(patterns)} patterns from database")
            return patterns

        except psycopg2.Error as e:
            logger.error(f"Database query error: {e}", exc_info=True)
            raise

    async def get_all_synergies(
        self,
        synergy_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        synergy_depth: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all synergies with optional filters.

        Args:
            synergy_type: Filter by synergy type
            min_confidence: Minimum confidence threshold
            synergy_depth: Filter by synergy depth (2, 3, 4)

        Returns:
            List of synergy dictionaries
        """
        if self.conn is None:
            self.conn = psycopg2.connect(self.pg_url)

        # Check if table exists
        if not self._table_exists('synergy_opportunities', 'patterns'):
            logger.warning("Table 'patterns.synergy_opportunities' does not exist in database")
            return []

        query = "SELECT * FROM patterns.synergy_opportunities WHERE 1=1"
        params = []

        if synergy_type:
            query += " AND synergy_type = %s"
            params.append(synergy_type)

        if min_confidence is not None:
            query += " AND confidence >= %s"
            params.append(min_confidence)

        if synergy_depth is not None:
            query += " AND synergy_depth = %s"
            params.append(synergy_depth)

        query += " ORDER BY impact_score DESC"

        try:
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, params)
            rows = cursor.fetchall()

            synergies = []
            for row in rows:
                synergy = dict(row)
                # Parse JSON fields
                for field in ['device_ids', 'opportunity_metadata', 'supporting_pattern_ids',
                             'chain_devices', 'explanation', 'context_breakdown']:
                    if field in synergy and synergy[field]:
                        try:
                            if isinstance(synergy[field], str):
                                synergy[field] = json.loads(synergy[field])
                        except (json.JSONDecodeError, TypeError):
                            synergy[field] = None if field in ['device_ids', 'chain_devices'] else {}

                synergies.append(synergy)

            logger.info(f"Retrieved {len(synergies)} synergies from database")
            return synergies

        except psycopg2.Error as e:
            logger.error(f"Database query error: {e}", exc_info=True)
            raise

    async def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.debug("Database connection closed")
