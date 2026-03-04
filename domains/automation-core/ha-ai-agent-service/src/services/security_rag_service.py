"""
Security RAG Context Service

Epic: Platform-Wide Pattern Rollout, Story 1
Extends RAGContextService to inject security automation patterns when
user prompts mention security-related keywords.
"""

import logging
from pathlib import Path

from homeiq_patterns import RAGContextService

logger = logging.getLogger(__name__)

SECURITY_KEYWORDS = (
    # Devices
    "camera", "alarm", "lock", "doorbell", "siren", "keypad",
    "alarm_control_panel",
    # Sensors — "motion" replaced with multi-word to avoid "motion pictures" false positive
    "motion sensor", "motion detected", "motion alert", "occupancy", "presence", "person",
    "door sensor", "window sensor", "glass break",
    # Actions
    "arm", "disarm", "alert", "notify", "intrusion", "break-in",
    "security alert",
    # Geofencing / presence
    "geofence", "geofencing", "away mode", "away", "nobody home",
    "everyone left", "arrive home", "leave home",
    # Patterns
    "security automation", "security system", "alarm system",
    "surveillance", "protect", "guard",
)


class SecurityRAGService(RAGContextService):
    """
    Injects security automation corpus when user prompt contains
    security-related keywords.
    """

    name = "security"
    keywords = SECURITY_KEYWORDS
    min_score = 0.2  # Higher threshold to reduce false positives
    corpus_path = Path(__file__).parent.parent / "data" / "security_automation_patterns.md"

    def __init__(self) -> None:
        super().__init__()

    def format_context(self, corpus: str) -> str:
        return (
            "\n---\n\nAUTOMATION RAG CONTEXT (Security patterns):\n"
            "Use these proven patterns when generating security automations:\n\n"
            f"{corpus}\n\n---\n"
        )
