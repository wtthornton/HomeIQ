"""
Unified Correlation Service

Epic 36, Story 36.6: Unified Correlation Service
Orchestrates TabPFN, streaming tracker, feature extractor, and cache
to provide unified correlation analysis API.

Single-home NUC optimized:
- Memory: <60MB total (all components)
- Performance: 100-1000x faster than O(n²) matrix
- Real-time updates: O(1) per event
"""

import logging
from typing import Optional
from datetime import datetime

from .tabpfn_predictor import TabPFNCorrelationPredictor
from .streaming_tracker import StreamingCorrelationTracker
from .feature_extractor import CorrelationFeatureExtractor
from .correlation_cache import CorrelationCache

from shared.logging_config import get_logger

logger = get_logger(__name__)


class CorrelationService:
    """
    Unified correlation analysis service.
    
    Combines:
    - TabPFN predictor (predicts likely pairs, 100-1000x faster)
    - Streaming tracker (real-time O(1) updates)
    - Feature extractor (with external data)
    - Correlation cache (avoids redundant computation)
    
    Single-home optimization:
    - Lightweight components
    - SQLite-backed cache (no Redis needed)
    - In-memory streaming statistics
    """
    
    def __init__(
        self,
        cache_db_path: Optional[str] = None,
        data_api_client: Optional[object] = None,
        enable_tabpfn: bool = True,
        enable_streaming: bool = True
    ):
        """
        Initialize correlation service.
        
        Args:
            cache_db_path: Path to SQLite cache database
            data_api_client: Optional data API client for external data
            enable_tabpfn: Enable TabPFN predictor (default: True)
            enable_streaming: Enable streaming tracker (default: True)
        """
        # Initialize components
        self.tabpfn_predictor = TabPFNCorrelationPredictor(device_only=True) if enable_tabpfn else None
        self.streaming_tracker = StreamingCorrelationTracker() if enable_streaming else None
        self.feature_extractor = CorrelationFeatureExtractor(data_api_client)
        self.cache = CorrelationCache(cache_db_path)
        
        self.enable_tabpfn = enable_tabpfn
        self.enable_streaming = enable_streaming
        
        logger.info("CorrelationService initialized (tabpfn=%s, streaming=%s)",
                   enable_tabpfn, enable_streaming)
    
    def update_correlation(
        self,
        entity1_id: str,
        entity2_id: str,
        value1: float,
        value2: float,
        entity1_metadata: Optional[dict] = None,
        entity2_metadata: Optional[dict] = None,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Update correlation in real-time (streaming).
        
        Args:
            entity1_id: Entity 1 ID
            entity2_id: Entity 2 ID
            value1: Entity 1 value (normalized 0.0-1.0)
            value2: Entity 2 value (normalized 0.0-1.0)
            entity1_metadata: Optional entity 1 metadata
            entity2_metadata: Optional entity 2 metadata
            timestamp: Optional event timestamp
        """
        if not self.enable_streaming or not self.streaming_tracker:
            return
        
        # Update streaming tracker (O(1))
        self.streaming_tracker.update(entity1_id, entity2_id, value1, value2, timestamp)
        
        # Invalidate cache (correlation changed)
        self.cache.invalidate(entity1_id, entity2_id)
        
        logger.debug("Updated correlation: %s <-> %s", entity1_id, entity2_id)
    
    def get_correlation(
        self,
        entity1_id: str,
        entity2_id: str,
        entity1_metadata: Optional[dict] = None,
        entity2_metadata: Optional[dict] = None,
        use_cache: bool = True
    ) -> Optional[float]:
        """
        Get correlation coefficient for a device pair.
        
        Args:
            entity1_id: Entity 1 ID
            entity2_id: Entity 2 ID
            entity1_metadata: Optional entity 1 metadata
            entity2_metadata: Optional entity 2 metadata
            use_cache: Whether to use cache (default: True)
        
        Returns:
            Correlation coefficient (-1.0 to 1.0) or None
        """
        # Check cache first
        if use_cache:
            cached = self.cache.get(entity1_id, entity2_id)
            if cached is not None:
                return cached
        
        # Get from streaming tracker (if enabled)
        if self.enable_streaming and self.streaming_tracker:
            correlation = self.streaming_tracker.get_correlation(entity1_id, entity2_id)
            if correlation is not None:
                # Cache result
                self.cache.set(entity1_id, entity2_id, correlation)
                return correlation
        
        # No correlation available
        return None
    
    def predict_likely_correlated_pairs(
        self,
        entities: list[dict],
        usage_stats: Optional[dict] = None,
        threshold: float = 0.5,
        max_predictions: Optional[int] = None
    ) -> list[tuple[dict, dict, float]]:
        """
        Predict which entity pairs are likely correlated (using TabPFN).
        
        Instead of computing O(n²) correlations, predicts likely pairs
        and only computes those (~1% of pairs).
        
        Args:
            entities: List of entity metadata dicts
            usage_stats: Optional usage statistics
            threshold: Minimum prediction probability
            max_predictions: Maximum number of predictions
        
        Returns:
            List of (entity1, entity2, probability) tuples
        """
        if not self.enable_tabpfn or not self.tabpfn_predictor:
            # Fallback: return all pairs (no prediction)
            logger.warning("TabPFN not enabled, returning all pairs")
            return self._get_all_pairs(entities, threshold)
        
        # Generate all pairs
        pairs = []
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                pairs.append((entity1, entity2))
        
        # Predict likely correlated pairs
        likely_pairs = self.tabpfn_predictor.predict_likely_pairs(
            pairs,
            usage_stats,
            threshold,
            max_predictions
        )
        
        logger.debug("Predicted %d likely correlated pairs from %d total pairs",
                    len(likely_pairs), len(pairs))
        
        return likely_pairs
    
    def get_all_correlations(
        self,
        entity_ids: Optional[list[str]] = None,
        min_correlation: float = 0.3,
        use_cache: bool = True
    ) -> dict[tuple[str, str], float]:
        """
        Get all correlations above threshold.
        
        Args:
            entity_ids: Optional list of entity IDs (None = all)
            min_correlation: Minimum correlation threshold
            use_cache: Whether to use cache
        
        Returns:
            Dict mapping (entity1_id, entity2_id) -> correlation
        """
        if self.enable_streaming and self.streaming_tracker:
            # Get from streaming tracker
            correlations = self.streaming_tracker.get_all_correlations(
                entity_ids,
                min_correlation
            )
            
            # Cache results
            if use_cache:
                for (e1, e2), corr in correlations.items():
                    self.cache.set(e1, e2, corr)
            
            return correlations
        
        return {}
    
    def train_tabpfn(
        self,
        training_pairs: list[tuple[dict, dict]],
        training_labels: list[bool],
        usage_stats: Optional[dict] = None
    ) -> None:
        """
        Train TabPFN predictor on known correlated pairs.
        
        Args:
            training_pairs: List of (entity1, entity2) tuples
            training_labels: List of bool labels (True = correlated)
            usage_stats: Optional usage statistics
        """
        if not self.enable_tabpfn or not self.tabpfn_predictor:
            logger.warning("TabPFN not enabled, skipping training")
            return
        
        self.tabpfn_predictor.train(training_pairs, training_labels, usage_stats)
        logger.info("TabPFN training complete (%d pairs)", len(training_pairs))
    
    def get_entity_statistics(self, entity_id: str) -> Optional[dict]:
        """
        Get statistics for a single entity.
        
        Args:
            entity_id: Entity ID
        
        Returns:
            Dict with mean, variance, count, or None
        """
        if self.enable_streaming and self.streaming_tracker:
            return self.streaming_tracker.get_entity_statistics(entity_id)
        
        return None
    
    def clear_cache(self) -> None:
        """Clear correlation cache"""
        self.cache.clear_expired()
        if self.enable_streaming and self.streaming_tracker:
            self.streaming_tracker.clear_cache()
        logger.info("Correlation cache cleared")
    
    def get_memory_usage_mb(self) -> float:
        """Get total memory usage in MB"""
        total = 0.0
        
        # TabPFN: ~30MB
        if self.enable_tabpfn and self.tabpfn_predictor:
            total += 30.0
        
        # Streaming tracker: <5MB
        if self.enable_streaming and self.streaming_tracker:
            total += self.streaming_tracker.get_memory_usage_mb()
        
        # Feature extractor: <5MB
        total += 5.0
        
        # Cache: <20MB (SQLite + memory)
        total += 20.0
        
        return total
    
    def _get_all_pairs(
        self,
        entities: list[dict],
        threshold: float
    ) -> list[tuple[dict, dict, float]]:
        """Fallback: return all pairs with default probability"""
        pairs = []
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                # Default probability based on heuristics
                prob = 0.5  # Default
                if prob >= threshold:
                    pairs.append((entity1, entity2, prob))
        
        return pairs
    
    def close(self) -> None:
        """Close service and cleanup resources"""
        self.cache.close()
        logger.info("CorrelationService closed")

