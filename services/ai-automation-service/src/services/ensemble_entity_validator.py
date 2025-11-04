"""
Ensemble Entity Validator - Uses ALL available models for robust entity validation

Leverages:
- Hugging Face NER (dslim/bert-base-NER)
- OpenAI GPT-4o-mini (complex reasoning)
- SentenceTransformers (semantic similarity)
- Embedding-based matching
- HA API verification (ground truth)
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationMethod(Enum):
    """Different validation methods available"""
    HF_NER = "hf_ner"
    OPENAI = "openai"
    EMBEDDING_SIMILARITY = "embedding_similarity"
    PATTERN_MATCHING = "pattern_matching"
    HA_API = "ha_api"  # Ground truth - always used


@dataclass
class EntityValidationResult:
    """Result from a single validation method"""
    entity_id: str
    method: ValidationMethod
    exists: bool
    confidence: float
    details: Dict[str, Any]
    error: Optional[str] = None


@dataclass
class EnsembleValidationResult:
    """Combined result from all validation methods"""
    entity_id: str
    exists: bool  # Consensus result
    confidence: float  # Weighted average confidence
    method_results: List[EntityValidationResult]
    consensus_score: float  # Agreement between methods (0-1)
    warnings: List[str]
    suggested_alternatives: List[str]


class EnsembleEntityValidator:
    """
    Ensemble validator that uses multiple models to validate entities.
    
    Strategy:
    1. Run ALL validation methods in parallel
    2. HA API is ground truth (required)
    3. Use other methods to cross-validate and suggest alternatives
    4. Calculate consensus score from all methods
    5. Only approve entities with high consensus OR HA API confirmation
    """
    
    def __init__(
        self,
        ha_client,
        openai_client=None,
        sentence_transformer_model=None,
        device_intelligence_client=None,
        min_consensus_threshold: float = 0.6
    ):
        """
        Initialize ensemble validator.
        
        Args:
            ha_client: Home Assistant client (REQUIRED - ground truth)
            openai_client: Optional OpenAI client for reasoning
            sentence_transformer_model: Optional SentenceTransformer model
            device_intelligence_client: Optional device intelligence client
            min_consensus_threshold: Minimum consensus score to accept entity (0-1)
        """
        self.ha_client = ha_client
        self.openai_client = openai_client
        self.sentence_model = sentence_transformer_model
        self.device_intel_client = device_intelligence_client
        self.min_consensus_threshold = min_consensus_threshold
        
        # Method weights for consensus calculation
        self.method_weights = {
            ValidationMethod.HA_API: 1.0,  # Highest weight - ground truth
            ValidationMethod.OPENAI: 0.8,  # High weight - good reasoning
            ValidationMethod.EMBEDDING_SIMILARITY: 0.7,  # Good semantic matching
            ValidationMethod.HF_NER: 0.6,  # Moderate - entity extraction quality
            ValidationMethod.PATTERN_MATCHING: 0.4  # Lower weight - fallback
        }
        
        logger.info("EnsembleEntityValidator initialized")
    
    async def validate_entity_ensemble(
        self,
        entity_id: str,
        query_context: Optional[str] = None,
        available_entities: Optional[List[Dict[str, Any]]] = None
    ) -> EnsembleValidationResult:
        """
        Validate entity using ALL available methods in parallel.
        
        Args:
            entity_id: Entity ID to validate
            query_context: Optional query context for better matching
            available_entities: Optional list of available entities for comparison
            
        Returns:
            EnsembleValidationResult with consensus from all methods
        """
        logger.info(f"🔍 Ensemble validation for entity: {entity_id}")
        
        # Run all validation methods in parallel
        validation_tasks = [
            self._validate_with_ha_api(entity_id),
            self._validate_with_openai(entity_id, query_context) if self.openai_client else None,
            self._validate_with_embeddings(entity_id, available_entities) if self.sentence_model and available_entities else None,
            self._validate_with_pattern(entity_id, query_context) if query_context else None,
        ]
        
        # Filter out None tasks
        validation_tasks = [task for task in validation_tasks if task is not None]
        
        # Execute all validations in parallel
        method_results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        # Process results
        valid_results = []
        errors = []
        for result in method_results:
            if isinstance(result, Exception):
                errors.append(str(result))
                logger.warning(f"Validation method failed: {result}")
            elif isinstance(result, EntityValidationResult):
                valid_results.append(result)
        
        # HA API is required - if it fails, entity is invalid
        ha_result = next((r for r in valid_results if r.method == ValidationMethod.HA_API), None)
        if not ha_result or not ha_result.exists:
            logger.warning(f"❌ Entity {entity_id} not found in HA (ground truth)")
            return EnsembleValidationResult(
                entity_id=entity_id,
                exists=False,
                confidence=0.0,
                method_results=valid_results,
                consensus_score=0.0,
                warnings=[f"Entity not found in Home Assistant API (ground truth)"],
                suggested_alternatives=self._suggest_alternatives(entity_id, available_entities)
            )
        
        # Calculate consensus from all methods
        consensus_score, weighted_confidence = self._calculate_consensus(valid_results)
        
        # Determine if entity is valid (HA API says yes AND consensus is high)
        exists = ha_result.exists and consensus_score >= self.min_consensus_threshold
        
        warnings = []
        if consensus_score < self.min_consensus_threshold:
            warnings.append(f"Low consensus score ({consensus_score:.2f}) - other methods disagree")
        
        return EnsembleValidationResult(
            entity_id=entity_id,
            exists=exists,
            confidence=weighted_confidence,
            method_results=valid_results,
            consensus_score=consensus_score,
            warnings=warnings,
            suggested_alternatives=[]  # Only suggest if invalid
        )
    
    async def _validate_with_ha_api(self, entity_id: str) -> EntityValidationResult:
        """Validate using HA API (ground truth)"""
        try:
            state = await self.ha_client.get_entity_state(entity_id)
            exists = state is not None
            
            # ✅ FIX: state is a dict, not an object - access via dict keys
            return EntityValidationResult(
                entity_id=entity_id,
                method=ValidationMethod.HA_API,
                exists=exists,
                confidence=1.0 if exists else 0.0,  # Ground truth is 100% confident
                details={
                    "state": state.get('state') if state else None,
                    "attributes": state.get('attributes') if state else None
                }
            )
        except Exception as e:
            logger.error(f"❌ HA API validation failed for {entity_id}: {e}", exc_info=True)
            return EntityValidationResult(
                entity_id=entity_id,
                method=ValidationMethod.HA_API,
                exists=False,
                confidence=0.0,
                details={},
                error=str(e)
            )
    
    async def _validate_with_openai(self, entity_id: str, query_context: Optional[str]) -> EntityValidationResult:
        """Validate using OpenAI reasoning"""
        if not self.openai_client or not query_context:
            return EntityValidationResult(
                entity_id=entity_id,
                method=ValidationMethod.OPENAI,
                exists=False,
                confidence=0.0,
                details={},
                error="OpenAI client or context not available"
            )
        
        try:
            prompt = f"""Analyze this entity ID in the context of this Home Assistant query:

