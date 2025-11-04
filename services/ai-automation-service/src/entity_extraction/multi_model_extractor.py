"""
Multi-Model Entity Extractor for Commercial NUC Deployment
Implements hybrid approach: NER → OpenAI → Pattern Matching
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache
import re

from transformers import pipeline
from openai import AsyncOpenAI
from spacy import load as spacy_load

from .pattern_extractor import extract_entities_from_query
from ..clients.device_intelligence_client import DeviceIntelligenceClient

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
                 device_intelligence_client: Optional[DeviceIntelligenceClient] = None,
                 ner_model: str = "dslim/bert-base-NER",
                 openai_model: str = "gpt-4o-mini"):
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
        
        # Performance tracking
        self.stats = {
            'total_queries': 0,
            'ner_success': 0,
            'openai_success': 0,
            'pattern_fallback': 0,
            'avg_processing_time': 0.0
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
    
    def _is_high_confidence(self, entities: List[Dict]) -> bool:
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
    def _cached_ner_extraction(self, query: str) -> List[Dict]:
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
    
    async def _extract_with_openai(self, query: str) -> List[Dict[str, Any]]:
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
                "devices": ["lights", "door sensor", "thermostat"],
                "actions": ["turn on", "flash", "monitor"],
                "intent": "automation"
            }}
            
            Focus on:
            - Room/area names
            - Device types (lights, sensors, switches, etc.)
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
                max_tokens=300
            )
            
            # Parse OpenAI response
            content = response.choices[0].message.content
            entities = self._parse_openai_response(content)
            
            logger.debug(f"OpenAI extracted {len(entities)} entities")
            return entities
            
        except Exception as e:
            logger.error(f"OpenAI extraction failed: {e}")
            return []
    
    def _parse_openai_response(self, content: str) -> List[Dict[str, Any]]:
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
                
                for device in data.get('devices', []):
                    entities.append({
                        'name': device,
                        'type': 'device',
                        'domain': 'unknown',
                        'confidence': 0.9,
                        'extraction_method': 'openai'
                    })
                
                return entities
        except Exception as e:
            logger.error(f"Failed to parse OpenAI response: {e}")
        
        return []
    
    async def _enhance_with_device_intelligence(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
    
    async def extract_entities(self, query: str) -> List[Dict[str, Any]]:
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
                
                processing_time = time.time() - start_time
                self.stats['avg_processing_time'] = (
                    (self.stats['avg_processing_time'] * (self.stats['total_queries'] - 1) + processing_time) 
                    / self.stats['total_queries']
                )
                
                return enhanced_entities
            
            # Step 2: Try OpenAI for complex queries (10% of queries)
            if self._is_complex_query(query):
                logger.debug("Complex query detected, using OpenAI")
                openai_entities = await self._extract_with_openai(query)
                
                if openai_entities:
                    self.stats['openai_success'] += 1
                    enhanced_entities = await self._enhance_with_device_intelligence(openai_entities)
                    
                    processing_time = time.time() - start_time
                    self.stats['avg_processing_time'] = (
                        (self.stats['avg_processing_time'] * (self.stats['total_queries'] - 1) + processing_time) 
                        / self.stats['total_queries']
                    )
                    
                    return enhanced_entities
            
            # Step 3: Fallback to pattern matching (0% of queries)
            logger.debug("Using pattern matching fallback")
            self.stats['pattern_fallback'] += 1
            
            pattern_entities = extract_entities_from_query(query)
            enhanced_entities = await self._enhance_with_device_intelligence(pattern_entities)
            
            processing_time = time.time() - start_time
            self.stats['avg_processing_time'] = (
                (self.stats['avg_processing_time'] * (self.stats['total_queries'] - 1) + processing_time) 
                / self.stats['total_queries']
            )
            
            return enhanced_entities
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            # Emergency fallback to pattern matching
            return extract_entities_from_query(query)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        total = self.stats['total_queries']
        if total == 0:
            return self.stats
        
        return {
            **self.stats,
            'ner_success_rate': self.stats['ner_success'] / total,
            'openai_success_rate': self.stats['openai_success'] / total,
            'pattern_fallback_rate': self.stats['pattern_fallback'] / total
        }
    
    def _build_enhanced_entity(
        self, 
        device_details: Dict[str, Any], 
        area: Optional[str] = None
    ) -> Dict[str, Any]:
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
        all_devices: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find devices matching search name (fuzzy, case-insensitive)."""
        search_name_lower = search_name.lower().strip()
        
        matches = []
        
        for device in all_devices:
            device_name = device.get('name', '').lower()
            
            # Exact match
            if device_name == search_name_lower:
                matches.append(device)
                continue
                
            # Contains match
            if search_name_lower in device_name or device_name in search_name_lower:
                matches.append(device)
                continue
                
            # Partial word match
            search_words = search_name_lower.split()
            device_words = device_name.split()
            if any(word in device_words for word in search_words):
                matches.append(device)
        
        return matches
    
    async def close(self):
        """Clean up resources"""
        if self.device_intel_client:
            await self.device_intel_client.close()
