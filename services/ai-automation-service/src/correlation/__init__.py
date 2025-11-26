"""
Correlation Analysis Module

Epic 36: Correlation Analysis Foundation
Implements foundational correlation analysis using TabPFN and streaming learning
for 100-1000x performance improvements in pattern/synergy detection.

Single-home NUC optimized:
- ~50-100 devices (1,225-4,950 pairs)
- Memory: <60MB total
- Real-time correlation updates (O(1) per event)
"""

from .tabpfn_predictor import TabPFNCorrelationPredictor
from .streaming_tracker import StreamingCorrelationTracker
from .feature_extractor import CorrelationFeatureExtractor
from .correlation_cache import CorrelationCache
from .correlation_service import CorrelationService
from .integration import CorrelationPatternEnhancer, CorrelationSynergyEnhancer

__all__ = [
    'TabPFNCorrelationPredictor',
    'StreamingCorrelationTracker',
    'CorrelationFeatureExtractor',
    'CorrelationCache',
    'CorrelationService',
    'CorrelationPatternEnhancer',
    'CorrelationSynergyEnhancer'
]

