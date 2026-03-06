"""Pytest configuration for ML embedding tests.

This module provides fixtures for embedding compatibility testing across
sentence-transformers version upgrades.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest

if TYPE_CHECKING:
    pass

FIXTURES_DIR = Path(__file__).parent / "fixtures"
REFERENCE_EMBEDDINGS_DIR = FIXTURES_DIR / "reference_embeddings"


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers for ML tests."""
    config.addinivalue_line(
        "markers",
        "embedding_regression: marks tests as embedding regression tests (may require model download)",
    )
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    )


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Return path to ML test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def reference_embeddings_dir() -> Path:
    """Return path to reference embeddings directory."""
    return REFERENCE_EMBEDDINGS_DIR


@pytest.fixture(scope="session")
def test_sentences() -> list[str]:
    """Load canonical test sentences for embedding comparison.

    These sentences cover HomeIQ use cases:
    - Device control commands
    - Time-based patterns
    - Conditional logic
    - Device types and states
    - Complex automations
    """
    sentences_file = FIXTURES_DIR / "test_sentences.json"
    if sentences_file.exists():
        with open(sentences_file, encoding="utf-8") as f:
            return json.load(f)

    # Fallback to default sentences if fixture not found
    return _get_default_test_sentences()


def _get_default_test_sentences() -> list[str]:
    """Return default test sentences for embedding comparison."""
    return [
        # Device control (20 sentences)
        "Turn on the living room lights",
        "Set the thermostat to 72 degrees",
        "Turn off all lights in the bedroom",
        "Open the garage door",
        "Close the blinds in the office",
        "Lock the front door",
        "Unlock the back door",
        "Start the dishwasher",
        "Stop the washing machine",
        "Dim the kitchen lights to 50%",
        "Set the fan speed to high",
        "Turn on the coffee maker",
        "Activate the security system",
        "Deactivate the alarm",
        "Play music in the living room",
        "Pause the TV",
        "Resume playback",
        "Mute all speakers",
        "Set volume to 70%",
        "Toggle the porch light",

        # Time-based patterns (15 sentences)
        "Every morning at 7am",
        "When I arrive home",
        "At sunset",
        "Between 10pm and 6am",
        "Every weekday at 8:30am",
        "On weekends after noon",
        "30 minutes before sunrise",
        "Every hour on the hour",
        "First Monday of each month",
        "During business hours",
        "At midnight",
        "Every 15 minutes",
        "When it gets dark outside",
        "One hour after I leave",
        "At the end of the day",

        # Conditional logic (15 sentences)
        "If temperature is above 75 degrees",
        "When motion is detected",
        "If humidity exceeds 60%",
        "When door is opened",
        "If someone is home",
        "When battery is low",
        "If it starts raining",
        "When smoke is detected",
        "If power usage is high",
        "When no motion for 30 minutes",
        "If temperature drops below 60",
        "When window is open",
        "If air quality is poor",
        "When water leak detected",
        "If carbon monoxide detected",

        # Device types (15 sentences)
        "light switch bedroom",
        "temperature sensor kitchen",
        "motion detector hallway",
        "smart plug office",
        "door sensor garage",
        "window sensor living room",
        "smoke detector basement",
        "thermostat main floor",
        "camera front porch",
        "lock entry door",
        "outlet bedroom",
        "fan ceiling",
        "blind motorized",
        "speaker wireless",
        "hub central",

        # Actions and states (15 sentences)
        "turn on",
        "turn off",
        "set to",
        "adjust",
        "toggle",
        "is on",
        "is off",
        "is open",
        "is closed",
        "is detected",
        "is armed",
        "is disarmed",
        "is locked",
        "is unlocked",
        "is running",

        # Complex automations (15 sentences)
        "Turn on lights when motion is detected after sunset",
        "Set thermostat to 68 when leaving home",
        "Turn off all devices at bedtime",
        "Notify me when door opens while away",
        "Close garage if left open for 10 minutes",
        "Turn on porch light when someone approaches",
        "Adjust blinds based on sun position",
        "Turn on fan when temperature exceeds 78",
        "Lock all doors when security system armed",
        "Play announcement when package delivered",
        "Turn off lights when everyone leaves",
        "Set scene for movie night",
        "Wake up routine at 6:30am weekdays",
        "Energy saving mode when electricity rates are high",
        "Alert when unusual activity detected",

        # Edge cases (5 sentences)
        "",  # Empty string
        "a",  # Single character
        "The quick brown fox jumps over the lazy dog",  # Standard test
        "🏠 Smart home automation 🤖",  # Emojis
        "A" * 200,  # Long text
    ]


@pytest.fixture(scope="session")
def similarity_threshold() -> float:
    """Return the minimum cosine similarity threshold for embedding compatibility.

    0.99 is used as the threshold per Story 38.1 acceptance criteria.
    This ensures embeddings are virtually identical across versions.
    """
    return 0.99


@pytest.fixture
def cosine_similarity_fn():
    """Return a function to compute cosine similarity between two vectors."""
    def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    return _cosine_similarity
