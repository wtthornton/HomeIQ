"""
Multi-Model Entity Extractor for Commercial NUC Deployment
Implements hybrid approach: NER → OpenAI → Pattern Matching
"""

import logging
import re
from functools import lru_cache
from typing import Any

from openai import AsyncOpenAI
from spacy import load as spacy_load
from transformers import pipeline

from ..clients.device_intelligence_client import DeviceIntelligenceClient
from ..trigger_analysis.trigger_condition_analyzer import TriggerConditionAnalyzer
from ..trigger_analysis.trigger_device_discovery import TriggerDeviceDiscovery
from .pattern_extractor import extract_entities_from_query

logger = logging.getLogger(__name__)

class MultiModelEntityExtractor:
    """
    Hybrid entity extraction using multiple models for optimal performance.
    
    Strategy:
    1. Primary: Hugging Face NER (90% of queries, FREE, 50ms)
    2. Fallback: OpenAI GPT-4o-mini (10% of queries, $0.0004, 1-2s)
    3. Emergency: Pattern matching (0% of queries, FREE, <1ms)
    """

    def __init__(self,
                 openai_api_key: str,
                 device_intelligence_client: DeviceIntelligenceClient | None = None,
                 ner_model: str = "dslim/bert-base-NER",
                 openai_model: str = "gpt-5.1"):
        """
        Initialize multi-model entity extractor.
        
        Args:
            openai_api_key: OpenAI API key for complex queries
            device_intelligence_client: Optional device intelligence client
            ner_model: Hugging Face NER model name
            openai_model: OpenAI model name
        """
        self.device_intel_client = device_intelligence_client

        # Initialize models
        self._ner_pipeline = None
        self._openai_client = None
        self._spacy_model = None

        # Configuration
        self.ner_model = ner_model
        self.openai_model = openai_model
        self.openai_api_key = openai_api_key

        # Initialize trigger analysis components
        self.trigger_condition_analyzer = None
        self.trigger_device_discovery = None
        if device_intelligence_client:
            self.trigger_condition_analyzer = TriggerConditionAnalyzer()
            self.trigger_device_discovery = TriggerDeviceDiscovery(device_intelligence_client)

        # Performance tracking
        self.stats = {
            'total_queries': 0,
            'ner_success': 0,
            'openai_success': 0,
            'pattern_fallback': 0,
            'avg_processing_time': 0.0,
            'trigger_devices_discovered': 0
        }

        # Call pattern tracking
        self.call_stats = {
            'direct_calls': 0,
            'orchestrated_calls': 0,  # Reserved for future orchestrated workflows
            'avg_direct_latency': 0.0,
            'avg_orch_latency': 0.0,
            'total_direct_time': 0.0,
            'total_orch_time': 0.0
        }

        logger.info(f"MultiModelEntityExtractor initialized with NER model: {ner_model}")

    def _get_ner_pipeline(self):
        """Lazy load NER pipeline"""
        if self._ner_pipeline is None:
            try:
                logger.info(f"Loading NER model: {self.ner_model}")
                self._ner_pipeline = pipeline("ner", model=self.ner_model)
                logger.info("NER pipeline loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load NER model: {e}")
                self._ner_pipeline = None
        return self._ner_pipeline

    def _get_openai_client(self):
        """Lazy load OpenAI client"""
        if self._openai_client is None:
            try:
                self._openai_client = AsyncOpenAI(api_key=self.openai_api_key)
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self._openai_client = None
        return self._openai_client

    def _get_spacy_model(self):
        """Lazy load spaCy model as emergency fallback"""
        if self._spacy_model is None:
            try:
                self._spacy_model = spacy_load("en_core_web_sm")
                logger.info("spaCy model loaded")
            except Exception as e:
                logger.error(f"Failed to load spaCy model: {e}")
                self._spacy_model = None
        return self._spacy_model

    def _is_high_confidence(self, entities: list[dict]) -> bool:
        """Check if NER results are high confidence"""
        if not entities:
            return False

        # Check if we have entities with high scores
        high_confidence_entities = [e for e in entities if e.get('score', 0) > 0.8]
        return len(high_confidence_entities) > 0

    def _is_complex_query(self, query: str) -> bool:
        """Determine if query is complex and needs OpenAI"""
        complex_indicators = [
            # Ambiguous references
            r'\b(the|this|that|my|our)\s+(thing|stuff|device|light|sensor)\b',
            # Complex relationships
            r'\b(when|if|unless|after|before)\s+',
            # Multiple actions
            r'\b(and|then|also|plus)\s+',
            # Conditional logic
            r'\b(unless|except|but|however)\s+',
            # Vague descriptions
            r'\b(something|anything|everything|nothing)\b'
        ]

        query_lower = query.lower()
        complexity_score = sum(1 for pattern in complex_indicators
                             if re.search(pattern, query_lower))

        # Also consider query length and complexity
        word_count = len(query.split())
        has_question = '?' in query

        return complexity_score >= 2 or (word_count > 15 and has_question)

    @lru_cache(maxsize=1000)
    def _cached_ner_extraction(self, query: str) -> list[dict]:
        """Cached NER extraction for performance"""
        ner_pipeline = self._get_ner_pipeline()
        if ner_pipeline is None:
            return []

        try:
            entities = ner_pipeline(query)
            return entities
        except Exception as e:
            logger.error(f"NER extraction failed: {e}")
            return []

    async def _extract_with_openai(self, query: str) -> list[dict[str, Any]]:
        """Extract entities using OpenAI for complex queries"""
        openai_client = self._get_openai_client()
        if openai_client is None:
            return []

        try:
            prompt = f"""
            Extract entities from this Home Assistant automation query: "{query}"
            
            Return JSON with:
            {{
                "areas": ["office", "kitchen", "bedroom"],
                "action_devices": ["lights", "thermostat"],
                "trigger_conditions": [
                    {{
                        "condition": "sit at desk",
                        "trigger_type": "presence",
                        "location": "office",
                        "required_device_class": "occupancy"
                    }}
                ],
                "actions": ["turn on", "flash", "monitor"],
                "intent": "automation"
            }}
            
            Focus on:
            - Room/area names
            - Action devices (devices that will be controlled: lights, switches, etc.)
            - Trigger conditions (conditions that trigger the automation: "when I sit at desk", "if door opens", etc.)
              For each trigger condition, identify:
              * The condition text
              * Trigger type (presence, motion, door, window, time, temperature, humidity)
              * Location/area context
              * Required device class (occupancy, motion, door, window, temperature, humidity)
            - Actions (turn on, flash, monitor, etc.)
            - Time references (morning, evening, sunset, etc.)
            """

            response = await openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a Home Assistant entity extraction expert. Extract entities from user queries for home automation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_completion_tokens=300  # Use max_completion_tokens for newer models
            )

            # Parse OpenAI response
            content = response.choices[0].message.content
            entities = self._parse_openai_response(content)

            logger.debug(f"OpenAI extracted {len(entities)} entities")
            return entities

        except Exception as e:
            logger.error(f"OpenAI extraction failed: {e}")
            return []

    def _parse_openai_response(self, content: str) -> list[dict[str, Any]]:
        """Parse OpenAI JSON response into entity format"""
        try:
            import json
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())

                entities = []
                # Convert OpenAI format to our entity format
                for area in data.get('areas', []):
                    entities.append({
                        'name': area,
                        'type': 'area',
                        'domain': 'unknown',
                        'confidence': 0.9,
                        'extraction_method': 'openai'
                    })

                # Handle both 'devices' and 'action_devices' for backward compatibility
                devices = data.get('action_devices', []) or data.get('devices', [])
                for device in devices:
                    entities.append({
                        'name': device,
                        'type': 'device',
                        'domain': 'unknown',
                        'confidence': 0.9,
                        'extraction_method': 'openai'
                    })

                # Store trigger_conditions in a special format for later processing
                # They will be processed by trigger condition analyzer
                trigger_conditions = data.get('trigger_conditions', [])
                if trigger_conditions:
                    # Store as metadata for trigger discovery
                    for condition in trigger_conditions:
                        entities.append({
                            'name': condition.get('condition', ''),
                            'type': 'trigger_condition',
                            'trigger_type': condition.get('trigger_type'),
                            'location': condition.get('location'),
                            'required_device_class': condition.get('required_device_class'),
                            'confidence': 0.9,
                            'extraction_method': 'openai'
                        })

                return entities
        except Exception as e:
            logger.error(f"Failed to parse OpenAI response: {e}")

        return []

    async def _enhance_with_device_intelligence(self, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Enhance entities with device intelligence data"""
        if not self.device_intel_client:
            return entities

        # Separate areas and devices
        area_entities = [e for e in entities if e.get('type') == 'area']
        device_entities = [e for e in entities if e.get('type') == 'device']
        unknown_entities = [e for e in entities if e.get('type') not in ['area', 'device']]

        enhanced_entities = []
        added_device_ids = set()  # Track to avoid duplicates

        # Process area entities (existing logic)
        for entity in area_entities:
            try:
                area_name = entity['name']
                devices = await self.device_intel_client.get_devices_by_area(area_name)

                for device in devices:
                    # Handle case where device might be a string (device ID) or dict
                    if isinstance(device, str):
                        device_id = device
                    elif isinstance(device, dict):
                        device_id = device.get('id') or device.get('device_id')
                    else:
                        logger.warning(f"Unexpected device type: {type(device)}, skipping")
                        continue

                    if not device_id:
                        logger.warning(f"Device missing ID: {device}, skipping")
                        continue

                    # Skip if already added from device entity lookup
                    if device_id in added_device_ids:
                        continue

                    device_details = await self.device_intel_client.get_device_details(device_id)
                    if device_details:
                        enhanced_entity = self._build_enhanced_entity(device_details, area_name)
                        enhanced_entities.append(enhanced_entity)
                        added_device_ids.add(device_id)
            except Exception as e:
                logger.error(f"Failed to enhance area {entity.get('name', 'unknown')}: {e}", exc_info=True)
                enhanced_entities.append(entity)

        # Process device entities (NEW LOGIC)
        if device_entities:
            try:
                # Fetch all devices once for searching
                all_devices = await self.device_intel_client.get_all_devices(limit=200)

                for entity in device_entities:
                    # Handle case where entity might be a string or dict
                    if isinstance(entity, str):
                        device_name = entity
                        entity = {'name': entity, 'type': 'device'}  # Convert to dict for consistency
                    else:
                        device_name = entity.get('name') if isinstance(entity, dict) else str(entity)

                    # Search for device by name (fuzzy matching)
                    matching_devices = self._find_matching_devices(device_name, all_devices)

                    for device in matching_devices:
                        # Handle case where device might be a string or dict
                        if isinstance(device, str):
                            device_id = device
                        elif isinstance(device, dict):
                            device_id = device.get('id') or device.get('device_id')
                        else:
                            continue

                        if not device_id:
                            continue

                        # Skip if already added from area lookup
                        if device_id in added_device_ids:
                            continue

                        device_details = await self.device_intel_client.get_device_details(device_id)
                        if device_details:
                            # ✅ FIX: Validate that device_details is a dict before processing
                            if not isinstance(device_details, dict):
                                logger.warning(f"⚠️ device_intel_client returned non-dict type for device {device_id}: {type(device_details).__name__}")
                                continue

                            enhanced_entity = self._build_enhanced_entity(device_details)
                            enhanced_entities.append(enhanced_entity)
                            added_device_ids.add(device_id)

                            # Break after first match to avoid duplicates
                            break

                    # If no match found, keep the original entity
                    matching_device_ids = []
                    for d in matching_devices:
                        if isinstance(d, str):
                            matching_device_ids.append(d)
                        elif isinstance(d, dict):
                            matching_device_ids.append(d.get('id') or d.get('device_id'))

                    if not any(did in added_device_ids for did in matching_device_ids if did):
                        enhanced_entities.append(entity)

            except Exception as e:
                logger.error(f"Failed to enhance device entities: {e}")
                # Add unenhanced device entities as fallback
                enhanced_entities.extend(device_entities)

        # Add unknown entities as-is
        enhanced_entities.extend(unknown_entities)

        return enhanced_entities

    async def extract_entities(self, query: str) -> list[dict[str, Any]]:
        """
        Extract entities using multi-model approach.
        
        Args:
            query: User query string
            
        Returns:
            List of extracted entities with metadata
        """
        import time
        start_time = time.time()
        self.stats['total_queries'] += 1

        try:
            # Step 1: Try NER first (90% of queries)
            logger.debug(f"Extracting entities from: {query}")

            ner_entities = self._cached_ner_extraction(query)

            if self._is_high_confidence(ner_entities):
                logger.debug("High confidence NER results, using NER")
                self.stats['ner_success'] += 1

                # Convert NER format to our format
                converted_entities = []
                for entity in ner_entities:
                    converted_entities.append({
                        'name': entity['word'],
                        'type': 'device' if entity['entity'] in ['B-DEVICE', 'I-DEVICE'] else 'area',
                        'domain': 'unknown',
                        'confidence': entity['score'],
                        'extraction_method': 'ner'
                    })

                # Enhance with device intelligence
                enhanced_entities = await self._enhance_with_device_intelligence(converted_entities)

                # Discover trigger devices
                all_entities = await self._discover_trigger_devices(query, enhanced_entities)

                processing_time = time.time() - start_time
                self.stats['avg_processing_time'] = (
                    (self.stats['avg_processing_time'] * (self.stats['total_queries'] - 1) + processing_time)
                    / self.stats['total_queries']
                )

                # Track direct call pattern
                processing_time_ms = processing_time * 1000
                self.call_stats['direct_calls'] += 1
                self.call_stats['total_direct_time'] += processing_time_ms
                self.call_stats['avg_direct_latency'] = (
                    self.call_stats['total_direct_time'] / self.call_stats['direct_calls']
                )
                logger.info(f"SERVICE_CALL: pattern=direct, service=ner, latency={processing_time_ms:.2f}ms, success=True")

                return all_entities

            # Step 2: Try OpenAI for complex queries (10% of queries)
            if self._is_complex_query(query):
                logger.debug("Complex query detected, using OpenAI")
                openai_entities = await self._extract_with_openai(query)

                if openai_entities:
                    self.stats['openai_success'] += 1
                    enhanced_entities = await self._enhance_with_device_intelligence(openai_entities)

                    # Discover trigger devices
                    all_entities = await self._discover_trigger_devices(query, enhanced_entities)

                    processing_time = time.time() - start_time
                    self.stats['avg_processing_time'] = (
                        (self.stats['avg_processing_time'] * (self.stats['total_queries'] - 1) + processing_time)
                        / self.stats['total_queries']
                    )

                    # Track direct call pattern
                    processing_time_ms = processing_time * 1000
                    self.call_stats['direct_calls'] += 1
                    self.call_stats['total_direct_time'] += processing_time_ms
                    self.call_stats['avg_direct_latency'] = (
                        self.call_stats['total_direct_time'] / self.call_stats['direct_calls']
                    )
                    logger.info(f"SERVICE_CALL: pattern=direct, service=openai, latency={processing_time_ms:.2f}ms, success=True")

                    return all_entities

            # Step 3: Fallback to pattern matching (0% of queries)
            logger.debug("Using pattern matching fallback")
            self.stats['pattern_fallback'] += 1

            pattern_entities = extract_entities_from_query(query)
            enhanced_entities = await self._enhance_with_device_intelligence(pattern_entities)

            # Discover trigger devices
            all_entities = await self._discover_trigger_devices(query, enhanced_entities)

            processing_time = time.time() - start_time
            self.stats['avg_processing_time'] = (
                (self.stats['avg_processing_time'] * (self.stats['total_queries'] - 1) + processing_time)
                / self.stats['total_queries']
            )

            # Track direct call pattern
            processing_time_ms = processing_time * 1000
            self.call_stats['direct_calls'] += 1
            self.call_stats['total_direct_time'] += processing_time_ms
            self.call_stats['avg_direct_latency'] = (
                self.call_stats['total_direct_time'] / self.call_stats['direct_calls']
            )
            logger.info(f"SERVICE_CALL: pattern=direct, service=pattern_fallback, latency={processing_time_ms:.2f}ms, success=True")

            return all_entities

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            # Emergency fallback to pattern matching
            return extract_entities_from_query(query)

    async def _discover_trigger_devices(
        self,
        query: str,
        enhanced_entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Discover trigger devices based on trigger conditions in the query.
        
        Args:
            query: User query string
            enhanced_entities: Already extracted and enhanced entities
            
        Returns:
            Combined list of enhanced entities and discovered trigger devices
        """
        try:
            # Skip trigger discovery if components not initialized
            if not self.trigger_condition_analyzer or not self.trigger_device_discovery:
                logger.debug("Trigger discovery components not initialized, skipping")
                return enhanced_entities

            # Check if OpenAI already extracted trigger conditions
            openai_trigger_conditions = [
                e for e in enhanced_entities
                if e.get('type') == 'trigger_condition' and e.get('extraction_method') == 'openai'
            ]

            # Filter out trigger_condition entities from enhanced_entities (they're metadata, not real entities)
            action_entities = [
                e for e in enhanced_entities
                if e.get('type') != 'trigger_condition'
            ]

            # If OpenAI extracted trigger conditions, use those
            if openai_trigger_conditions:
                trigger_conditions = [
                    {
                        'type': 'trigger_condition',
                        'trigger_type': tc.get('trigger_type'),
                        'condition_text': tc.get('name', ''),
                        'location': tc.get('location'),
                        'required_device_class': tc.get('required_device_class'),
                        'confidence': tc.get('confidence', 0.9),
                        'extraction_method': 'openai'
                    }
                    for tc in openai_trigger_conditions
                ]
            else:
                # Analyze trigger conditions using pattern matching
                trigger_conditions = await self.trigger_condition_analyzer.analyze_trigger_conditions(
                    query, action_entities
                )

            if not trigger_conditions:
                logger.debug("No trigger conditions found in query")
                return action_entities

            # Discover trigger devices
            trigger_devices = await self.trigger_device_discovery.discover_trigger_devices(
                trigger_conditions
            )

            if trigger_devices:
                self.stats['trigger_devices_discovered'] += len(trigger_devices)
                logger.info(
                    f"Discovered {len(trigger_devices)} trigger devices: "
                    f"{[d.get('name', 'unknown') for d in trigger_devices]}"
                )
                # Combine entities (action entities + trigger devices, excluding trigger_condition metadata)
                return action_entities + trigger_devices
            else:
                logger.debug("No trigger devices discovered")
                return action_entities

        except Exception as e:
            logger.error(f"Error discovering trigger devices: {e}", exc_info=True)
            # On error, return original entities (graceful degradation)
            # Filter out trigger_condition metadata entities
            return [e for e in enhanced_entities if e.get('type') != 'trigger_condition']

    def get_stats(self) -> dict[str, Any]:
        """Get performance statistics with model names and cost information"""
        total = self.stats['total_queries']
        if total == 0:
            return {
                **self.stats,
                'models': {
                    'ner': {
                        'model_name': self.ner_model,
                        'calls': 0,
                        'success_rate': 0.0,
                        'cost_usd': 0.0
                    },
                    'openai': {
                        'model_name': self.openai_model,
                        'calls': 0,
                        'success_rate': 0.0,
                        'cost_usd': 0.0
                    },
                    'pattern': {
                        'model_name': 'pattern_matching',
                        'calls': 0,
                        'success_rate': 0.0,
                        'cost_usd': 0.0
                    }
                }
            }

        # Calculate model-specific stats
        from ..llm.cost_tracker import CostTracker

        # Estimate costs (we don't track exact tokens for NER/pattern, so estimate)
        # NER and pattern matching are free (local models)
        ner_cost = 0.0  # Local model, no cost

        # OpenAI costs would need token tracking - for now estimate based on average
        # This is a limitation - we'd need to track tokens per call for accurate costs
        openai_cost = 0.0  # Would need token tracking for accurate cost

        pattern_cost = 0.0  # Pattern matching is free

        return {
            **self.stats,
            'ner_success_rate': self.stats['ner_success'] / total if total > 0 else 0.0,
            'openai_success_rate': self.stats['openai_success'] / total if total > 0 else 0.0,
            'pattern_fallback_rate': self.stats['pattern_fallback'] / total if total > 0 else 0.0,
            'models': {
                'ner': {
                    'model_name': self.ner_model,
                    'calls': self.stats['ner_success'],
                    'success_rate': self.stats['ner_success'] / total if total > 0 else 0.0,
                    'cost_usd': ner_cost,
                    'is_local': CostTracker.is_local_model(self.ner_model)
                },
                'openai': {
                    'model_name': self.openai_model,
                    'calls': self.stats['openai_success'],
                    'success_rate': self.stats['openai_success'] / total if total > 0 else 0.0,
                    'cost_usd': openai_cost,  # Would need token tracking for accurate cost
                    'is_local': CostTracker.is_local_model(self.openai_model)
                },
                'pattern': {
                    'model_name': 'pattern_matching',
                    'calls': self.stats['pattern_fallback'],
                    'success_rate': self.stats['pattern_fallback'] / total if total > 0 else 0.0,
                    'cost_usd': pattern_cost,
                    'is_local': True
                }
            }
        }

    def _build_enhanced_entity(
        self,
        device_details: dict[str, Any],
        area: str | None = None
    ) -> dict[str, Any]:
        """Build enhanced entity from device details."""
        # ✅ FIX: Defensive check - ensure device_details is a dict
        if not isinstance(device_details, dict):
            logger.error(f"❌ _build_enhanced_entity received non-dict type: {type(device_details).__name__}")
            raise ValueError(f"device_details must be a dict, got {type(device_details).__name__}")

        entities_list = device_details.get('entities', [])
        entity_id = entities_list[0]['entity_id'] if entities_list else None
        domain = entities_list[0]['domain'] if entities_list else 'unknown'

        return {
            'name': device_details['name'],
            'entity_id': entity_id,
            'domain': domain,
            'area': area or device_details.get('area_name', 'Unknown'),
            'manufacturer': device_details.get('manufacturer', 'Unknown'),
            'model': device_details.get('model', 'Unknown'),
            'health_score': device_details.get('health_score', 0),
            'capabilities': device_details.get('capabilities', []),
            'extraction_method': 'device_intelligence',
            'confidence': 0.9
        }

    def _find_matching_devices(
        self,
        search_name: str,
        all_devices: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Medium Win 1: Enhanced device matching with multiple strategies.
        
        Improved matching that checks:
        - name (exact, contains, partial word)
        - friendly_name (user-friendly names)
        - name_by_user (custom user names)
        - fuzzy matching with rapidfuzz (if available)
        """
        search_name_lower = search_name.lower().strip()
        if not search_name_lower:
            return []

        matches = []
        match_scores = {}  # Track match quality scores

        # Try rapidfuzz if available (better fuzzy matching)
        try:
            from rapidfuzz import fuzz, process
            rapidfuzz_available = True
        except ImportError:
            rapidfuzz_available = False

        for device in all_devices:
            if not isinstance(device, dict):
                logger.debug(f"Skipping non-dict device entry during match: {device!r}")
                continue

            # Check multiple name fields
            device_name = device.get('name', '').lower()
            friendly_name = device.get('friendly_name', '').lower()
            name_by_user = device.get('name_by_user', '').lower()
            
            # Collect all name variants to check
            name_variants = [device_name]
            if friendly_name and friendly_name != device_name:
                name_variants.append(friendly_name)
            if name_by_user and name_by_user not in name_variants:
                name_variants.append(name_by_user)

            best_score = 0.0
            best_match_type = None

            for variant in name_variants:
                if not variant:
                    continue
                
                # Exact match (highest priority)
                if variant == search_name_lower:
                    best_score = 1.0
                    best_match_type = 'exact'
                    break
                
                # Contains match (high priority)
                if search_name_lower in variant or variant in search_name_lower:
                    score = len(search_name_lower) / max(len(variant), 1)
                    if score > best_score:
                        best_score = score
                        best_match_type = 'contains'
                
                # Fuzzy match with rapidfuzz (if available)
                if rapidfuzz_available:
                    ratio = fuzz.ratio(search_name_lower, variant) / 100.0
                    if ratio > 0.7 and ratio > best_score:  # 70% similarity threshold
                        best_score = ratio
                        best_match_type = 'fuzzy'
                
                # Partial word match
                search_words = search_name_lower.split()
                variant_words = variant.split()
                if any(word in variant_words for word in search_words):
                    word_match_ratio = sum(1 for word in search_words if word in variant_words) / max(len(search_words), 1)
                    if word_match_ratio > best_score:
                        best_score = word_match_ratio
                        best_match_type = 'partial'

            # Add match if score is above threshold
            if best_score > 0.5:  # 50% similarity threshold
                matches.append(device)
                match_scores[id(device)] = {
                    'score': best_score,
                    'type': best_match_type
                }

        # Sort by match quality (exact > contains > fuzzy > partial)
        match_priority = {'exact': 4, 'contains': 3, 'fuzzy': 2, 'partial': 1}
        matches.sort(
            key=lambda d: (
                match_priority.get(match_scores.get(id(d), {}).get('type', ''), 0),
                match_scores.get(id(d), {}).get('score', 0)
            ),
            reverse=True
        )

        return matches

    async def close(self):
        """Clean up resources"""
        if self.device_intel_client:
            await self.device_intel_client.close()
