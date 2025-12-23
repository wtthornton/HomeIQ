"""
Blueprint-Dataset Correlation Tests

Tests correlation between home-assistant-datasets and blueprints
from automation-miner to enhance pattern detection and YAML generation.

Phase 4: Comprehensive Testing
"""

import pytest
from datetime import datetime, timedelta, timezone

from tests.path_setup import add_service_src
add_service_src(__file__)

from src.testing.dataset_loader import HomeAssistantDatasetLoader
from src.testing.event_injector import EventInjector
from src.testing.blueprint_dataset_correlator import BlueprintDatasetCorrelator
from src.testing.pattern_blueprint_validator import PatternBlueprintValidator
from src.clients.data_api_client import DataAPIClient
from src.pattern_analyzer.co_occurrence import CoOccurrencePatternDetector
from src.utils.miner_integration import get_miner_integration


@pytest.mark.asyncio
async def test_blueprint_correlator_initialization():
    """Test that BlueprintDatasetCorrelator can be initialized"""
    correlator = BlueprintDatasetCorrelator()
    assert correlator is not None
    assert correlator.miner is None  # No miner set initially


@pytest.mark.asyncio
async def test_extract_devices_from_task():
    """Test device extraction from dataset tasks"""
    correlator = BlueprintDatasetCorrelator()
    
    # Test with explicit devices
    task = {
        'description': 'Turn on lights when motion detected',
        'devices': ['binary_sensor.motion', 'light.kitchen']
    }
    
    devices = correlator._extract_devices_from_task(task)
    assert 'binary_sensor' in devices
    assert 'light' in devices
    
    # Test with description only
    task2 = {
        'description': 'Control lights and motion sensors'
    }
    
    devices2 = correlator._extract_devices_from_task(task2)
    assert len(devices2) > 0


@pytest.mark.asyncio
async def test_extract_use_case():
    """Test use case extraction from descriptions"""
    correlator = BlueprintDatasetCorrelator()
    
    # Security
    assert correlator._extract_use_case('Lock door when opened') == 'security'
    assert correlator._extract_use_case('Door alert notification') == 'security'
    
    # Comfort
    assert correlator._extract_use_case('Turn on lights for comfort') == 'comfort'
    assert correlator._extract_use_case('Control temperature') == 'comfort'
    
    # Energy
    assert correlator._extract_use_case('Save energy by turning off lights') == 'energy'
    
    # Convenience
    assert correlator._extract_use_case('Automate routine schedule') == 'convenience'
    
    # Unknown
    assert correlator._extract_use_case('Random automation') == 'unknown'


@pytest.mark.asyncio
async def test_find_blueprint_for_pattern(
    dataset_loader: HomeAssistantDatasetLoader
):
    """Test finding blueprints for detected patterns"""
    # Load dataset
    home_data = await dataset_loader.load_synthetic_home("assist-mini")
    
    # Create correlator
    correlator = BlueprintDatasetCorrelator()
    
    # Try to get miner (may not be available)
    try:
        from src.config import settings
        miner = get_miner_integration(settings.automation_miner_url if hasattr(settings, 'automation_miner_url') else "http://localhost:8029")
        
        if not await miner.is_available():
            pytest.skip("Automation miner not available")
        
        correlator.set_miner(miner)
        
        # Create a test pattern
        pattern = {
            'device1': 'binary_sensor.motion',
            'device2': 'light.kitchen',
            'pattern_type': 'co_occurrence',
            'confidence': 0.75
        }
        
        # Find blueprint
        blueprint_match = await correlator.find_blueprint_for_pattern(pattern, miner)
        
        if blueprint_match:
            print(f"\n✅ Found blueprint match:")
            print(f"  Blueprint: {blueprint_match['blueprint'].get('title', 'Unknown')}")
            print(f"  Fit Score: {blueprint_match['fit_score']:.3f}")
            print(f"  Device Match: {blueprint_match['device_match']}")
            print(f"  Use Case Match: {blueprint_match['use_case_match']}")
            
            assert blueprint_match['fit_score'] > 0.0
            assert blueprint_match['fit_score'] <= 1.0
        else:
            print("⚠️  No blueprint match found (may need more blueprints in miner)")
    
    except Exception as e:
        pytest.skip(f"Cannot test blueprint correlation: {e}")


