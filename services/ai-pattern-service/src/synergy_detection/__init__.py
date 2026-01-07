"""
Synergy Detection Module

Detects cross-device automation opportunities and contextual patterns.

Epic AI-3: Cross-Device Synergy & Contextual Opportunities
Story AI3.1: Device Synergy Detector Foundation
Story AI3.2: Same-Area Device Pair Detection
Epic 39, Story 39.5: Extracted to ai-pattern-service.

Refactored Architecture:
- synergy_detector.py: Main orchestrator and pairwise detection
- chain_detection.py: 3-device and 4-device chain detection
- scene_detection.py: Scene-based synergy detection
- context_detection.py: Context-aware synergy detection (weather, energy)
"""

from .synergy_detector import DeviceSynergyDetector
from .chain_detection import ChainDetector
from .scene_detection import SceneDetector
from .context_detection import ContextAwareDetector

__all__ = [
    'DeviceSynergyDetector',
    'ChainDetector',
    'SceneDetector',
    'ContextAwareDetector',
]

