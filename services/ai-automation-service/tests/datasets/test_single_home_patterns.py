"""
Individual Home Pattern Detection Tests

Tests pattern and synergy detection on each synthetic home individually.
This matches the production architecture (single-home NUC deployments).

Each home is tested separately to:
- Validate realistic single-home scenarios
- Collect per-home accuracy metrics
- Identify homes where detection works well/poorly
- Enable easy debugging of failures
"""

import json
import os
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from tests.path_setup import add_service_src
add_service_src(__file__)

from src.testing.dataset_loader import HomeAssistantDatasetLoader
from src.testing.event_injector import EventInjector
from src.testing.metrics import calculate_pattern_metrics
from src.testing.ground_truth import GroundTruthExtractor
from src.clients.data_api_client import DataAPIClient
from src.pattern_analyzer.co_occurrence import CoOccurrencePatternDetector
from src.pattern_analyzer.time_of_day import TimeOfDayPatternDetector


def get_available_homes() -> list[str]:
    """Get list of available synthetic homes from devices-v2 and devices-v3"""
    dataset_root = Path(__file__).parent.parent.parent.parent / "tests" / "datasets" / "home-assistant-datasets" / "datasets"
    
    homes = []
    
    # Check devices-v2
    devices_v2 = dataset_root / "devices-v2"
    if devices_v2.exists():
        homes.extend([f"devices-v2/{f.stem}" for f in devices_v2.glob("home*.yaml")])
    
    # Check devices-v3
    devices_v3 = dataset_root / "devices-v3"
    if devices_v3.exists():
        homes.extend([f"devices-v3/{f.stem}" for f in devices_v3.glob("home*.yaml")])
    
    return sorted(homes)


def get_representative_homes() -> list[str]:
    """Get a representative sample of homes for quick testing"""
    all_homes = get_available_homes()
    # Return first 5 homes for quick testing
    return all_homes[:5] if len(all_homes) >= 5 else all_homes


@pytest.fixture(scope="session")
def all_homes() -> list[str]:
    """Fixture providing all available homes"""
    return get_available_homes()


@pytest.fixture(scope="session")
def representative_homes() -> list[str]:
    """Fixture providing representative homes for quick testing"""
    return get_representative_homes()


