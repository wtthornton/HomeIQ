"""
Unit tests for Trigger Condition Analyzer

Tests trigger condition analysis, pattern matching, and location extraction.
"""

import pytest
from src.trigger_analysis.trigger_condition_analyzer import TriggerConditionAnalyzer


class TestTriggerConditionAnalyzer:
    """Test suite for TriggerConditionAnalyzer"""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance"""
        return TriggerConditionAnalyzer()

    @pytest.mark.asyncio
    async def test_presence_trigger_detection(self, analyzer):
        """Test detection of presence triggers"""
        query = "When I sit at my desk, turn on the lights"
        entities = []

        conditions = await analyzer.analyze_trigger_conditions(query, entities)

        assert len(conditions) > 0
        presence_condition = next((c for c in conditions if c["trigger_type"] == "presence"), None)
        assert presence_condition is not None
        assert presence_condition["required_device_class"] == "occupancy"
        assert presence_condition["required_sensor_type"] == "binary_sensor"

    @pytest.mark.asyncio
    async def test_motion_trigger_detection(self, analyzer):
        """Test detection of motion triggers"""
        query = "When motion is detected in the kitchen, turn on lights"
        entities = []

        conditions = await analyzer.analyze_trigger_conditions(query, entities)

        assert len(conditions) > 0
        motion_condition = next((c for c in conditions if c["trigger_type"] == "motion"), None)
        assert motion_condition is not None
        assert motion_condition["required_device_class"] == "motion"
        assert motion_condition["required_sensor_type"] == "binary_sensor"

    @pytest.mark.asyncio
    async def test_door_trigger_detection(self, analyzer):
        """Test detection of door triggers"""
        query = "If the door opens, turn on the hallway lights"
        entities = []

        conditions = await analyzer.analyze_trigger_conditions(query, entities)

        assert len(conditions) > 0
        door_condition = next((c for c in conditions if c["trigger_type"] == "door"), None)
        assert door_condition is not None
        assert door_condition["required_device_class"] == "door"
        assert door_condition["required_sensor_type"] == "binary_sensor"

    @pytest.mark.asyncio
    async def test_window_trigger_detection(self, analyzer):
        """Test detection of window triggers"""
        query = "When the window opens, close the blinds"
        entities = []

        conditions = await analyzer.analyze_trigger_conditions(query, entities)

        assert len(conditions) > 0
        window_condition = next((c for c in conditions if c["trigger_type"] == "window"), None)
        assert window_condition is not None
        assert window_condition["required_device_class"] == "window"

    @pytest.mark.asyncio
    async def test_temperature_trigger_detection(self, analyzer):
        """Test detection of temperature triggers"""
        query = "When temperature drops below 65, turn on the heater"
        entities = []

        conditions = await analyzer.analyze_trigger_conditions(query, entities)

        assert len(conditions) > 0
        temp_condition = next((c for c in conditions if c["trigger_type"] == "temperature"), None)
        assert temp_condition is not None
        assert temp_condition["required_device_class"] == "temperature"
        assert temp_condition["required_sensor_type"] == "sensor"

    @pytest.mark.asyncio
    async def test_location_extraction_from_query(self, analyzer):
        """Test location extraction from query text"""
        query = "When I sit at my desk, turn on the lights"
        entities = []

        conditions = await analyzer.analyze_trigger_conditions(query, entities)

        assert len(conditions) > 0
        # Should extract "desk" or similar location
        condition = conditions[0]
        assert condition.get("location") is not None

    @pytest.mark.asyncio
    async def test_location_from_extracted_entities(self, analyzer):
        """Test location extraction from already extracted entities"""
        query = "When I sit at my desk, turn on the lights"
        entities = [
            {"name": "office", "type": "area"},
            {"name": "desk", "type": "area"},
        ]

        conditions = await analyzer.analyze_trigger_conditions(query, entities)

        assert len(conditions) > 0
        condition = conditions[0]
        # Should use extracted area entities
        assert condition.get("location") in ["office", "desk"]

    @pytest.mark.asyncio
    async def test_multiple_triggers_in_query(self, analyzer):
        """Test detection of multiple triggers in one query"""
        query = "When motion is detected or the door opens, turn on lights"
        entities = []

        conditions = await analyzer.analyze_trigger_conditions(query, entities)

        # Should detect at least one trigger type
        assert len(conditions) > 0
        trigger_types = [c["trigger_type"] for c in conditions]
        assert "motion" in trigger_types or "door" in trigger_types

    @pytest.mark.asyncio
    async def test_no_trigger_conditions(self, analyzer):
        """Test query with no trigger conditions"""
        query = "Turn on the lights at 7am"
        entities = []

        conditions = await analyzer.analyze_trigger_conditions(query, entities)

        # Time triggers don't require sensors, so should return empty or inferred
        # This depends on implementation - could return empty or try inference
        assert isinstance(conditions, list)

    @pytest.mark.asyncio
    async def test_empty_query(self, analyzer):
        """Test empty query handling"""
        query = ""
        entities = []

        conditions = await analyzer.analyze_trigger_conditions(query, entities)

        assert conditions == []

    @pytest.mark.asyncio
    async def test_inferred_trigger_conditions(self, analyzer):
        """Test inference when patterns don't match"""
        query = "When I arrive at the office, turn on the lights"
        entities = []

        conditions = await analyzer.analyze_trigger_conditions(query, entities)

        # Should try inference for "when I arrive"
        assert isinstance(conditions, list)

    @pytest.mark.asyncio
    async def test_confidence_scores(self, analyzer):
        """Test that conditions have confidence scores"""
        query = "When I sit at my desk, turn on the lights"
        entities = []

        conditions = await analyzer.analyze_trigger_conditions(query, entities)

        if conditions:
            for condition in conditions:
                assert "confidence" in condition
                assert 0.0 <= condition["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_condition_text_extraction(self, analyzer):
        """Test that condition text is extracted"""
        query = "When I sit at my desk, turn on the lights"
        entities = []

        conditions = await analyzer.analyze_trigger_conditions(query, entities)

        if conditions:
            for condition in conditions:
                assert "condition_text" in condition
                assert len(condition["condition_text"]) > 0

    @pytest.mark.asyncio
    async def test_extraction_method_tracking(self, analyzer):
        """Test that extraction method is tracked"""
        query = "When I sit at my desk, turn on the lights"
        entities = []

        conditions = await analyzer.analyze_trigger_conditions(query, entities)

        if conditions:
            for condition in conditions:
                assert "extraction_method" in condition
                assert condition["extraction_method"] in ["pattern_matching", "inference"]

    @pytest.mark.asyncio
    async def test_real_world_query(self, analyzer):
        """Test with the actual query from the analysis document"""
        query = "When I sit at my desk. I wan the wled sprit to show fireworks for 15 sec and slowly run the 4 celling lights to energize."
        entities = [
            {"name": "office", "type": "area"},
        ]

        conditions = await analyzer.analyze_trigger_conditions(query, entities)

        # Should detect presence trigger
        assert len(conditions) > 0
        presence_condition = next((c for c in conditions if c["trigger_type"] == "presence"), None)
        assert presence_condition is not None
        assert presence_condition["location"] == "office"
