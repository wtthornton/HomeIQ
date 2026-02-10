"""
Device Setup RAG Context Service

Epic: High-Value Domain Extensions, Story 6
Extends RAGContextService to inject device setup guides when user prompts
mention device configuration keywords (Zigbee, Hue, Z-Wave, MQTT, etc.).
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

DEVICE_SETUP_KEYWORDS = (
    # Protocols / standards
    "zigbee", "z-wave", "zwave", "matter", "thread", "bluetooth", "ble",
    "wifi", "wi-fi",
    # Bridges / coordinators
    "hue", "hue bridge", "philips hue", "conbee", "sonoff", "skyconnect",
    "coordinator", "dongle", "usb stick",
    # MQTT
    "mqtt", "mosquitto", "zigbee2mqtt", "z2m",
    # Setup actions
    "pairing", "pair", "setup", "set up", "configure", "add device",
    "discover", "discovery", "commissioning", "inclusion", "interview",
    "join network",
    # Integration management
    "integration", "add integration", "install integration",
    # Troubleshooting
    "device not found", "pairing failed", "not responding",
    "unavailable device", "offline device",
)


class DeviceSetupRAGService(RAGContextService):
    """
    Injects device setup and pairing corpus when user prompt
    mentions device configuration keywords.
    """

    name = "device_setup"
    keywords = DEVICE_SETUP_KEYWORDS
    corpus_path = Path(__file__).parent.parent / "data" / "device_setup_patterns.md"

    def __init__(self) -> None:
        super().__init__()

    def format_context(self, corpus: str) -> str:
        """Format device setup corpus with domain-specific header."""
        return (
            "\n---\n\nAUTOMATION RAG CONTEXT (Device Setup patterns):\n"
            "Use these guides when helping with device setup and configuration:\n\n"
            f"{corpus}\n\n---\n"
        )
