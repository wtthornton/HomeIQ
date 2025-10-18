"""
Synergy Detection Module

Detects cross-device automation opportunities and contextual patterns.

Epic AI-3: Cross-Device Synergy & Contextual Opportunities
Story AI3.1: Device Synergy Detector Foundation
Story AI3.2: Same-Area Device Pair Detection
"""

from .synergy_detector import DeviceSynergyDetector
from .device_pair_analyzer import DevicePairAnalyzer

__all__ = ['DeviceSynergyDetector', 'DevicePairAnalyzer']

