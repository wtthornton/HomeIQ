"""
Confidence Calculator - Enhanced confidence calculation with clarification support

2025 Best Practices:
- Full type hints (PEP 484/526)
- Async/await for database operations
- Adaptive thresholds based on query complexity
- Hybrid penalty calculation (multiplicative + additive)
"""

import logging
import os
from typing import Any, Literal

import numpy as np

from .confidence_calibrator import ClarificationConfidenceCalibrator
from .models import Ambiguity, AmbiguitySeverity, ClarificationAnswer
from .rl_calibrator import RLConfidenceCalibrator
from .uncertainty_quantification import ConfidenceWithUncertainty, UncertaintyQuantifier

logger = logging.getLogger(__name__)


class ConfidenceCalculator:
    """Enhanced confidence calculation with clarification support and RAG-based historical learning"""

    def __init__(
        self,
        default_threshold: float | None = None,
        rag_client: Any | None = None,
        calibrator: ClarificationConfidenceCalibrator | None = None,
        calibration_enabled: bool = True,
        rl_calibrator: RLConfidenceCalibrator | None = None,
        rl_calibration_enabled: bool = False,  # Phase 3: Optional RL calibration
        uncertainty_quantifier: UncertaintyQuantifier | None = None,
        uncertainty_enabled: bool = False  # Phase 3: Optional uncertainty quantification
    ):
        """
        Initialize confidence calculator.
        
        Args:
            default_threshold: Default confidence threshold for proceeding (defaults to 0.75 or env var)
            rag_client: Optional RAG client for historical success checking
            calibrator: Optional confidence calibrator instance (isotonic regression)
            calibration_enabled: Whether to apply calibration (default: True)
            rl_calibrator: Optional RL-based calibrator (Phase 3)
            rl_calibration_enabled: Whether to apply RL calibration (default: False)
            uncertainty_quantifier: Optional uncertainty quantifier (Phase 3)
            uncertainty_enabled: Whether to calculate uncertainty (default: False)
        """
        # Quick Win 1: Lower default threshold from 0.85 to 0.75, configurable via env var
        if default_threshold is None:
            threshold_str = os.getenv("CLARIFICATION_CONFIDENCE_THRESHOLD", "0.75")
            try:
                default_threshold = float(threshold_str)
                # Validate bounds
                if not (0.0 <= default_threshold <= 1.0):
                    logger.warning(f"Invalid threshold {default_threshold}, using default 0.75")
                    default_threshold = 0.75
            except (ValueError, TypeError):
                logger.warning(f"Invalid threshold format '{threshold_str}', using default 0.75")
                default_threshold = 0.75
        self.default_threshold = default_threshold
        self.rag_client = rag_client
        self.calibrator = calibrator
        self.calibration_enabled = calibration_enabled
        self.rl_calibrator = rl_calibrator
        self.rl_calibration_enabled = rl_calibration_enabled
        self.uncertainty_quantifier = uncertainty_quantifier or UncertaintyQuantifier()
        self.uncertainty_enabled = uncertainty_enabled

    async def calculate_confidence(
        self,
        query: str,
        extracted_entities: list[dict[str, Any]],
        ambiguities: list[Ambiguity],
        clarification_answers: list[ClarificationAnswer] | None = None,
        base_confidence: float = 0.75,
        rag_client: Any | None = None,
        return_uncertainty: bool = False
    ) -> float | ConfidenceWithUncertainty:
        """
        Calculate confidence score.
        
        Factors:
        - Base confidence (from entity extraction)
        - Historical success (RAG-based similarity to successful queries)
        - Ambiguity severity (reduces confidence)
        - Clarification completeness (increases confidence)
        - Answer quality (validated answers increase confidence)
        - Phase 3: RL calibration (optional)
        - Phase 3: Uncertainty quantification (optional)
        
        Args:
            query: Original user query (or enriched query)
            extracted_entities: Extracted entities
            ambiguities: Detected ambiguities
            clarification_answers: Answers to clarification questions
            base_confidence: Base confidence from extraction
            rag_client: Optional RAG client for historical success checking (if not set in __init__)
            return_uncertainty: If True and uncertainty_enabled, returns ConfidenceWithUncertainty
            
        Returns:
            Confidence score (0.0 to 1.0) or ConfidenceWithUncertainty if return_uncertainty=True
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
                    
                    # Validate and clamp values to [0, 1] range
                    similarity = max(0.0, min(1.0, similarity))
                    success_score = max(0.0, min(1.0, success_score))

                    # Boost base_confidence based on similarity and historical success
                    # Formula: similarity * success_score * max_boost
                    # Higher similarity (closer to 1.0) and higher success_score = bigger boost
                    # Quick Win 3: Increased from 20% to 30% for better historical learning
                    max_boost = 0.30  # Maximum boost of 30% (increased from 20%)
                    historical_boost = min(max_boost, similarity * success_score * max_boost)

                    logger.debug(
                        f"📚 Historical success boost: similarity={similarity:.2f}, "
                        f"success_score={success_score:.2f}, boost=+{historical_boost:.2f}"
                    )
            except Exception as e:
                # Non-critical: continue even if RAG check fails
                logger.debug(f"⚠️ RAG historical check failed: {e}")

        # Medium Win 2: Add entity match quality scoring
        entity_quality_boost = self._calculate_entity_quality_boost(extracted_entities)
        
        # Start with base_confidence + historical boost + entity quality boost
        # Clamp early to prevent overflow in intermediate calculations
        confidence = base_confidence + historical_boost + entity_quality_boost
        confidence = min(1.0, max(0.0, confidence))  # Early clamp for safety

        # Reduce for ambiguities using hybrid approach (Phase 1.3: Reduced aggressiveness)
        # First ambiguity: multiplicative, additional ambiguities: additive
        if ambiguities:
            # Apply first ambiguity penalty multiplicatively
            first_ambiguity = ambiguities[0]
            if first_ambiguity.severity == AmbiguitySeverity.CRITICAL:
                confidence *= 0.7
            elif first_ambiguity.severity == AmbiguitySeverity.IMPORTANT:
                confidence *= 0.85
            elif first_ambiguity.severity == AmbiguitySeverity.OPTIONAL:
                confidence *= 0.95

            # Apply additional ambiguities additively (less aggressive)
            if len(ambiguities) > 1:
                additive_penalty = 0.0
                for ambiguity in ambiguities[1:]:
                    if ambiguity.severity == AmbiguitySeverity.CRITICAL:
                        additive_penalty += 0.25  # -25% per additional critical
                    elif ambiguity.severity == AmbiguitySeverity.IMPORTANT:
                        additive_penalty += 0.15  # -15% per additional important
                    elif ambiguity.severity == AmbiguitySeverity.OPTIONAL:
                        additive_penalty += 0.05  # -5% per additional optional

                # Cap maximum total penalty at 60% reduction
                additive_penalty = min(0.60, additive_penalty)
                penalty_multiplier = 1.0 - additive_penalty
                confidence *= penalty_multiplier

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
        raw_confidence = min(1.0, max(0.0, confidence))

        # Apply calibration if enabled and calibrator is available (Phase 1.1)
        if self.calibration_enabled and self.calibrator:
            try:
                # Count ambiguities for calibration features
                critical_count = sum(
                    1 for amb in ambiguities
                    if amb.severity == AmbiguitySeverity.CRITICAL
                )
                answer_count = len(clarification_answers or [])
                rounds = 0  # Will be provided by caller if available

                calibrated_confidence = self.calibrator.calibrate(
                    raw_confidence=raw_confidence,
                    ambiguity_count=len(ambiguities),
                    critical_ambiguity_count=critical_count,
                    rounds=rounds,
                    answer_count=answer_count
                )

                logger.debug(
                    f"📊 Confidence calibrated: {raw_confidence:.2f} → {calibrated_confidence:.2f} "
                    f"(base: {base_confidence:.2f}, ambiguities: {len(ambiguities)}, "
                    f"answers: {len(clarification_answers or [])})"
                )
                final_confidence = calibrated_confidence
            except Exception as e:
                logger.warning(f"Calibration failed, using raw confidence: {e}")
                final_confidence = raw_confidence
        else:
            final_confidence = raw_confidence

        # Phase 3: Apply RL calibration if enabled (optional enhancement)
        if self.rl_calibration_enabled and self.rl_calibrator:
            try:
                critical_count = sum(
                    1 for amb in ambiguities
                    if amb.severity == AmbiguitySeverity.CRITICAL
                )
                answer_count = len(clarification_answers or [])
                rounds = 0  # Will be provided by caller if available

                rl_calibrated = self.rl_calibrator.calibrate(
                    raw_confidence=final_confidence,
                    ambiguity_count=len(ambiguities),
                    critical_ambiguity_count=critical_count,
                    rounds=rounds,
                    answer_count=answer_count
                )

                logger.debug(
                    f"🤖 RL calibration: {final_confidence:.2f} → {rl_calibrated:.2f}"
                )
                final_confidence = rl_calibrated
            except Exception as e:
                logger.warning(f"RL calibration failed, using previous confidence: {e}")

        # Phase 3: Calculate uncertainty if enabled (optional enhancement)
        if self.uncertainty_enabled and return_uncertainty:
            try:
                # Get historical confidence data for uncertainty estimation
                # For now, use empty array (could be enhanced to fetch from database)
                historical_data = np.array([])  # TODO: Fetch from database if available

                uncertainty = self.uncertainty_quantifier.calculate_uncertainty(
                    raw_confidence=final_confidence,
                    historical_data=historical_data,
                    confidence_level=0.90
                )

                logger.debug(
                    f"📊 Uncertainty: {self.uncertainty_quantifier.get_uncertainty_summary(uncertainty)}"
                )
                return uncertainty
            except Exception as e:
                logger.warning(f"Uncertainty calculation failed: {e}")
                # Fall back to point estimate
                return final_confidence

        logger.debug(
            f"📊 Confidence calculated: {final_confidence:.2f} (base: {base_confidence:.2f}, "
            f"ambiguities: {len(ambiguities)}, answers: {len(clarification_answers or [])})"
        )
        return final_confidence

    def should_ask_clarification(
        self,
        confidence: float,
        ambiguities: list[Ambiguity],
        threshold: float | None = None
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

    def calculate_query_complexity(
        self,
        query: str,
        extracted_entities: list[dict[str, Any]],
        ambiguities: list[Ambiguity]
    ) -> Literal["simple", "medium", "complex"]:
        """
        Calculate query complexity level.
        
        Uses 2025 best practices: Literal type for type-safe return value.
        
        Args:
            query: User query
            extracted_entities: Extracted entities
            ambiguities: Detected ambiguities
            
        Returns:
            Complexity level: 'simple', 'medium', or 'complex'
        """
        entity_count = len(extracted_entities)
        ambiguity_count = len(ambiguities)
        word_count = len(query.split())

        # Simple: < 3 entities, no conditions, few words
        if entity_count < 3 and ambiguity_count == 0 and word_count < 10:
            return 'simple'

        # Complex: 5+ entities, multiple ambiguities, long query
        if entity_count >= 5 or ambiguity_count >= 3 or word_count >= 20:
            return 'complex'

        # Medium: everything else
        return 'medium'

    async def calculate_adaptive_threshold(
        self,
        query: str,
        extracted_entities: list[dict[str, Any]],
        ambiguities: list[Ambiguity],
        user_preferences: dict[str, str] | None = None,
        rag_client: Any | None = None
    ) -> float:
        """
        Calculate adaptive confidence threshold based on context.
        
        Uses 2025 best practices: type hints, context-aware adjustments, RAG-based historical learning.
        
        Args:
            query: User query
            extracted_entities: Extracted entities
            ambiguities: Detected ambiguities
            user_preferences: Optional user preferences dict with 'risk_tolerance' key
                ('high', 'medium', or 'low')
            rag_client: Optional RAG client for historical success checking
            
        Returns:
            Adaptive threshold (0.65 to 0.95)
        """
        base_threshold: float = self.default_threshold
        threshold: float = base_threshold

        # Adjust based on query complexity
        complexity = self.calculate_query_complexity(query, extracted_entities, ambiguities)
        if complexity == 'simple':
            threshold -= 0.10  # Lower threshold for simple queries
        elif complexity == 'complex':
            threshold += 0.05  # Higher threshold for complex queries

        # Adjust based on ambiguity count
        ambiguity_count = len(ambiguities)
        if ambiguity_count == 0:
            threshold -= 0.05  # Lower threshold if no ambiguities
        elif ambiguity_count >= 3:
            threshold += 0.05  # Higher threshold if many ambiguities

        # Adjust based on historical success (2025: RAG-based learning)
        active_rag_client = rag_client or self.rag_client
        if active_rag_client:
            try:
                # Check for similar successful queries using hybrid retrieval
                similar_queries = await active_rag_client.retrieve_hybrid(
                    query=query,
                    knowledge_type='query',
                    top_k=1,
                    min_similarity=0.75,
                    use_query_expansion=True,
                    use_reranking=True
                )
                
                if similar_queries:
                    top_result = similar_queries[0]
                    similarity = top_result.get('final_score') or top_result.get('hybrid_score') or top_result.get('similarity', 0.0)
                    success_score = top_result.get('success_score', 0.5)
                    
                    # Validate and clamp values to [0, 1] range
                    similarity = max(0.0, min(1.0, similarity))
                    success_score = max(0.0, min(1.0, success_score))
                    
                    # If similar query was successful, lower threshold
                    # Quick Win 4: Increased threshold reduction from 0.10 to 0.15 for proven patterns
                    if similarity >= 0.75 and success_score > 0.8:
                        threshold -= 0.15  # Lower threshold for proven patterns (increased from 0.10)
                        logger.debug(
                            f"Historical success detected (similarity={similarity:.2f}, "
                            f"success={success_score:.2f}) - lowering threshold by 0.15"
                        )
            except Exception as e:
                logger.debug(f"RAG historical check failed in adaptive threshold: {e}")

        # Adjust based on user preferences (2025: type-safe with Literal if using Pydantic)
        if user_preferences:
            risk_tolerance: str = user_preferences.get('risk_tolerance', 'medium')
            if risk_tolerance == 'high':  # User wants fewer questions
                threshold -= 0.10
            elif risk_tolerance == 'low':  # User wants more certainty
                threshold += 0.10

        # Clamp to safe range [0.65, 0.95]
        threshold = min(0.95, max(0.65, threshold))

        logger.debug(
            f"Adaptive threshold calculated: {threshold:.2f} "
            f"(base: {base_threshold:.2f}, complexity: {complexity}, "
            f"ambiguities: {ambiguity_count})"
        )

        return threshold
    
    def _calculate_entity_quality_boost(self, extracted_entities: list[dict[str, Any]]) -> float:
        """
        Medium Win 2: Calculate confidence boost based on entity match quality.
        
        Factors:
        - Entity ID presence (exact matches are high quality)
        - Device intelligence data (capabilities, health scores)
        - Semantic similarity scores
        - Extraction confidence
        
        Args:
            extracted_entities: List of extracted entities
            
        Returns:
            Quality boost (0.0 to 0.15)
        """
        if not extracted_entities:
            return 0.0
        
        quality_indicators = []
        
        for entity in extracted_entities:
            entity_quality = 0.0
            
            # Has entity_id? (exact match = high quality)
            if entity.get('entity_id'):
                entity_quality += 0.4
            
            # Has device intelligence data?
            if entity.get('capabilities'):
                entity_quality += 0.2
            if entity.get('health_score') is not None:
                entity_quality += 0.1
            
            # High extraction confidence?
            extraction_confidence = entity.get('confidence', 0.5)
            if extraction_confidence > 0.8:
                entity_quality += 0.2
            elif extraction_confidence > 0.6:
                entity_quality += 0.1
            
            # High semantic similarity?
            similarity = entity.get('similarity', entity.get('match_score', 0.0))
            if similarity > 0.85:
                entity_quality += 0.1
            
            quality_indicators.append(min(1.0, entity_quality))
        
        # Average quality across all entities
        avg_quality = sum(quality_indicators) / len(quality_indicators) if quality_indicators else 0.0
        
        # Boost: up to 15% based on average quality
        # High quality entities (avg > 0.7) get full boost
        # Medium quality (avg > 0.5) get partial boost
        if avg_quality > 0.7:
            return 0.15
        elif avg_quality > 0.5:
            return 0.10
        elif avg_quality > 0.3:
            return 0.05
        else:
            return 0.0

