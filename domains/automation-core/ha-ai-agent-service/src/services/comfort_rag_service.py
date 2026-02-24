"""
Comfort RAG Context Service

Epic: Platform-Wide Pattern Rollout, Story 2
Extends RAGContextService to inject comfort/climate automation patterns when
user prompts mention HVAC, thermostat, or comfort keywords.
"""

from pathlib import Path
import logging

from homeiq_patterns import RAGContextService

logger = logging.getLogger(__name__)

COMFORT_KEYWORDS = (
    # HVAC — "cool" replaced with multi-word to avoid "cool app" false positive
    "thermostat", "hvac", "heat", "heating", "cool down", "cooling", "cooling mode",
    "air conditioning", "ac", "furnace", "boiler",
    # Climate control
    "climate", "temperature", "humidity", "setpoint", "set point",
    "fan", "fan speed", "ventilation",
    # Scheduling
    "schedule", "scheduled", "morning routine", "night mode", "sleep mode",
    "bedtime", "wake up",
    # Modes
    "eco mode", "comfort mode", "away mode thermostat", "vacation mode",
    "occupied", "unoccupied",
    # Zones
    "zone", "multi-zone", "room temperature", "floor heating",
    # Comfort
    "comfort", "cozy", "warm", "cold",
)


class ComfortRAGService(RAGContextService):
    """
    Injects comfort/climate automation corpus when user prompt contains
    HVAC and comfort-related keywords.
    """

    name = "comfort"
    keywords = COMFORT_KEYWORDS
    corpus_path = Path(__file__).parent.parent / "data" / "comfort_automation_patterns.md"

    def __init__(self) -> None:
        super().__init__()

    def format_context(self, corpus: str) -> str:
        return (
            "\n---\n\nAUTOMATION RAG CONTEXT (Comfort/Climate patterns):\n"
            "Use these proven patterns when generating comfort and climate automations:\n\n"
            f"{corpus}\n\n---\n"
        )
