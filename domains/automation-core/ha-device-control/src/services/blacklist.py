"""Entity blacklist service.

Supports three pattern types (ported from Sapphire):
- Glob patterns: ``cover.*``, ``light.bedroom_*``
- Exact entity IDs: ``switch.computer1``
- Area-based: ``area:Garage`` (excludes all entities in that area)
"""

from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BlacklistEntry:
    """A single blacklist pattern with its auto-assigned ID."""

    id: int
    pattern: str


class BlacklistService:
    """Manages entity blacklist patterns.

    Patterns are stored in-memory and initialized from the service
    configuration.  A future iteration will persist to PostgreSQL
    via admin-api.
    """

    def __init__(self) -> None:
        self._entries: list[BlacklistEntry] = []
        self._next_id: int = 1

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def load_from_config(self, patterns_csv: str) -> None:
        """Populate the blacklist from a comma-separated config string."""
        if not patterns_csv.strip():
            return
        for raw in patterns_csv.split(","):
            pattern = raw.strip()
            if pattern:
                self.add(pattern)
        logger.info("Loaded %d blacklist patterns from config", len(self._entries))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, pattern: str) -> BlacklistEntry:
        """Add a pattern and return the new entry."""
        entry = BlacklistEntry(id=self._next_id, pattern=pattern)
        self._next_id += 1
        self._entries.append(entry)
        logger.info("Blacklist pattern added: %s (id=%d)", pattern, entry.id)
        return entry

    def remove(self, entry_id: int) -> bool:
        """Remove a pattern by ID.  Returns True if found."""
        before = len(self._entries)
        self._entries = [e for e in self._entries if e.id != entry_id]
        removed = len(self._entries) < before
        if removed:
            logger.info("Blacklist pattern removed (id=%d)", entry_id)
        return removed

    def list_all(self) -> list[BlacklistEntry]:
        """Return all current blacklist entries."""
        return list(self._entries)

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------

    def is_blacklisted(self, entity_id: str, entity_area: str = "") -> bool:
        """Check whether an entity matches any blacklist pattern.

        Args:
            entity_id: The full entity ID (e.g. ``light.kitchen``).
            entity_area: The area name the entity belongs to (optional).

        Returns:
            True if the entity matches at least one pattern.
        """
        for entry in self._entries:
            pattern = entry.pattern

            # Area-based exclusion
            if pattern.startswith("area:"):
                area_name = pattern[5:].strip()
                if entity_area and entity_area.lower() == area_name.lower():
                    return True
                continue

            # Glob / exact match
            if fnmatch.fnmatch(entity_id, pattern):
                return True

        return False
