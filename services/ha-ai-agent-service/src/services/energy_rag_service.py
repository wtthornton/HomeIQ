"""
Energy RAG Context Service

Epic: High-Value Domain Extensions, Story 1
Extends RAGContextService to inject energy automation patterns when
user prompts mention energy-related keywords (TOU, solar, battery, etc.).
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

ENERGY_KEYWORDS = (
    # Utility / rate structure
    "electricity", "electric", "power bill", "utility", "tariff", "rate",
    "tou", "time-of-use", "time of use", "peak", "off-peak", "off peak",
    "mid-peak", "shoulder",
    # Solar
    "solar", "pv", "photovoltaic", "solar panel", "solar production",
    "solar export", "net metering", "feed-in",
    # Battery / storage
    "battery", "powerwall", "energy storage", "charge", "discharge",
    "state of charge", "soc",
    # EV charging
    "ev charging", "ev charger", "electric vehicle", "charger", "wallbox",
    # Energy metrics
    "kwh", "kw", "watt", "wh", "energy consumption", "energy usage",
    "power consumption", "demand",
    # Load management
    "load shift", "load shifting", "load shedding", "demand response",
    "grid", "export", "import",
    # Smart meter
    "smart meter", "meter reading",
)


class EnergyRAGService(RAGContextService):
    """
    Injects energy automation corpus when user prompt contains
    energy-related keywords (TOU, solar, battery, EV charging, etc.).
    """

    name = "energy"
    keywords = ENERGY_KEYWORDS
    corpus_path = Path(__file__).parent.parent / "data" / "energy_automation_patterns.md"

    def __init__(self) -> None:
        super().__init__()

    def format_context(self, corpus: str) -> str:
        """Format energy corpus with domain-specific header."""
        return (
            "\n---\n\nAUTOMATION RAG CONTEXT (Energy patterns):\n"
            "Use these proven patterns when generating energy-related automations:\n\n"
            f"{corpus}\n\n---\n"
        )
