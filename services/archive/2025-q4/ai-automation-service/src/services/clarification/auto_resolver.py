"""
Auto Resolver Service - Orchestrates intelligent auto-resolution of ambiguities

2025 Best Practices:
- Full type hints (PEP 484/526)
- Async/await for all I/O operations
- Comprehensive observability (metrics tracking)
- Hybrid RAG retrieval for pattern matching
- Embedding-based similarity matching
"""

import logging
import time
from typing import Any

from .models import Ambiguity, AmbiguitySeverity

logger = logging.getLogger(__name__)


class AutoResolver:
    """
    Orchestrates intelligent auto-resolution of ambiguities.
    
    Coordinates multiple resolution strategies:
    1. Location-based resolution
    2. Historical pattern matching (RAG)
    3. User preference matching
    4. Embedding-based similarity
    """

    def __init__(
        self,
        detector: Any,  # ClarificationDetector
        rag_client: Any | None = None,
        uncertainty_quantifier: Any | None = None
    ):
        """
        Initialize auto resolver.
        
        Args:
            detector: ClarificationDetector instance with auto_resolve_ambiguities method
            rag_client: Optional RAG client for historical pattern lookup
            uncertainty_quantifier: Optional uncertainty quantifier for confidence bounds
        """
        self.detector = detector
        self.rag_client = rag_client
        self.uncertainty_quantifier = uncertainty_quantifier

    async def resolve_ambiguities(
        self,
        ambiguities: list[Ambiguity],
        query: str,
        extracted_entities: list[dict[str, Any]],
        available_devices: dict[str, Any],
        user_preferences: list[dict[str, Any]] | None = None,
        min_confidence: float = 0.85
    ) -> tuple[list[Ambiguity], dict[str, dict[str, Any]]]:
        """
        Resolve ambiguities using intelligent auto-resolution.
        
        Uses multiple strategies in priority order:
        1. Location-based (highest confidence)
        2. Historical patterns (RAG)
        3. User preferences
        
        Args:
            ambiguities: List of detected ambiguities
            query: Original user query
            extracted_entities: Extracted entities from query
            available_devices: Available devices/entities in system
            user_preferences: Optional user preferences for auto-resolution
            min_confidence: Minimum confidence threshold for auto-resolution (default: 0.85)
            
        Returns:
            Tuple of (remaining_ambiguities, auto_resolved_answers)
            auto_resolved_answers maps ambiguity_id to resolution dict with:
            - 'entities': List of selected entity IDs
            - 'confidence': Confidence score (0.0-1.0)
            - 'method': Resolution method used ('location', 'historical_pattern', 'user_preference')
            - 'reason': Human-readable explanation
            - 'latency_ms': Resolution latency in milliseconds
        """
        if not ambiguities:
            return [], {}
        
        start_time = time.time()
        
        # Use detector's auto_resolve_ambiguities method
        remaining, auto_resolved = await self.detector.auto_resolve_ambiguities(
            ambiguities=ambiguities,
            query=query,
            extracted_entities=extracted_entities,
            available_devices=available_devices,
            rag_client=self.rag_client,
            user_preferences=user_preferences
        )
        
        # Filter by minimum confidence threshold
        filtered_resolved = {}
        for amb_id, resolution in auto_resolved.items():
            confidence = resolution.get('confidence', 0.0)
            if confidence >= min_confidence:
                # Add latency to resolution
                resolution['latency_ms'] = (time.time() - start_time) * 1000
                filtered_resolved[amb_id] = resolution
            else:
                # Confidence too low - add back to remaining
                remaining.append(next(amb for amb in ambiguities if amb.id == amb_id))
                logger.debug(
                    f"Auto-resolution confidence {confidence:.2f} below threshold {min_confidence:.2f} "
                    f"for ambiguity {amb_id}"
                )
        
        # Calculate uncertainty bounds if quantifier available
        if self.uncertainty_quantifier:
            for amb_id, resolution in filtered_resolved.items():
                try:
                    # Get historical confidence data (empty for now, could be enhanced)
                    historical_data = []  # TODO: Fetch from database if available
                    
                    uncertainty = self.uncertainty_quantifier.calculate_uncertainty(
                        raw_confidence=resolution['confidence'],
                        historical_data=historical_data,
                        confidence_level=0.90
                    )
                    
                    # Add uncertainty bounds to resolution
                    resolution['uncertainty'] = {
                        'lower_bound': uncertainty.lower_bound,
                        'upper_bound': uncertainty.upper_bound,
                        'std': uncertainty.std
                    }
                except Exception as e:
                    logger.debug(f"Uncertainty calculation failed for {amb_id}: {e}")
        
        latency_ms = (time.time() - start_time) * 1000
        logger.info(
            f"🔍 Auto-resolution complete: {len(filtered_resolved)} resolved, "
            f"{len(remaining)} remaining (latency: {latency_ms:.1f}ms)"
        )
        
        return remaining, filtered_resolved

    def should_skip_question(
        self,
        ambiguity: Ambiguity,
        confidence: float,
        adaptive_threshold: float
    ) -> bool:
        """
        Determine if a question should be skipped based on ambiguity severity and confidence.
        
        Uses 2025 best practice: severity-based filtering.
        
        Args:
            ambiguity: Ambiguity to check
            confidence: Current confidence score
            adaptive_threshold: Adaptive confidence threshold
            
        Returns:
            True if question should be skipped, False otherwise
        """
        # Always ask for CRITICAL ambiguities (unless auto-resolved)
        if ambiguity.severity == AmbiguitySeverity.CRITICAL:
            return False
        
        # Skip OPTIONAL ambiguities if confidence is high
        if ambiguity.severity == AmbiguitySeverity.OPTIONAL:
            return confidence >= adaptive_threshold
        
        # For IMPORTANT ambiguities, use adaptive threshold
        if ambiguity.severity == AmbiguitySeverity.IMPORTANT:
            return confidence >= adaptive_threshold
        
        return False

    def filter_ambiguities_by_severity(
        self,
        ambiguities: list[Ambiguity],
        confidence: float,
        adaptive_threshold: float
    ) -> list[Ambiguity]:
        """
        Filter ambiguities based on severity and confidence.
        
        Skips questions for:
        - OPTIONAL ambiguities when confidence >= threshold
        - IMPORTANT ambiguities when confidence >= threshold (with some margin)
        
        Always asks for:
        - CRITICAL ambiguities
        
        Args:
            ambiguities: List of ambiguities to filter
            confidence: Current confidence score
            adaptive_threshold: Adaptive confidence threshold
            
        Returns:
            Filtered list of ambiguities that should trigger questions
        """
        filtered = []
        
        for amb in ambiguities:
            if not self.should_skip_question(amb, confidence, adaptive_threshold):
                filtered.append(amb)
            else:
                logger.debug(
                    f"Skipping question for {amb.id} ({amb.severity.value}): "
                    f"confidence {confidence:.2f} >= threshold {adaptive_threshold:.2f}"
                )
        
        return filtered

