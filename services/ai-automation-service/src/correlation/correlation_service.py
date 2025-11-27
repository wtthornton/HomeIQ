"""
Unified Correlation Service

Epic 36, Story 36.6: Unified Correlation Service
Epic 37, Story 37.2: Vector Database Integration
Orchestrates TabPFN, streaming tracker, feature extractor, cache, and vector database
to provide unified correlation analysis API.

Single-home NUC optimized:
- Memory: <90MB total (all components including vector DB)
- Performance: 100-1000x faster than O(n²) matrix
- Similarity search: Fast vector search for <10k correlations
- Real-time updates: O(1) per event
"""

import logging
from typing import Optional, List, Tuple
import numpy as np
from datetime import datetime

from .tabpfn_predictor import TabPFNCorrelationPredictor
from .streaming_tracker import StreamingCorrelationTracker
from .feature_extractor import CorrelationFeatureExtractor
from .correlation_cache import CorrelationCache

try:
    from .vector_db import CorrelationVectorDatabase, FAISS_AVAILABLE
except ImportError:
    CorrelationVectorDatabase = None
    FAISS_AVAILABLE = False

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
    - Vector database (similarity search for <10k correlations)
    
    Single-home optimization:
    - Lightweight components
    - SQLite-backed cache (no Redis needed)
    - In-memory streaming statistics
    - FAISS flat index for vector search (CPU-only, simple)
    """
    
    def __init__(
        self,
        cache_db_path: Optional[str] = None,
        data_api_client: Optional[object] = None,
        calendar_integration: Optional[object] = None,
        enable_tabpfn: bool = True,
        enable_streaming: bool = True,
        enable_vector_db: bool = True
    ):
        """
        Initialize correlation service.
        
        Args:
            cache_db_path: Path to SQLite cache database
            data_api_client: Optional data API client for external data
            calendar_integration: Optional calendar integration for presence features (Epic 38)
            enable_tabpfn: Enable TabPFN predictor (default: True)
            enable_streaming: Enable streaming tracker (default: True)
            enable_vector_db: Enable vector database for similarity search (default: True)
        """
        # Initialize components
        self.tabpfn_predictor = TabPFNCorrelationPredictor(device_only=True) if enable_tabpfn else None
        self.streaming_tracker = StreamingCorrelationTracker() if enable_streaming else None
        self.feature_extractor = CorrelationFeatureExtractor(
            data_api_client,
            calendar_integration=calendar_integration
        )
        self.cache = CorrelationCache(cache_db_path)
        self.calendar_integration = calendar_integration
        
        # Vector database (Epic 37)
        if enable_vector_db and FAISS_AVAILABLE and CorrelationVectorDatabase:
            try:
                self.vector_db = CorrelationVectorDatabase(vector_dim=32)
                self.enable_vector_db = True
            except Exception as e:
                logger.warning("Failed to initialize vector database: %s", e)
                self.vector_db = None
                self.enable_vector_db = False
        else:
            self.vector_db = None
            self.enable_vector_db = False
        
        self.enable_tabpfn = enable_tabpfn
        self.enable_streaming = enable_streaming
        
        # Hyperparameter optimization support (Epic 37)
        self._tabpfn_threshold = 0.5  # Default threshold
        self._feature_weights = None  # Feature weights (set by optimizer)
        
        logger.info(
            "CorrelationService initialized (tabpfn=%s, streaming=%s, vector_db=%s, calendar=%s)",
            enable_tabpfn, enable_streaming, self.enable_vector_db,
            "enabled" if calendar_integration else "disabled"
        )
    
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
        
        # Update vector database with feature vector (Epic 37)
        if self.enable_vector_db and self.vector_db and entity1_metadata and entity2_metadata:
            try:
                # Extract feature vector
                features = self.feature_extractor.extract_pair_features(
                    entity1_metadata, entity2_metadata, timestamp=timestamp
                )
                # Convert features dict to numpy array (32-dim vector)
                feature_vector = self._features_to_vector(features)
                if feature_vector is not None:
                    self.vector_db.add_correlation_vector(
                        entity1_id, entity2_id, feature_vector
                    )
            except Exception as e:
                logger.debug("Failed to update vector database: %s", e)
        
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
        threshold: Optional[float] = None,
        max_predictions: Optional[int] = None
    ) -> list[tuple[dict, dict, float]]:
        """
        Predict which entity pairs are likely correlated (using TabPFN).
        
        Instead of computing O(n²) correlations, predicts likely pairs
        and only computes those (~1% of pairs).
        
        Args:
            entities: List of entity metadata dicts
            usage_stats: Optional usage statistics
            threshold: Minimum prediction probability (uses optimized threshold if None)
            max_predictions: Maximum number of predictions
        
        Returns:
            List of (entity1, entity2, probability) tuples
        """
        if not self.enable_tabpfn or not self.tabpfn_predictor:
            # Fallback: return all pairs (no prediction)
            logger.warning("TabPFN not enabled, returning all pairs")
            threshold = threshold or self._tabpfn_threshold
            return self._get_all_pairs(entities, threshold)
        
        # Use optimized threshold if not specified
        if threshold is None:
            threshold = self._tabpfn_threshold
        
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
        min_correlation: Optional[float] = None,
        use_cache: bool = True
    ) -> dict[tuple[str, str], float]:
        """
        Get all correlations above threshold.
        
        Args:
            entity_ids: Optional list of entity IDs (None = all)
            min_correlation: Minimum correlation threshold (uses optimized if None)
            use_cache: Whether to use cache
        
        Returns:
            Dict mapping (entity1_id, entity2_id) -> correlation
        """
        if self.enable_streaming and self.streaming_tracker:
            # Use optimized min_correlation if available
            if min_correlation is None and hasattr(self.streaming_tracker, '_optimized_min_correlation'):
                min_correlation = self.streaming_tracker._optimized_min_correlation
            elif min_correlation is None:
                min_correlation = 0.3  # Default
            
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
    
    def search_similar_correlations(
        self,
        entity1_id: str,
        entity2_id: str,
        entity1_metadata: Optional[dict] = None,
        entity2_metadata: Optional[dict] = None,
        k: int = 10,
        min_similarity: Optional[float] = None
    ) -> List[Tuple[str, str, float]]:
        """
        Search for correlations similar to a given entity pair (Epic 37).
        
        Uses vector similarity search instead of linear search for better performance.
        
        Args:
            entity1_id: Entity 1 ID
            entity2_id: Entity 2 ID
            entity1_metadata: Optional entity 1 metadata
            entity2_metadata: Optional entity 2 metadata
            k: Number of similar correlations to return
            min_similarity: Optional minimum similarity threshold (L2 distance)
        
        Returns:
            List of (entity1_id, entity2_id, distance) tuples
        """
        if not self.enable_vector_db or not self.vector_db:
            logger.debug("Vector database not enabled, returning empty results")
            return []
        
        try:
            # Extract feature vector for query
            if entity1_metadata and entity2_metadata:
                features = self.feature_extractor.extract_pair_features(
                    entity1_metadata, entity2_metadata
                )
                query_vector = self._features_to_vector(features)
                if query_vector is not None:
                    # Search for similar correlations
                    return self.vector_db.search_similar_correlations(
                        query_vector, k=k, min_similarity=min_similarity
                    )
        except Exception as e:
            logger.debug("Failed to search similar correlations: %s", e)
        
        return []
    
    def _features_to_vector(self, features: dict) -> Optional[np.ndarray]:
        """
        Convert features dict to numpy array (32-dim vector).
        
        Args:
            features: Features dict from feature extractor
        
        Returns:
            32-dim numpy array or None if conversion fails
        """
        try:
            # Select 32 key features (or pad/truncate as needed)
            feature_list = [
                features.get('same_area', 0.0),
                features.get('same_domain', 0.0),
                features.get('same_device_type', 0.0),
                features.get('entity1_domain_encoded', 0.0),
                features.get('entity2_domain_encoded', 0.0),
                features.get('usage_frequency_1', 0.0),
                features.get('usage_frequency_2', 0.0),
                features.get('co_occurrence_count', 0.0),
                features.get('temperature', 0.0),
                features.get('humidity', 0.0),
                features.get('carbon_intensity', 0.0),
                features.get('electricity_price', 0.0),
                features.get('air_quality_index', 0.0),
                features.get('hour_of_day', 0.0),
                features.get('day_of_week', 0.0),
                features.get('is_weekend', 0.0),
                # Add more features or pad to 32
            ]
            
            # Pad or truncate to 32 dimensions
            while len(feature_list) < 32:
                feature_list.append(0.0)
            feature_list = feature_list[:32]
            
            return np.array(feature_list, dtype=np.float32)
        except Exception as e:
            logger.debug("Failed to convert features to vector: %s", e)
            return None
    
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
        
        # Vector database: ~30MB (Epic 37)
        if self.enable_vector_db and self.vector_db:
            total += self.vector_db.get_memory_usage_mb()
        
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
        if self.enable_vector_db and self.vector_db:
            self.vector_db.clear()  # Clear vector database on close
        logger.info("CorrelationService closed")

