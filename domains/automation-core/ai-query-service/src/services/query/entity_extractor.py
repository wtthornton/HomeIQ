"""
Entity Extractor for AI Query Service

Epic 7, Story 2: Wire Entity Extractor into ai-query-service
Resolves Home Assistant entity references from natural language queries
using keyword matching and data-api entity lookups.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from homeiq_resilience import CircuitBreaker, CircuitOpenError, CrossGroupClient

from ...config import settings

logger = logging.getLogger(__name__)

# Module-level circuit breaker for data-api calls
_data_api_breaker = CircuitBreaker(name="core-platform-query")

# Common HA domain prefixes and their friendly names
_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "light": ["light", "lights", "lamp", "lamps", "bulb", "bulbs", "lighting"],
    "switch": ["switch", "switches", "outlet", "outlets", "plug", "plugs"],
    "climate": ["thermostat", "climate", "hvac", "heating", "cooling", "ac", "air conditioning"],
    "cover": ["cover", "blind", "blinds", "curtain", "curtains", "shade", "shades", "garage"],
    "lock": ["lock", "locks", "deadbolt"],
    "fan": ["fan", "fans"],
    "media_player": ["speaker", "speakers", "tv", "television", "media", "player"],
    "sensor": ["sensor", "temperature", "humidity", "motion"],
    "binary_sensor": ["motion sensor", "door sensor", "window sensor", "contact sensor"],
    "automation": ["automation", "routine", "scene"],
    "camera": ["camera", "cameras"],
    "vacuum": ["vacuum", "robot vacuum"],
}

# Common room/area names
_AREA_KEYWORDS: list[str] = [
    "kitchen", "living room", "bedroom", "bathroom", "office", "garage",
    "hallway", "dining room", "basement", "attic", "porch", "patio",
    "laundry", "nursery", "guest room", "master bedroom", "den",
    "front door", "back door", "backyard", "front yard",
]


class EntityExtractor:
    """Extracts HA entity references from natural language queries.

    Uses a two-phase approach:
    1. Keyword matching to identify domains and areas from the query text.
    2. Data-api lookup to resolve matching entities (with circuit breaker fallback).
    """

    def __init__(self, data_api_url: str | None = None, api_key: str | None = None):
        self._base_url = (data_api_url or settings.data_api_url).rstrip("/")
        _key = api_key
        self._cross_client = CrossGroupClient(
            base_url=self._base_url,
            group_name="core-platform",
            timeout=float(settings.extraction_timeout),
            max_retries=1,
            auth_token=_key,
            circuit_breaker=_data_api_breaker,
        )

    async def extract(
        self,
        query: str,
        area_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Extract entities from a natural language query.

        Args:
            query: Natural language query string.
            area_filter: Optional comma-separated area filter.

        Returns:
            List of entity dicts with keys: entity_id, name, domain, area, type.
        """
        if not query or not query.strip():
            return []

        query_lower = query.lower()

        # Phase 1: keyword extraction
        detected_domains = self._extract_domains(query_lower)
        detected_areas = self._extract_areas(query_lower)

        # Apply explicit area filter
        if area_filter:
            filter_areas = [a.strip().lower() for a in area_filter.split(",") if a.strip()]
            if filter_areas:
                detected_areas = filter_areas

        # Phase 2: resolve via data-api
        entities = await self._resolve_entities(detected_domains, detected_areas)

        if entities:
            logger.info(
                "Extracted %d entities (domains=%s, areas=%s)",
                len(entities), detected_domains, detected_areas,
            )
        else:
            logger.debug("No entities extracted from query")

        return entities

    def _extract_domains(self, query_lower: str) -> list[str]:
        """Identify HA domains mentioned in the query."""
        domains: list[str] = []
        for domain, keywords in _DOMAIN_KEYWORDS.items():
            for kw in keywords:
                if re.search(rf"\b{re.escape(kw)}\b", query_lower):
                    if domain not in domains:
                        domains.append(domain)
                    break
        return domains

    def _extract_areas(self, query_lower: str) -> list[str]:
        """Identify area/room names mentioned in the query."""
        areas: list[str] = []
        for area in _AREA_KEYWORDS:
            if area in query_lower:
                areas.append(area)
        return areas

    async def _resolve_entities(
        self,
        domains: list[str],
        areas: list[str],
    ) -> list[dict[str, Any]]:
        """Resolve extracted keywords to concrete HA entities via data-api.

        Falls back to empty list when data-api is unavailable.
        """
        try:
            response = await self._cross_client.call(
                "GET", "/api/entities", params={"limit": 500},
            )
            response.raise_for_status()
            data = response.json()
            all_entities: list[dict[str, Any]] = data.get("entities", [])
        except CircuitOpenError:
            logger.warning("AI FALLBACK: Data-api circuit open -- returning empty entities")
            return []
        except (httpx.HTTPError, Exception) as e:
            logger.warning("Failed to fetch entities from data-api: %s", e)
            return []

        if not all_entities:
            return []

        results: list[dict[str, Any]] = []
        for entity in all_entities:
            entity_id = entity.get("entity_id", "")
            entity_domain = entity_id.split(".")[0] if "." in entity_id else ""
            entity_area = (entity.get("area_id") or "").lower()
            friendly_name = entity.get("friendly_name") or entity.get("name") or ""

            domain_match = not domains or entity_domain in domains
            area_match = not areas or any(a in entity_area for a in areas)

            if domain_match and area_match:
                results.append({
                    "entity_id": entity_id,
                    "name": friendly_name,
                    "domain": entity_domain,
                    "area": entity_area,
                    "type": "device" if entity_domain not in ("sensor", "binary_sensor") else "sensor",
                })

        return results
