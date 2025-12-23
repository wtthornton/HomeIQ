"""
N-Level Synergy Detection Module

Epic AI-4: Multi-hop automation chain discovery using HuggingFace models.

This module provides:
- Device embedding generation (Story AI4.1)
- Multi-hop path discovery (Story AI4.2)
- Path re-ranking (Story AI4.3)
- Chain classification (Story AI4.4)

Usage:
    from nlevel_synergy import NLevelSynergyDetector
    
    detector = NLevelSynergyDetector(db_session, data_api_client)
    synergies = await detector.detect_nlevel_synergies(devices, max_depth=3)
"""

__version__ = "1.0.0"
__author__ = "AI Automation Team"

from .descriptor_builder import DeviceDescriptorBuilder
from .device_embedding_generator import DeviceEmbeddingGenerator
from .embedding_cache import EmbeddingCache
from .embedding_model import DeviceEmbeddingModel

__all__ = [
    'DeviceDescriptorBuilder',
    'DeviceEmbeddingModel',
    'EmbeddingCache',
    'DeviceEmbeddingGenerator',
]

