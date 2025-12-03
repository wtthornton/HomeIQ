"""
Unit tests for GroundTruthGenerator.
"""

import pytest

from src.data_generation.ground_truth_generator import GroundTruthGenerator
from src.data_generation.pattern_extractor import PatternExtractor


@pytest.fixture
def sample_home_data():
    """Create sample home data for testing."""
    return {
        "home_id": "test_home_1",
        "home_type": "apartment",
        "devices": [
            {"device_id": "device_1", "entity_id": "light.living_room"},
            {"device_id": "device_2", "entity_id": "switch.kitchen"}
        ],
        "events": [
            {
                "entity_id": "light.living_room",
                "state": "off",
                "timestamp": "2025-01-01T10:00:00Z"
            },
            {
                "entity_id": "light.living_room",
                "state": "on",
                "timestamp": "2025-01-01T10:05:00Z"
            },
            {
                "entity_id": "switch.kitchen",
                "state": "off",
                "timestamp": "2025-01-01T10:06:00Z"
            }
        ]
    }


def test_extract_patterns(sample_home_data):
    """Test pattern extraction."""
    generator = GroundTruthGenerator()
    
    patterns = generator.extract_patterns(sample_home_data["events"])
    
    assert len(patterns) > 0
    assert all("pattern_type" in p for p in patterns)
    assert all("occurrences" in p for p in patterns)


def test_extract_synergies(sample_home_data):
    """Test synergy extraction."""
    generator = GroundTruthGenerator()
    
    synergies = generator.extract_synergies(
        sample_home_data["devices"],
        sample_home_data["events"]
    )
    
    # May or may not have synergies depending on data
    assert isinstance(synergies, list)
    if synergies:
        assert all("entity_1" in s for s in synergies)
        assert all("entity_2" in s for s in synergies)


def test_generate_ground_truth(sample_home_data):
    """Test complete ground truth generation."""
    generator = GroundTruthGenerator()
    
    ground_truth = generator.generate_ground_truth(sample_home_data)
    
    assert "home_id" in ground_truth
    assert "patterns" in ground_truth
    assert "synergies" in ground_truth
    assert "metadata" in ground_truth


def test_pattern_extractor_temporal():
    """Test temporal pattern extraction."""
    extractor = PatternExtractor()
    
    events = [
        {"entity_id": "light.1", "timestamp": "2025-01-01T10:00:00Z"},
        {"entity_id": "light.2", "timestamp": "2025-01-01T10:00:00Z"},
        {"entity_id": "light.3", "timestamp": "2025-01-01T10:05:00Z"}
    ]
    
    patterns = extractor.extract_temporal_patterns(events)
    assert isinstance(patterns, list)


def test_pattern_extractor_sequential():
    """Test sequential pattern extraction."""
    extractor = PatternExtractor()
    
    events = [
        {"entity_id": "light.1", "state": "off", "timestamp": "2025-01-01T10:00:00Z"},
        {"entity_id": "light.1", "state": "on", "timestamp": "2025-01-01T10:05:00Z"},
        {"entity_id": "light.1", "state": "off", "timestamp": "2025-01-01T10:10:00Z"}
    ]
    
    patterns = extractor.extract_sequential_patterns(events)
    assert isinstance(patterns, list)

