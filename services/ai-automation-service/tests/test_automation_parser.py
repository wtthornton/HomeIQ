"""
Tests for Automation Parser

Story AI4.2: Automation Parser
"""


import pytest
from src.clients.automation_parser import AutomationParser, EntityRelationship


class TestAutomationParser:
    """
    Test suite for AutomationParser
    
    Story AI4.2: Tests configuration parsing, relationship extraction, and efficient lookup
    """

    def test_initialization(self):
        """Test parser initialization"""
        parser = AutomationParser()

        assert len(parser._relationships) == 0
        assert len(parser._entity_pair_index) == 0
        assert parser._last_parse_time is None

    def test_parse_simple_automation(self):
        """
        Test AC2: Parse simple state-based automation
        """
        parser = AutomationParser()

        automation = {
            'id': 'morning_lights',
            'alias': 'Morning Lights',
            'trigger': {
                'platform': 'state',
                'entity_id': 'binary_sensor.motion_sensor_living_room',
                'to': 'on'
            },
            'action': {
                'service': 'light.turn_on',
                'entity_id': 'light.living_room'
            }
        }

        count = parser.parse_automations([automation])

        assert count == 1
        assert 'morning_lights' in parser._relationships

        rel = parser._relationships['morning_lights']
        assert rel.automation_id == 'morning_lights'
        assert rel.automation_alias == 'Morning Lights'
        assert 'binary_sensor.motion_sensor_living_room' in rel.trigger_entities
        assert 'light.living_room' in rel.action_entities
        assert rel.automation_type == 'state_based'

    def test_parse_multiple_triggers_actions(self):
        """
        Test AC2: Parse automation with multiple triggers and actions
        """
        parser = AutomationParser()

        automation = {
            'id': 'security_alert',
            'alias': 'Security Alert',
            'triggers': [
                {
                    'platform': 'state',
                    'entity_id': 'binary_sensor.door_sensor_front',
                    'to': 'on'
                },
                {
                    'platform': 'state',
                    'entity_id': 'binary_sensor.door_sensor_back',
                    'to': 'on'
                }
            ],
            'actions': [
                {
                    'service': 'light.turn_on',
                    'target': {'entity_id': 'light.outdoor_front'}
                },
                {
                    'service': 'light.turn_on',
                    'target': {'entity_id': 'light.outdoor_back'}
                },
                {
                    'service': 'notify.send',
                    'data': {'message': 'Door opened!'}
                }
            ]
        }

        count = parser.parse_automations([automation])

        assert count == 1
        rel = parser._relationships['security_alert']

        assert len(rel.trigger_entities) == 2
        assert 'binary_sensor.door_sensor_front' in rel.trigger_entities
        assert 'binary_sensor.door_sensor_back' in rel.trigger_entities

        assert len(rel.action_entities) == 2
        assert 'light.outdoor_front' in rel.action_entities
        assert 'light.outdoor_back' in rel.action_entities

    def test_parse_time_based_automation(self):
        """
        Test AC2: Parse time-based automation
        """
        parser = AutomationParser()

        automation = {
            'id': 'morning_routine',
            'alias': 'Morning Routine',
            'trigger': {
                'platform': 'time',
                'at': '07:00:00'
            },
            'action': {
                'service': 'light.turn_on',
                'entity_id': ['light.bedroom', 'light.kitchen']
            }
        }

        count = parser.parse_automations([automation])

        assert count == 1
        rel = parser._relationships['morning_routine']

        assert rel.automation_type == 'time_based'
        assert len(rel.action_entities) == 2
        assert 'light.bedroom' in rel.action_entities
        assert 'light.kitchen' in rel.action_entities

    def test_entity_pair_indexing(self):
        """
        Test AC4: Efficient entity pair indexing
        """
        parser = AutomationParser()

        automations = [
            {
                'id': 'auto1',
                'alias': 'Auto 1',
                'trigger': {'platform': 'state', 'entity_id': 'sensor.temp'},
                'action': {'service': 'climate.set_temperature', 'entity_id': 'climate.living_room'}
            },
            {
                'id': 'auto2',
                'alias': 'Auto 2',
                'trigger': {'platform': 'state', 'entity_id': 'binary_sensor.motion'},
                'action': {'service': 'light.turn_on', 'entity_id': 'light.hallway'}
            }
        ]

        count = parser.parse_automations(automations)

        assert count == 2
        assert parser.get_entity_pair_count() == 4  # 2 pairs x 2 directions

    def test_has_relationship(self):
        """
        Test AC4: Fast relationship checking
        """
        parser = AutomationParser()

        automation = {
            'id': 'test_auto',
            'alias': 'Test Auto',
            'trigger': {'platform': 'state', 'entity_id': 'sensor.motion'},
            'action': {'service': 'light.turn_on', 'entity_id': 'light.room'}
        }

        parser.parse_automations([automation])

        # Should find relationship in both directions
        assert parser.has_relationship('sensor.motion', 'light.room')
        assert parser.has_relationship('light.room', 'sensor.motion')

        # Should not find non-existent relationship
        assert not parser.has_relationship('sensor.motion', 'light.other')

    def test_get_relationships_for_pair(self):
        """
        Test AC3, AC4: Query relationships by entity pair
        """
        parser = AutomationParser()

        automations = [
            {
                'id': 'auto1',
                'alias': 'Auto 1',
                'trigger': {'platform': 'state', 'entity_id': 'sensor.motion'},
                'action': {'service': 'light.turn_on', 'entity_id': 'light.room'}
            },
            {
                'id': 'auto2',
                'alias': 'Auto 2  - Different pair',
                'trigger': {'platform': 'state', 'entity_id': 'sensor.other'},
                'action': {'service': 'light.turn_on', 'entity_id': 'light.other'}
            }
        ]

        parser.parse_automations(automations)

        # Get relationships for specific pair
        rels = parser.get_relationships_for_pair('sensor.motion', 'light.room')

        assert len(rels) == 1
        assert rels[0].automation_id == 'auto1'

        # Check bidirectional
        rels_reverse = parser.get_relationships_for_pair('light.room', 'sensor.motion')
        assert len(rels_reverse) == 1
        assert rels_reverse[0].automation_id == 'auto1'

    def test_parse_with_conditions(self):
        """
        Test AC2: Parse automation with conditions
        """
        parser = AutomationParser()

        automation = {
            'id': 'conditional_auto',
            'alias': 'Conditional Auto',
            'trigger': {'platform': 'state', 'entity_id': 'sensor.motion'},
            'condition': [
                {'condition': 'state', 'entity_id': 'sun.sun', 'state': 'below_horizon'}
            ],
            'action': {'service': 'light.turn_on', 'entity_id': 'light.room'}
        }

        count = parser.parse_automations([automation])

        assert count == 1
        rel = parser._relationships['conditional_auto']
        assert rel.conditions is not None
        assert len(rel.conditions) == 1

    def test_entity_relationship_get_pairs(self):
        """
        Test EntityRelationship.get_entity_pairs()
        """
        rel = EntityRelationship(
            automation_id='test',
            automation_alias='Test',
            trigger_entities={'sensor.1', 'sensor.2'},
            action_entities={'light.1', 'light.2'},
            automation_type='state_based'
        )

        pairs = rel.get_entity_pairs()

        assert len(pairs) == 4  # 2 triggers x 2 actions
        assert ('sensor.1', 'light.1') in pairs
        assert ('sensor.1', 'light.2') in pairs
        assert ('sensor.2', 'light.1') in pairs
        assert ('sensor.2', 'light.2') in pairs

    def test_entity_relationship_involves_entities(self):
        """
        Test EntityRelationship.involves_entities()
        """
        rel = EntityRelationship(
            automation_id='test',
            automation_alias='Test',
            trigger_entities={'sensor.motion'},
            action_entities={'light.room'},
            automation_type='state_based'
        )

        assert rel.involves_entities('sensor.motion', 'light.room')
        assert rel.involves_entities('light.room', 'sensor.motion')
        assert not rel.involves_entities('sensor.motion', 'light.other')

    def test_parse_malformed_automation(self):
        """
        Test AC2: Handle malformed automation gracefully
        """
        parser = AutomationParser()

        automations = [
            {
                'id': 'good_auto',
                'alias': 'Good Auto',
                'trigger': {'platform': 'state', 'entity_id': 'sensor.temp'},
                'action': {'service': 'climate.set_temperature', 'entity_id': 'climate.room'}
            },
            {
                'id': 'bad_auto',
                'alias': 'Bad Auto',
                # Missing trigger and action
            },
            {
                'id': 'another_good',
                'alias': 'Another Good',
                'trigger': {'platform': 'state', 'entity_id': 'sensor.motion'},
                'action': {'service': 'light.turn_on', 'entity_id': 'light.room'}
            }
        ]

        count = parser.parse_automations(automations)

        # Should parse the 2 good automations, skip the bad one
        assert count == 2
        assert 'good_auto' in parser._relationships
        assert 'another_good' in parser._relationships
        assert 'bad_auto' not in parser._relationships

    def test_get_stats(self):
        """
        Test parser statistics
        """
        parser = AutomationParser()

        automations = [
            {
                'id': 'state_auto',
                'alias': 'State Auto',
                'trigger': {'platform': 'state', 'entity_id': 'sensor.temp'},
                'action': {'service': 'climate.set_temperature', 'entity_id': 'climate.room'}
            },
            {
                'id': 'state_auto2',
                'alias': 'State Auto 2',
                'trigger': {'platform': 'state', 'entity_id': 'sensor.motion'},
                'action': {'service': 'light.turn_on', 'entity_id': 'light.room'}
            }
        ]

        parser.parse_automations(automations)

        stats = parser.get_stats()

        assert stats['total_automations'] == 2
        assert stats['entity_pairs_indexed'] == 4  # 2 pairs x 2 directions
        assert 'state_based' in stats['automation_types']
        assert stats['last_parse_time'] is not None

    def test_numeric_state_trigger(self):
        """
        Test AC2: Parse numeric_state trigger
        """
        parser = AutomationParser()

        automation = {
            'id': 'temp_control',
            'alias': 'Temperature Control',
            'trigger': {
                'platform': 'numeric_state',
                'entity_id': 'sensor.temperature',
                'above': 25
            },
            'action': {
                'service': 'climate.turn_on',
                'entity_id': 'climate.ac'
            }
        }

        count = parser.parse_automations([automation])

        assert count == 1
        rel = parser._relationships['temp_control']
        assert 'sensor.temperature' in rel.trigger_entities
        assert 'climate.ac' in rel.action_entities
        assert rel.automation_type == 'state_based'

    def test_parse_multiple_automations(self):
        """
        Test AC1: Parse multiple automation configurations
        """
        parser = AutomationParser()

        automations = [
            {
                'id': f'auto_{i}',
                'alias': f'Auto {i}',
                'trigger': {'platform': 'state', 'entity_id': f'sensor.{i}'},
                'action': {'service': 'light.turn_on', 'entity_id': f'light.{i}'}
            }
            for i in range(10)
        ]

        count = parser.parse_automations(automations)

        assert count == 10
        assert len(parser._relationships) == 10
        assert parser.get_entity_pair_count() == 20  # 10 pairs x 2 directions


@pytest.mark.asyncio
async def test_integration_with_empty_list():
    """Test parser handles empty automation list"""
    parser = AutomationParser()

    count = parser.parse_automations([])

    assert count == 0
    assert len(parser.get_all_relationships()) == 0


@pytest.mark.asyncio
async def test_get_all_relationships():
    """Test getting all parsed relationships"""
    parser = AutomationParser()

    automations = [
        {
            'id': 'auto1',
            'alias': 'Auto 1',
            'trigger': {'platform': 'state', 'entity_id': 'sensor.1'},
            'action': {'service': 'light.turn_on', 'entity_id': 'light.1'}
        },
        {
            'id': 'auto2',
            'alias': 'Auto 2',
            'trigger': {'platform': 'state', 'entity_id': 'sensor.2'},
            'action': {'service': 'light.turn_on', 'entity_id': 'light.2'}
        }
    ]

    parser.parse_automations(automations)

    all_rels = parser.get_all_relationships()

    assert len(all_rels) == 2
    assert all(isinstance(rel, EntityRelationship) for rel in all_rels)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

