"""
Entity Resolver - User text → canonical entity_id
Resolves user text, device names, and aliases to canonical Home Assistant entity IDs.
"""

import logging
from dataclasses import dataclass
from typing import Any

from ..utils.fuzzy import fuzzy_match_best
from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class ResolutionResult:
    """Result of entity resolution"""
    canonical_entity_id: str | None = None
    resolved: bool = False
    confidence: float = 0.0
    alternatives: list[str] = None
    capability_deltas: dict[str, Any] = None  # Missing/unknown capabilities
    resolution_method: str | None = None  # "exact", "alias", "fuzzy", "none"

    def __post_init__(self):
        if self.alternatives is None:
            self.alternatives = []
        if self.capability_deltas is None:
            self.capability_deltas = {}


class EntityResolver:
    """
    Resolves user text to canonical Home Assistant entity IDs.
    
    Handles:
    - Exact entity ID matches
    - Friendly name matches
    - Alias resolution
    - Domain/name normalization
    - Capability availability checks
    """

    def __init__(
        self,
        entity_validator=None,
        data_api_client=None,
        ha_client=None
    ):
        """
        Initialize entity resolver.
        
        Args:
            entity_validator: EntityValidator instance (optional)
            data_api_client: DataAPIClient instance (optional)
            ha_client: HomeAssistantClient instance (optional)
        """
        self.entity_validator = entity_validator
        self.data_api_client = data_api_client
        self.ha_client = ha_client
        self._entity_cache: dict[str, dict[str, Any]] = {}
        logger.info("EntityResolver initialized")

    async def resolve(
        self,
        user_text: str,
        domain_hint: str | None = None
    ) -> ResolutionResult:
        """
        Resolve user text to canonical entity_id.
        
        Args:
            user_text: User-provided text (entity_id, friendly name, alias)
            domain_hint: Optional domain hint (e.g., "light", "switch")
            
        Returns:
            ResolutionResult with canonical entity_id or alternatives
        """
        # Normalize input
        user_text = user_text.strip()

        # Try exact match first (if already in entity_id format)
        if '.' in user_text:
            result = await self._resolve_exact(user_text)
            if result.resolved:
                return result

        # Try alias resolution
        if self.entity_validator:
            result = await self._resolve_alias(user_text)
            if result.resolved:
                return result

        # Try fuzzy matching
        result = await self._resolve_fuzzy(user_text, domain_hint)
        if result.resolved:
            return result

        # No match found
        return ResolutionResult(
            resolved=False,
            confidence=0.0,
            alternatives=[],
            resolution_method="none"
        )

    async def resolve_multiple(
        self,
        user_texts: list[str],
        domain_hint: str | None = None
    ) -> dict[str, ResolutionResult]:
        """
        Resolve multiple user texts to entity IDs.
        
        Args:
            user_texts: List of user-provided texts
            domain_hint: Optional domain hint
            
        Returns:
            Dict mapping user_text -> ResolutionResult
        """
        results = {}
        for text in user_texts:
            results[text] = await self.resolve(text, domain_hint)
        return results

    async def _resolve_exact(self, entity_id: str) -> ResolutionResult:
        """Resolve exact entity_id match"""
        await self._ensure_entity_cache()

        if entity_id in self._entity_cache:
            entity = self._entity_cache[entity_id]
            return ResolutionResult(
                canonical_entity_id=entity_id,
                resolved=True,
                confidence=1.0,
                resolution_method="exact",
                capability_deltas=await self._check_capabilities(entity)
            )

        return ResolutionResult(resolved=False)

    async def _resolve_alias(self, user_text: str) -> ResolutionResult:
        """Resolve via entity alias"""
        if not self.entity_validator:
            return ResolutionResult(resolved=False)

        try:
            # Check aliases (if entity_validator supports it)
            if hasattr(self.entity_validator, '_check_aliases'):
                entity_id = await self.entity_validator._check_aliases(user_text)
                if entity_id:
                    await self._ensure_entity_cache()
                    if entity_id in self._entity_cache:
                        entity = self._entity_cache[entity_id]
                        return ResolutionResult(
                            canonical_entity_id=entity_id,
                            resolved=True,
                            confidence=0.9,
                            resolution_method="alias",
                            capability_deltas=await self._check_capabilities(entity)
                        )
        except Exception as e:
            logger.debug(f"Alias resolution failed: {e}")

        return ResolutionResult(resolved=False)

    async def _resolve_fuzzy(
        self,
        user_text: str,
        domain_hint: str | None = None
    ) -> ResolutionResult:
        """
        Resolve via fuzzy matching on friendly names using rapidfuzz.
        
        Uses fuzzy_match_best() for typo handling, abbreviation matching,
        and word order independence. Handles cases like:
        - Typos: "office lite" → "office light"
        - Abbreviations: "LR light" → "Living Room Light"
        - Word order: "light living room" → "living room light"
        """
        await self._ensure_entity_cache()

        # Build candidate mapping: friendly_name -> entity_id
        candidate_names = []
        name_to_entity = {}
        
        for entity_id, entity_data in self._entity_cache.items():
            # Apply domain filter if hint provided
            if domain_hint:
                if not entity_id.startswith(f"{domain_hint}."):
                    continue

            # Check friendly name
            friendly_name = entity_data.get('friendly_name', '')
            if friendly_name:
                candidate_names.append(friendly_name)
                name_to_entity[friendly_name] = entity_id

        if not candidate_names:
            return ResolutionResult(resolved=False)

        # Use fuzzy_match_best() for efficient batch matching with rapidfuzz
        # Lower threshold (0.6) for fuzzy matching to catch typos
        threshold = settings.fuzzy_matching_threshold - 0.1 if settings.fuzzy_matching_enabled else 0.0
        matches = fuzzy_match_best(
            user_text,
            candidate_names,
            threshold=max(threshold, 0.5),  # Minimum 0.5 threshold
            limit=6  # Top 5 alternatives + best match
        )

        if matches:
            best_match_name, confidence = matches[0]
            entity_id = name_to_entity[best_match_name]
            alternatives = [name_to_entity[name] for name, _ in matches[1:6] if name in name_to_entity]

            entity = self._entity_cache[entity_id]
            return ResolutionResult(
                canonical_entity_id=entity_id,
                resolved=True,
                confidence=confidence,
                alternatives=alternatives,
                resolution_method="fuzzy",
                capability_deltas=await self._check_capabilities(entity)
            )

        return ResolutionResult(resolved=False)

    async def _check_capabilities(self, entity: dict[str, Any]) -> dict[str, Any]:
        """
        Check entity capabilities and return deltas.
        
        Returns:
            Dict with missing/unknown capabilities
        """
        # Basic capability check (can be extended)
        capability_deltas = {
            "missing": [],
            "unknown": []
        }

        # Check if entity has required capabilities
        # This is a placeholder - can be extended with device intelligence integration
        domain = entity.get('domain', '')
        if domain in ['light', 'switch', 'fan']:
            # These domains should have turn_on/turn_off
            pass  # Assume present for now

        return capability_deltas

    async def _ensure_entity_cache(self):
        """Ensure entity cache is populated"""
        if not self._entity_cache and self.data_api_client:
            try:
                entities = await self.data_api_client.fetch_entities(limit=1000)
                self._entity_cache = {e['entity_id']: e for e in entities}
                logger.debug(f"Cached {len(self._entity_cache)} entities")
            except Exception as e:
                logger.warning(f"Failed to cache entities: {e}")
                self._entity_cache = {}

