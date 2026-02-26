"""
RAG Context Services for Proactive Agent

Epic: Platform-Wide Pattern Rollout, Story 3
Closes the RAGContextRegistry integration gap for proactive-agent-service.

Three RAGContextService subclasses provide domain-specific corpus injection
into the LLM prompt when generating proactive automation suggestions.
"""

import logging
from pathlib import Path

from homeiq_patterns import RAGContextService

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"

ENERGY_SAVINGS_KEYWORDS = (
    "energy", "electricity", "solar", "battery", "peak", "off-peak",
    "tariff", "tou", "time-of-use", "kwh", "power bill", "smart meter",
    "load shift", "demand response", "carbon", "grid", "ev charging",
    "consumption", "standby", "export", "self-consumption",
)


class EnergySavingsRAGService(RAGContextService):
    """Injects energy savings patterns for proactive suggestions."""

    name = "energy_savings"
    keywords = ENERGY_SAVINGS_KEYWORDS
    corpus_path = DATA_DIR / "energy_savings_patterns.md"

    def __init__(self) -> None:
        super().__init__()

    def format_context(self, corpus: str) -> str:
        return (
            "\n---\n\nPROACTIVE RAG CONTEXT (Energy savings):\n"
            "Use these patterns for energy-related proactive suggestions:\n\n"
            f"{corpus}\n\n---\n"
        )


SECURITY_KEYWORDS = (
    "security", "alarm", "lock", "camera", "motion", "presence",
    "away", "intrusion", "doorbell", "surveillance", "geofence",
    "arm", "disarm", "notification", "vacation", "door",
    "window sensor", "siren",
)


class SecurityBestPracticesRAGService(RAGContextService):
    """Injects security best practices for proactive suggestions."""

    name = "security_best_practices"
    keywords = SECURITY_KEYWORDS
    corpus_path = DATA_DIR / "security_best_practices.md"

    def __init__(self) -> None:
        super().__init__()

    def format_context(self, corpus: str) -> str:
        return (
            "\n---\n\nPROACTIVE RAG CONTEXT (Security best practices):\n"
            "Use these patterns for security-related proactive suggestions:\n\n"
            f"{corpus}\n\n---\n"
        )


COMFORT_KEYWORDS = (
    "comfort", "temperature", "humidity", "thermostat", "climate",
    "heating", "cooling", "schedule", "seasonal", "occupancy",
    "sleep", "morning", "routine", "scene", "lighting", "ventilation",
    "air quality", "blinds", "fan",
)


class ComfortOptimizationRAGService(RAGContextService):
    """Injects comfort optimization patterns for proactive suggestions."""

    name = "comfort_optimization"
    keywords = COMFORT_KEYWORDS
    corpus_path = DATA_DIR / "comfort_optimization_patterns.md"

    def __init__(self) -> None:
        super().__init__()

    def format_context(self, corpus: str) -> str:
        return (
            "\n---\n\nPROACTIVE RAG CONTEXT (Comfort optimization):\n"
            "Use these patterns for comfort-related proactive suggestions:\n\n"
            f"{corpus}\n\n---\n"
        )
