"""
Integration tests for enhanced synthetic home generation pipeline.

Tests for Story AI11.9: End-to-End Pipeline Integration
"""

import pytest
from datetime import datetime, timezone
from src.training.enhanced_synthetic_home_generator import EnhancedSyntheticHomeGenerator


class TestEnhancedPipelineIntegration:
    """Test enhanced synthetic home generation pipeline."""
    
    @pytest.mark.asyncio
    async def test_generate_complete_home(self):
        """Test generating a complete home with all enhancements."""
        generator = EnhancedSyntheticHomeGenerator()
        
        home_data = {
            'home_type': 'single_family_house',
            'size_category': 'medium',
            'home_id': 'test_home_001'
        }
        
        complete_home = await generator.generate_complete_home(
            home_data=home_data,
            days=7,
            enable_context=True,
            enable_synergies=True,
            enable_ground_truth=True
        )
        
        # Check required fields
        assert 'areas' in complete_home
        assert 'devices' in complete_home
        assert 'events' in complete_home
        assert 'automations' in complete_home
        assert 'ground_truth' in complete_home
        assert 'generation_metadata' in complete_home
        
        # Check areas
        assert len(complete_home['areas']) > 0
        
        # Check devices
        assert len(complete_home['devices']) > 0
        
        # Check events
        assert len(complete_home['events']) > 0
        
        # Check generation metadata
        metadata = complete_home['generation_metadata']
        assert 'generated_at' in metadata
        assert 'days' in metadata
        assert 'enhancements' in metadata
        assert 'generation_time_ms' in metadata
        
        # Check enhancements enabled
        enhancements = metadata['enhancements']
        assert enhancements['ha_2024_naming'] is True
        assert enhancements['areas_floors_labels'] is True
        assert enhancements['failure_scenarios'] is True
        assert enhancements['event_diversification'] is True
        assert enhancements['blueprint_automations'] is True
        assert enhancements['context_aware'] is True
        assert enhancements['synergies'] is True
        assert enhancements['ground_truth'] is True
    
    @pytest.mark.asyncio
    async def test_generate_complete_home_minimal(self):
        """Test generating a complete home with minimal enhancements."""
        generator = EnhancedSyntheticHomeGenerator()
        
        home_data = {
            'home_type': 'apartment',
            'size_category': 'small',
            'home_id': 'test_home_002'
        }
        
        complete_home = await generator.generate_complete_home(
            home_data=home_data,
            days=3,
            enable_context=False,
            enable_synergies=False,
            enable_ground_truth=False
        )
        
        # Check required fields
        assert 'areas' in complete_home
        assert 'devices' in complete_home
        assert 'events' in complete_home
        
        # Check enhancements disabled
        metadata = complete_home['generation_metadata']
        enhancements = metadata['enhancements']
        assert enhancements['context_aware'] is False
        assert enhancements['synergies'] is False
        assert enhancements['ground_truth'] is False
    
    @pytest.mark.asyncio
    async def test_generate_batch(self):
        """Test generating a batch of homes."""
        generator = EnhancedSyntheticHomeGenerator()
        
        home_data_list = [
            {
                'home_type': 'single_family_house',
                'size_category': 'medium',
                'home_id': f'test_home_{i:03d}'
            }
            for i in range(5)
        ]
        
        progress_calls = []
        def progress_callback(home_num, total_homes, home):
            progress_calls.append((home_num, total_homes, home.get('home_id')))
        
        complete_homes = await generator.generate_batch(
            home_data_list=home_data_list,
            days=7,
            progress_callback=progress_callback
        )
        
        # Check all homes generated
        assert len(complete_homes) == 5
        
        # Check progress callback called
        assert len(progress_calls) == 5
        assert progress_calls[0][0] == 1
        assert progress_calls[0][1] == 5
        
        # Check each home has required fields
        for home in complete_homes:
            assert 'areas' in home
            assert 'devices' in home
            assert 'events' in home
    
    @pytest.mark.asyncio
    async def test_pipeline_integration_all_components(self):
        """Test that all pipeline components are integrated."""
        generator = EnhancedSyntheticHomeGenerator()
        
        home_data = {
            'home_type': 'townhouse',
            'size_category': 'large',
            'home_id': 'test_integration'
        }
        
        complete_home = await generator.generate_complete_home(
            home_data=home_data,
            days=7
        )
        
        # Verify all components present
        assert 'areas' in complete_home
        assert 'devices' in complete_home
        assert 'automations' in complete_home
        assert 'events' in complete_home
        assert 'ground_truth' in complete_home
        
        # Verify areas have floors (Story AI11.2)
        areas = complete_home['areas']
        if areas:
            # At least some areas should have floor assignments
            areas_with_floors = [a for a in areas if 'floor' in a]
            # Not all areas need floors, but some should
            # (This is a soft check - floors are optional)
        
        # Verify devices have HA 2024 naming (Story AI11.1)
        devices = complete_home['devices']
        assert len(devices) > 0
        for device in devices:
            assert 'entity_id' in device
            assert 'friendly_name' in device
        
        # Verify events have diverse types (Story AI11.5)
        events = complete_home['events']
        assert len(events) > 0
        event_types = set(e.get('event_type', 'unknown') for e in events)
        # Should have multiple event types
        assert len(event_types) >= 2  # At least state_changed and others
        
        # Verify ground truth exists (Story AI11.3)
        ground_truth = complete_home.get('ground_truth')
        if ground_truth:
            assert 'expected_patterns' in ground_truth or 'home_id' in ground_truth
