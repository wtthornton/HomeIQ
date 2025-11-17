"""
Confidence Calculator - Enhanced confidence calculation with clarification support
"""

import logging
from typing import List, Dict, Any, Optional
from .models import Ambiguity, ClarificationAnswer, AmbiguitySeverity

logger = logging.getLogger(__name__)


class ConfidenceCalculator:
    """Enhanced confidence calculation with clarification support and RAG-based historical learning"""
    
    def __init__(self, default_threshold: float = 0.85, rag_client: Optional[Any] = None):
        """
        Initialize confidence calculator.
        
        Args:
            default_threshold: Default confidence threshold for proceeding
            rag_client: Optional RAG client for historical success checking
        """
        self.default_threshold = default_threshold
        self.rag_client = rag_client
    
    async def calculate_confidence(
        self,
        query: str,
        extracted_entities: List[Dict[str, Any]],
        ambiguities: List[Ambiguity],
        clarification_answers: Optional[List[ClarificationAnswer]] = None,
        base_confidence: float = 0.75,
        rag_client: Optional[Any] = None
    ) -> float:
        """
        Calculate confidence score.
        
        Factors:
        - Base confidence (from entity extraction)
        - Historical success (RAG-based similarity to successful queries)
        - Ambiguity severity (reduces confidence)
        - Clarification completeness (increases confidence)
        - Answer quality (validated answers increase confidence)
        
        Args:
            query: Original user query (or enriched query)
            extracted_entities: Extracted entities
            ambiguities: Detected ambiguities
            clarification_answers: Answers to clarification questions
            base_confidence: Base confidence from extraction
            rag_client: Optional RAG client for historical success checking (if not set in __init__)
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Use provided rag_client or instance rag_client
        active_rag_client = rag_client or self.rag_client
        
        # OPTION 3: Factor historical success in initial confidence
        # Check RAG for similar successful queries and boost base_confidence if found
        historical_boost = 0.0
        if active_rag_client:
            try:
                # Check for similar successful queries
                similar_queries = await active_rag_client.retrieve(
                    query=query,
                    knowledge_type='query',
                    top_k=1,
                    min_similarity=0.75  # Moderate threshold for historical matching
                )
                
                if similar_queries and similar_queries[0]['similarity'] > 0.75:
                    similarity = similar_queries[0]['similarity']
                    success_score = similar_queries[0].get('success_score', 0.5)
                    
                    # Boost base_confidence based on similarity and historical success
                    # Formula: similarity * success_score * max_boost
                    # Higher similarity (closer to 1.0) and higher success_score = bigger boost
                    max_boost = 0.20  # Maximum boost of 20%
                    historical_boost = min(max_boost, similarity * success_score * max_boost)
                    
                    logger.debug(
                        f"📚 Historical success boost: similarity={similarity:.2f}, "
                        f"success_score={success_score:.2f}, boost=+{historical_boost:.2f}"
                    )
            except Exception as e:
                # Non-critical: continue even if RAG check fails
                logger.debug(f"⚠️ RAG historical check failed: {e}")
        
        # Start with base_confidence + historical boost
        confidence = base_confidence + historical_boost
        
        # Reduce for ambiguities
        for ambiguity in ambiguities:
            if ambiguity.severity == AmbiguitySeverity.CRITICAL:
                confidence *= 0.7
            elif ambiguity.severity == AmbiguitySeverity.IMPORTANT:
                confidence *= 0.85
            elif ambiguity.severity == AmbiguitySeverity.OPTIONAL:
                confidence *= 0.95
        
        # Increase for complete clarifications
        if clarification_answers:
            # Count critical ambiguities
            critical_ambiguities = [
                amb for amb in ambiguities
                if amb.severity == AmbiguitySeverity.CRITICAL
            ]
            
            # Count important ambiguities
            important_ambiguities = [
                amb for amb in ambiguities
                if amb.severity == AmbiguitySeverity.IMPORTANT
            ]
            
            # Count answered critical questions (with validation)
            answered_critical = sum(
                1 for answer in clarification_answers
                if answer.validated and answer.confidence > 0.7
            )
            
            # Count answered important questions
            answered_important = sum(
                1 for answer in clarification_answers
                if answer.validated and answer.confidence > 0.6
            )
            
            total_critical = len(critical_ambiguities)
            total_important = len(important_ambiguities)
            total_answered = len([a for a in clarification_answers if a.validated])
            
            # Calculate completion rate for critical ambiguities
            if total_critical > 0:
                completion_rate = answered_critical / total_critical
                # Boost confidence based on completion rate (more weight for critical)
                confidence += (1.0 - confidence) * completion_rate * 0.4
            
            # Calculate completion rate for important ambiguities
            if total_important > 0:
                completion_rate_important = answered_important / total_important
                # Boost confidence based on important completion (less weight)
                confidence += (1.0 - confidence) * completion_rate_important * 0.2
            
            # Boost for having any valid answers
            if total_answered > 0:
                confidence += (1.0 - confidence) * min(0.2, total_answered * 0.05)
            
            # Average answer confidence boost
            validated_answers = [a for a in clarification_answers if a.validated]
            if validated_answers:
                avg_answer_confidence = sum(
                    a.confidence for a in validated_answers
                ) / len(validated_answers)
                
                # Strong boost for high-quality answers
                if avg_answer_confidence > 0.8:
                    confidence += (1.0 - confidence) * 0.15
                elif avg_answer_confidence > 0.6:
                    confidence += (1.0 - confidence) * 0.1
        
        # Adjust based on query clarity
        word_count = len(query.split())
        if word_count < 5:
            confidence *= 0.85
        elif word_count < 8:
            confidence *= 0.95
        
        # Ensure within bounds
        confidence = min(1.0, max(0.0, confidence))
        
        logger.debug(f"📊 Confidence calculated: {confidence:.2f} (base: {base_confidence:.2f}, ambiguities: {len(ambiguities)}, answers: {len(clarification_answers or [])})")
        
        return confidence
    
    def should_ask_clarification(
        self,
        confidence: float,
        ambiguities: List[Ambiguity],
        threshold: Optional[float] = None
    ) -> bool:
        """
        Determine if clarification should be requested.
        
        Args:
            confidence: Current confidence score
            ambiguities: Detected ambiguities
            threshold: Confidence threshold (defaults to instance default)
            
        Returns:
            True if clarification should be requested
        """
        if threshold is None:
            threshold = self.default_threshold
        
        # Always ask if there are critical ambiguities
        has_critical = any(
            amb.severity == AmbiguitySeverity.CRITICAL
            for amb in ambiguities
        )
        
        if has_critical:
            return True
        
        # Ask if confidence is below threshold
        return confidence < threshold

