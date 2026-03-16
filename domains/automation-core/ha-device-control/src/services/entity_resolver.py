"""Entity resolution service with caching and confidence scoring.

Resolves user-provided entity names/IDs to actual HA entity IDs using
a cached entity registry with TTL-based refresh.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .blacklist import BlacklistService
    from .ha_rest_client import HARestClient

logger = logging.getLogger(__name__)


@dataclass
class ResolvedEntity:
    """Result of entity resolution."""

    entity_id: str
    friendly_name: str
    domain: str
    area: str
    state: str
    attributes: dict[str, Any]
    confidence: float  # 1.0 = exact, 0.8 = partial


@dataclass
class CachedEntity:
    """A single cached entity from HA."""

    entity_id: str
    friendly_name: str
    domain: str
    state: str
    area: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    # Story 62.7: Aliases for entity resolution
    aliases: list[str] = field(default_factory=list)


class EntityResolver:
    """Resolves entity names/IDs with caching and blacklist filtering.

    Cache is refreshed on demand when TTL expires.  Matching tiers:
    1. Exact entity_id match (confidence 1.0)
    2. Exact friendly_name match (confidence 1.0)
    3. Exact alias match (confidence 0.95) — Story 62.7
    4. Partial/substring match on friendly_name (confidence 0.8)
    5. Partial alias match (confidence 0.75) — Story 62.7
    6. Partial match on entity_id suffix (confidence 0.7)
    """

    def __init__(
        self,
        ha_client: HARestClient,
        blacklist: BlacklistService,
        cache_ttl: int = 1800,
    ) -> None:
        self._ha_client = ha_client
        self._blacklist = blacklist
        self._cache_ttl = cache_ttl
        self._entities: dict[str, CachedEntity] = {}
        self._last_refresh: float = 0.0

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    @property
    def cache_age_seconds(self) -> float:
        """Seconds since the last cache refresh."""
        if self._last_refresh == 0.0:
            return float("inf")
        return time.monotonic() - self._last_refresh

    @property
    def cache_size(self) -> int:
        """Number of entities in the cache."""
        return len(self._entities)

    async def refresh_cache(self) -> int:
        """Fetch all states from HA and rebuild the entity cache.

        Returns the number of entities cached.
        """
        try:
            states = await self._ha_client.get_states()
        except Exception:
            logger.warning("Failed to fetch HA states for cache refresh")
            return len(self._entities)

        new_cache: dict[str, CachedEntity] = {}
        entity_ids: list[str] = []

        for state in states:
            eid: str = state.get("entity_id", "")
            if not eid:
                continue
            attrs = state.get("attributes", {})
            friendly = attrs.get("friendly_name", eid)
            domain = eid.split(".")[0] if "." in eid else ""
            new_cache[eid] = CachedEntity(
                entity_id=eid,
                friendly_name=friendly,
                domain=domain,
                state=state.get("state", "unknown"),
                attributes=attrs,
                # Story 62.7: Pull aliases from HA attributes or entity registry
                aliases=attrs.get("aliases", []) or [],
            )
            entity_ids.append(eid)

        # Resolve areas in batches
        try:
            area_map = await self._ha_client.get_entity_areas(entity_ids)
            for eid, area in area_map.items():
                if eid in new_cache:
                    new_cache[eid].area = area
        except Exception:
            logger.warning("Failed to resolve entity areas")

        self._entities = new_cache
        self._last_refresh = time.monotonic()
        logger.info("Entity cache refreshed: %d entities", len(self._entities))
        return len(self._entities)

    async def _ensure_cache(self) -> None:
        """Refresh cache if TTL has expired."""
        if self.cache_age_seconds > self._cache_ttl:
            await self.refresh_cache()

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    async def resolve(
        self,
        name_or_id: str,
        domain_filter: str = "",
    ) -> ResolvedEntity | None:
        """Resolve a user-provided name or ID to an entity.

        Args:
            name_or_id: Entity ID, friendly name, or partial name.
            domain_filter: Optional domain to restrict search (e.g. ``light``).

        Returns:
            A ResolvedEntity if found (best match), or None.
        """
        await self._ensure_cache()
        query = name_or_id.strip()
        query_lower = query.lower()
        candidates = self._filtered_entities(domain_filter)

        # Tier 1: exact entity_id match
        match = self._match_exact_id(candidates, query)
        if match:
            return match

        # Tier 2: exact friendly_name match (case-insensitive)
        match = self._match_friendly_name(candidates, query_lower, exact=True)
        if match:
            return match

        # Tier 3: exact alias match (Story 62.7)
        match = self._match_alias(candidates, query_lower, exact=True)
        if match:
            return match

        # Tier 4: partial / substring match on friendly_name
        match = self._match_friendly_name(candidates, query_lower, exact=False)
        if match:
            return match

        # Tier 5: partial alias match (Story 62.7)
        match = self._match_alias(candidates, query_lower, exact=False)
        if match:
            return match

        # Tier 6: partial match on entity_id (without domain prefix)
        return self._match_entity_id_suffix(candidates, query_lower)

    def _match_exact_id(
        self,
        candidates: dict[str, CachedEntity],
        query: str,
    ) -> ResolvedEntity | None:
        """Match by exact entity_id."""
        if query in candidates and not self._is_blocked(candidates[query]):
            return self._to_resolved(candidates[query], confidence=1.0)
        return None

    def _match_friendly_name(
        self,
        candidates: dict[str, CachedEntity],
        query_lower: str,
        *,
        exact: bool,
    ) -> ResolvedEntity | None:
        """Match by friendly_name (exact or substring)."""
        confidence = 1.0 if exact else 0.8
        for ent in candidates.values():
            name_lower = ent.friendly_name.lower()
            matched = (name_lower == query_lower) if exact else (query_lower in name_lower)
            if matched and not self._is_blocked(ent):
                return self._to_resolved(ent, confidence=confidence)
        return None

    def _match_alias(
        self,
        candidates: dict[str, CachedEntity],
        query_lower: str,
        *,
        exact: bool,
    ) -> ResolvedEntity | None:
        """Story 62.7: Match by alias (exact or substring)."""
        confidence = 0.95 if exact else 0.75
        for ent in candidates.values():
            if self._is_blocked(ent):
                continue
            for alias in ent.aliases:
                alias_lower = alias.lower()
                matched = (alias_lower == query_lower) if exact else (query_lower in alias_lower)
                if matched:
                    return self._to_resolved(ent, confidence=confidence)
        return None

    def _match_entity_id_suffix(
        self,
        candidates: dict[str, CachedEntity],
        query_lower: str,
    ) -> ResolvedEntity | None:
        """Match by entity_id suffix (after the domain dot)."""
        for ent in candidates.values():
            id_short = ent.entity_id.split(".", 1)[-1] if "." in ent.entity_id else ent.entity_id
            if query_lower in id_short.lower() and not self._is_blocked(ent):
                return self._to_resolved(ent, confidence=0.7)
        return None

    def _is_blocked(self, ent: CachedEntity) -> bool:
        """Check if an entity is blacklisted."""
        return self._blacklist.is_blacklisted(ent.entity_id, ent.area)

    async def resolve_by_area(
        self,
        area: str,
        domain_filter: str = "",
    ) -> list[ResolvedEntity]:
        """Return all non-blacklisted entities in an area.

        Args:
            area: Area name to match (case-insensitive).
            domain_filter: Optional domain filter.

        Returns:
            List of resolved entities in the area.
        """
        await self._ensure_cache()
        area_lower = area.lower()
        candidates = self._filtered_entities(domain_filter)
        return [
            self._to_resolved(ent, confidence=1.0)
            for ent in candidates.values()
            if ent.area.lower() == area_lower and not self._is_blocked(ent)
        ]

    async def list_entities(self, domain_filter: str = "") -> list[ResolvedEntity]:
        """List all non-blacklisted entities, optionally filtered by domain."""
        await self._ensure_cache()
        candidates = self._filtered_entities(domain_filter)
        return [
            self._to_resolved(ent, confidence=1.0)
            for ent in candidates.values()
            if not self._is_blocked(ent)
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _filtered_entities(self, domain_filter: str) -> dict[str, CachedEntity]:
        """Return entities filtered by domain if specified."""
        if not domain_filter:
            return self._entities
        return {
            eid: ent
            for eid, ent in self._entities.items()
            if ent.domain == domain_filter
        }

    @staticmethod
    def _to_resolved(ent: CachedEntity, confidence: float) -> ResolvedEntity:
        """Convert a CachedEntity to a ResolvedEntity."""
        return ResolvedEntity(
            entity_id=ent.entity_id,
            friendly_name=ent.friendly_name,
            domain=ent.domain,
            area=ent.area,
            state=ent.state,
            attributes=ent.attributes,
            confidence=confidence,
        )
