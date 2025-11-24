"""
Entity Validation Service for AI Automation

Validates that entities exist in Home Assistant before generating automations.
This prevents "Entity not found" errors by ensuring only real entities are monitored

Enhanced with Full Model Chain:
1. NER Extraction (HuggingFace)
2. Entity Enrichment (device metadata, friendly_name)
3. Embedding-Based Matching (sentence-transformers)
4. Hybrid Scoring (semantic + numbered + location + exact)
5. Confidence Scoring
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics for entity resolution"""
    entity_count: int = 0
    candidates_total: int = 0
    candidates_after_domain: int = 0
    candidates_after_location: int = 0
    enrichment_count: int = 0
    matches_found: int = 0
    domain_filter_ms: float = 0.0
    location_filter_ms: float = 0.0
    enrichment_ms: float = 0.0
    matching_ms: float = 0.0
    total_resolution_ms: float = 0.0

    def log_summary(self):
        """Log performance summary in readable format"""
        logger.info("=" * 60)
        logger.info("📊 ENTITY RESOLUTION PERFORMANCE")
        logger.info("=" * 60)
        logger.info(f"Entities requested: {self.entity_count}")
        logger.info("")
        logger.info("Candidate Reduction:")
        logger.info(f"  Total candidates:      {self.candidates_total:>6}")
        logger.info(f"  After domain filter:   {self.candidates_after_domain:>6}")
        logger.info(f"  After location filter: {self.candidates_after_location:>6}")
        logger.info(f"  Entities enriched:     {self.enrichment_count:>6}")
        logger.info("")
        logger.info("Timing Breakdown:")
        logger.info(f"  Domain filter:     {self.domain_filter_ms:>6.1f}ms")
        logger.info(f"  Location filter:   {self.location_filter_ms:>6.1f}ms")
        logger.info(f"  Enrichment:        {self.enrichment_ms:>6.1f}ms")
        logger.info(f"  Matching:          {self.matching_ms:>6.1f}ms")
        logger.info("")
        logger.info(f"  TOTAL RESOLUTION:  {self.total_resolution_ms:>6.1f}ms")
        logger.info("")
        logger.info(f"Matches found: {self.matches_found}")
        logger.info("=" * 60)

# Lazy imports for optional dependencies
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available, embedding matching will be disabled")

try:
    from transformers import pipeline as transformers_pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers not available, NER will be disabled")


@dataclass
class EntityValidationResult:
    """Result of entity validation"""
    entity_id: str
    exists: bool
    suggested_alternatives: list[str]
    confidence_score: float