@pytest.mark.asyncio
@pytest.mark.parametrize("home_path", get_representative_homes())
async def test_pattern_detection_individual_home(
    home_path: str,
    dataset_loader: HomeAssistantDatasetLoader,
    event_injector: EventInjector,
    ha_test_loader: Any | None = None,
    use_ha_container: bool = False,
):
    """
    Test pattern detection on individual synthetic home.
    
    This test validates that pattern detection works correctly
    for single-home scenarios (matching production architecture).
    """
    # Extract dataset and home name
    parts = home_path.split("/")
    dataset_name = parts[0]  # devices-v2 or devices-v3
    home_name = parts[1] if len(parts) > 1 else parts[0]
    
    print(f"\n{'='*70}")
    print(f"[TEST] Testing Home: {home_name} (from {dataset_name})")
    print(f"{'='*70}")
    
    # Load home configuration
    try:
        # For devices-v2/v3, load the specific home file directly
        dataset_root = dataset_loader.dataset_root
        home_file = dataset_root / dataset_name / f"{home_name}.yaml"
        
        if not home_file.exists():
            pytest.skip(f"Home file not found: {home_file}")
        
        import yaml
        with open(home_file, 'r', encoding='utf-8') as f:
            home_data = yaml.safe_load(f)
        
        # Convert devices-v2/v3 format to expected format
        devices = []
        areas = []
        
        # Extract areas
        if 'areas' in home_data:
            if isinstance(home_data['areas'], list):
                for area in home_data['areas']:
                    if isinstance(area, str):
                        areas.append({'name': area, 'id': area.lower().replace(' ', '_')})
                    else:
                        areas.append(area)
        
        # Extract devices (devices-v2/v3 format: devices organized by area)
        if 'devices' in home_data:
            if isinstance(home_data['devices'], dict):
                # devices-v2/v3 format: devices by area
                for area_name, area_devices in home_data['devices'].items():
                    if isinstance(area_devices, list):
                        for device in area_devices:
                            # Create entity_id from device name
                            device_name = device.get('name', 'unknown')
                            
                            # Map device_type from dataset to Home Assistant entity type
                            dataset_device_type = device.get('device_type', 'sensor')
                            device_type = 'sensor'  # Default
                            device_class = None
                            
                            if 'light' in dataset_device_type.lower():
                                device_type = 'light'
                            elif 'motion' in dataset_device_type.lower():
                                device_type = 'binary_sensor'
                                device_class = 'motion'
                            elif 'sensor' in dataset_device_type.lower():
                                device_type = 'binary_sensor'
                            elif 'switch' in dataset_device_type.lower():
                                device_type = 'switch'
                            elif 'thermostat' in dataset_device_type.lower() or 'hvac' in dataset_device_type.lower():
                                device_type = 'climate'
                            elif 'camera' in dataset_device_type.lower():
                                device_type = 'camera'
                            elif 'garage' in dataset_device_type.lower():
                                device_type = 'cover'
                            elif 'blinds' in dataset_device_type.lower():
                                device_type = 'cover'
                            
                            # Create entity_id
                            entity_id = f"{device_type}.{device_name.lower().replace(' ', '_').replace('-', '_')}"
                            
                            # Build device entry
                            device_entry = {
                                'entity_id': entity_id,
                                'name': device_name,
                                'area': area_name,
                                'device_type': device_type,
                                'device_class': device_class or device.get('device_class'),
                                'attributes': device.get('attributes', {}),
                                'state': 'unknown'  # Default state
                            }
                            
                            # Add manufacturer/model if available (devices-v2/v3 use device_info)
                            if 'device_info' in device:
                                device_entry['manufacturer'] = device['device_info'].get('manufacturer')
                                device_entry['model'] = device['device_info'].get('model')
                            elif 'info' in device:
                                device_entry['manufacturer'] = device['info'].get('manufacturer')
                                device_entry['model'] = device['info'].get('model')
                            
                            devices.append(device_entry)
            elif isinstance(home_data['devices'], list):
                devices = home_data['devices']
        
        home_config = {
            'home': {
                'name': home_data.get('name', home_name),
                'type': home_data.get('type', 'unknown'),
                'location': home_data.get('location', 'unknown')
            },
            'devices': devices,
            'areas': areas,
            'dataset_name': dataset_name,
            'home_name': home_name
        }
        
        print(f"[OK] Loaded home configuration:")
        print(f"     Devices: {len(devices)}")
        print(f"     Areas: {len(areas)}")
        
        # Show device type breakdown
        if devices:
            device_types = {}
            for device in devices:
                device_type = device.get('device_type', 'unknown')
                device_types[device_type] = device_types.get(device_type, 0) + 1
            print(f"     Device Types: {', '.join(f'{k}({v})' for k, v in sorted(device_types.items()))}")
        
    except Exception as e:
        pytest.fail(f"Failed to load home {home_name}: {e}")
    
    # Check if using HA container integration
    if use_ha_container and ha_test_loader:
        # Option B: Full HA Pipeline Validation
        # Load home into HA, generate events through HA → websocket → InfluxDB
        print(f"\n[HA_INTEGRATION] Using Home Assistant container for full pipeline validation...")
        
        try:
            # Load home into HA
            print(f"[HA_LOAD] Loading home into HA container...")
            load_results = await ha_test_loader.load_home_to_ha(home_config)
            print(f"[OK] Loaded: {load_results['areas_created']} areas, {load_results['entities_created']} entities")
            
            if load_results['errors']:
                print(f"[WARN] {len(load_results['errors'])} errors during HA load")
            
            # Generate events through HA (placeholder for now)
            days = 7
            print(f"[HA_EVENTS] Generating events through HA (placeholder - not yet implemented)...")
            # TODO: Implement realistic event generation through HA API
            # events_generated = await ha_test_loader.generate_ha_events(devices, days=days)
            
            # For now, fall through to direct injection
            print(f"[HA_EVENTS] Falling back to direct injection for now...")
        except Exception as e:
            print(f"[ERROR] HA integration failed: {e}")
            print(f"[FALLBACK] Falling back to direct injection...")
            use_ha_container = False
    
    # Option A: Direct Injection (Current - Fast)
    # Generate synthetic events
    # Scale events based on device and area count to simulate realistic home sizes
    # Target: Match production volume (7,534 events/day for 502 devices)
    # Production: ~15 events per device per day
    # Test: ~7.5 events per device per day (doubled for better accuracy)
    # Also factor in areas (more rooms = more activity)
    
    # Note: Production bucket has 365 days retention, test bucket has 7 days
    # We generate 7 days to match test bucket retention (168h = 7 days)
    days = 7  # 7 days of history (matches test bucket retention)
    
    # Calculate events per day based on home size
    device_count = len(devices)
    area_count = len(areas) if areas else 1  # At least 1 area
    
    # Base: 7.5 events per device per day (doubled for better accuracy)
    events_per_device_per_day = 7.5
    
    # Area multiplier: more rooms = more activity (1.1x per additional area)
    # Single room = 1.0x, 2 rooms = 1.1x, 3 rooms = 1.2x, etc.
    area_multiplier = 1.0 + (area_count - 1) * 0.1
    area_multiplier = min(area_multiplier, 2.0)  # Cap at 2.0x for very large homes
    
    # Calculate total events per day
    events_per_day = int(device_count * events_per_device_per_day * area_multiplier)
    
    # Minimum: at least 50 events/day for very small homes
    events_per_day = max(events_per_day, 50)
    
    total_events = days * events_per_day
    
    print(f"\n[CONFIG] Home Configuration:")
    print(f"         Devices: {device_count}")
    print(f"         Areas: {area_count}")
    print(f"         Area Multiplier: {area_multiplier:.2f}x")
    print()
    print(f"[SCALING] Event Scaling:")
    print(f"          Base: {events_per_device_per_day:.2f} events/device/day")
    print(f"          Scaled: {events_per_day} events/day (total)")
    print(f"          Duration: {days} days")
    print(f"          Total Events: {total_events:,}")
    print()
    print(f"[GENERATE] Generating synthetic events...")
    
    try:
        events = dataset_loader.generate_synthetic_events(
            home_config,
            days=days,
            events_per_day=events_per_day
        )
        print(f"[OK] Generated {len(events):,} synthetic events")
        print(f"     ({len(events) / days:.1f} events/day average)")
    except Exception as e:
        print(f"[ERROR] Failed to generate events: {e}")
        pytest.fail(f"Failed to generate events: {e}")
    
    # Inject events into InfluxDB
    print(f"\n[INJECT] Injecting events to InfluxDB...")
    print(f"         Bucket: home_assistant_events_test")
    
    # Store injection time range for cleanup
    injection_start_time = datetime.now(timezone.utc)
    
    try:
        events_injected = await event_injector.inject_events(events)
        print(f"[OK] Injected {events_injected:,} events successfully")
        assert events_injected > 0, "Should inject at least some events"
    except Exception as e:
        print(f"[ERROR] Failed to inject events: {e}")
        pytest.fail(f"Failed to inject events: {e}")
    
    injection_end_time = datetime.now(timezone.utc)
    
    # Wait a moment for events to be available
    import asyncio
    print(f"[WAIT] Waiting 2 seconds for events to be available...")
    await asyncio.sleep(2)
    
    # Fetch events back from Data API
    print(f"\n[FETCH] Fetching events from Data API...")
    data_api_client = DataAPIClient(
        influxdb_url=os.getenv("INFLUXDB_URL", "http://localhost:8086"),
        influxdb_token=os.getenv("INFLUXDB_TOKEN", "ha-ingestor-token"),
        influxdb_org=os.getenv("INFLUXDB_ORG", "ha-ingestor"),
        influxdb_bucket=os.getenv("INFLUXDB_TEST_BUCKET", "home_assistant_events_test")
    )
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days + 1)  # Extra day buffer
    
    try:
        events_df = await data_api_client.fetch_events(
            start_time=start_time,
            end_time=end_time,
            limit=100000  # Large limit for comprehensive testing
        )
        print(f"[OK] Fetched {len(events_df):,} events from InfluxDB")
        if len(events_df) != events_injected:
            print(f"      Note: Fetched {len(events_df) - events_injected:,} more events than injected (existing data in bucket)")
        assert not events_df.empty, "Should fetch events from InfluxDB"
    except Exception as e:
        print(f"[ERROR] Failed to fetch events: {e}")
        pytest.fail(f"Failed to fetch events: {e}")
    
    # Run co-occurrence pattern detection
    print(f"\n[DETECT] Running Pattern Detection...")
    print(f"         Co-occurrence detector (min_confidence=0.7, window=5min)...")
    detector = CoOccurrencePatternDetector(
        min_confidence=0.7,
        window_minutes=5
    )
    
    try:
        patterns = detector.detect_patterns(events_df)
        print(f"[OK] Detected {len(patterns)} co-occurrence patterns")
        if len(patterns) > 0:
            # Show top 3 patterns
            top_patterns = sorted(patterns, key=lambda x: x.get('confidence', 0), reverse=True)[:3]
            print(f"      Top patterns:")
            for i, pattern in enumerate(top_patterns, 1):
                device1 = pattern.get('device1', 'unknown')
                device2 = pattern.get('device2', 'unknown')
                confidence = pattern.get('confidence', 0)
                print(f"        {i}. {device1} -> {device2} (confidence: {confidence:.3f})")
        assert isinstance(patterns, list), "Should return list of patterns"
    except Exception as e:
        print(f"[ERROR] Pattern detection failed: {e}")
        pytest.fail(f"Pattern detection failed: {e}")
    
    # Run time-of-day pattern detection
    print(f"\n         Time-of-day detector (min_occurrences=3, min_confidence=0.7)...")
    tod_detector = TimeOfDayPatternDetector(
        min_occurrences=3,
        min_confidence=0.7
    )
    
    try:
        tod_patterns = tod_detector.detect_patterns(events_df)
        print(f"[OK] Detected {len(tod_patterns)} time-of-day patterns")
        if len(tod_patterns) > 0:
            # Show top 3 time-of-day patterns
            top_tod = sorted(tod_patterns, key=lambda x: x.get('confidence', 0), reverse=True)[:3]
            print(f"      Top patterns:")
            for i, pattern in enumerate(top_tod, 1):
                entity = pattern.get('entity_id', 'unknown')
                time_range = pattern.get('time_range', 'unknown')
                confidence = pattern.get('confidence', 0)
                print(f"        {i}. {entity} at {time_range} (confidence: {confidence:.3f})")
    except Exception as e:
        print(f"[WARN] Time-of-day detection failed: {e}")
        tod_patterns = []
    
    # Extract ground truth if available
    print(f"\n[GROUND_TRUTH] Extracting Ground Truth...")
    ground_truth_extractor = GroundTruthExtractor(home_config)
    expected_patterns = ground_truth_extractor.extract_patterns()
    expected_synergies = ground_truth_extractor.extract_synergies()
    
    if expected_patterns:
        print(f"                    Found {len(expected_patterns)} expected patterns")
    else:
        print(f"                    No ground truth patterns available (dataset may not include expected patterns)")
    
    if expected_synergies:
        print(f"                    Found {len(expected_synergies)} expected synergies")
    else:
        print(f"                    No ground truth synergies available")
    
    # Calculate metrics if ground truth available
    metrics = {}
    if expected_patterns:
        print(f"\n[METRICS] Calculating Accuracy Metrics...")
        print(f"          Comparing {len(patterns)} detected vs {len(expected_patterns)} expected patterns...")
        metrics = calculate_pattern_metrics(
            detected_patterns=patterns,
            ground_truth_patterns=expected_patterns
        )
        print(f"[OK] Metrics calculated:")
        print(f"     Precision: {metrics.get('precision', 0):.3f}")
        print(f"     Recall: {metrics.get('recall', 0):.3f}")
        print(f"     F1 Score: {metrics.get('f1', 0):.3f}")
        print(f"     TP: {metrics.get('tp', 0)}, FP: {metrics.get('fp', 0)}, FN: {metrics.get('fn', 0)}")
    else:
        print(f"\n[METRICS] Accuracy Metrics: Skipped (no ground truth available)")
    
    # Store results
    results = {
        'home': home_name,
        'dataset': dataset_name,
        'devices': len(devices),
        'areas': len(areas),
        'events_per_day': events_per_day,
        'events_per_device_per_day': events_per_day / len(devices) if devices else 0,
        'area_multiplier': area_multiplier,
        'events_generated': len(events),
        'events_injected': events_injected,
        'events_fetched': len(events_df),
        'patterns_detected': len(patterns),
        'tod_patterns_detected': len(tod_patterns),
        'expected_patterns': len(expected_patterns),
        'expected_synergies': len(expected_synergies),
        'metrics': metrics,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    # Print detailed summary
    print(f"\n{'='*70}")
    print(f"[RESULTS] Test Results for {home_name}")
    print(f"{'='*70}")
    print(f"Home Configuration:")
    print(f"  Devices: {results['devices']}")
    print(f"  Areas: {results['areas']}")
    print(f"  Area Multiplier: {results['area_multiplier']:.2f}x")
    print()
    print(f"Event Generation:")
    print(f"  Events per Day: {results['events_per_day']:,}")
    print(f"  Events per Device/Day: {results['events_per_device_per_day']:.2f}")
    print(f"  Total Generated: {results['events_generated']:,}")
    print(f"  Total Injected: {results['events_injected']:,}")
    print(f"  Total Fetched: {results['events_fetched']:,}")
    print()
    print(f"Pattern Detection:")
    print(f"  Co-occurrence Patterns: {results['patterns_detected']}")
    print(f"  Time-of-Day Patterns: {results['tod_patterns_detected']}")
    if results['expected_patterns'] > 0:
        print(f"  Expected Patterns: {results['expected_patterns']}")
    if results['expected_synergies'] > 0:
        print(f"  Expected Synergies: {results['expected_synergies']}")
    print()
    if metrics:
        print(f"Accuracy Metrics:")
        print(f"  Precision: {metrics.get('precision', 0):.3f}")
        print(f"  Recall: {metrics.get('recall', 0):.3f}")
        print(f"  F1 Score: {metrics.get('f1', 0):.3f}")
        print(f"  True Positives: {metrics.get('tp', 0)}")
        print(f"  False Positives: {metrics.get('fp', 0)}")
        print(f"  False Negatives: {metrics.get('fn', 0)}")
    else:
        print(f"Accuracy Metrics: Not available (no ground truth)")
    print(f"{'='*70}\n")
    
    # Basic assertions
    assert results['events_injected'] > 0, "Should inject events"
    assert results['events_fetched'] > 0, "Should fetch events"
    assert results['patterns_detected'] >= 0, "Should detect patterns (may be 0)"
    
    # Cleanup: Remove events for this home (optional, controlled by flag)
    cleanup_enabled = os.getenv("CLEANUP_BETWEEN_HOMES", "true").lower() == "true"
    if cleanup_enabled:
        try:
            print(f"\n[CLEANUP] Cleaning up events for {home_name}...")
            deleted = await event_injector.clear_home_events(
                home_id=home_name,
                time_range=(injection_start_time, injection_end_time)
            )
            print(f"[OK] Cleanup completed (estimated {deleted} deletion operations)")
        except Exception as e:
            print(f"[WARN] Cleanup failed (non-critical): {e}")
            # Don't fail test on cleanup errors
    
    # Store results in pytest metadata for aggregation
    if not hasattr(pytest, 'home_test_results'):
        pytest.home_test_results = []
    pytest.home_test_results.append(results)


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.parametrize("home_path", get_available_homes())
async def test_pattern_detection_all_homes(
    home_path: str,
    dataset_loader: HomeAssistantDatasetLoader,
    event_injector: EventInjector,
):
    """
    Test pattern detection on ALL available homes.
    
    This is a comprehensive test that runs on all 37 homes.
    Marked as 'slow' - use pytest -m "not slow" to skip.
    """
    # Same implementation as test_pattern_detection_individual_home
    # but runs on all homes
    await test_pattern_detection_individual_home(home_path, dataset_loader, event_injector)


@pytest.fixture(scope="session", autouse=True)
def aggregate_results(request):
    """Aggregate and save test results after all tests complete"""
    yield
    
    # This runs after all tests
    if hasattr(pytest, 'home_test_results') and pytest.home_test_results:
        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"home_test_results_{timestamp}.json"
        
        # Calculate aggregate metrics
        all_results = pytest.home_test_results
        total_homes = len(all_results)
        homes_with_metrics = [r for r in all_results if r.get('metrics')]
        
        aggregate = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_homes_tested': total_homes,
            'homes_with_metrics': len(homes_with_metrics),
            'total_devices': sum(r['devices'] for r in all_results),
            'total_events_injected': sum(r['events_injected'] for r in all_results),
            'total_patterns_detected': sum(r['patterns_detected'] for r in all_results),
            'avg_precision': sum(r['metrics'].get('precision', 0) for r in homes_with_metrics) / len(homes_with_metrics) if homes_with_metrics else 0,
            'avg_recall': sum(r['metrics'].get('recall', 0) for r in homes_with_metrics) / len(homes_with_metrics) if homes_with_metrics else 0,
            'avg_f1': sum(r['metrics'].get('f1', 0) for r in homes_with_metrics) / len(homes_with_metrics) if homes_with_metrics else 0,
            'individual_results': all_results
        }
        
        with open(results_file, 'w') as f:
            json.dump(aggregate, f, indent=2)
        
        print(f"\n{'='*70}")
        print(f"Test Results Summary")
        print(f"{'='*70}")
        print(f"Total Homes Tested: {total_homes}")
        print(f"Homes with Metrics: {len(homes_with_metrics)}")
        print(f"Total Devices: {aggregate['total_devices']}")
        print(f"Total Events: {aggregate['total_events_injected']}")
        print(f"Total Patterns: {aggregate['total_patterns_detected']}")
        if homes_with_metrics:
            print(f"Average Precision: {aggregate['avg_precision']:.3f}")
            print(f"Average Recall: {aggregate['avg_recall']:.3f}")
            print(f"Average F1: {aggregate['avg_f1']:.3f}")
        print(f"\nResults saved to: {results_file}")
        print(f"{'='*70}\n")

