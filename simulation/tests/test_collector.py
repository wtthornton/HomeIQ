"""
Unit tests for TrainingDataCollector.
"""

import pytest

from src.training_data.collector import TrainingDataCollector
from src.training_data.validators import DataQualityValidator


@pytest.fixture
def collector():
    """Create training data collector."""
    return TrainingDataCollector()


def test_collect_pattern_data(collector):
    """Test pattern data collection."""
    pattern = {
        "entity_id": "light.living_room",
        "pattern_type": "state_transition",
        "confidence": 0.8,
        "occurrences": 5
    }
    
    result = collector.collect_pattern_data(pattern)
    assert result is True
    
    data = collector.get_collected_data("pattern_detection")
    assert len(data) == 1


def test_collect_synergy_data(collector):
    """Test synergy data collection."""
    synergy = {
        "entity_1": "light.living_room",
        "entity_2": "switch.kitchen",
        "confidence": 0.7
    }
    
    result = collector.collect_synergy_data(synergy)
    assert result is True
    
    data = collector.get_collected_data("synergy_detection")
    assert len(data) == 1


def test_collect_suggestion_data(collector):
    """Test suggestion data collection."""
    suggestion = {
        "description": "Turn on lights when motion detected",
        "automation_type": "motion_trigger",
        "quality_score": 0.8
    }
    
    result = collector.collect_suggestion_data(suggestion)
    assert result is True
    
    data = collector.get_collected_data("suggestion_generation")
    assert len(data) == 1


def test_collect_yaml_data(collector):
    """Test YAML data collection."""
    yaml_pair = {
        "input": "Turn on lights when motion detected",
        "output": "automation:\n  - trigger:\n      platform: state\n      entity_id: binary_sensor.motion"
    }
    validation_result = {"is_valid": True}
    
    result = collector.collect_yaml_data(yaml_pair, validation_result)
    assert result is True
    
    data = collector.get_collected_data("yaml_generation")
    assert len(data) == 1


def test_collect_ask_ai_data(collector):
    """Test Ask AI data collection."""
    query = "Turn on the lights when I enter the room"
    response = {"suggestion": "Motion-triggered lighting automation"}
    
    result = collector.collect_ask_ai_data(query, response)
    assert result is True
    
    data = collector.get_collected_data("ask_ai_conversation")
    assert len(data) == 1


def test_quality_filtering(collector):
    """Test quality filtering."""
    # Low quality pattern (low confidence)
    low_quality_pattern = {
        "entity_id": "light.1",
        "confidence": 0.3,  # Below threshold
        "occurrences": 1
    }
    
    result = collector.collect_pattern_data(low_quality_pattern)
    assert result is False  # Should be filtered
    
    data = collector.get_collected_data("pattern_detection")
    assert len(data) == 0


def test_collection_stats(collector):
    """Test collection statistics."""
    collector.collect_pattern_data({
        "entity_id": "light.1",
        "confidence": 0.8,
        "occurrences": 5
    })
    
    stats = collector.get_collection_stats()
    assert stats["total_collected"] == 1
    assert stats["by_type"]["pattern_detection"] == 1


def test_clear_collected_data(collector):
    """Test clearing collected data."""
    collector.collect_pattern_data({
        "entity_id": "light.1",
        "confidence": 0.8,
        "occurrences": 5
    })
    
    assert len(collector.get_collected_data("pattern_detection")) == 1
    
    collector.clear_collected_data()
    
    assert len(collector.get_collected_data("pattern_detection")) == 0
    assert collector.get_collection_stats()["total_collected"] == 0

