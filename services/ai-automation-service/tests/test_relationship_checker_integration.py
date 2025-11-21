"""
Tests for Relationship Checker Integration

Story AI4.3: Relationship Checker
"""

from unittest.mock import AsyncMock

import pytest
from src.clients.automation_parser import AutomationParser
from src.synergy_detection.synergy_detector import DeviceSynergyDetector


class TestRelationshipCheckerIntegration:
    """
    Test suite for relationship checker integration into synergy detector

    Story AI4.3: Tests filtering of existing automations from synergy suggestions
    """

    @pytest.mark.asyncio
    async def test_filter_with_existing_automations(self):
        """
        Test AC1, AC3: Filter out pairs that have existing automations
        """
        # Mock HA client
        ha_client = AsyncMock()
        ha_client.get_automations = AsyncMock(return_value=[
            {
                "id": "motion_light_auto",
                "alias": "Motion Light Automation",
                "trigger": {
                    "platform": "state",
                    "entity_id": "binary_sensor.motion_living_room",
                },
                "action": {
                    "service": "light.turn_on",
                    "entity_id": "light.living_room",
                },
            },
        ])

        # Mock data API client
        data_api_client = AsyncMock()

        # Create detector with HA client
        detector = DeviceSynergyDetector(
            data_api_client=data_api_client,
            ha_client=ha_client,
            min_confidence=0.5,
        )

        # Compatible pairs (one matches existing automation)
        compatible_pairs = [
            {
                "trigger_entity": "binary_sensor.motion_living_room",
                "action_entity": "light.living_room",
                "relationship_type": "motion_to_light",
                "area": "living_room",
            },
            {
                "trigger_entity": "binary_sensor.motion_bedroom",
                "action_entity": "light.bedroom",
                "relationship_type": "motion_to_light",
                "area": "bedroom",
            },
        ]

        # Filter existing automations
        new_pairs = await detector._filter_existing_automations(compatible_pairs)

        # Should filter out the first pair (already automated)
        assert len(new_pairs) == 1
        assert new_pairs[0]["trigger_entity"] == "binary_sensor.motion_bedroom"
        assert new_pairs[0]["action_entity"] == "light.bedroom"

    @pytest.mark.asyncio
    async def test_filter_with_no_existing_automations(self):
        """
        Test AC3: All pairs remain when no automations exist
        """
        # Mock HA client with no automations
        ha_client = AsyncMock()
        ha_client.get_automations = AsyncMock(return_value=[])

        data_api_client = AsyncMock()

        detector = DeviceSynergyDetector(
            data_api_client=data_api_client,
            ha_client=ha_client,
        )

        compatible_pairs = [
            {
                "trigger_entity": "binary_sensor.motion_bedroom",
                "action_entity": "light.bedroom",
                "relationship_type": "motion_to_light",
            },
        ]

        new_pairs = await detector._filter_existing_automations(compatible_pairs)

        # All pairs should remain (no existing automations)
        assert len(new_pairs) == 1

    @pytest.mark.asyncio
    async def test_filter_without_ha_client(self):
        """
        Test AC3: Graceful fallback when HA client not available
        """
        data_api_client = AsyncMock()

        # Detector without HA client
        detector = DeviceSynergyDetector(
            data_api_client=data_api_client,
            ha_client=None,
        )

        compatible_pairs = [
            {
                "trigger_entity": "binary_sensor.motion_bedroom",
                "action_entity": "light.bedroom",
                "relationship_type": "motion_to_light",
            },
        ]

        new_pairs = await detector._filter_existing_automations(compatible_pairs)

        # All pairs should remain (no filtering without HA client)
        assert len(new_pairs) == 1

    @pytest.mark.asyncio
    async def test_bidirectional_relationship_filtering(self):
        """
        Test AC2: Handle bidirectional relationships (A→B and B→A)
        """
        ha_client = AsyncMock()
        ha_client.get_automations = AsyncMock(return_value=[
            {
                "id": "door_lock_auto",
                "alias": "Auto Lock Door",
                "trigger": {
                    "platform": "state",
                    "entity_id": "binary_sensor.front_door",
                },
                "action": {
                    "service": "lock.lock",
                    "entity_id": "lock.front_door",
                },
            },
        ])

        data_api_client = AsyncMock()

        detector = DeviceSynergyDetector(
            data_api_client=data_api_client,
            ha_client=ha_client,
        )

        # Try both directions - both should be filtered
        compatible_pairs = [
            {
                "trigger_entity": "binary_sensor.front_door",
                "action_entity": "lock.front_door",
                "relationship_type": "door_to_lock",
            },
            {
                "trigger_entity": "lock.front_door",
                "action_entity": "binary_sensor.front_door",
                "relationship_type": "lock_to_door",
            },
        ]

        new_pairs = await detector._filter_existing_automations(compatible_pairs)

        # Both should be filtered (bidirectional check)
        assert len(new_pairs) == 0

    @pytest.mark.asyncio
    async def test_filter_with_error_handling(self):
        """
        Test AC3: Graceful error handling during filtering
        """
        # Mock HA client that raises error
        ha_client = AsyncMock()
        ha_client.get_automations = AsyncMock(side_effect=Exception("Connection failed"))

        data_api_client = AsyncMock()

        detector = DeviceSynergyDetector(
            data_api_client=data_api_client,
            ha_client=ha_client,
        )

        compatible_pairs = [
            {
                "trigger_entity": "binary_sensor.motion_bedroom",
                "action_entity": "light.bedroom",
                "relationship_type": "motion_to_light",
            },
        ]

        # Should not raise, should return all pairs
        new_pairs = await detector._filter_existing_automations(compatible_pairs)

        # All pairs should remain (fallback on error)
        assert len(new_pairs) == 1

    @pytest.mark.asyncio
    async def test_filter_performance_with_large_dataset(self):
        """
        Test AC4: Performance with 100+ pairs and 50+ automations
        """
        import time

        # Create 50 automations
        automations = [
            {
                "id": f"auto_{i}",
                "alias": f"Auto {i}",
                "trigger": {
                    "platform": "state",
                    "entity_id": f"sensor.trigger_{i}",
                },
                "action": {
                    "service": "light.turn_on",
                    "entity_id": f"light.action_{i}",
                },
            }
            for i in range(50)
        ]

        ha_client = AsyncMock()
        ha_client.get_automations = AsyncMock(return_value=automations)

        data_api_client = AsyncMock()

        detector = DeviceSynergyDetector(
            data_api_client=data_api_client,
            ha_client=ha_client,
        )

        # Create 100 device pairs (half will match existing automations)
        compatible_pairs = []
        for i in range(100):
            if i < 50:
                # These match existing automations
                compatible_pairs.append({
                    "trigger_entity": f"sensor.trigger_{i}",
                    "action_entity": f"light.action_{i}",
                    "relationship_type": "sensor_to_light",
                })
            else:
                # These are new
                compatible_pairs.append({
                    "trigger_entity": f"sensor.new_trigger_{i}",
                    "action_entity": f"light.new_action_{i}",
                    "relationship_type": "sensor_to_light",
                })

        # Measure performance
        start_time = time.time()
        new_pairs = await detector._filter_existing_automations(compatible_pairs)
        elapsed_time = time.time() - start_time

        # Should filter out 50 pairs
        assert len(new_pairs) == 50

        # Should complete within 5 seconds (AC4 requirement)
        assert elapsed_time < 5.0, f"Filtering took {elapsed_time:.2f}s, expected < 5s"

        # Verify correct filtering
        for pair in new_pairs:
            assert pair["trigger_entity"].startswith("sensor.new_trigger_")

    @pytest.mark.asyncio
    async def test_filter_with_multiple_triggers_actions(self):
        """
        Test AC2: Handle automations with multiple triggers and actions
        """
        ha_client = AsyncMock()
        ha_client.get_automations = AsyncMock(return_value=[
            {
                "id": "multi_auto",
                "alias": "Multi Trigger Auto",
                "triggers": [
                    {"platform": "state", "entity_id": "binary_sensor.motion_1"},
                    {"platform": "state", "entity_id": "binary_sensor.motion_2"},
                ],
                "actions": [
                    {"service": "light.turn_on", "entity_id": "light.1"},
                    {"service": "light.turn_on", "entity_id": "light.2"},
                ],
            },
        ])

        data_api_client = AsyncMock()

        detector = DeviceSynergyDetector(
            data_api_client=data_api_client,
            ha_client=ha_client,
        )

        # All these combinations should be filtered
        compatible_pairs = [
            {"trigger_entity": "binary_sensor.motion_1", "action_entity": "light.1"},
            {"trigger_entity": "binary_sensor.motion_1", "action_entity": "light.2"},
            {"trigger_entity": "binary_sensor.motion_2", "action_entity": "light.1"},
            {"trigger_entity": "binary_sensor.motion_2", "action_entity": "light.2"},
            # This one is new
            {"trigger_entity": "binary_sensor.motion_3", "action_entity": "light.3"},
        ]

        new_pairs = await detector._filter_existing_automations(compatible_pairs)

        # Only the last pair should remain
        assert len(new_pairs) == 1
        assert new_pairs[0]["trigger_entity"] == "binary_sensor.motion_3"


@pytest.mark.asyncio
async def test_automation_parser_integration():
    """Test that automation parser correctly identifies relationships"""
    parser = AutomationParser()

    automations = [
        {
            "id": "test_auto",
            "alias": "Test Auto",
            "trigger": {"platform": "state", "entity_id": "sensor.test"},
            "action": {"service": "light.turn_on", "entity_id": "light.test"},
        },
    ]

    parser.parse_automations(automations)

    # Should find relationship
    assert parser.has_relationship("sensor.test", "light.test")
    assert parser.has_relationship("light.test", "sensor.test")  # Bidirectional

    # Should not find non-existent relationship
    assert not parser.has_relationship("sensor.test", "light.other")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