class EntityValidator:
    """
    Validates entities against real Home Assistant entities.
    
    This service ensures that automations use actual entities that exist
    in the Home Assistant instance, preventing "Entity not found" errors.
    """
    
    # Quick Win 2: Common device aliases for better matching
    COMMON_DEVICE_ALIASES = {
        'light': ['lamp', 'bulb', 'lamp', 'fixture', 'luminaire'],
        'lamp': ['light', 'bulb', 'fixture'],
        'switch': ['toggle', 'button', 'control'],
        'toggle': ['switch', 'button'],
        'sensor': ['detector', 'monitor', 'gauge'],
        'detector': ['sensor', 'monitor'],
        'thermostat': ['climate', 'temperature control'],
        'climate': ['thermostat', 'temperature control'],
        'door': ['entrance', 'entry'],
        'window': ['opening'],
        'fan': ['ventilator', 'blower'],
        'lock': ['deadbolt', 'latch'],
        'camera': ['webcam', 'security camera'],
        'motion': ['movement', 'motion sensor'],
        'presence': ['occupancy', 'presence sensor']
    }

    def __init__(self, data_api_client=None, enable_full_chain: bool = True, db_session=None, ha_client=None):
        """
        Initialize EntityValidator.
        
        Args:
            data_api_client: Data API client for fetching entities (cached fallback)
            enable_full_chain: Enable full model chain (embeddings, NER, etc.)
            db_session: Optional database session for alias support
            ha_client: Optional HA client for real-time entity queries and attribute-based scoring
        """
        self.data_api_client = data_api_client
        self.ha_client = ha_client
        self.entity_cache = {}
        self.enable_full_chain = enable_full_chain
        self.db_session = db_session

        # Lazy-loaded models for full chain
        self._embedding_model = None
        self._ner_pipeline = None
        self._device_metadata_cache = {}  # Cache device metadata by device_id
        self._alias_service = None  # Lazy-loaded alias service
        self._attribute_cache = {}  # Cache enriched entity attributes

    def _get_alias_service(self):
        """Lazy-load alias service if db_session is available"""
        if self._alias_service is None and self.db_session:
            try:
                from .alias_service import AliasService
                self._alias_service = AliasService(self.db_session)
                logger.debug("Alias service initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize alias service: {e}")
                self._alias_service = False  # Mark as unavailable to avoid repeated attempts
        return self._alias_service if self._alias_service else None

    async def _check_aliases(
        self,
        query_term: str,
        user_id: str = "anonymous"
    ) -> str | None:
        """
        Check if query matches any user-defined alias.
        Returns entity_id if alias found, None otherwise.
        
        Priority: Exact alias match (fast, high confidence)
        
        Args:
            query_term: Query string to check
            user_id: User ID (default: "anonymous")
            
        Returns:
            Entity ID if alias found, None otherwise
        """
        alias_service = self._get_alias_service()
        if not alias_service:
            return None

        try:
            entity_id = await alias_service.get_entity_for_alias(query_term.lower(), user_id)
            if entity_id:
                logger.info(f"✅ Alias match: '{query_term}' → {entity_id}")
                return entity_id
        except Exception as e:
            logger.debug(f"Error checking aliases for '{query_term}': {e}")

        return None

    async def validate_entities(self, entity_ids: list[str]) -> dict[str, EntityValidationResult]:
        """
        Validate a list of entity IDs against real Home Assistant entities.
        
        Args:
            entity_ids: List of entity IDs to validate
            
        Returns:
            Dictionary mapping entity_id to validation result
        """
        results = {}

        # Get all available entities from data-api
        available_entities = await self._get_available_entities()

        for entity_id in entity_ids:
            result = await self._validate_single_entity(entity_id, available_entities)
            results[entity_id] = result

        return results

    async def _get_available_entities(
        self,
        domain: str | None = None,
        area_id: str | None = None,
        integration: str | None = None,
        use_realtime: bool = True
    ) -> list[dict[str, Any]]:
        """
        Get available entities with optional filtering.
        
        Priority: Real-time HA API query (if ha_client available) > Cached database query
        
        Args:
            domain: Optional domain filter (e.g., "light", "switch")
            area_id: Optional area filter for location-based blocking
            integration: Optional integration filter for brand-based blocking
            use_realtime: If True, prefer real-time HA API query (default: True)
            
        Returns:
            List of entity dictionaries
        """
        # Priority 1: Real-time HA API query (if available and requested)
        if use_realtime and self.ha_client and area_id:
            try:
                logger.info(
                    f"🔍 Fetching entities from HA API (real-time) "
                    f"(domain={domain}, area_id={area_id})"
                )
                entities = await self.ha_client.get_entities_by_area_and_domain(
                    area_id=area_id,
                    domain=domain
                )

                if entities:
                    logger.info(f"✅ Fetched {len(entities)} entities from HA API (real-time)")
                    if len(entities) > 0:
                        logger.info(f"First 3 entities: {[e.get('entity_id') for e in entities[:3]]}")
                    return entities
                else:
                    logger.warning("⚠️ No entities found from HA API, falling back to database")
            except Exception as e:
                logger.warning(
                    f"⚠️ Error fetching entities from HA API (real-time): {e}, "
                    f"falling back to database"
                )
                # Fall through to database query

        # Priority 2: Cached database query (fallback)
        try:
            if self.data_api_client:
                logger.info(
                    f"🔍 Fetching entities from data-api (cached) "
                    f"(domain={domain}, area_id={area_id}, integration={integration})"
                )
                entities = await self.data_api_client.fetch_entities(
                    domain=domain,
                    area_id=area_id,
                    platform=integration  # Note: data API uses 'platform' for integration
                )
                logger.info(f"✅ Fetched {len(entities)} entities from data-api (cached)")
                if len(entities) > 0:
                    logger.info(f"First 3 entities: {[e.get('entity_id') for e in entities[:3]]}")
                return entities
            else:
                logger.warning("Data API client not available, using empty entity list")
                return []
        except Exception as e:
            logger.error(f"Error fetching entities from data-api: {e}", exc_info=True)
            return []

    async def _validate_single_entity(self, entity_id: str, available_entities: list[dict[str, Any]]) -> EntityValidationResult:
        """
        Validate a single entity ID.
        
        Args:
            entity_id: Entity ID to validate
            available_entities: List of available entities
            
        Returns:
            EntityValidationResult with validation details
        """
        # Check if entity exists exactly
        exact_match = self._find_exact_match(entity_id, available_entities)
        if exact_match:
            # Get sibling entities for suggestions even if entity exists
            sibling_alternatives = await self._get_sibling_entity_alternatives(entity_id)
            return EntityValidationResult(
                entity_id=entity_id,
                exists=True,
                suggested_alternatives=sibling_alternatives,
                confidence_score=1.0
            )

        # Find alternatives using similarity
        alternatives = self._find_alternatives(entity_id, available_entities)

        # Also get sibling entities if we found a match
        if alternatives:
            # Try to get siblings for the first alternative
            sibling_alternatives = await self._get_sibling_entity_alternatives(alternatives[0])
            # Merge sibling alternatives (avoid duplicates)
            for sibling in sibling_alternatives:
                if sibling not in alternatives:
                    alternatives.append(sibling)

        return EntityValidationResult(
            entity_id=entity_id,
            exists=False,
            suggested_alternatives=alternatives,
            confidence_score=0.0
        )

    def _find_exact_match(self, entity_id: str, available_entities: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Find exact match for entity ID"""
        for entity in available_entities:
            if entity.get('entity_id') == entity_id:
                return entity
        return None

    def _find_alternatives(self, entity_id: str, available_entities: list[dict[str, Any]]) -> list[str]:
        """
        Find alternative entity IDs based on similarity.
        
        Args:
            entity_id: Entity ID to find alternatives for
            available_entities: List of available entities
            
        Returns:
            List of alternative entity IDs
        """
        alternatives = []

        # Extract domain and name parts
        if '.' in entity_id:
            domain, name = entity_id.split('.', 1)
        else:
            domain = 'unknown'
            name = entity_id

        # Find entities with same domain
        same_domain = [
            entity for entity in available_entities
            if entity.get('domain') == domain
        ]

        # Find entities with similar names
        name_words = set(re.findall(r'\w+', name.lower()))

        for entity in same_domain:
            entity_name = entity.get('entity_id', '').split('.', 1)[1] if '.' in entity.get('entity_id', '') else ''
            entity_words = set(re.findall(r'\w+', entity_name.lower()))

            # Calculate similarity
            common_words = name_words.intersection(entity_words)
            if common_words:
                similarity = len(common_words) / len(name_words.union(entity_words))
                if similarity > 0.3:  # 30% similarity threshold
                    alternatives.append(entity.get('entity_id'))

        # Limit to top 5 alternatives
        return alternatives[:5]

    async def _get_sibling_entity_alternatives(self, entity_id: str) -> list[str]:
        """
        Get sibling entities (entities from same device) as alternatives.
        
        Uses relationship query endpoint to fetch sibling entities.
        
        Args:
            entity_id: Entity ID to get siblings for
            
        Returns:
            List of sibling entity IDs
        """
        if not self.data_api_client:
            return []

        try:
            import aiohttp

            # Get base URL for data-api
            data_api_url = getattr(self.data_api_client, 'base_url', 'http://data-api:8006')

            # Fetch sibling entities
            siblings_url = f"{data_api_url}/api/entities/{entity_id}/siblings"
            async with aiohttp.ClientSession() as session:
                async with session.get(siblings_url, timeout=aiohttp.ClientTimeout(total=2.0)) as response:
                    if response.status == 200:
                        siblings_data = await response.json()
                        siblings = siblings_data.get('siblings', [])
                        sibling_ids = [s.get('entity_id') for s in siblings if s.get('entity_id') and s.get('entity_id') != entity_id]
                        logger.debug(f"Found {len(sibling_ids)} sibling entities for {entity_id}")
                        return sibling_ids[:5]  # Limit to 5 siblings
                    else:
                        logger.debug(f"Could not fetch sibling entities for {entity_id}: HTTP {response.status}")
                        return []
        except Exception as e:
            logger.debug(f"Error fetching sibling entities for {entity_id}: {e}")
            return []

    def _extract_location_from_query(self, query: str) -> str | None:
        """
        Extract location/area name from query.
        
        Examples:
            "office light" -> "office"
            "living room lamp" -> "living room"
            "garage door" -> "garage"
            "bedroom ewlight 1" -> "bedroom"
        
        Args:
            query: User query
            
        Returns:
            Location/area name or None if not found
        """
        query_lower = query.lower()

        # Common location patterns
        location_patterns = [
            r'\b(living room|livingroom)\b',
            r'\b(bedroom|bed room)\b',
            r'\b(kitchen)\b',
            r'\b(bathroom|bath room)\b',
            r'\b(office)\b',
            r'\b(garage)\b',
            r'\b(entry|entryway|entry way)\b',
            r'\b(dining room|diningroom)\b',
            r'\b(family room|familyroom)\b',
            r'\b(basement)\b',
            r'\b(attic)\b',
            r'\b(patio|deck|porch)\b',
        ]

        import re
        for pattern in location_patterns:
            match = re.search(pattern, query_lower)
            if match:
                location = match.group(1).replace(' ', '_').replace('-', '_')
                logger.debug(f"Extracted location from query: '{location}'")
                return location

        # Try to extract single-word location before common device words
        # "office light", "garage door", "bedroom fan"
        device_keywords = ['light', 'lamp', 'door', 'fan', 'switch', 'sensor', 'camera', 'thermostat']
        words = query_lower.split()
        for i, word in enumerate(words):
            if word in device_keywords and i > 0:
                # Previous word might be location
                potential_location = words[i-1]
                # Filter out numbers and common words
                if potential_location.isdigit() or potential_location in ['the', 'a', 'an', 'my', 'this', 'that']:
                    continue
                logger.debug(f"Potential location from word order: '{potential_location}'")
                return potential_location.replace('-', '_')

        return None

    def _extract_domain_from_query(self, query: str) -> str | None:
        """
        Extract device domain from query keywords.
        
        Examples:
            "turn on light" -> "light"
            "dim the lamp" -> "light"
            "switch on" -> "switch"
            "set temperature" -> "climate"
            "open garage door" -> "cover"
        
        Args:
            query: User query
            
        Returns:
            Domain name (e.g., "light", "switch", "climate") or None if not found
        """
        query_lower = query.lower()

        # Domain keywords mapping
        domain_keywords = {
            "light": ["light", "lamp", "lamp", "bulb", "led", "brightness", "dim", "bright", "illuminate"],
            "switch": ["switch", "outlet", "plug", "power"],
            "climate": ["temperature", "thermostat", "heat", "cool", "ac", "hvac", "climate", "temp"],
            "cover": ["blind", "shade", "curtain", "garage door", "door", "cover", "open", "close"],
            "sensor": ["sensor", "motion sensor", "temperature sensor"],
            "binary_sensor": ["motion", "door sensor", "window sensor", "door", "window", "presence", "presence sensor", "occupancy", "contact"],
            "fan": ["fan", "ventilation"],
            "media_player": ["tv", "television", "speaker", "music", "audio"],
            "lock": ["lock", "unlock", "door lock"],
        }

        for domain, keywords in domain_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                logger.debug(f"Extracted domain from query: '{domain}'")
                return domain

        return None

    def _extract_all_domains_from_query(self, query: str) -> list[str]:
        """
        Extract ALL device domains from query keywords (not just one).
        
        Examples:
            "presence sensor triggers lights" -> ["binary_sensor", "light"]
            "turn on office lights when door opens" -> ["light", "binary_sensor"]
        
        Args:
            query: User query
            
        Returns:
            List of domain names found in query
        """
        query_lower = query.lower()
        found_domains = []

        # Domain keywords mapping (same as _extract_domain_from_query)
        domain_keywords = {
            "light": ["light", "lamp", "lamp", "bulb", "led", "brightness", "dim", "bright", "illuminate"],
            "switch": ["switch", "outlet", "plug", "power"],
            "climate": ["temperature", "thermostat", "heat", "cool", "ac", "hvac", "climate", "temp"],
            "cover": ["blind", "shade", "curtain", "garage door", "door", "cover", "open", "close"],
            "sensor": ["sensor", "motion sensor", "temperature sensor"],
            "binary_sensor": ["motion", "door sensor", "window sensor", "door", "window", "presence", "presence sensor", "occupancy", "contact"],
            "fan": ["fan", "ventilation"],
            "media_player": ["tv", "television", "speaker", "music", "audio"],
            "lock": ["lock", "unlock", "door lock"],
        }

        for domain, keywords in domain_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                found_domains.append(domain)
                logger.debug(f"Extracted domain from query: '{domain}'")

        return found_domains

    def _extract_quantity_and_category(self, query: str) -> list[tuple[int | None, str, list[str]]]:
        """
        Extract quantity and category patterns from query.
        
        Examples:
        - "4 ceiling lights" → (4, "ceiling light", ["ceiling", "light"])
        - "wled sprit" → (None, "wled sprit", ["wled", "sprit"])
        - "all lights" → (None, "light", ["light"])
        - "ceiling lights" → (None, "ceiling light", ["ceiling", "light"])
        
        Returns:
            List of tuples: (quantity, category, search_terms)
        """
        import re
        patterns = []
        query_lower = query.lower()

        # Pattern 1: Numbered quantity (e.g., "4 ceiling lights", "2 lights")
        # Matches: number + optional words + light/device type
        numbered_pattern = r'(\d+)\s+((?:ceiling|wall|floor|desk|table|bedroom|living|kitchen|office|garage|bathroom|dining|hall|entry|front|back|left|right|north|south|east|west)\s+)?(lights?|light|sensors?|switches?|devices?)'
        matches = re.finditer(numbered_pattern, query_lower)
        for match in matches:
            quantity = int(match.group(1))
            location = match.group(2).strip() if match.group(2) else ""
            device_type = match.group(3).rstrip('s') if match.group(3) else ""  # Remove plural 's'
            category = f"{location} {device_type}".strip() if location else device_type
            search_terms = [t for t in [location.strip(), device_type] if t]
            patterns.append((quantity, category, search_terms))
            logger.info(f"🔍 Detected numbered pattern: {quantity} {category} (search terms: {search_terms})")

        # Pattern 2: Category without quantity (e.g., "ceiling lights", "wled sprit")
        # Match common device categories
        category_patterns = [
            (r'wled\s+sprit', 'wled sprit', ['wled', 'sprit']),
            (r'ceiling\s+lights?', 'ceiling light', ['ceiling', 'light']),
            (r'wall\s+lights?', 'wall light', ['wall', 'light']),
            (r'floor\s+lights?', 'floor light', ['floor', 'light']),
            (r'all\s+lights?', 'light', ['light']),
        ]

        for pattern, category, search_terms in category_patterns:
            if re.search(pattern, query_lower):
                # Check if this category was already captured by numbered pattern
                if not any(p[1] == category for p in patterns):
                    patterns.append((None, category, search_terms))
                    logger.info(f"🔍 Detected category pattern: {category} (search terms: {search_terms})")

        return patterns

    async def _query_entities_by_category(
        self,
        category: str,
        search_terms: list[str],
        quantity: int | None,
        query: str
    ) -> list[dict[str, Any]]:
        """
        Query database for all entities matching a category.
        
        Uses regular logic (database queries) combined with AI understanding.
        Searches by domain, name patterns, and friendly_name.
        
        Args:
            category: Category name (e.g., "ceiling light")
            search_terms: List of search terms to match
            quantity: Optional quantity limit
            query: Original query for context
            
        Returns:
            List of matching entity dictionaries
        """
        if not self.data_api_client:
            logger.warning("⚠️ Data API client not available - cannot query entities by category")
            return []

        try:
            # Extract domain from category (e.g., "ceiling light" → "light")
            domain = None
            for term in search_terms:
                if term in ['light', 'sensor', 'switch', 'device', 'wled']:
                    domain = term
                    break

            # If no domain found, try to infer from category
            if not domain:
                if 'light' in category:
                    domain = 'light'
                elif 'sensor' in category:
                    domain = 'sensor'
                elif 'switch' in category:
                    domain = 'switch'

            # Query all entities with matching domain
            logger.info(f"🔍 Querying entities by domain={domain} for category '{category}'")
            all_entities = await self._get_available_entities(domain=domain)

            if not all_entities:
                logger.warning(f"⚠️ No entities found for domain '{domain}'")
                return []

            logger.info(f"🔍 Found {len(all_entities)} entities with domain '{domain}', filtering by category...")

            # Filter entities by search terms
            matching_entities = []
            for entity in all_entities:
                entity_id = entity.get('entity_id', '').lower()
                friendly_name = entity.get('friendly_name', '').lower() if entity.get('friendly_name') else ''
                entity_name_part = entity_id.split('.', 1)[1] if '.' in entity_id else entity_id

                # Score entity based on how many search terms match
                score = 0
                for term in search_terms:
                    term_lower = term.lower()
                    # Check if term appears in entity_id or friendly_name
                    if term_lower in entity_id or term_lower in friendly_name or term_lower in entity_name_part:
                        score += 1
                    # Also check for partial matches (e.g., "ceiling" matches "ceiling_light")
                    if any(term_lower in word for word in entity_name_part.split('_') if word):
                        score += 0.5

                # Entity matches if it has at least one search term match
                if score > 0:
                    matching_entities.append((entity, score))

            # Sort by score (best matches first)
            matching_entities.sort(key=lambda x: x[1], reverse=True)

            # Extract just the entities (drop scores)
            result_entities = [entity for entity, score in matching_entities]

            # Limit to quantity if specified
            if quantity:
                result_entities = result_entities[:quantity]
                logger.info(f"✅ Limited to {quantity} entities as requested")

            logger.info(f"✅ Found {len(result_entities)} matching entities for category '{category}'")
            for idx, entity in enumerate(result_entities[:5]):  # Log first 5
                logger.info(f"  {idx + 1}. {entity.get('entity_id')} (score: {matching_entities[idx][1]:.1f})")

            return result_entities

        except Exception as e:
            logger.error(f"❌ Error querying entities by category '{category}': {e}", exc_info=True)
            return []

    async def map_query_to_entities(self, query: str, entities: list[str]) -> dict[str, str]:
        """
        Map query terms to actual entity IDs.
        
        Enhanced to use area_id/location context for better matching.
        Only matches entities in the correct room/area when location is mentioned.
        
        NEW: Detects quantities and categories (e.g., "4 ceiling lights") and queries
        database for ALL matching entities, not just one.
        
        Args:
            query: Original user query
            entities: List of entities mentioned in query
            
        Returns:
            Dictionary mapping query terms to actual entity IDs
            For quantities, returns multiple mappings (e.g., "ceiling light 1", "ceiling light 2", ...)
        """
        import time
        blocking_start = time.time()
        logger.info(f"map_query_to_entities called with query='{query}', entities={entities}")
        mapping = {}

        # Initialize performance metrics
        metrics = PerformanceMetrics()
        metrics.entity_count = len(entities)
        metrics.total_resolution_ms = 0  # Will be set at end

        # STEP 0: Detect quantities and categories in query (NEW LOGIC)
        # Examples: "4 ceiling lights", "all lights", "ceiling lights", "wled sprit"
        quantity_matches = self._extract_quantity_and_category(query)
        if quantity_matches:
            logger.info(f"🔍 QUANTITY DETECTION: Found {len(quantity_matches)} quantity/category patterns in query")
            for quantity_info in quantity_matches:
                quantity, category, search_terms = quantity_info
                logger.info(f"  → Quantity: {quantity}, Category: {category}, Search terms: {search_terms}")

                # Query database for ALL matching entities
                matching_entities = await self._query_entities_by_category(
                    category=category,
                    search_terms=search_terms,
                    quantity=quantity,
                    query=query
                )

                if matching_entities:
                    logger.info(f"✅ Found {len(matching_entities)} matching entities for '{category}'")
                    # Map each entity to a unique key
                    for idx, entity in enumerate(matching_entities[:quantity] if quantity else matching_entities):
                        entity_id = entity.get('entity_id')
                        if entity_id:
                            # Create unique mapping key (e.g., "ceiling light 1", "ceiling light 2")
                            if quantity and quantity > 1:
                                mapping_key = f"{category} {idx + 1}" if idx < quantity else f"{category} {idx + 1}"
                            else:
                                mapping_key = f"{category} {idx + 1}" if len(matching_entities) > 1 else category
                            mapping[mapping_key] = entity_id
                            logger.info(f"  → Mapped '{mapping_key}' → {entity_id}")

                    # Also add the category itself mapping to all entities as a list (for backward compatibility)
                    # This allows the system to use all matching entities when the category is referenced
                    if category not in mapping and matching_entities:
                        # For quantities > 1, store all entity IDs as a comma-separated list
                        # The YAML generator can split this to create multiple actions
                        if quantity and quantity > 1:
                            all_entity_ids = ','.join([e.get('entity_id') for e in matching_entities[:quantity] if e.get('entity_id')])
                            mapping[category] = all_entity_ids
                            logger.info(f"  → Mapped category '{category}' to all {quantity} entities: {all_entity_ids}")
                        else:
                            mapping[category] = matching_entities[0].get('entity_id')
                else:
                    logger.warning(f"⚠️ No entities found for category '{category}' with search terms: {search_terms}")

        # STEP 1: Extract blocking filters from query
        # 1.1: Extract domain (e.g., "light", "switch")
        query_domain = self._extract_domain_from_query(query)
        if query_domain:
            logger.info(f"🔍 BLOCKING: Extracted domain from query: '{query_domain}'")
        else:
            logger.debug("🔍 BLOCKING: No domain found in query - will fetch all domains")

        # 1.2: Extract location context from query
        query_location = self._extract_location_from_query(query)
        if query_location:
            logger.info(f"🔍 BLOCKING: Extracted location from query: '{query_location}'")
        else:
            logger.debug("🔍 BLOCKING: No location found in query - will match any location")

        # STEP 2: Multi-level blocking pipeline
        # Level 1: Domain filter (reduces 10,000 → ~500 entities)
        domain_filter_start = time.time()
        available_entities = await self._get_available_entities(domain=query_domain)
        domain_filter_time = (time.time() - domain_filter_start) * 1000
        total_entities_after_domain = len(available_entities)
        metrics.candidates_total = 10000  # Estimated starting point
        metrics.candidates_after_domain = total_entities_after_domain
        metrics.domain_filter_ms = domain_filter_time
        logger.info(
            f"🔍 BLOCKING: Domain filter ({query_domain or 'all'}) "
            f"→ {total_entities_after_domain} entities ({domain_filter_time:.1f}ms)"
        )

        # Level 2: Location filter (if location found, reduces ~500 → ~50 entities)
        # Note: Location filtering happens at API level if query_location is provided
        # But we also filter in-memory after enrichment in full chain
        location_filter_start = time.time()
        if query_location:
            # Fetch entities with location filter if domain was already used
            # Otherwise, this is redundant with domain fetch
            if query_domain:
                # Re-fetch with both domain and location for optimal blocking
                available_entities = await self._get_available_entities(
                    domain=query_domain,
                    area_id=query_location
                )
            else:
                # Only location filter
                available_entities = await self._get_available_entities(area_id=query_location)
            location_filter_time = (time.time() - location_filter_start) * 1000
            total_entities_after_location = len(available_entities)
            metrics.candidates_after_location = total_entities_after_location
            metrics.location_filter_ms = location_filter_time
            logger.info(
                f"🔍 BLOCKING: Location filter ({query_location}) "
                f"→ {total_entities_after_location} entities ({location_filter_time:.1f}ms)"
            )
        else:
            location_filter_time = 0
            total_entities_after_location = total_entities_after_domain
            metrics.candidates_after_location = total_entities_after_location

        blocking_time = (time.time() - blocking_start) * 1000
        reduction_percentage = (
            (1 - total_entities_after_location / 10000) * 100
            if total_entities_after_location < 10000
            else 0
        )
        logger.info(
            f"🔍 BLOCKING SUMMARY: {total_entities_after_location} entities after blocking "
            f"(~{reduction_percentage:.0f}% reduction), total blocking time: {blocking_time:.1f}ms"
        )

        # If entities list is empty, try to extract from query directly
        if not entities:
            logger.info("No entities provided, extracting from query directly")
            # Extract potential entities from query
            query_lower = query.lower()

            # Look for living room-related entities
            if 'living room' in query_lower or 'livingroom' in query_lower:
                living_room_entities = [e for e in available_entities if 'living' in e.get('entity_id', '').lower() and 'room' in e.get('entity_id', '').lower()]
                if living_room_entities:
                    # Prefer lights for living room
                    living_room_lights = [e for e in living_room_entities if e.get('domain') == 'light']
                    if living_room_lights:
                        mapping['living room'] = living_room_lights[0]['entity_id']
                        mapping['lights'] = living_room_lights[0]['entity_id']
                        logger.info(f"Mapped 'living room' to {living_room_lights[0]['entity_id']}")

            # Look for office-related entities
            if 'office' in query_lower:
                office_entities = [e for e in available_entities if 'office' in e.get('entity_id', '').lower()]
                if office_entities:
                    # Prefer lights for office
                    office_lights = [e for e in office_entities if e.get('domain') == 'light']
                    if office_lights:
                        mapping['office'] = office_lights[0]['entity_id']
                        logger.info(f"Mapped 'office' to {office_lights[0]['entity_id']}")

            # Look for door-related entities
            if 'door' in query_lower or 'front' in query_lower:
                door_entities = [e for e in available_entities if 'door' in e.get('entity_id', '').lower()]
                if door_entities:
                    # Prefer binary sensors for doors
                    door_sensors = [e for e in door_entities if e.get('domain') == 'binary_sensor']
                    if door_sensors:
                        mapping['door'] = door_sensors[0]['entity_id']
                        logger.info(f"Mapped 'door' to {door_sensors[0]['entity_id']}")
                    else:
                        # Fallback to any door entity
                        mapping['door'] = door_entities[0]['entity_id']
                        logger.info(f"Mapped 'door' to {door_entities[0]['entity_id']}")

            # Look for light-related entities
            if 'light' in query_lower or 'flash' in query_lower:
                light_entities = [e for e in available_entities if e.get('domain') == 'light']
                if light_entities:
                    # Prefer living room lights if query mentions living room
                    living_room_lights = [e for e in light_entities if 'living' in e.get('entity_id', '').lower() and 'room' in e.get('entity_id', '').lower()]
                    if living_room_lights:
                        mapping['lights'] = living_room_lights[0]['entity_id']
                        logger.info(f"Mapped 'lights' to living room light: {living_room_lights[0]['entity_id']}")
                    else:
                        # Prefer office lights if available
                        office_lights = [e for e in light_entities if 'office' in e.get('entity_id', '').lower()]
                        if office_lights:
                            mapping['lights'] = office_lights[0]['entity_id']
                            logger.info(f"Mapped 'lights' to {office_lights[0]['entity_id']}")
                        else:
                            # Use any light
                            mapping['lights'] = light_entities[0]['entity_id']
                            logger.info(f"Mapped 'lights' to {light_entities[0]['entity_id']}")
        else:
            # Use the provided entities list
            logger.info(f"Using provided entities list: {entities}")
            for entity in entities:
                # Try to find best match
                logger.info(f"Looking for best match for '{entity}'...")

                # STEP 0: Check aliases FIRST (before full chain matching)
                # This provides fast, high-confidence matches for user-defined nicknames
                alias_entity_id = await self._check_aliases(entity, user_id=getattr(self, 'user_id', 'anonymous'))
                if alias_entity_id:
                    # Alias found - skip ML matching and return immediately
                    mapping[entity] = alias_entity_id
                    logger.info(f"✅ Alias match: '{entity}' → {alias_entity_id}")
                    continue

                # If query mentions "light", prefer light entities
                entity_lower = entity.lower()
                filtered_entities = available_entities
                if 'light' in entity_lower or 'flash' in entity_lower:
                    # Try to find lights first
                    light_entities = [e for e in available_entities if e.get('domain') == 'light']
                    if light_entities:
                        filtered_entities = light_entities

                # Extract location from this specific entity if not already extracted from query
                entity_location = self._extract_location_from_query(entity)
                location_to_use = entity_location or query_location

                # Filter by location if we have location context
                location_filtered_entities = filtered_entities
                if location_to_use:
                    location_normalized = location_to_use.replace(' ', '_').replace('-', '_').lower()

                    # Check if any entities have area_id set (entity or device area_id after enrichment)
                    # Note: area_id check happens after enrichment in full chain, so for now we pass all entities
                    # and let the full chain handle location filtering with device_area_id
                    entities_with_area = [e for e in filtered_entities if e.get('area_id')]

                    if entities_with_area:
                        # Try filtering by area_id (entity area_id only - device_area_id will be checked in full chain)
                        location_filtered = [
                            e for e in filtered_entities
                            if e.get('area_id') and location_normalized in e.get('area_id', '').lower()
                        ]
                        if location_filtered:
                            logger.info(
                                f"Filtered to {len(location_filtered)} entities in area '{location_to_use}' "
                                f"(from {len(filtered_entities)} total {entity_lower} entities)"
                            )
                            location_filtered_entities = location_filtered
                        else:
                            # No matches with entity area_id - but device_area_id might match
                            # Pass all entities to full chain which will check device_area_id
                            logger.debug(
                                f"No entities found with entity area_id '{location_to_use}' for '{entity}', "
                                f"will check device_area_id in full chain"
                            )
                    else:
                        # No area_ids available - skip area filtering and use entity_id matching
                        logger.debug(
                            f"No area_id data available for entities, using entity_id-based matching "
                            f"for '{entity}' with location context '{location_to_use}'"
                        )
                        # location_filtered_entities remains as filtered_entities (all entities)
                        # The _find_best_match will use entity_id patterns and location context for scoring

                # Use full chain if enabled, otherwise fallback to simple matching
                if self.enable_full_chain:
                    best_match, confidence = await self._find_best_match_full_chain(
                        entity, location_filtered_entities, query, location_context=location_to_use
                    )
                    if best_match:
                        logger.info(f"Mapped '{entity}' to {best_match['entity_id']} (confidence: {confidence:.2f})")
                else:
                    best_match = self._find_best_match(entity, location_filtered_entities, location_context=location_to_use)
                    confidence = None

                # Check if this is a numbered device query
                numbered_info = self._extract_number_from_query(entity)
                is_numbered_query = numbered_info is not None

                if best_match:
                    # Check confidence threshold for numbered queries (more lenient)
                    # Lowered from 0.3 to 0.15 to allow partial matches with location penalties
                    if is_numbered_query and confidence is not None and confidence < 0.15:
                        logger.warning(
                            f"Very low confidence ({confidence:.2f}) for numbered device '{entity}' -> {best_match['entity_id']}. "
                            f"Skipping mapping - no match found for '{entity}' (will be addressed on system cleanup page)"
                        )
                        # Don't map - let system cleanup page handle it
                    else:
                        mapping[entity] = best_match['entity_id']
                        match_area = best_match.get('area_id') or best_match.get('device_area_id', 'unknown')
                        logger.info(f"Mapped '{entity}' to {best_match['entity_id']} (area: {match_area})")
                        metrics.matches_found += 1
                else:
                    logger.warning(f"No match found for '{entity}' (will be addressed on system cleanup page)")

        # Record total time and enrichment stats
        metrics.total_resolution_ms = (time.time() - blocking_start) * 1000
        metrics.enrichment_count = len(location_filtered_entities) if 'location_filtered_entities' in locals() else len(available_entities)
        metrics.matching_ms = metrics.total_resolution_ms - metrics.domain_filter_ms - metrics.location_filter_ms

        # Log performance summary
        metrics.log_summary()

        logger.info(f"Final entity mapping: {mapping}")
        return mapping

    def _find_binary_sensor_fuzzy(self, query_term: str, available_entities: list[dict[str, Any]]) -> dict[str, Any] | None:
        """
        Find binary sensor with fuzzy matching for presence/motion/occupancy patterns.
        
        Uses rapidfuzz base score combined with domain-specific bonuses for binary sensors.
        Handles common binary sensor naming variations:
        - {location}_{type} (e.g., office_desk_presence)
        - {type}_{location} (e.g., presence_office_desk)
        - {location}_{device}_{type} (e.g., office_desk_occupancy)
        - {location}_{type}_{device} (e.g., office_presence_desk)
        
        Args:
            query_term: Query term like "office desk presence" or "desk presence"
            available_entities: List of available entities (filtered by binary_sensor domain)
            
        Returns:
            Best matching binary sensor entity or None
        """
        from ..utils.fuzzy import fuzzy_match_with_context
        
        query_lower = query_term.lower()
        query_words = set(re.findall(r'\w+', query_lower))

        # Common binary sensor type keywords
        sensor_types = {'presence', 'motion', 'occupancy', 'contact', 'door', 'window'}
        query_has_sensor_type = any(st in query_words for st in sensor_types)

        # Extract location and sensor type from query
        location_words = query_words - sensor_types
        sensor_type_words = query_words & sensor_types

        candidates = []

        for entity in available_entities:
            entity_id = entity.get('entity_id', '')
            if not entity_id.startswith('binary_sensor.'):
                continue

            entity_name = entity_id.replace('binary_sensor.', '').lower()
            entity_words = set(re.findall(r'\w+', entity_name))

            # Build context bonuses for domain-specific scoring
            context_bonuses = {}

            # Location words match bonus
            if location_words:
                location_match = location_words.intersection(entity_words)
                if location_match:
                    location_score = len(location_match) / len(location_words)
                    context_bonuses['location'] = location_score * 0.1  # 0-0.1 bonus

            # Sensor type match bonus (important for binary sensors)
            if query_has_sensor_type and sensor_type_words:
                type_match = sensor_type_words.intersection(entity_words)
                if type_match:
                    type_score = len(type_match) / len(sensor_type_words)
                    context_bonuses['sensor_type'] = type_score * 0.15  # 0-0.15 bonus (higher weight)

            # Pattern matching bonus for common binary sensor patterns
            if location_words and sensor_type_words:
                # Pattern: location_type or type_location
                for loc_word in location_words:
                    for type_word in sensor_type_words:
                        pattern1 = f"{loc_word}_{type_word}"
                        pattern2 = f"{type_word}_{loc_word}"
                        if pattern1 in entity_name or pattern2 in entity_name:
                            context_bonuses['pattern'] = 0.1  # Pattern match bonus
                            break

            # Use rapidfuzz base score with domain-specific context bonuses
            base_score = fuzzy_match_with_context(
                query_term,
                entity_name,
                context_bonuses if context_bonuses else None
            )

            # Also check exact substring match for high confidence
            if query_lower in entity_name or entity_name in query_lower:
                base_score = max(base_score, 1.0)

            if base_score > 0.5:  # Threshold for fuzzy match
                candidates.append((entity, base_score))

        # Return best match
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            best_entity, best_score = candidates[0]
            logger.info(f"🔍 Fuzzy match for '{query_term}': {best_entity['entity_id']} (score: {best_score:.2f})")
            return best_entity

        return None

    def _find_best_match(
        self,
        query_term: str,
        available_entities: list[dict[str, Any]],
        location_context: str | None = None
    ) -> dict[str, Any] | None:
        """
        Find the best matching entity for a query term.
        
        Enhanced to:
        - Handle numbered devices (e.g., "Office light 1" -> "light.office_1")
        - Use location/area context to prefer entities in the correct room
        - Fuzzy matching for binary sensors (presence, motion, occupancy)
        
        Args:
            query_term: Term from user query (e.g., "office light" or "office light 1")
            available_entities: List of available entities (should already be filtered by domain/location)
            location_context: Optional location/area name from query (e.g., "office", "living_room")
            
        Returns:
            Best matching entity or None
        """
        query_words = set(re.findall(r'\w+', query_term.lower()))
        logger.debug(f"_find_best_match for '{query_term}' with {len(query_words)} words: {query_words}")

        # SPECIAL HANDLING: Try fuzzy matching for binary sensors first
        # Check if query mentions presence/motion/occupancy/door/window
        binary_sensor_keywords = {'presence', 'motion', 'occupancy', 'door', 'window', 'contact', 'sensor'}
        if any(keyword in query_term.lower() for keyword in binary_sensor_keywords):
            binary_sensors = [e for e in available_entities if e.get('entity_id', '').startswith('binary_sensor.')]
            if binary_sensors:
                fuzzy_match = self._find_binary_sensor_fuzzy(query_term, binary_sensors)
                if fuzzy_match:
                    return fuzzy_match

        # STEP 1: Check if query contains a number
        numbered_info = self._extract_number_from_query(query_term)

        numbered_match = None
        if numbered_info:
            base_term, number = numbered_info
            logger.debug(f"Detected numbered device: base='{base_term}', number='{number}'")

            # Try to find domain from available entities
            domain = None
            for entity in available_entities:
                entity_id = entity.get('entity_id', '')
                if '.' in entity_id:
                    potential_domain = entity_id.split('.', 1)[0]
                    # Use domain if it appears multiple times (likely correct)
                    if sum(1 for e in available_entities if e.get('entity_id', '').startswith(f"{potential_domain}.")) > 1:
                        domain = potential_domain
                        break

            # Build search patterns for numbered entities
            patterns = self._build_numbered_entity_patterns(base_term, number, domain)
            logger.debug(f"Searching for numbered entity patterns: {patterns}")

            # Search for exact numbered matches first
            for pattern in patterns:
                for entity in available_entities:
                    entity_id = entity.get('entity_id', '').lower()
                    # Check if entity_id ends with the pattern or contains it
                    if entity_id.endswith(pattern.lower()) or pattern.lower() in entity_id:
                        logger.debug(f"Found numbered match: {entity.get('entity_id')} matches pattern '{pattern}'")
                        numbered_match = entity
                        break
                if numbered_match:
                    break

        # STEP 2: Generic matching (fallback if no numbered match, or always check for better score)
        best_match = numbered_match
        best_score = 0.5 if numbered_match else 0  # Prioritize numbered matches

        for entity in available_entities:
            entity_id = entity.get('entity_id', '')
            entity_name = entity_id.split('.', 1)[1] if '.' in entity_id else entity_id

            # Split on underscores and hyphens to handle "living_room" -> ["living", "room"]
            entity_words = set()
            for word in re.findall(r'\w+', entity_name.lower()):
                # Also split underscores and hyphens
                entity_words.update(word.split('_'))
                entity_words.update(word.split('-'))

            # Calculate word overlap score
            common_words = query_words.intersection(entity_words)

            if common_words:
                score = len(common_words) / len(query_words.union(entity_words))

                # Boost score if it's a numbered match that wasn't found earlier
                if numbered_info and numbered_info[1] in entity_id:
                    score += 0.3  # Boost numbered matches

                # Boost score if location matches (CRITICAL for correct room matching)
                if location_context:
                    location_normalized = location_context.replace(' ', '_').replace('-', '_').lower()

                    # Check area_id first (preferred method)
                    entity_area = entity.get('area_id', '').lower() if entity.get('area_id') else ''
                    location_in_area = location_normalized in entity_area if entity_area else False

                    # Also check entity_id for location match (fallback when area_id not available)
                    location_in_entity_id = location_normalized in entity_id.lower() or location_context.lower() in entity_id.lower()

                    if location_in_area or location_in_entity_id:
                        score += 0.5  # Strong boost for location match
                        match_source = "area_id" if location_in_area else "entity_id"
                        logger.debug(f"Location match boost: '{location_context}' in {match_source}")
                    else:
                        # Penalize entities in wrong location (but don't exclude completely)
                        score *= 0.3  # Reduce score significantly for wrong location
                        logger.debug(f"Location mismatch: '{location_context}' not found in area_id or entity_id")

                if score > best_score:
                    best_score = score
                    best_match = entity
                    entity_area = entity.get('area_id', 'unknown')
                    logger.debug(
                        f"Better match: {entity_id} (score: {score:.2f}, area: {entity_area}, "
                        f"common: {common_words})"
                    )

        # Lower threshold to 25% to catch "Living Room Light" -> "light.living_room"
        result_entity_id = best_match.get('entity_id') if best_match else 'NONE'
        logger.debug(f"Best match: {result_entity_id} (score: {best_score:.2f})")
        return best_match if best_score >= 0.25 else None

    def _extract_number_from_query(self, query_term: str) -> tuple | None:
        """
        Extract number and base term from query.
        
        Examples:
            "Office light 1" -> ("office light", "1")
            "Bedroom lamp 3" -> ("bedroom lamp", "3")
            "Office light" -> None (no number)
        
        Args:
            query_term: Query term that may contain a number
            
        Returns:
            Tuple of (base_term, number) or None if no number found
        """
        # Match numbers at the end: "office light 1", "light 2", etc.
        match = re.search(r'(.+?)\s+(\d+)\s*$', query_term.strip())
        if match:
            base_term = match.group(1).strip().lower()
            number = match.group(2)
            return (base_term, number)
        return None

    def _build_numbered_entity_patterns(self, base_term: str, number: str, domain: str | None = None) -> list[str]:
        """
        Build entity ID patterns to search for numbered entities.
        
        Args:
            base_term: Base term without number (e.g., "office light")
            number: Number to append (e.g., "1")
            domain: Optional domain prefix (e.g., "light")
            
        Returns:
            List of entity ID patterns to search for
        """
        patterns = []

        # Split base term into words
        base_words = re.findall(r'\w+', base_term.lower())

        # Common patterns:
        # light.office_1, light.office_lamp_1, light.office_light_1
        if len(base_words) >= 2:
            # office light -> office_1, office_lamp_1, office_light_1
            base_joined = '_'.join(base_words)
            patterns.append(f"{base_joined}_{number}")

            # For multi-word, try variations
            if domain:
                patterns.append(f"{domain}.{base_joined}_{number}")
                patterns.append(f"{domain}.{base_joined}_lamp_{number}")
                patterns.append(f"{domain}.{base_joined}_light_{number}")
        elif len(base_words) == 1:
            # Single word: light -> light_1
            word = base_words[0]
            patterns.append(f"{word}_{number}")
            if domain:
                patterns.append(f"{domain}.{word}_{number}")
                patterns.append(f"{domain}.{word}_lamp_{number}")
                patterns.append(f"{domain}.{word}_light_{number}")

        return patterns

    async def validate_automation_yaml(self, yaml_content: str) -> dict[str, Any]:
        """
        Validate all entities in an automation YAML.
        
        Args:
            yaml_content: Automation YAML content
            
        Returns:
            Validation result with entity status
        """
        import yaml

        try:
            automation_data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            return {
                "valid": False,
                "error": f"Invalid YAML: {e}",
                "entity_results": {}
            }

        # Extract entity IDs from YAML
        entity_ids = self._extract_entity_ids_from_yaml(automation_data)

        # Validate entities
        validation_results = await self.validate_entities(entity_ids)

        # Check if all entities are valid
        all_valid = all(result.exists for result in validation_results.values())

        return {
            "valid": all_valid,
            "entity_results": validation_results,
            "invalid_entities": [
                entity_id for entity_id, result in validation_results.items()
                if not result.exists
            ]
        }

    def _extract_entity_ids_from_yaml(self, automation_data: dict[str, Any]) -> list[str]:
        """Extract all entity IDs from automation YAML data"""
        entity_ids = set()

        def extract_from_dict(data):
            if isinstance(data, dict):
                if 'entity_id' in data:
                    entity_id = data['entity_id']
                    if isinstance(entity_id, str):
                        entity_ids.add(entity_id)
                    elif isinstance(entity_id, list):
                        entity_ids.update(entity_id)

                for value in data.values():
                    extract_from_dict(value)
            elif isinstance(data, list):
                for item in data:
                    extract_from_dict(item)

        extract_from_dict(automation_data)
        return list(entity_ids)

    # ============================================================================
    # FULL MODEL CHAIN IMPLEMENTATION
    # ============================================================================

    def _get_embedding_model(self):
        """Lazy load sentence-transformers embedding model"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            return None

        if self._embedding_model is None:
            try:
                logger.info("Loading sentence-transformers model for entity matching...")
                self._embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
                logger.info("Embedding model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                self._embedding_model = None
        return self._embedding_model

    def _get_ner_pipeline(self):
        """Lazy load HuggingFace NER pipeline"""
        if not TRANSFORMERS_AVAILABLE:
            return None

        if self._ner_pipeline is None:
            try:
                logger.info("Loading NER pipeline for entity extraction...")
                self._ner_pipeline = transformers_pipeline("ner", model="dslim/bert-base-NER")
                logger.info("NER pipeline loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load NER pipeline: {e}")
                self._ner_pipeline = None
        return self._ner_pipeline

    async def _enrich_entity_with_metadata(self, entity: dict[str, Any]) -> dict[str, Any]:
        """
        Enrich entity with device metadata and friendly_name.
        
        Adds:
        - device_name: From device registry (via device_id)
        - friendly_name: From entity attributes or metadata
        - device_manufacturer: From device registry
        - device_model: From device registry
        
        Args:
            entity: Entity dict with entity_id, device_id, etc.
            
        Returns:
            Enriched entity dict
        """
        enriched = entity.copy()

        if not self.data_api_client:
            return enriched

        # Fetch device metadata if device_id exists
        device_id = entity.get('device_id')
        if device_id and device_id not in self._device_metadata_cache:
            try:
                device_metadata = await self.data_api_client.get_device_metadata(device_id)
                if device_metadata:
                    self._device_metadata_cache[device_id] = device_metadata
            except Exception as e:
                logger.debug(f"Failed to fetch device metadata for {device_id}: {e}")

        if device_id and device_id in self._device_metadata_cache:
            device_metadata = self._device_metadata_cache[device_id]
            # Priority: name_by_user > name > entity_id parts
            enriched['device_name'] = device_metadata.get('name_by_user') or device_metadata.get('name', '')
            enriched['name_by_user'] = device_metadata.get('name_by_user', '')
            enriched['device_manufacturer'] = device_metadata.get('manufacturer', '')
            enriched['device_model'] = device_metadata.get('model', '')
            enriched['device_area_id'] = device_metadata.get('area_id', '')  # Always store device_area_id
            enriched['suggested_area'] = device_metadata.get('suggested_area', '')
            enriched['integration'] = device_metadata.get('integration', '')
            # Use device area_id if entity area_id is missing (for location matching)
            if not enriched.get('area_id') and device_metadata.get('area_id'):
                enriched['area_id'] = device_metadata.get('area_id')
            # Fallback to suggested_area if area_id still missing
            if not enriched.get('area_id') and device_metadata.get('suggested_area'):
                enriched['area_id'] = device_metadata.get('suggested_area')

        # Try to get friendly_name from entity metadata
        entity_id = entity.get('entity_id')
        if entity_id:
            try:
                entity_metadata = await self.data_api_client.get_entity_metadata(entity_id)
                if entity_metadata:
                    # Extract friendly_name from metadata or attributes
                    friendly_name = entity_metadata.get('friendly_name') or entity_metadata.get('name')
                    if friendly_name:
                        enriched['friendly_name'] = friendly_name
            except Exception as e:
                logger.debug(f"Failed to fetch entity metadata for {entity_id}: {e}")

        return enriched

    async def _enrich_entities_batch(self, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Enrich multiple entities with metadata in parallel"""
        tasks = [self._enrich_entity_with_metadata(entity) for entity in entities]
        enriched = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and return valid enriched entities
        result = []
        for i, item in enumerate(enriched):
            if isinstance(item, Exception):
                logger.warning(f"Failed to enrich entity {entities[i].get('entity_id')}: {item}")
                result.append(entities[i])  # Return original if enrichment failed
            else:
                result.append(item)
        return result

    async def _find_best_match_full_chain(
        self,
        query_term: str,
        available_entities: list[dict[str, Any]],
        full_query: str,
        location_context: str | None = None
    ) -> tuple[dict[str, Any] | None, float]:
        """
        Full model chain for entity matching:
        1. NER Extraction (optional, for complex queries)
        2. Entity Enrichment (device metadata, friendly_name)
        3. Embedding-Based Matching (semantic similarity)
        4. Hybrid Scoring (combines all signals)
        5. Confidence Scoring
        
        Args:
            query_term: Specific term to match (e.g., "Office light 1")
            available_entities: List of candidate entities
            full_query: Full user query for context
            location_context: Optional location/area name
            
        Returns:
            Tuple of (best_match_entity, confidence_score)
        """
        if not available_entities:
            return None, 0.0

        logger.debug(f"Full chain matching for '{query_term}' with {len(available_entities)} candidates")

        # STEP 1: Enrich entities with metadata (device names, friendly_names)
        enriched_entities = await self._enrich_entities_batch(available_entities)
        logger.debug(f"Enriched {len(enriched_entities)} entities with metadata")

        # STEP 2: Extract chronological matching signals
        numbered_info = self._extract_number_from_query(query_term)
        query_lower = query_term.lower()

        # STEP 3: Build candidate strings for embedding matching
        candidate_strings = []
        for entity in enriched_entities:
            # Build searchable string from all available names
            search_terms = []

            # Priority order: friendly_name > name_by_user > device_name > entity_id
            if entity.get('friendly_name'):
                search_terms.append(entity['friendly_name'])
            if entity.get('name_by_user'):
                search_terms.append(entity['name_by_user'])
            if entity.get('device_name'):
                search_terms.append(entity['device_name'])

            # Also include entity_id parts
            entity_id = entity.get('entity_id', '')
            entity_name = entity_id.split('.', 1)[1] if '.' in entity_id else entity_id
            search_terms.append(entity_name)

            # Combine all terms
            candidate_string = ' '.join(search_terms)
            candidate_strings.append(candidate_string)

        # STEP 4: Embedding-based semantic matching
        embedding_scores = {}
        embedding_model = self._get_embedding_model()

        if embedding_model and candidate_strings:
            try:
                # Generate embeddings
                query_embedding = embedding_model.encode([query_term], convert_to_numpy=True)[0]
                candidate_embeddings = embedding_model.encode(candidate_strings, convert_to_numpy=True)

                # Calculate cosine similarity
                import numpy as np
                for i, candidate_embedding in enumerate(candidate_embeddings):
                    # Cosine similarity
                    dot_product = np.dot(query_embedding, candidate_embedding)
                    norm_query = np.linalg.norm(query_embedding)
                    norm_candidate = np.linalg.norm(candidate_embedding)
                    similarity = dot_product / (norm_query * norm_candidate) if (norm_query * norm_candidate) > 0 else 0.0
                    embedding_scores[i] = float(similarity)

                logger.debug(f"Computed embedding similarities: {list(embedding_scores.values())[:3]}")
            except Exception as e:
                logger.warning(f"Embedding matching failed: {e}, falling back to word-based matching")
                embedding_scores = {}

        # STEP 5: Hybrid scoring - combine all signals
        best_match = None
        best_score = 0.0

        logger.debug(
            f"🔍 SCORING DEBUG: Starting scoring for query '{query_term}' with location_context='{location_context}'"
        )
        logger.debug(f"🔍 SCORING DEBUG: Numbered info: {numbered_info}")
        logger.debug(f"🔍 SCORING DEBUG: Evaluating {len(enriched_entities)} entities")

        # Track location mismatches for summary logging
        location_mismatches = []

        for i, entity in enumerate(enriched_entities):
            score = 0.0
            score_details = {}

            entity_id = entity.get('entity_id', '')
            friendly_name = entity.get('friendly_name', '').lower()
            name_by_user = entity.get('name_by_user', '').lower()
            device_name = entity.get('device_name', '').lower()
            entity_name = entity_id.split('.', 1)[1] if '.' in entity_id else entity_id.lower()

            # Log entity metadata for debugging (only for top candidates)
            if i < 3:  # Only log first 3 candidates
                entity_area = entity.get('area_id', '') or 'None'
                device_area = entity.get('device_area_id', '') or 'None'
                suggested_area = entity.get('suggested_area', '') or 'None'
                logger.debug(
                    f"🔍 SCORING DEBUG [{i}] Entity: {entity_id}\n"
                    f"  - friendly_name: {friendly_name or 'None'}\n"
                    f"  - name_by_user: {name_by_user or 'None'}\n"
                    f"  - device_name: {device_name or 'None'}\n"
                    f"  - entity_area_id: {entity_area}\n"
                    f"  - device_area_id: {device_area}\n"
                    f"  - suggested_area: {suggested_area}"
                )

            # Signal 1: Embedding similarity (0.0 - 1.0) - Weight: 35% (reduced from 40%)
            if i in embedding_scores:
                embedding_score = embedding_scores[i]
                score += embedding_score * 0.35
                score_details['embedding'] = embedding_score

            # Signal 2: Exact name matches (highest priority) - Weight: 30%
            # Priority: friendly_name > name_by_user > device_name
            exact_match = False
            if friendly_name and query_lower == friendly_name:
                score += 1.0 * 0.3
                exact_match = True
                score_details['exact_friendly_name'] = True
            elif name_by_user and query_lower == name_by_user:
                score += 1.0 * 0.3
                exact_match = True
                score_details['exact_name_by_user'] = True
            elif device_name and query_lower == device_name:
                score += 1.0 * 0.3
                exact_match = True
                score_details['exact_device_name'] = True

            # Signal 2.5: Common alias matching (Quick Win 2) - Weight: 15%
            # Check aliases before fuzzy matching for better accuracy
            alias_match_score = 0.0
            if not exact_match:
                query_lower_words = query_lower.split()
                # Check if query contains alias terms
                for alias_term, aliases in self.COMMON_DEVICE_ALIASES.items():
                    if alias_term in query_lower_words or any(alias in query_lower_words for alias in aliases):
                        # Check if entity names contain the alias or its alternatives
                        entity_texts = [t for t in [friendly_name, name_by_user, device_name, entity_name] if t]
                        for entity_text in entity_texts:
                            entity_lower = entity_text.lower()
                            if alias_term in entity_lower or any(alias in entity_lower for alias in aliases):
                                alias_match_score = 0.8  # High score for alias match
                                score_details['alias_match'] = True
                                break
                        if alias_match_score > 0:
                            break
                
                if alias_match_score > 0:
                    score += alias_match_score * 0.15
                else:
                    # Signal 2.6: Fuzzy string matching (for typos/abbreviations) - Weight: 15%
                    # Only use if exact match and alias match failed
                    fuzzy_scores = []
                    # Check against all available names in priority order
                    if friendly_name:
                        fuzzy_scores.append(self._fuzzy_match_score(query_term, friendly_name))
                    if name_by_user:
                        fuzzy_scores.append(self._fuzzy_match_score(query_term, name_by_user))
                    if device_name:
                        fuzzy_scores.append(self._fuzzy_match_score(query_term, device_name))
                    # Also check entity_id parts
                    if entity_name:
                        fuzzy_scores.append(self._fuzzy_match_score(query_term, entity_name))

                    if fuzzy_scores:
                        max_fuzzy = max(fuzzy_scores)
                        # Quick Win 2: Lower threshold from 0.6 to 0.5 for better typo handling
                        if max_fuzzy > 0.5:
                            score += max_fuzzy * 0.15
                            score_details['fuzzy_match'] = max_fuzzy

            # Signal 3: Numbered device matching - Weight: 15% (reduced from 20%)
            if numbered_info:
                base_term, number = numbered_info

                # Check if EXACT number appears in names/entity_id (word boundary matching)
                number_in_friendly = self._number_matches_exactly(number, friendly_name) if friendly_name else False
                number_in_name_by_user = self._number_matches_exactly(number, name_by_user) if name_by_user else False
                number_in_device = self._number_matches_exactly(number, device_name) if device_name else False
                number_in_entity = self._number_matches_exactly(number, entity_id)

                # Combined check for any number match
                exact_number_match = number_in_friendly or number_in_name_by_user or number_in_device or number_in_entity

                # Check if this is a group entity (e.g., light.office is a group)
                is_group_entity = self._is_group_entity(entity)

                # exact_number_match already calculated above

                if exact_number_match:
                    # Full points for exact number match (weight adjusted to 15%)
                    score += 0.5 * 0.15
                    score_details['numbered_match'] = True
                    logger.debug(f"🔍 NUMBERED MATCH: Exact number '{number}' found in {entity_id}")

                    # Extra boost if base term also matches (proportionally reduced)
                    base_words = set(base_term.split())
                    friendly_words = set(friendly_name.split()) if friendly_name else set()
                    name_by_user_words = set(name_by_user.split()) if name_by_user else set()
                    device_words = set(device_name.split()) if device_name else set()
                    entity_words = set(entity_name.split())

                    all_words = friendly_words | name_by_user_words | device_words | entity_words
                    base_match = len(base_words.intersection(all_words)) / len(base_words) if base_words else 0
                    score += base_match * 0.10  # Reduced proportionally
                    score_details['numbered_base_match'] = base_match
                elif is_group_entity:
                    # When a numbered device is requested, heavily penalize group entities
                    # e.g., "Office light 1" should NOT match "light.office" (group)
                    score *= 0.1  # Reduce to 10% of current score
                    score_details['group_penalty'] = True
                    logger.debug(f"Penalized group entity {entity_id} for numbered query '{query_term}'")
                else:
                    # Entity has a different number or no number - don't give credit
                    # This prevents "Office light 3" from matching "light.office_light_2"
                    score_details['number_mismatch'] = True
                    logger.debug(
                        f"🔍 NUMBERED MISMATCH: Query asks for number '{number}', "
                        f"but {entity_id} doesn't match (friendly: {friendly_name}, device: {device_name})"
                    )

            # Signal 3.5: Attribute-based scoring (is_hue_group detection, etc.) - Weight: 5%
            if self.ha_client:
                try:
                    # Check cache first
                    if entity_id not in self._attribute_cache:
                        # Fetch entity attributes
                        from ..services.entity_attribute_service import EntityAttributeService
                        attribute_service = EntityAttributeService(self.ha_client)
                        enriched = await attribute_service.enrich_entity_with_attributes(entity_id)
                        if enriched:
                            self._attribute_cache[entity_id] = enriched

                    attributes = self._attribute_cache.get(entity_id, {})
                    is_group = attributes.get('is_group', False)

                    # Boost group entities when query suggests a group
                    if 'all' in query_lower or 'group' in query_lower or 'room' in query_lower:
                        if is_group:
                            score += 0.3 * 0.05
                            score_details['group_attribute_match'] = True
                            if i < 3:
                                logger.debug(f"🔍 ATTRIBUTE DEBUG [{i}] {entity_id}: Group boost (query suggests group)")
                    # Penalize group entities when query suggests an individual device
                    elif is_group and numbered_info:
                        score *= 0.7  # Reduce score by 30% for group when numbered device requested
                        score_details['group_attribute_penalty'] = True
                        if i < 3:
                            logger.debug(f"🔍 ATTRIBUTE DEBUG [{i}] {entity_id}: Group penalty (numbered device requested)")
                except Exception as e:
                    logger.debug(f"Error in attribute-based scoring: {e}")

            # Signal 4: Location matching - Weight: 5% (reduced from 10%, but with heavy penalty for mismatches)
            if location_context:
                location_normalized = location_context.replace(' ', '_').replace('-', '_').lower()

                # Check all possible area_id sources (entity area_id + device area_id + suggested_area)
                entity_area = entity.get('area_id', '').lower() if entity.get('area_id') else ''
                device_area = entity.get('device_area_id', '').lower() if entity.get('device_area_id') else ''
                suggested_area = entity.get('suggested_area', '').lower() if entity.get('suggested_area') else ''
                combined_area = f"{entity_area} {device_area} {suggested_area}".strip()

                location_in_area = location_normalized in combined_area if combined_area else False
                location_in_entity_id = location_normalized in entity_id.lower()
                location_in_friendly = location_normalized in friendly_name if friendly_name else False
                location_in_device = location_normalized in device_name if device_name else False

                # Only log detailed location debug for first 3 candidates
                if i < 3:
                    logger.debug(
                        f"🔍 LOCATION DEBUG [{i}] {entity_id}:\n"
                        f"  - location_context: '{location_context}' -> normalized: '{location_normalized}'\n"
                        f"  - entity_area: '{entity_area}' (match: {location_normalized in entity_area if entity_area else False})\n"
                        f"  - device_area: '{device_area}' (match: {location_normalized in device_area if device_area else False})\n"
                        f"  - combined_area: '{combined_area}'"
                    )

                score_before_location = score

                if location_in_area or location_in_friendly or location_in_device or location_in_entity_id:
                    score += 0.5 * 0.05  # Weight reduced to 5%
                    score_details['location_match'] = True
                    if i < 3:  # Only log for top candidates
                        logger.debug(
                            f"🔍 LOCATION DEBUG [{i}] {entity_id}: ✅ Location MATCH "
                            f"(score: {score_before_location:.3f} -> {score:.3f})"
                        )
                else:
                    # CRITICAL: If location is specified but doesn't match, heavily penalize
                    # This prevents "Office light 3" from matching master_bedroom lights
                    score_before_penalty = score
                    score *= 0.05  # Reduce to 5% of current score (very heavy penalty)
                    score_details['location_mismatch_penalty'] = True
                    # Track mismatch for summary logging
                    location_mismatches.append({
                        'entity_id': entity_id,
                        'entity_area': entity_area,
                        'device_area': device_area
                    })

            # Track best match (only log for top 3 candidates)
            if i < 3:
                logger.debug(
                    f"🔍 SCORING DEBUG [{i}] {entity_id}: Final score = {score:.3f}"
                )

            if score > best_score:
                best_score = score
                best_match = entity
                logger.debug(
                    f"🔍 NEW BEST MATCH [{i}] {entity_id}: score = {score:.3f}"
                )

        # Log location mismatch summary
        if location_mismatches and location_context:
            unique_areas = set()
            for mismatch in location_mismatches:
                if mismatch['entity_area']:
                    unique_areas.add(mismatch['entity_area'])
                if mismatch['device_area']:
                    unique_areas.add(mismatch['device_area'])

            logger.debug(
                f"📍 Location mismatch summary: {len(location_mismatches)} entities in wrong location "
                f"('{location_context}' not found in areas: {sorted(unique_areas)})"
            )

        # Confidence calculation: normalize to 0.0-1.0 and consider margin
        confidence = min(best_score, 1.0) if best_match else 0.0

        # Reduce confidence if score is close to other candidates (uncertainty)
        if best_match and len(enriched_entities) > 1:
            # Recalculate scores for all entities to find second-best
            # (simplified - in production, cache scores)
            pass

        logger.info(
            f"🔍 SCORING RESULT: '{query_term}' -> {best_match.get('entity_id') if best_match else 'NONE'} "
            f"(confidence: {confidence:.3f}, best_score: {best_score:.3f})"
        )

        if best_match:
            result_area = best_match.get('area_id') or best_match.get('device_area_id', 'unknown')
            logger.info(
                f"🔍 SCORING RESULT: Matched entity area: {result_area}, "
                f"location_context: {location_context}"
            )

            # Warn if location mismatch but still matched
            if location_context and confidence < 0.3:
                logger.warning(
                    f"🔍 SCORING WARNING: Low confidence ({confidence:.3f}) for '{query_term}' -> "
                    f"{best_match.get('entity_id')} - may be location mismatch issue"
                )

        return best_match, confidence

    def _number_matches_exactly(self, number: str, text: str) -> bool:
        """
        Check if a number appears as an exact match in text (word boundary matching).
        
        This ensures "2" matches "light_2" but not "light_20" or "light_12".
        Uses word boundaries to prevent partial number matches.
        
        Args:
            number: The number to search for (e.g., "2", "3")
            text: The text to search in (entity_id, friendly_name, device_name)
        
        Returns:
            True if number appears as exact match (word boundary), False otherwise
        """
        if not text:
            return False

        # Convert to lowercase for case-insensitive matching
        text_lower = text.lower()
        number_lower = number.lower()

        # Pattern for exact number match in entity IDs with underscores/dots
        # Matches: "light_2", "light_2_2", "light.2", "light 2", but not "light_20" or "light_12"
        # Handles entity IDs like "light.hue_color_downlight_1_6" (number "1" after underscore)
        # Pattern: number preceded by start/underscore/dot/space, followed by underscore/dot/space/end
        pattern = r'(^|[._\s])' + re.escape(number_lower) + r'([._\s]|$)'
        return bool(re.search(pattern, text_lower))

    def _fuzzy_match_score(self, query: str, candidate: str) -> float:
        """
        Calculate fuzzy string similarity score (0.0-1.0) for typo and abbreviation handling.
        
        Uses rapidfuzz WRatio (weighted ratio) which combines multiple algorithms:
        - token_sort_ratio (order-independent)
        - partial_ratio (substring matching)
        - token_set_ratio (set-based matching)
        
        Handles:
        - Typos: "office lite" vs "office light"
        - Abbreviations: "LR light" vs "Living Room Light"
        - Partial matches: "kitchen" vs "Kitchen Light"
        - Word order: "light living room" vs "living room light"
        
        Args:
            query: Query string to match
            candidate: Candidate string to match against
            
        Returns:
            Similarity score between 0.0 (no match) and 1.0 (perfect match)
        """
        from ..utils.fuzzy import fuzzy_score
        
        # Use centralized fuzzy_score utility with WRatio for best accuracy
        # threshold=0.0 to get raw score without filtering
        return fuzzy_score(query, candidate, threshold=0.0)

    def _is_group_entity(self, entity: dict[str, Any]) -> bool:
        """
        Detect if an entity is a group/zone entity (e.g., light.office controls all office lights).
        
        Group entities typically:
        - Don't have device_id (they're virtual/group entities, not physical devices)
        - Have simple names like "light.office", "light.living_room"
        - Don't contain numbers in entity_id
        - May have friendly_name matching area/room name
        
        Args:
            entity: Entity dictionary
            
        Returns:
            True if this appears to be a group entity
        """
        entity_id = entity.get('entity_id', '').lower()
        device_id = entity.get('device_id')
        friendly_name = entity.get('friendly_name', '').lower() if entity.get('friendly_name') else ''

        # Heuristic 1: No device_id often indicates a group/zone entity
        if not device_id:
            # Check if entity_id is simple (just domain + area name, no numbers)
            entity_name_part = entity_id.split('.', 1)[1] if '.' in entity_id else entity_id

            # Common group patterns: light.office, light.living_room, etc.
            # Exclude entities with numbers, underscores with numbers, or complex names
            import re
            has_number = bool(re.search(r'\d', entity_name_part))
            has_complex_naming = '_' in entity_name_part and len(entity_name_part.split('_')) > 2

            if not has_number and not has_complex_naming:
                # Likely a group entity
                logger.debug(f"Detected group entity: {entity_id} (no device_id, simple name)")
                return True

        # Heuristic 2: Entity ID matches common group patterns
        # e.g., light.office, light.living_room (simple area names)
        common_area_names = ['office', 'living_room', 'bedroom', 'kitchen', 'garage', 'bathroom']
        entity_name_part = entity_id.split('.', 1)[1] if '.' in entity_id else entity_id
        if entity_name_part in common_area_names:
            logger.debug(f"Detected group entity: {entity_id} (matches area name pattern)")
            return True

        # Heuristic 3: Friendly name matches entity ID exactly (often groups)
        if friendly_name:
            friendly_normalized = friendly_name.replace(' ', '_').replace('-', '_').lower()
            if friendly_normalized == entity_name_part:
                logger.debug(f"Detected group entity: {entity_id} (friendly_name matches entity_id)")
                return True

        return False