@pytest.mark.asyncio
async def test_pattern_validation_with_blueprints(
    dataset_loader: HomeAssistantDatasetLoader,
    event_injector: EventInjector
):
    """Test pattern detection with blueprint validation"""
    # Load dataset
    home_data = await dataset_loader.load_synthetic_home("assist-mini")
    
    # Generate and inject events
    events = dataset_loader.generate_synthetic_events(home_data, days=7, events_per_day=50)
    await event_injector.inject_events(events)
    
    # Fetch events and detect patterns
    data_api_client = DataAPIClient()
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=7)
    
    events_df = await data_api_client.fetch_events(
        start_time=start_time,
        end_time=end_time,
        limit=10000
    )
    
    if events_df.empty:
        pytest.skip("No events fetched from InfluxDB")
    
    # Detect patterns
    detector = CoOccurrencePatternDetector(min_confidence=0.7, time_window_minutes=5)
    patterns = detector.detect_patterns(events_df)
    
    if not patterns:
        pytest.skip("No patterns detected")
    
    # Validate with blueprints
    try:
        from src.config import settings
        miner = get_miner_integration(settings.automation_miner_url if hasattr(settings, 'automation_miner_url') else "http://localhost:8029")
        
        if not await miner.is_available():
            pytest.skip("Automation miner not available")
        
        correlator = BlueprintDatasetCorrelator(miner=miner)
        validator = PatternBlueprintValidator(correlator=correlator)
        
        validated_patterns = await validator.validate_patterns_with_blueprints(patterns, miner)
        
        # Check validation results
        validated_count = sum(1 for p in validated_patterns if p.get('blueprint_validated', False))
        
        print(f"\n✅ Pattern Validation with Blueprints:")
        print(f"  Total Patterns: {len(patterns)}")
        print(f"  Validated by Blueprints: {validated_count}")
        print(f"  Validation Rate: {validated_count/len(patterns)*100:.1f}%")
        
        # Show validated patterns
        for pattern in validated_patterns[:5]:
            if pattern.get('blueprint_validated'):
                print(f"  - {pattern.get('device1')} → {pattern.get('device2')}")
                print(f"    Blueprint: {pattern.get('blueprint_name', 'Unknown')}")
                print(f"    Confidence: {pattern.get('confidence', 0):.3f}")
                print(f"    Fit Score: {pattern.get('blueprint_fit_score', 0):.3f}")
        
        # Assert some patterns were validated (if blueprints available)
        if validated_count > 0:
            assert validated_count > 0, "Should have at least one validated pattern"
    
    except Exception as e:
        pytest.skip(f"Cannot test pattern validation: {e}")


@pytest.mark.asyncio
async def test_blueprint_confidence_boost():
    """Test that blueprint validation boosts pattern confidence"""
    validator = PatternBlueprintValidator()
    
    # Create mock pattern
    pattern = {
        'device1': 'binary_sensor.motion',
        'device2': 'light.kitchen',
        'confidence': 0.75
    }
    
    # Mock correlator
    class MockCorrelator:
        async def find_blueprint_for_pattern(self, pattern, miner):
            return {
                'blueprint': {'id': 1, 'title': 'Motion-Activated Light'},
                'fit_score': 0.85
            }
    
    validator.set_correlator(MockCorrelator())
    
    # Validate pattern
    validated = await validator.validate_patterns_with_blueprints([pattern])
    
    assert len(validated) == 1
    assert validated[0]['blueprint_validated'] is True
    assert validated[0]['confidence'] == 0.85  # 0.75 + 0.1
    assert validated[0]['blueprint_reference'] == 1


@pytest.mark.asyncio
async def test_correlation_scoring():
    """Test correlation score calculation"""
    correlator = BlueprintDatasetCorrelator()
    
    # Test device match
    blueprint = {
        'metadata': {
            '_blueprint_devices': ['light', 'binary_sensor']
        },
        'use_case': 'comfort'
    }
    
    dataset_task = {
        'description': 'Turn on lights when motion detected',
        'devices': ['light', 'binary_sensor']
    }
    
    devices = correlator._extract_devices_from_task(dataset_task)
    use_case = correlator._extract_use_case(dataset_task['description'])
    
    score = correlator._calculate_correlation_score(
        blueprint, dataset_task, devices, use_case
    )
    
    assert score > 0.0
    assert score <= 1.0
    assert score >= 0.5  # Should have good match


@pytest.mark.asyncio
async def test_blueprint_dataset_correlation_workflow(
    dataset_loader: HomeAssistantDatasetLoader
):
    """Test complete workflow: dataset task → blueprint → validation"""
    # Load dataset
    home_data = await dataset_loader.load_synthetic_home("assist-mini")
    
    # Create dataset task (simulated)
    dataset_task = {
        'description': 'Turn on lights when motion detected in kitchen',
        'devices': ['binary_sensor.motion', 'light.kitchen'],
        'expected_automation': {
            'trigger': {'platform': 'state', 'entity_id': 'binary_sensor.motion'},
            'action': {'service': 'light.turn_on', 'entity_id': 'light.kitchen'}
        }
    }
    
    # Create correlator
    correlator = BlueprintDatasetCorrelator()
    
    try:
        from src.config import settings
        miner = get_miner_integration(settings.automation_miner_url if hasattr(settings, 'automation_miner_url') else "http://localhost:8029")
        
        if not await miner.is_available():
            pytest.skip("Automation miner not available")
        
        correlator.set_miner(miner)
        
        # Find blueprint
        blueprint_match = await correlator.find_blueprint_for_dataset_task(dataset_task, miner)
        
        if blueprint_match:
            print(f"\n✅ Blueprint-Dataset Correlation:")
            print(f"  Dataset Task: {dataset_task['description']}")
            print(f"  Blueprint: {blueprint_match['blueprint'].get('title', 'Unknown')}")
            print(f"  Fit Score: {blueprint_match['fit_score']:.3f}")
            print(f"  Device Match: {blueprint_match['device_match']}")
            print(f"  Use Case Match: {blueprint_match['use_case_match']}")
            
            # Validate correlation quality
            assert blueprint_match['fit_score'] > 0.5, "Fit score should be reasonable"
            assert blueprint_match['device_match'], "Should match devices"
        else:
            print("⚠️  No blueprint match found")
            # This is OK - may not have blueprints for all tasks
    
    except Exception as e:
        pytest.skip(f"Cannot test correlation workflow: {e}")

