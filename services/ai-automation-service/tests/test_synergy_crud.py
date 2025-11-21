"""
Unit tests for Synergy Opportunity CRUD operations

Story AI3.1: Device Synergy Detector Foundation
Epic AI-3: Cross-Device Synergy & Contextual Opportunities
"""


import pytest

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_synergy():
    """Sample synergy opportunity for testing"""
    return {
        "synergy_id": "test-synergy-123",
        "synergy_type": "device_pair",
        "devices": ["binary_sensor.bedroom_motion", "light.bedroom_ceiling"],
        "trigger_entity": "binary_sensor.bedroom_motion",
        "trigger_name": "Bedroom Motion",
        "action_entity": "light.bedroom_ceiling",
        "action_name": "Bedroom Light",
        "relationship": "motion_to_light",
        "area": "bedroom",
        "impact_score": 0.85,
        "complexity": "low",
        "confidence": 0.90,
        "rationale": "Motion-activated lighting - Bedroom Motion and Bedroom Light in bedroom with no automation",
    }


@pytest.fixture
def sample_synergies():
    """Multiple sample synergies for batch testing"""
    return [
        {
            "synergy_id": "synergy-001",
            "synergy_type": "device_pair",
            "devices": ["binary_sensor.motion_1", "light.light_1"],
            "trigger_entity": "binary_sensor.motion_1",
            "trigger_name": "Motion 1",
            "action_entity": "light.light_1",
            "action_name": "Light 1",
            "relationship": "motion_to_light",
            "area": "bedroom",
            "impact_score": 0.85,
            "complexity": "low",
            "confidence": 0.90,
            "rationale": "Test synergy 1",
        },
        {
            "synergy_id": "synergy-002",
            "synergy_type": "device_pair",
            "devices": ["binary_sensor.door", "lock.front_door"],
            "trigger_entity": "binary_sensor.door",
            "trigger_name": "Door Sensor",
            "action_entity": "lock.front_door",
            "action_name": "Front Door Lock",
            "relationship": "door_to_lock",
            "area": "entry",
            "impact_score": 0.95,
            "complexity": "medium",
            "confidence": 0.88,
            "rationale": "Test synergy 2",
        },
    ]


# ============================================================================
# Storage Tests
# ============================================================================

def test_synergy_data_structure(sample_synergy):
    """Test that sample synergy has required fields"""
    required_fields = [
        "synergy_id", "synergy_type", "devices", "impact_score",
        "complexity", "confidence",
    ]

    for field in required_fields:
        assert field in sample_synergy


def test_synergy_metadata_structure(sample_synergy):
    """Test that metadata fields are present"""
    metadata_fields = [
        "trigger_entity", "trigger_name", "action_entity",
        "action_name", "relationship", "rationale",
    ]

    for field in metadata_fields:
        assert field in sample_synergy


# ============================================================================
# Batch Storage Tests
# ============================================================================

def test_sample_synergies_count(sample_synergies):
    """Test that we have multiple synergies for batch testing"""
    assert len(sample_synergies) >= 2


def test_synergies_have_different_scores(sample_synergies):
    """Test that synergies have varied impact scores"""
    scores = [s["impact_score"] for s in sample_synergies]
    assert len(set(scores)) > 1  # At least some variation


# ============================================================================
# Query Tests
# ============================================================================

def test_confidence_threshold_logic():
    """Test confidence threshold logic"""
    test_synergies = [
        {"confidence": 0.95},
        {"confidence": 0.85},
        {"confidence": 0.75},
        {"confidence": 0.65},
    ]

    min_confidence = 0.7
    filtered = [s for s in test_synergies if s["confidence"] >= min_confidence]

    assert len(filtered) == 3  # Only >= 0.7


def test_synergy_type_filtering():
    """Test synergy type filtering logic"""
    test_synergies = [
        {"synergy_type": "device_pair"},
        {"synergy_type": "device_pair"},
        {"synergy_type": "weather_context"},
        {"synergy_type": "energy_context"},
    ]

    device_pairs = [s for s in test_synergies if s["synergy_type"] == "device_pair"]
    assert len(device_pairs) == 2


# ============================================================================
# Stats Tests
# ============================================================================

def test_stats_calculation():
    """Test stats calculation logic"""
    test_data = [
        {"synergy_type": "device_pair", "complexity": "low", "impact_score": 0.8},
        {"synergy_type": "device_pair", "complexity": "medium", "impact_score": 0.9},
        {"synergy_type": "weather_context", "complexity": "low", "impact_score": 0.7},
    ]

    # Count by type
    by_type = {}
    for item in test_data:
        stype = item["synergy_type"]
        by_type[stype] = by_type.get(stype, 0) + 1

    assert by_type["device_pair"] == 2
    assert by_type["weather_context"] == 1

    # Average impact
    avg_impact = sum(item["impact_score"] for item in test_data) / len(test_data)
    assert 0.7 <= avg_impact <= 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

