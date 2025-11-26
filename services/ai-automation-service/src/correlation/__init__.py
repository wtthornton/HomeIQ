"""
Correlation Analysis Module

Epic 36: Correlation Analysis Foundation
Epic 37: Correlation Analysis Optimization
Implements foundational correlation analysis using TabPFN, streaming learning,
and vector database for 100-1000x performance improvements.

Single-home NUC optimized:
- ~50-100 devices (1,225-4,950 pairs)
- Memory: <90MB total (including vector DB)
- Real-time correlation updates (O(1) per event)
- Vector similarity search for <10k correlations
"""

from .tabpfn_predictor import TabPFNCorrelationPredictor
from .streaming_tracker import StreamingCorrelationTracker
from .feature_extractor import CorrelationFeatureExtractor
from .correlation_cache import CorrelationCache
from .correlation_service import CorrelationService
from .integration import CorrelationPatternEnhancer, CorrelationSynergyEnhancer

try:
    from .vector_db import CorrelationVectorDatabase, FAISS_AVAILABLE
except ImportError:
    CorrelationVectorDatabase = None
    FAISS_AVAILABLE = False

from .state_history_client import StateHistoryClient
from .long_term_patterns import LongTermPatternDetector
from .automl_optimizer import AutoMLCorrelationOptimizer, HyperparameterConfig
from .hyperparameter_optimization import (
    CorrelationHyperparameterOptimizer,
    create_validation_data_from_correlations
)

__all__ = [
    'TabPFNCorrelationPredictor',
    'StreamingCorrelationTracker',
    'CorrelationFeatureExtractor',
    'CorrelationCache',
    'CorrelationService',
    'CorrelationPatternEnhancer',
    'CorrelationSynergyEnhancer',
    'CorrelationVectorDatabase',
    'FAISS_AVAILABLE',
    'StateHistoryClient',
    'LongTermPatternDetector',
    'AutoMLCorrelationOptimizer',
    'HyperparameterConfig',
    'CorrelationHyperparameterOptimizer',
    'create_validation_data_from_correlations'
]

