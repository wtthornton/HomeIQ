"""
Model Orchestrator - Coordinates Multiple Model Services
Manages the multi-model entity extraction pipeline
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import httpx
import time
from functools import lru_cache

logger = logging.getLogger(__name__)

class ModelOrchestrator:
    """
    Orchestrates multiple model services for entity extraction.
    
    Strategy:
    1. Try NER service (fast, free)
    2. Fallback to OpenAI service (accurate, paid)
    3. Emergency fallback to pattern matching (built-in)
    """
    
    def __init__(self,
                 ner_service_url: str = "http://ner-service:8019",
                 openai_service_url: str = "http://openai-service:8020",
                 timeout: float = 5.0):
        """
        Initialize model orchestrator.
        
        Args:
            ner_service_url: URL of NER model service
            openai_service_url: URL of OpenAI service
            timeout: Request timeout in seconds
        """
        self.ner_service_url = ner_service_url
        self.openai_service_url = openai_service_url
        self.timeout = timeout
        
        # Performance tracking
        self.stats = {
            'total_queries': 0,
            'ner_success': 0,
            'openai_success': 0,
            'pattern_fallback': 0,
            'avg_processing_time': 0.0,
            'total_cost_usd': 0.0
        }
        
        # Call pattern tracking
        self.call_stats = {
            'direct_calls': 0,
            'orchestrated_calls': 0,
            'avg_direct_latency': 0.0,
            'avg_orch_latency': 0.0,
            'total_direct_time': 0.0,
            'total_orch_time': 0.0
        }
        
        logger.info(f"ModelOrchestrator initialized with NER: {ner_service_url}, OpenAI: {openai_service_url}")
    
    async def extract_entities(self, query: str, confidence_threshold: float = 0.8) -> List[Dict[str, Any]]:
        """
        Extract entities using multi-model approach.
        
        Args:
            query: User query string
            confidence_threshold: Minimum confidence for NER results
            
        Returns:
            List of extracted entities with metadata
        """
        start_time = time.time()
        self.stats['total_queries'] += 1
        
        try:
            # Step 1: Try NER service (90% of queries)
            logger.debug(f"Extracting entities from: {query}")
            
            ner_entities = await self._try_ner_extraction(query, confidence_threshold)
            
            if ner_entities and self._is_high_confidence(ner_entities):
                logger.debug("High confidence NER results, using NER")
                self.stats['ner_success'] += 1
                
                processing_time = time.time() - start_time
                self._update_stats(processing_time, 0.0)
                
                # Track direct call pattern
                processing_time_ms = processing_time * 1000
                self.call_stats['direct_calls'] += 1
                self.call_stats['total_direct_time'] += processing_time_ms
                self.call_stats['avg_direct_latency'] = (
                    self.call_stats['total_direct_time'] / self.call_stats['direct_calls']
                )
                logger.info(f"SERVICE_CALL: pattern=direct, service=ner, latency={processing_time_ms:.2f}ms, success=True")
                
                return ner_entities
            
            # Step 2: Try OpenAI service for complex queries (10% of queries)
            if self._is_complex_query(query):
                logger.debug("Complex query detected, using OpenAI")
                openai_entities, cost = await self._try_openai_extraction(query)
                
                if openai_entities:
                    self.stats['openai_success'] += 1
                    
                    processing_time = time.time() - start_time
                    self._update_stats(processing_time, cost)
                    
                    # Track direct call pattern
                    processing_time_ms = processing_time * 1000
                    self.call_stats['direct_calls'] += 1
                    self.call_stats['total_direct_time'] += processing_time_ms
                    self.call_stats['avg_direct_latency'] = (
                        self.call_stats['total_direct_time'] / self.call_stats['direct_calls']
                    )
                    logger.info(f"SERVICE_CALL: pattern=direct, service=openai, latency={processing_time_ms:.2f}ms, success=True")
                    
                    return openai_entities
            
            # Step 3: Fallback to pattern matching (0% of queries)
            logger.debug("Using pattern matching fallback")
            self.stats['pattern_fallback'] += 1
            
            pattern_entities = self._pattern_extraction(query)
            
            processing_time = time.time() - start_time
            self._update_stats(processing_time, 0.0)
            
            # Track direct call pattern
            processing_time_ms = processing_time * 1000
            self.call_stats['direct_calls'] += 1
            self.call_stats['total_direct_time'] += processing_time_ms
            self.call_stats['avg_direct_latency'] = (
                self.call_stats['total_direct_time'] / self.call_stats['direct_calls']
            )
            logger.info(f"SERVICE_CALL: pattern=direct, service=pattern_fallback, latency={processing_time_ms:.2f}ms, success=True")
            
            return pattern_entities
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            # Emergency fallback to pattern matching
            return self._pattern_extraction(query)
    
    async def _try_ner_extraction(self, query: str, confidence_threshold: float) -> Optional[List[Dict[str, Any]]]:
        """Try NER service extraction"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.ner_service_url}/extract",
                    json={
                        "query": query,
                        "confidence_threshold": confidence_threshold
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get('entities', [])
                else:
                    logger.warning(f"NER service returned {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.debug(f"NER service unavailable: {e}")
            return None
    
    async def _try_openai_extraction(self, query: str) -> tuple[Optional[List[Dict[str, Any]]], float]:
        """Try OpenAI service extraction"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout * 2) as client:  # Longer timeout for OpenAI
                response = await client.post(
                    f"{self.openai_service_url}/extract",
                    json={
                        "query": query,
                        "model": "gpt-4o-mini",
                        "temperature": 0.1,
                        "max_tokens": 300
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    entities = data.get('entities', [])
                    cost = data.get('cost_usd', 0.0)
                    return entities, cost
                else:
                    logger.warning(f"OpenAI service returned {response.status_code}")
                    return None, 0.0
                    
        except Exception as e:
            logger.debug(f"OpenAI service unavailable: {e}")
            return None, 0.0
    
    def _is_high_confidence(self, entities: List[Dict[str, Any]]) -> bool:
        """Check if NER results are high confidence"""
        if not entities:
            return False
        
        # Check if we have entities with high confidence
        high_confidence_entities = [e for e in entities if e.get('confidence', 0) > 0.8]
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
        
        import re
        query_lower = query.lower()
        complexity_score = sum(1 for pattern in complex_indicators 
                             if re.search(pattern, query_lower))
        
        # Also consider query length and complexity
        word_count = len(query.split())
        has_question = '?' in query
        
        return complexity_score >= 2 or (word_count > 15 and has_question)
    
    def _pattern_extraction(self, query: str) -> List[Dict[str, Any]]:
        """Fallback pattern extraction (built-in)"""
        # Simple pattern matching as emergency fallback
        import re
        
        entities = []
        
        # Area patterns
        area_patterns = [
            r'\b(office|kitchen|bedroom|living room|garage|bathroom|dining room)\b',
            r'\b(front|back|side|main|master)\b'
        ]
        
        for pattern in area_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                entities.append({
                    'name': match.group().lower(),
                    'type': 'area',
                    'domain': 'unknown',
                    'confidence': 0.7,
                    'extraction_method': 'pattern',
                    'start': match.start(),
                    'end': match.end()
                })
        
        # Device patterns
        device_patterns = [
            r'\b(light|lamp|bulb|fixture)\b',
            r'\b(door|sensor|motion|contact)\b',
            r'\b(switch|outlet|plug)\b',
            r'\b(thermostat|temperature|climate)\b'
        ]
        
        for pattern in device_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                entities.append({
                    'name': match.group().lower(),
                    'type': 'device',
                    'domain': 'unknown',
                    'confidence': 0.7,
                    'extraction_method': 'pattern',
                    'start': match.start(),
                    'end': match.end()
                })
        
        return entities
    
    def _update_stats(self, processing_time: float, cost: float):
        """Update performance statistics"""
        self.stats['avg_processing_time'] = (
            (self.stats['avg_processing_time'] * (self.stats['total_queries'] - 1) + processing_time) 
            / self.stats['total_queries']
        )
        self.stats['total_cost_usd'] += cost
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        total = self.stats['total_queries']
        if total == 0:
            return self.stats
        
        return {
            **self.stats,
            'ner_success_rate': self.stats['ner_success'] / total,
            'openai_success_rate': self.stats['openai_success'] / total,
            'pattern_fallback_rate': self.stats['pattern_fallback'] / total,
            'avg_cost_per_query': self.stats['total_cost_usd'] / total
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all model services"""
        health_status = {
            'ner_service': False,
            'openai_service': False,
            'overall_healthy': False
        }
        
        # Check NER service
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.ner_service_url}/health")
                health_status['ner_service'] = response.status_code == 200
        except:
            pass
        
        # Check OpenAI service
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.openai_service_url}/health")
                health_status['openai_service'] = response.status_code == 200
        except:
            pass
        
        # Overall health (at least one service must be healthy)
        health_status['overall_healthy'] = health_status['ner_service'] or health_status['openai_service']
        
        return health_status
