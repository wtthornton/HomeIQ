"""
Unit tests for LineageTracker.
"""

import tempfile
from pathlib import Path

import pytest

from src.training_data.lineage_tracker import LineageTracker


@pytest.fixture
def temp_db_path():
    """Create temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "lineage.db"


@pytest.fixture
def tracker(temp_db_path):
    """Create lineage tracker."""
    return LineageTracker(lineage_db_path=temp_db_path)


def test_track_data(tracker):
    """Test data tracking."""
    tracker.track_data(
        data_id="data_1",
        data_type="pattern_detection",
        source_cycle="cycle_1",
        source_home_id="home_1",
        transformations=["quality_filter", "normalization"]
    )
    
    lineage = tracker.query_by_cycle("cycle_1")
    assert len(lineage) == 1
    assert lineage[0]["data_id"] == "data_1"


def test_track_relationship(tracker):
    """Test relationship tracking."""
    tracker.track_data(data_id="data_1", data_type="pattern_detection")
    tracker.track_data(data_id="data_2", data_type="synergy_detection")
    
    tracker.track_relationship("data_1", "data_2", "linked")
    
    relationships = tracker.get_relationships("data_1")
    assert len(relationships) == 1
    assert relationships[0]["relationship_type"] == "linked"


def test_query_by_cycle(tracker):
    """Test query by cycle."""
    tracker.track_data(
        data_id="data_1",
        data_type="pattern_detection",
        source_cycle="cycle_1"
    )
    tracker.track_data(
        data_id="data_2",
        data_type="synergy_detection",
        source_cycle="cycle_1"
    )
    tracker.track_data(
        data_id="data_3",
        data_type="pattern_detection",
        source_cycle="cycle_2"
    )
    
    cycle_1_data = tracker.query_by_cycle("cycle_1")
    assert len(cycle_1_data) == 2
    
    cycle_2_data = tracker.query_by_cycle("cycle_2")
    assert len(cycle_2_data) == 1


def test_query_by_model(tracker):
    """Test query by model type."""
    tracker.track_data(data_id="data_1", data_type="synergy_detection")
    tracker.track_data(data_id="data_2", data_type="synergy_detection")
    tracker.track_data(data_id="data_3", data_type="pattern_detection")
    
    gnn_data = tracker.query_by_model("gnn_synergy")
    assert len(gnn_data) == 2


def test_export_lineage(tracker, temp_db_path):
    """Test lineage export."""
    tracker.track_data(
        data_id="data_1",
        data_type="pattern_detection",
        source_cycle="cycle_1"
    )
    
    export_path = temp_db_path.parent / "lineage_export.json"
    tracker.export_lineage(export_path)
    
    assert export_path.exists()
    
    import json
    with open(export_path) as f:
        data = json.load(f)
        assert "lineage" in data
        assert "relationships" in data

