"""
Synergy Detection Module

Detects cross-device automation opportunities and contextual patterns.

Epic AI-3: Cross-Device Synergy & Contextual Opportunities
Story AI3.1: Device Synergy Detector Foundation
Story AI3.2: Same-Area Device Pair Detection
Epic 39, Story 39.5: Extracted to ai-pattern-service.
"""

# Note: DevicePairAnalyzer and other modules will be copied in later stories
# For now, export the main detector
from .synergy_detector import DeviceSynergyDetector

__all__ = ['DeviceSynergyDetector']