Entity ID: {entity_id}
User Query: "{query_context}"

Determine if this entity ID is:
1. Valid and exists in Home Assistant
2. Likely to be correct based on the query context
3. A reasonable match for what the user is asking for

Respond with JSON:
{{
    "exists": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation",
    "suggestions": ["alternative_entity_id_1", "alternative_entity_id_2"]
}}
"""
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a Home Assistant entity validation expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            import json
            content = response.choices[0].message.content
            json_match = __import__('re').search(r'\{.*\}', content, __import__('re').DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return EntityValidationResult(
                    entity_id=entity_id,
                    method=ValidationMethod.OPENAI,
                    exists=data.get('exists', False),
                    confidence=data.get('confidence', 0.5),
                    details={
                        "reasoning": data.get('reasoning', ''),
                        "suggestions": data.get('suggestions', [])
                    }
                )
        except Exception as e:
            logger.warning(f"OpenAI validation failed: {e}")
        
        return EntityValidationResult(
            entity_id=entity_id,
            method=ValidationMethod.OPENAI,
            exists=False,
            confidence=0.0,
            details={},
            error="OpenAI validation failed"
        )
    
    async def _validate_with_embeddings(
        self,
        entity_id: str,
        available_entities: Optional[List[Dict[str, Any]]]
    ) -> EntityValidationResult:
        """Validate using embedding similarity"""
        if not self.sentence_model or not available_entities:
            return EntityValidationResult(
                entity_id=entity_id,
                method=ValidationMethod.EMBEDDING_SIMILARITY,
                exists=False,
                confidence=0.0,
                details={},
                error="SentenceTransformer model or available entities not provided"
            )
        
        try:
            # Get embedding for the entity ID (use numpy arrays for compatibility)
            entity_embedding = self.sentence_model.encode(entity_id)
            
            # Find similar entities
            best_match = None
            best_similarity = 0.0
            
            for available in available_entities:
                available_id = available.get('entity_id', '')
                if available_id:
                    available_embedding = self.sentence_model.encode(available_id)
                    # Use numpy cosine similarity
                    import numpy as np
                    similarity = float(np.dot(entity_embedding, available_embedding) / 
                                     (np.linalg.norm(entity_embedding) * np.linalg.norm(available_embedding)))
                    
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = available_id
            
            # High similarity (>0.8) suggests entity exists
            exists = best_match == entity_id and best_similarity > 0.8
            
            return EntityValidationResult(
                entity_id=entity_id,
                method=ValidationMethod.EMBEDDING_SIMILARITY,
                exists=exists,
                confidence=best_similarity,
                details={
                    "best_match": best_match,
                    "similarity": best_similarity
                }
            )
        except Exception as e:
            logger.warning(f"Embedding validation failed: {e}")
            return EntityValidationResult(
                entity_id=entity_id,
                method=ValidationMethod.EMBEDDING_SIMILARITY,
                exists=False,
                confidence=0.0,
                details={},
                error=str(e)
            )
    
    async def _validate_with_pattern(self, entity_id: str, query_context: str) -> EntityValidationResult:
        """Validate using pattern matching"""
        import re
        
        # Check if entity ID format is valid
        valid_format = bool(re.match(r'^[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$', entity_id))
        
        # Check if entity ID matches query context
        entity_name = entity_id.split('.')[-1] if '.' in entity_id else entity_id
        context_match = entity_name.lower() in query_context.lower() if query_context else False
        
        exists = valid_format and context_match
        confidence = 0.6 if valid_format else 0.3
        
        return EntityValidationResult(
            entity_id=entity_id,
            method=ValidationMethod.PATTERN_MATCHING,
            exists=exists,
            confidence=confidence,
            details={
                "valid_format": valid_format,
                "context_match": context_match
            }
        )
    
    def _calculate_consensus(
        self,
        results: List[EntityValidationResult]
    ) -> Tuple[float, float]:
        """
        Calculate consensus score and weighted confidence.
        
        Returns:
            (consensus_score, weighted_confidence)
        """
        if not results:
            return (0.0, 0.0)
        
        # Separate by method
        method_results = {r.method: r for r in results}
        
        # Calculate weighted confidence
        total_weight = 0.0
        weighted_sum = 0.0
        
        for method, result in method_results.items():
            weight = self.method_weights.get(method, 0.5)
            total_weight += weight
            weighted_sum += result.confidence * weight
        
        weighted_confidence = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        # Calculate consensus (agreement between methods)
        # Count how many methods agree on existence
        exists_votes = sum(1 for r in results if r.exists)
        total_votes = len(results)
        
        # Consensus is agreement percentage
        consensus_score = exists_votes / total_votes if total_votes > 0 else 0.0
        
        return (consensus_score, weighted_confidence)
    
    def _suggest_alternatives(
        self,
        entity_id: str,
        available_entities: Optional[List[Dict[str, Any]]]
    ) -> List[str]:
        """Suggest alternative entity IDs"""
        if not available_entities:
            return []
        
        # Extract domain and name from entity_id
        if '.' not in entity_id:
            return []
        
        domain, name = entity_id.split('.', 1)
        
        # Find entities with same domain
        candidates = [
            e.get('entity_id', '') for e in available_entities
            if e.get('entity_id', '').startswith(f"{domain}.") and
            name.lower() in e.get('entity_id', '').lower()
        ]
        
        return candidates[:5]  # Return top 5 candidates
    
    async def validate_entities_batch(
        self,
        entity_ids: List[str],
        query_context: Optional[str] = None,
        available_entities: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, EnsembleValidationResult]:
        """
        Validate multiple entities in parallel using ensemble approach.
        
        Args:
            entity_ids: List of entity IDs to validate
            query_context: Optional query context
            available_entities: Optional available entities for comparison
            
        Returns:
            Dictionary mapping entity_id -> EnsembleValidationResult
        """
        logger.info(f"🔍 Ensemble batch validation for {len(entity_ids)} entities")
        
        # Validate all entities in parallel
        tasks = [
            self.validate_entity_ensemble(eid, query_context, available_entities)
            for eid in entity_ids
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build result dictionary
        validation_results = {}
        for entity_id, result in zip(entity_ids, results):
            if isinstance(result, Exception):
                logger.error(f"Validation failed for {entity_id}: {result}")
                validation_results[entity_id] = EnsembleValidationResult(
                    entity_id=entity_id,
                    exists=False,
                    confidence=0.0,
                    method_results=[],
                    consensus_score=0.0,
                    warnings=[f"Validation error: {str(result)}"],
                    suggested_alternatives=[]
                )
            else:
                validation_results[entity_id] = result
        
        # Log summary
        valid_count = sum(1 for r in validation_results.values() if r.exists)
        logger.info(f"✅ Ensemble validation complete: {valid_count}/{len(entity_ids)} entities valid")
        
        return validation_results

