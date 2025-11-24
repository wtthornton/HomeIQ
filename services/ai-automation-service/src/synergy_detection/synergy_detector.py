"""
Device Synergy Detector

Detects unconnected device pairs that could work together for automation opportunities.

Epic AI-3: Cross-Device Synergy & Contextual Opportunities
Story AI3.1: Device Synergy Detector Foundation
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..config import settings

logger = logging.getLogger(__name__)


# Compatible device relationship mappings
COMPATIBLE_RELATIONSHIPS = {
    # Original patterns
    'motion_to_light': {
        'trigger_domain': 'binary_sensor',
        'trigger_device_class': 'motion',
        'action_domain': 'light',
        'benefit_score': 0.7,  # Convenience
        'complexity': 'low',
        'description': 'Motion-activated lighting'
    },
    'door_to_light': {
        'trigger_domain': 'binary_sensor',
        'trigger_device_class': 'door',
        'action_domain': 'light',
        'benefit_score': 0.6,
        'complexity': 'low',
        'description': 'Door-activated lighting'
    },
    'door_to_lock': {
        'trigger_domain': 'binary_sensor',
        'trigger_device_class': 'door',
        'action_domain': 'lock',
        'benefit_score': 1.0,  # Security
        'complexity': 'medium',
        'description': 'Auto-lock when door closes'
    },
    'temp_to_climate': {
        'trigger_domain': 'sensor',
        'trigger_device_class': 'temperature',
        'action_domain': 'climate',
        'benefit_score': 0.5,  # Comfort
        'complexity': 'medium',
        'description': 'Temperature-based climate control'
    },
    'occupancy_to_light': {
        'trigger_domain': 'binary_sensor',
        'trigger_device_class': 'occupancy',
        'action_domain': 'light',
        'benefit_score': 0.7,
        'complexity': 'low',
        'description': 'Occupancy-based lighting'
    },
    # NEW: Additional patterns (Phase 2)
    'motion_to_climate': {
        'trigger_domain': 'binary_sensor',
        'trigger_device_class': 'motion',
        'action_domain': 'climate',
        'benefit_score': 0.6,
        'complexity': 'medium',
        'description': 'Motion-activated climate control'
    },
    'light_to_media': {
        'trigger_domain': 'light',
        'action_domain': 'media_player',
        'benefit_score': 0.5,
        'complexity': 'low',
        'description': 'Light change triggers media player'
    },
    'temp_to_fan': {
        'trigger_domain': 'sensor',
        'trigger_device_class': 'temperature',
        'action_domain': 'fan',
        'benefit_score': 0.6,
        'complexity': 'medium',
        'description': 'Temperature-based fan control'
    },
    'window_to_climate': {
        'trigger_domain': 'binary_sensor',
        'trigger_device_class': 'window',
        'action_domain': 'climate',
        'benefit_score': 0.8,
        'complexity': 'medium',
        'description': 'Window open triggers climate adjustment'
    },
    'humidity_to_fan': {
        'trigger_domain': 'sensor',
        'trigger_device_class': 'humidity',
        'action_domain': 'fan',
        'benefit_score': 0.6,
        'complexity': 'medium',
        'description': 'Humidity-based fan control'
    },
    'presence_to_light': {
        'trigger_domain': 'device_tracker',
        'action_domain': 'light',
        'benefit_score': 0.7,
        'complexity': 'low',
        'description': 'Presence-based lighting'
    },
    'presence_to_climate': {
        'trigger_domain': 'device_tracker',
        'action_domain': 'climate',
        'benefit_score': 0.6,
        'complexity': 'medium',
        'description': 'Presence-based climate control'
    },
    'light_to_switch': {
        'trigger_domain': 'light',
        'action_domain': 'switch',
        'benefit_score': 0.5,
        'complexity': 'low',
        'description': 'Light triggers switch'
    },
    'door_to_notify': {
        'trigger_domain': 'binary_sensor',
        'trigger_device_class': 'door',
        'action_domain': 'notify',
        'benefit_score': 0.8,  # Security
        'complexity': 'low',
        'description': 'Door open triggers notification'
    },
    'motion_to_switch': {
        'trigger_domain': 'binary_sensor',
        'trigger_device_class': 'motion',
        'action_domain': 'switch',
        'benefit_score': 0.6,
        'complexity': 'low',
        'description': 'Motion-activated switch'
    }
}


class DeviceSynergyDetector:
    """
    Detects cross-device synergy opportunities for automation suggestions.
    
    Analyzes device relationships to find unconnected pairs that could
    work together (e.g., motion sensor + light in same area).
    
    Story AI3.1: Device Synergy Detector Foundation
    """

    def __init__(
        self,
        data_api_client,
        ha_client=None,
        influxdb_client=None,
        min_confidence: float = 0.7,
        same_area_required: bool = True,
        enrichment_fetcher=None
    ):
        """
        Initialize synergy detector.
        
        Args:
            data_api_client: Client for querying devices from data-api
            ha_client: Optional HA client for checking existing automations
            influxdb_client: Optional InfluxDB client for usage statistics (Story AI3.2)
            min_confidence: Minimum confidence threshold (0.0-1.0)
            same_area_required: Whether devices must be in same area
        """
        self.data_api = data_api_client
        self.ha_client = ha_client
        self.influxdb_client = influxdb_client
        self.min_confidence = min_confidence
        self.same_area_required = same_area_required
        self.enrichment_fetcher = enrichment_fetcher  # 2025 Enhancement: Multi-modal context

        # Cache for performance (with TTL)
        self._device_cache = None
        self._device_cache_timestamp = None
        self._entity_cache = None
        self._entity_cache_timestamp = None
        self._automation_cache = None
        self._cache_ttl = timedelta(hours=6)  # 6-hour cache TTL

        # Initialize synergy cache (Phase 1)
        try:
            from .synergy_cache import SynergyCache
            self.synergy_cache = SynergyCache()
            logger.info("SynergyCache enabled for improved performance")
        except Exception as e:
            logger.warning(f"Failed to initialize SynergyCache: {e}, continuing without cache")
            self.synergy_cache = None

        # Initialize advanced analyzer if InfluxDB available (Story AI3.2)
        self.pair_analyzer = None
        if influxdb_client:
            from .device_pair_analyzer import DevicePairAnalyzer
            self.pair_analyzer = DevicePairAnalyzer(influxdb_client)
            logger.info("DevicePairAnalyzer enabled for advanced impact scoring")

        logger.info(
            f"DeviceSynergyDetector initialized: "
            f"min_confidence={min_confidence}, same_area_required={same_area_required}"
        )

    async def detect_synergies(self) -> list[dict]:
        """
        Detect all synergy opportunities.
        
        Returns:
            List of synergy opportunity dictionaries
        """
        start_time = datetime.now(timezone.utc)
        logger.info("🔗 Starting synergy detection...")
        logger.info(f"   → Parameters: min_confidence={self.min_confidence}, same_area_required={self.same_area_required}")

        try:
            # Step 1: Load device data
            logger.info("   → Step 1: Loading device data...")
            devices = await self._get_devices()
            entities = await self._get_entities()

            if not devices or not entities:
                logger.warning("⚠️ No devices/entities found, skipping synergy detection")
                logger.warning(f"   → Devices: {len(devices) if devices else 0}, Entities: {len(entities) if entities else 0}")
                return []

            logger.info(f"📊 Loaded {len(devices)} devices, {len(entities)} entities")

            if getattr(settings, "enable_pdl_workflows", False):
                try:
                    from ..pdl.runtime import PDLExecutionError, PDLInterpreter

                    script_path = Path(__file__).resolve().parent.parent / "pdl" / "scripts" / "synergy_guardrails.yaml"
                    interpreter = PDLInterpreter.from_file(script_path, logger)
                    await interpreter.run(
                        {
                            "requested_depth": 4,  # Current detector supports up to 4-device chains
                            "max_supported_depth": 4,
                            "candidate_device_count": len(devices),
                            "max_device_capacity": 150,  # Single-home practical ceiling
                        }
                    )
                except PDLExecutionError as pdl_exc:
                    logger.error("❌ Synergy guardrail violation: %s", pdl_exc)
                    return []
                except Exception as pdl_exc:  # pragma: no cover - defensive logging
                    logger.warning(
                        "⚠️ Failed to execute synergy guardrail PDL script (%s). Continuing with standard workflow.",
                        pdl_exc,
                        exc_info=True,
                    )

            # Step 2: Detect device pairs by area
            logger.info("   → Step 2: Finding device pairs...")
            device_pairs = self._find_device_pairs_by_area(devices, entities)
            logger.info(f"🔍 Found {len(device_pairs)} potential device pairs")
            if device_pairs:
                logger.info(f"   → Sample pairs: {[(p.get('domain1', '?'), p.get('domain2', '?'), p.get('area', '?')) for p in device_pairs[:3]]}")

            # Step 3: Filter for compatible relationships
            logger.info("   → Step 3: Filtering for compatible relationships...")
            compatible_pairs = self._filter_compatible_pairs(device_pairs)
            logger.info(f"✅ Found {len(compatible_pairs)} compatible pairs")
            if compatible_pairs:
                logger.info(f"   → Sample compatible: {[p.get('relationship_type', '?') for p in compatible_pairs[:3]]}")

            # Step 4: Check for existing automations
            synergies = await self._filter_existing_automations(compatible_pairs)
            logger.info(f"🆕 Found {len(synergies)} new synergy opportunities (no existing automation)")

            # Step 5: Rank opportunities (with advanced scoring if available)
            # 2025 Enhancement: Get enrichment fetcher for multi-modal context
            enrichment_fetcher = None
            if hasattr(self, 'enrichment_fetcher'):
                enrichment_fetcher = self.enrichment_fetcher
            
            if self.pair_analyzer:
                ranked_synergies = await self._rank_opportunities_advanced(
                    synergies, entities, enrichment_fetcher=enrichment_fetcher
                )
            else:
                ranked_synergies = self._rank_opportunities(synergies)

            # Step 6: Filter by confidence threshold
            pairwise_synergies = [
                s for s in ranked_synergies
                if s['confidence'] >= self.min_confidence
            ]

            # Step 7: Detect 3-device chains (Phase 3)
            logger.info("   → Step 7: Detecting 3-device chains...")
            chains_3 = await self._detect_3_device_chains(pairwise_synergies, devices, entities)
            logger.info(f"🔗 Found {len(chains_3)} 3-device chains")

            # Step 8: Detect 4-device chains (Epic AI-4: N-Level Synergy)
            logger.info("   → Step 8: Detecting 4-device chains...")
            chains_4 = await self._detect_4_device_chains(chains_3, pairwise_synergies, devices, entities)
            logger.info(f"🔗 Found {len(chains_4)} 4-device chains")

            # Combine pairwise, 3-level, and 4-level chains
            final_synergies = pairwise_synergies + chains_3 + chains_4

            # Re-sort all synergies by impact score
            final_synergies.sort(key=lambda x: x.get('impact_score', 0), reverse=True)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            logger.info(
                f"✅ Synergy detection complete in {duration:.1f}s\n"
                f"   Pairwise opportunities: {len(pairwise_synergies)}\n"
                f"   3-device chains: {len(chains_3)}\n"
                f"   4-device chains: {len(chains_4)}\n"
                f"   Total opportunities: {len(final_synergies)}\n"
                f"   Above confidence threshold ({self.min_confidence}): {len(final_synergies)}"
            )

            # Log top 3 opportunities
            if final_synergies:
                logger.info("🏆 Top 3 synergy opportunities:")
                for i, synergy in enumerate(final_synergies[:3], 1):
                    synergy_type = synergy.get('synergy_type', 'device_pair')
                    if synergy_type == 'device_chain':
                        chain_path = synergy.get('chain_path', '?')
                        depth = len(synergy.get('devices', []))
                        logger.info(
                            f"   {i}. {depth}-chain: {chain_path} "
                            f"(impact: {synergy['impact_score']:.2f}, confidence: {synergy['confidence']:.2f})"
                        )
                    else:
                        logger.info(
                            f"   {i}. {synergy['relationship']} in {synergy.get('area', 'unknown')} "
                            f"(impact: {synergy['impact_score']:.2f}, confidence: {synergy['confidence']:.2f})"
                        )

            return final_synergies

        except Exception as e:
            logger.error(f"❌ Synergy detection failed: {e}", exc_info=True)
            return []

    async def _get_devices(self) -> list[dict]:
        """Fetch all devices from data-api with caching (6-hour TTL)."""
        # Check cache validity
        if (self._device_cache is not None and 
            self._device_cache_timestamp is not None and
            datetime.now(timezone.utc) - self._device_cache_timestamp < self._cache_ttl):
            logger.info("✅ Using cached device data")
            return self._device_cache

        try:
            logger.info("📥 Loading device data from data-api...")
            self._device_cache = await self.data_api.fetch_devices()
            self._device_cache_timestamp = datetime.now(timezone.utc)
            logger.info(f"✅ Loaded {len(self._device_cache)} devices (cached for 6 hours)")
            return self._device_cache
        except Exception as e:
            logger.error(f"Failed to fetch devices: {e}")
            return []

    async def _get_entities(self) -> list[dict]:
        """Fetch all entities from data-api with caching (6-hour TTL)."""
        # Check cache validity
        if (self._entity_cache is not None and 
            self._entity_cache_timestamp is not None and
            datetime.now(timezone.utc) - self._entity_cache_timestamp < self._cache_ttl):
            logger.info("✅ Using cached entity data")
            return self._entity_cache

        try:
            logger.info("📥 Loading entity data from data-api...")
            self._entity_cache = await self.data_api.fetch_entities()
            self._entity_cache_timestamp = datetime.now(timezone.utc)
            logger.info(f"✅ Loaded {len(self._entity_cache)} entities (cached for 6 hours)")
            return self._entity_cache
        except Exception as e:
            logger.error(f"Failed to fetch entities: {e}")
            return []

    def _find_device_pairs_by_area(
        self,
        devices: list[dict],
        entities: list[dict]
    ) -> list[dict]:
        """
        Find device pairs in the same area, or without areas.
        
        Args:
            devices: List of devices from data-api
            entities: List of entities from data-api
        
        Returns:
            List of potential device pairs
        """
        # Group entities by area
        entities_by_area = {}
        entities_without_area = []
        for entity in entities:
            area = entity.get('area_id')
            if area:
                if area not in entities_by_area:
                    entities_by_area[area] = []
                entities_by_area[area].append(entity)
            else:
                entities_without_area.append(entity)

        pairs = []

        # Find pairs within each area
        for area, area_entities in entities_by_area.items():
            for i, entity1 in enumerate(area_entities):
                for entity2 in area_entities[i+1:]:
                    # Don't pair entity with itself
                    if entity1['entity_id'] == entity2['entity_id']:
                        continue

                    domain1 = entity1['entity_id'].split('.')[0]
                    domain2 = entity2['entity_id'].split('.')[0]

                    # Create potential pair
                    pairs.append({
                        'entity1': entity1,
                        'entity2': entity2,
                        'area': area,
                        'domain1': domain1,
                        'domain2': domain2
                    })

        # Also pair entities without areas (cross-area or no-area synergies)
        # This allows finding synergies even when area data is missing
        # OPTIMIZATION: Only pair entities with compatible domains to reduce computation
        if entities_without_area:
            logger.info(f"   → Found {len(entities_without_area)} entities without area, pairing compatible domains")
            # Get compatible domain pairs from relationship configs
            compatible_domain_pairs = set()
            for rel_config in COMPATIBLE_RELATIONSHIPS.values():
                trigger_domain = rel_config['trigger_domain']
                action_domain = rel_config['action_domain']
                compatible_domain_pairs.add((trigger_domain, action_domain))
                compatible_domain_pairs.add((action_domain, trigger_domain))  # Bidirectional

            # Group entities by domain for efficient pairing
            entities_by_domain = {}
            for entity in entities_without_area:
                domain = entity['entity_id'].split('.')[0]
                if domain not in entities_by_domain:
                    entities_by_domain[domain] = []
                entities_by_domain[domain].append(entity)

            # Only create pairs for compatible domain combinations
            processed_pairs = 0
            for domain1, entities1 in entities_by_domain.items():
                for domain2, entities2 in entities_by_domain.items():
                    # Check if this domain pair is compatible
                    if (domain1, domain2) not in compatible_domain_pairs:
                        continue

                    # Create pairs between these domains
                    for entity1 in entities1:
                        for entity2 in entities2:
                            # Don't pair entity with itself
                            if entity1['entity_id'] == entity2['entity_id']:
                                continue

                            pairs.append({
                                'entity1': entity1,
                                'entity2': entity2,
                                'area': entity1.get('area_id') or entity2.get('area_id') or None,
                                'domain1': domain1,
                                'domain2': domain2
                            })
                            processed_pairs += 1

            logger.info(f"   → Created {processed_pairs} pairs from entities without area (filtered by compatible domains)")

        return pairs

    def _filter_compatible_pairs(self, pairs: list[dict]) -> list[dict]:
        """
        Filter device pairs for compatible relationships.
        
        Args:
            pairs: List of potential device pairs
        
        Returns:
            List of compatible pairs with relationship metadata
        """
        compatible = []

        for pair in pairs:
            entity1 = pair['entity1']
            entity2 = pair['entity2']
            domain1 = pair['domain1']
            domain2 = pair['domain2']

            # Check each relationship type
            for rel_type, rel_config in COMPATIBLE_RELATIONSHIPS.items():
                trigger_domain = rel_config['trigger_domain']
                action_domain = rel_config['action_domain']

                # Check if pair matches this relationship (either direction)
                match = None
                if domain1 == trigger_domain and domain2 == action_domain:
                    # Check device class if required
                    if 'trigger_device_class' in rel_config:
                        device_class1 = entity1.get('device_class', entity1.get('original_device_class'))
                        if device_class1 == rel_config['trigger_device_class']:
                            match = (entity1, entity2)
                    else:
                        match = (entity1, entity2)

                elif domain2 == trigger_domain and domain1 == action_domain:
                    # Reverse direction
                    if 'trigger_device_class' in rel_config:
                        device_class2 = entity2.get('device_class', entity2.get('original_device_class'))
                        if device_class2 == rel_config['trigger_device_class']:
                            match = (entity2, entity1)
                    else:
                        match = (entity2, entity1)

                if match:
                    trigger_entity, action_entity = match
                    compatible.append({
                        'trigger_entity': trigger_entity['entity_id'],
                        'trigger_name': trigger_entity.get('friendly_name', trigger_entity['entity_id']),
                        'action_entity': action_entity['entity_id'],
                        'action_name': action_entity.get('friendly_name', action_entity['entity_id']),
                        'area': pair['area'],
                        'relationship_type': rel_type,
                        'relationship_config': rel_config
                    })

        return compatible

    async def _filter_existing_automations(
        self,
        compatible_pairs: list[dict]
    ) -> list[dict]:
        """
        Filter out pairs that already have automations.
        
        Stories:
        - AI3.3: Unconnected Relationship Analysis
        - AI4.3: Relationship Checker (Enhanced with automation parser)
        
        Args:
            compatible_pairs: List of compatible device pairs
        
        Returns:
            List of pairs without existing automations
        """
        # If no HA client, assume no existing automations (all pairs are new)
        if not self.ha_client:
            logger.debug("No HA client available, assuming all pairs are new opportunities")
            return compatible_pairs

        try:
            # Story AI4.3: Use new automation parser for efficient filtering
            from ..clients.automation_parser import AutomationParser

            # Get and parse automations
            logger.info("   → Fetching automation configurations from HA...")
            automations = await self.ha_client.get_automations()

            if not automations:
                logger.info("   → No existing automations found, all pairs are new")
                return compatible_pairs

            # Parse automations and build relationship index
            parser = AutomationParser()
            count = parser.parse_automations(automations)
            logger.info(f"   → Parsed {count} automations, indexed {parser.get_entity_pair_count()} entity pairs")

            # Filter out pairs that already have automations (O(1) lookup per pair!)
            # Story AI4.3: Efficient filtering using hash-based lookup (Context7 best practice)
            new_pairs = []
            filtered_pairs = []

            for pair in compatible_pairs:
                trigger_entity = pair.get('trigger_entity')
                action_entity = pair.get('action_entity')

                # O(1) hash table lookup (Context7: sets provide O(1) membership testing)
                if parser.has_relationship(trigger_entity, action_entity):
                    # Get automation details for logging
                    relationships = parser.get_relationships_for_pair(trigger_entity, action_entity)
                    automation_names = [rel.automation_alias for rel in relationships]
                    logger.debug(
                        f"   ⏭️  Filtering: {trigger_entity} → {action_entity} "
                        f"(already automated by: {', '.join(automation_names)})"
                    )
                    filtered_pairs.append({
                        'trigger': trigger_entity,
                        'action': action_entity,
                        'existing_automations': automation_names
                    })
                else:
                    new_pairs.append(pair)

            filtered_count = len(filtered_pairs)
            logger.info(
                f"✅ Filtered {filtered_count} pairs with existing automations, "
                f"{len(new_pairs)} new opportunities remain"
            )

            if filtered_pairs and len(filtered_pairs) <= 5:
                filtered_pair_names = [f"{p['trigger']} → {p['action']}" for p in filtered_pairs]
                logger.info(f"   → Filtered pairs: {filtered_pair_names}")

            return new_pairs

        except Exception as e:
            logger.warning(f"⚠️ Automation checking failed: {e}, returning all pairs")
            logger.debug(f"   → Error details: {e}", exc_info=True)
            return compatible_pairs

    def _rank_opportunities(self, synergies: list[dict]) -> list[dict]:
        """
        Rank and score synergy opportunities.
        
        Args:
            synergies: List of synergy opportunities
        
        Returns:
            List of ranked opportunities with scores
        """
        scored_synergies = []

        for synergy in synergies:
            rel_config = synergy['relationship_config']

            # Calculate scores
            benefit_score = rel_config['benefit_score']
            complexity = rel_config['complexity']

            # Complexity penalty
            complexity_penalty = {
                'low': 0.0,
                'medium': 0.1,
                'high': 0.3
            }.get(complexity, 0.1)

            # Impact score (benefit - complexity penalty)
            impact_score = benefit_score * (1 - complexity_penalty)

            # Confidence (for same-area matches, high confidence)
            confidence = 0.9 if synergy.get('area') else 0.7

            # Add synergy_id and scores
            scored_synergies.append({
                'synergy_id': str(uuid.uuid4()),
                'synergy_type': 'device_pair',
                'devices': [synergy['trigger_entity'], synergy['action_entity']],
                'trigger_entity': synergy['trigger_entity'],
                'trigger_name': synergy['trigger_name'],
                'action_entity': synergy['action_entity'],
                'action_name': synergy['action_name'],
                'relationship': synergy['relationship_type'],
                'area': synergy.get('area', 'unknown'),
                'impact_score': round(impact_score, 2),
                'complexity': complexity,
                'confidence': confidence,
                'rationale': f"{rel_config['description']} - {synergy['trigger_name']} and {synergy['action_name']} in {synergy.get('area', 'same area')} with no automation",
                # Epic AI-4: N-level synergy fields
                'synergy_depth': 2,
                'chain_devices': [synergy['trigger_entity'], synergy['action_entity']]
            })

        # Sort by impact_score descending
        scored_synergies.sort(key=lambda x: x['impact_score'], reverse=True)

        return scored_synergies

    async def _rank_opportunities_advanced(
        self,
        synergies: list[dict],
        entities: list[dict],
        enrichment_fetcher=None
    ) -> list[dict]:
        """
        Rank opportunities with advanced impact scoring using usage data.
        
        Story AI3.2: Same-Area Device Pair Detection
        2025 Enhancement: Multi-modal context integration
        
        Args:
            synergies: List of synergy opportunities
            entities: List of entities for area lookup
            enrichment_fetcher: Optional enrichment context fetcher for multi-modal scoring
        
        Returns:
            List of ranked synergies with advanced scores
        """
        logger.info("📊 Using advanced impact scoring with usage data...")

        # Group synergies by area for area-specific normalization
        synergies_by_area = {}
        for s in synergies:
            area = s.get('area', 'unknown')
            if area not in synergies_by_area:
                synergies_by_area[area] = []
            synergies_by_area[area].append(s)

        scored_synergies = []

        # Calculate scores with area context for normalization
        for synergy in synergies:
            try:
                area = synergy.get('area', 'unknown')
                area_synergies = synergies_by_area.get(area, [synergy])

                # Get advanced impact score from DevicePairAnalyzer with area context
                # 2025 Enhancement: Include enrichment fetcher for multi-modal context
                advanced_impact = await self.pair_analyzer.calculate_advanced_impact_score(
                    synergy,
                    entities,
                    all_synergies_in_area=area_synergies if len(area_synergies) > 1 else None,
                    enrichment_fetcher=enrichment_fetcher
                )

                # Create scored synergy with advanced impact
                scored_synergy = synergy.copy()
                scored_synergy['impact_score'] = advanced_impact
                scored_synergies.append(scored_synergy)

            except Exception as e:
                logger.warning(f"Failed advanced scoring for synergy, using basic score: {e}")
                # Ensure synergy has confidence if advanced scoring failed
                if 'confidence' not in synergy:
                    synergy['confidence'] = 0.9 if synergy.get('area') else 0.7
                # Ensure synergy has impact_score if advanced scoring failed
                if 'impact_score' not in synergy:
                    rel_config = synergy.get('relationship_config', {})
                    if isinstance(rel_config, dict):
                        benefit_score = rel_config.get('benefit_score', 0.7)
                        complexity = rel_config.get('complexity', 'medium')
                        complexity_penalty = {'low': 0.0, 'medium': 0.1, 'high': 0.3}.get(complexity, 0.1)
                        synergy['impact_score'] = benefit_score * (1 - complexity_penalty)
                    else:
                        synergy['impact_score'] = 0.7
                scored_synergies.append(synergy)

        # Sort by advanced impact score descending
        scored_synergies.sort(key=lambda x: x['impact_score'], reverse=True)

        if scored_synergies:
            top_score = scored_synergies[0]['impact_score']
            # Log score distribution for debugging
            if len(scored_synergies) > 1:
                unique_scores = len(set(round(s['impact_score'], 4) for s in scored_synergies))
                score_range = max(s['impact_score'] for s in scored_synergies) - min(s['impact_score'] for s in scored_synergies)
                logger.info(
                    f"✅ Advanced scoring complete: top impact = {top_score:.4f}, "
                    f"unique scores (4 dec) = {unique_scores}/{len(scored_synergies)}, "
                    f"score range = {score_range:.4f}"
                )
            else:
                logger.info(f"✅ Advanced scoring complete: top impact = {top_score:.4f}")
        else:
            logger.info("No synergies to score")

        return scored_synergies

    async def _detect_3_device_chains(
        self,
        pairwise_synergies: list[dict],
        devices: list[dict],
        entities: list[dict]
    ) -> list[dict]:
        """
        Detect 3-device chains by connecting pairs.
        
        Simple approach: For each pair A→B, find pairs B→C.
        Result: Chains A→B→C
        
        Phase 3: Simple 3-device chain detection (no graph DB needed)
        
        Args:
            pairwise_synergies: List of 2-device synergy opportunities
            devices: List of devices
            entities: List of entities
        
        Returns:
            List of 3-device chain synergies
        """
        # Limit chain detection to prevent timeout with large datasets
        MAX_CHAINS = 100  # Maximum chains to detect
        MAX_PAIRWISE_FOR_CHAINS = 500  # Skip chain detection if too many pairs

        if len(pairwise_synergies) > MAX_PAIRWISE_FOR_CHAINS:
            logger.info(f"   → Skipping 3-device chain detection: {len(pairwise_synergies)} pairs (limit: {MAX_PAIRWISE_FOR_CHAINS})")
            return []

        chains = []

        # Build lookup: action_device -> list of pairs where it's the action
        action_lookup = {}
        for synergy in pairwise_synergies:
            action_entity = synergy.get('action_entity')
            if action_entity:
                if action_entity not in action_lookup:
                    action_lookup[action_entity] = []
                action_lookup[action_entity].append(synergy)

        # Find chains: For each pair A→B, find pairs B→C
        # Limit to prevent exponential growth
        processed_count = 0
        for synergy in pairwise_synergies:
            # Early exit if we've found enough chains
            if len(chains) >= MAX_CHAINS:
                logger.info(f"   → Reached chain limit ({MAX_CHAINS}), stopping chain detection")
                break
            trigger_entity = synergy.get('trigger_entity')
            action_entity = synergy.get('action_entity')

            # Find pairs where action_entity is the trigger (B→C)
            if action_entity in action_lookup:
                for next_synergy in action_lookup[action_entity]:
                    next_action = next_synergy.get('action_entity')

                    # Skip if same device (A→B→A is not useful)
                    if next_action == trigger_entity:
                        continue

                    # Skip if devices not in same area (unless beneficial)
                    if synergy.get('area') != next_synergy.get('area'):
                        # Only allow cross-area if it makes sense
                        if not self._is_valid_cross_area_chain(trigger_entity, action_entity, next_action, entities):
                            continue

                    # Check cache if available
                    chain_key = f"chain:{trigger_entity}:{action_entity}:{next_action}"
                    if self.synergy_cache:
                        cached = await self.synergy_cache.get_chain_result(chain_key)
                        if cached:
                            chains.append(cached)
                            continue

                    # Create chain synergy
                    chain = {
                        'synergy_id': str(uuid.uuid4()),
                        'synergy_type': 'device_chain',
                        'devices': [trigger_entity, action_entity, next_action],
                        'chain_path': f"{trigger_entity} → {action_entity} → {next_action}",
                        'trigger_entity': trigger_entity,
                        'action_entity': next_action,
                        'impact_score': round((synergy.get('impact_score', 0) +
                                             next_synergy.get('impact_score', 0)) / 2, 2),
                        'confidence': min(synergy.get('confidence', 0.7),
                                        next_synergy.get('confidence', 0.7)),
                        'complexity': 'medium',
                        'area': synergy.get('area'),
                        'rationale': f"Chain: {synergy.get('rationale', '')} then {next_synergy.get('rationale', '')}",
                        # Epic AI-4: N-level synergy fields
                        'synergy_depth': 3,
                        'chain_devices': [trigger_entity, action_entity, next_action]
                    }

                    # Cache if available
                    if self.synergy_cache:
                        try:
                            await self.synergy_cache.set_chain_result(chain_key, chain)
                        except Exception as e:
                            logger.debug(f"Cache set failed for chain {chain_key}: {e}")

                    chains.append(chain)

                    # Early exit if we've found enough chains
                    if len(chains) >= MAX_CHAINS:
                        logger.info(f"   → Reached chain limit ({MAX_CHAINS}), stopping chain detection")
                        break

                # Early exit if we've found enough chains
                if len(chains) >= MAX_CHAINS:
                    break

            processed_count += 1
            # Progress logging for large datasets
            if processed_count % 100 == 0:
                logger.debug(f"   → Processed {processed_count}/{len(pairwise_synergies)} pairs for chains, found {len(chains)} chains")

        return chains

    async def _detect_4_device_chains(
        self,
        three_level_chains: list[dict],
        pairwise_synergies: list[dict],
        devices: list[dict],
        entities: list[dict]
    ) -> list[dict]:
        """
        Detect 4-device chains by extending 3-level chains.
        
        Simple approach: For each 3-chain A→B→C, find pairs C→D.
        Result: Chains A→B→C→D
        
        Epic AI-4: N-Level Synergy Detection (4-level implementation)
        Single home focus: Simple extension, no over-engineering
        
        Args:
            three_level_chains: List of 3-device chain synergies
            pairwise_synergies: List of 2-device synergy opportunities
            devices: List of devices
            entities: List of entities
        
        Returns:
            List of 4-device chain synergies
        """
        # Reasonable limits for single home (20-50 devices)
        MAX_CHAINS = 50  # Maximum 4-level chains to detect
        MAX_3CHAINS_FOR_4 = 200  # Skip 4-level detection if too many 3-chains

        if len(three_level_chains) > MAX_3CHAINS_FOR_4:
            logger.info(
                f"   → Skipping 4-device chain detection: {len(three_level_chains)} 3-chains "
                f"(limit: {MAX_3CHAINS_FOR_4})"
            )
            return []

        if not three_level_chains:
            logger.debug("   → No 3-level chains to extend to 4-level")
            return []

        chains = []

        # Build lookup: action_device -> list of pairs where it's the action
        action_lookup = {}
        for synergy in pairwise_synergies:
            action_entity = synergy.get('action_entity')
            if action_entity:
                if action_entity not in action_lookup:
                    action_lookup[action_entity] = []
                action_lookup[action_entity].append(synergy)

        # For each 3-chain A→B→C, find pairs C→D
        processed_count = 0
        for three_chain in three_level_chains:
            # Early exit if we've found enough chains
            if len(chains) >= MAX_CHAINS:
                logger.info(f"   → Reached 4-level chain limit ({MAX_CHAINS}), stopping detection")
                break

            chain_devices = three_chain.get('devices', [])
            if len(chain_devices) != 3:
                continue

            a, b, c = chain_devices

            # Find pairs where C is the trigger (C→D)
            if c in action_lookup:
                for next_synergy in action_lookup[c]:
                    d = next_synergy.get('action_entity')

                    # Skip if D already in chain (prevent circular paths)
                    if d in chain_devices:
                        continue

                    # Skip if same device (A→B→C→A is not useful)
                    if d == a:
                        continue

                    # Skip if devices not in same area (unless beneficial)
                    if three_chain.get('area') != next_synergy.get('area'):
                        # Use same cross-area validation as 3-level chains
                        if not self._is_valid_cross_area_chain(a, b, c, entities):
                            continue
                        # Also check if adding D makes sense
                        if not self._is_valid_cross_area_chain(b, c, d, entities):
                            continue

                    # Check cache if available
                    chain_key = f"chain4:{a}:{b}:{c}:{d}"
                    if self.synergy_cache:
                        cached = await self.synergy_cache.get_chain_result(chain_key)
                        if cached:
                            chains.append(cached)
                            continue

                    # Create 4-chain synergy
                    chain = {
                        'synergy_id': str(uuid.uuid4()),
                        'synergy_type': 'device_chain',
                        'devices': [a, b, c, d],
                        'chain_path': f"{a} → {b} → {c} → {d}",
                        'trigger_entity': a,
                        'action_entity': d,
                        'impact_score': round((
                            three_chain.get('impact_score', 0) +
                            next_synergy.get('impact_score', 0)
                        ) / 2, 2),
                        'confidence': min(
                            three_chain.get('confidence', 0.7),
                            next_synergy.get('confidence', 0.7)
                        ),
                        'complexity': 'medium',
                        'area': three_chain.get('area'),
                        'rationale': (
                            f"4-device chain: {three_chain.get('rationale', '')} "
                            f"then {next_synergy.get('rationale', '')}"
                        ),
                        # Epic AI-4: N-level synergy fields
                        'synergy_depth': 4,
                        'chain_devices': [a, b, c, d]
                    }

                    # Cache if available
                    if self.synergy_cache:
                        try:
                            await self.synergy_cache.set_chain_result(chain_key, chain)
                        except Exception as e:
                            logger.debug(f"Cache set failed for 4-chain {chain_key}: {e}")

                    chains.append(chain)

                    # Early exit if we've found enough chains
                    if len(chains) >= MAX_CHAINS:
                        logger.info(f"   → Reached 4-level chain limit ({MAX_CHAINS}), stopping detection")
                        break

                # Early exit if we've found enough chains
                if len(chains) >= MAX_CHAINS:
                    break

            processed_count += 1
            # Progress logging for large datasets
            if processed_count % 50 == 0:
                logger.debug(
                    f"   → Processed {processed_count}/{len(three_level_chains)} 3-chains for 4-level, "
                    f"found {len(chains)} 4-chains"
                )

        return chains

    def _is_valid_cross_area_chain(
        self,
        device1: str,
        device2: str,
        device3: str,
        entities: list[dict]
    ) -> bool:
        """
        Check if cross-area chain makes sense (simple heuristic).
        
        For now, allow cross-area chains (can be enhanced later).
        """
        # Simple rule: Allow cross-area chains (common pattern like bedroom → hallway → kitchen)
        # Could be enhanced with adjacency checks, but keeping it simple for now
        return True

    def clear_cache(self):
        """Clear cached data (useful for testing)."""
        self._device_cache = None
        self._entity_cache = None
        self._automation_cache = None

        if self.pair_analyzer:
            self.pair_analyzer.clear_cache()

        # Note: synergy_cache.clear() is async, but clear_cache is sync
        # This is fine - cache will be cleared on next access or service restart

        logger.debug("Synergy detector cache cleared")

