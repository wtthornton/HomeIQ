"""
Device Capability RAG Context Service

Epic: Platform-Wide Pattern Rollout, Story 9
Extends RAGContextService to inject device-specific capability patterns
when suggesting features for specific device types (WLED, Hue, Sonoff, etc.).
"""

import logging
import sys
from pathlib import Path

try:
    _project_root = str(Path(__file__).resolve().parents[4])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
except IndexError:
    pass  # Docker: PYTHONPATH already includes /app

from shared.patterns import RAGContextService

logger = logging.getLogger(__name__)

DEVICE_CAPABILITY_KEYWORDS = (
    # WLED
    "wled", "effect_list", "segment", "led strip", "addressable led",
    # Hue
    "hue scene", "hue group", "hue room", "hue zone", "hue effect",
    # Smart plugs
    "smart plug", "power monitoring", "energy monitoring", "power meter",
    "consumption", "wattage",
    # Sonoff / Shelly / Tasmota
    "sonoff", "shelly", "tasmota", "esphome",
    # Covers / blinds
    "cover", "blind", "curtain", "roller shutter", "tilt",
    # Media
    "media_player", "speaker", "chromecast", "sonos", "tts",
    # Sensors
    "sensor automation", "sensor trigger", "threshold", "numeric_state",
)


class DeviceCapabilityRAGService(RAGContextService):
    """
    Injects device capability patterns when the user prompt mentions
    specific device types or capability-related keywords.
    """

    name = "device_capability"
    keywords = DEVICE_CAPABILITY_KEYWORDS
    corpus_path = Path(__file__).parent.parent / "data" / "device_capability_patterns.md"

    def __init__(self) -> None:
        super().__init__()

    def format_context(self, corpus: str) -> str:
        return (
            "\n---\n\nAUTOMATION RAG CONTEXT (Device Capability patterns):\n"
            "Use these device-specific patterns for feature suggestions and automations:\n\n"
            f"{corpus}\n\n---\n"
        )
