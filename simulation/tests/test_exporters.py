"""
Unit tests for TrainingDataExporter.
"""

import tempfile
from pathlib import Path

import pytest

from src.training_data.exporters import TrainingDataExporter


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def exporter(temp_output_dir):
    """Create training data exporter."""
    return TrainingDataExporter(temp_output_dir)


def test_export_gnn_synergy_json(exporter):
    """Test GNN synergy data export (JSON)."""
    synergy_data = [
        {
            "synergy": {
                "entity_1": "light.1",
                "entity_2": "switch.1",
                "confidence": 0.8
            }
        }
    ]
    
    output_path = exporter.export_gnn_synergy_data(synergy_data, format="json")
    assert output_path.exists()
    assert output_path.suffix == ".json"


def test_export_soft_prompt_json(exporter):
    """Test Soft Prompt data export (JSON)."""
    prompt_data = [
        {
            "suggestion": {
                "description": "Turn on lights",
                "automation_type": "motion_trigger",
                "quality_score": 0.9
            },
            "prompt": {
                "user_prompt": "Turn on lights when motion detected"
            }
        }
    ]
    
    output_path = exporter.export_soft_prompt_data(prompt_data, format="json")
    assert output_path.exists()
    assert output_path.suffix == ".json"


def test_export_soft_prompt_sqlite(exporter):
    """Test Soft Prompt data export (SQLite)."""
    prompt_data = [
        {
            "suggestion": {
                "description": "Turn on lights",
                "automation_type": "motion_trigger",
                "quality_score": 0.9
            },
            "prompt": {
                "user_prompt": "Turn on lights when motion detected"
            }
        }
    ]
    
    output_path = exporter.export_soft_prompt_data(prompt_data, format="sqlite")
    assert output_path.exists()
    assert output_path.suffix == ".db"


def test_export_pattern_detection_json(exporter):
    """Test pattern detection data export (JSON)."""
    pattern_data = [
        {
            "pattern": {
                "entity_id": "light.1",
                "pattern_type": "state_transition",
                "confidence": 0.8,
                "occurrences": 5
            }
        }
    ]
    
    output_path = exporter.export_pattern_detection_data(pattern_data, format="json")
    assert output_path.exists()
    assert output_path.suffix == ".json"


def test_export_yaml_generation(exporter):
    """Test YAML generation data export."""
    yaml_data = [
        {
            "yaml_pair": {
                "input": "Turn on lights",
                "output": "automation:\n  - trigger:\n      platform: state"
            }
        }
    ]
    
    output_path = exporter.export_yaml_generation_data(yaml_data)
    assert output_path.exists()
    assert output_path.suffix == ".json"


def test_export_device_intelligence_json(exporter):
    """Test device intelligence data export (JSON)."""
    device_data = [
        {
            "device_id": "device_1",
            "entity_id": "light.1",
            "device_type": "light",
            "capabilities": ["on", "off"]
        }
    ]
    
    output_path = exporter.export_device_intelligence_data(device_data, format="json")
    assert output_path.exists()
    assert output_path.suffix == ".json"


def test_export_device_intelligence_csv(exporter):
    """Test device intelligence data export (CSV)."""
    device_data = [
        {
            "device_id": "device_1",
            "entity_id": "light.1",
            "device_type": "light",
            "capabilities": ["on", "off"]
        }
    ]
    
    output_path = exporter.export_device_intelligence_data(device_data, format="csv")
    assert output_path.exists()
    assert output_path.suffix == ".csv"

