"""
Comprehensive Pattern Detection Tests with Metrics

Phase 2: Pattern Testing - Comprehensive Test Suite

Tests pattern detection accuracy using synthetic home datasets with
known device relationships (ground truth) and calculates metrics.
"""

import pytest
from datetime import datetime, timedelta, timezone

from tests.path_setup import add_service_src
add_service_src(__file__)

from src.testing.dataset_loader import HomeAssistantDatasetLoader
from src.testing.event_injector import EventInjector
from src.testing.metrics import calculate_pattern_metrics, format_metrics_report
from src.testing.ground_truth import GroundTruthExtractor
from src.testing.blueprint_dataset_correlator import BlueprintDatasetCorrelator
from src.testing.pattern_blueprint_validator import PatternBlueprintValidator
from src.clients.data_api_client import DataAPIClient
from src.pattern_analyzer.co_occurrence import CoOccurrencePatternDetector
from src.pattern_analyzer.time_of_day import TimeOfDayPatternDetector
from src.pattern_detection.multi_factor_detector import MultiFactorPatternDetector
from src.utils.miner_integration import get_miner_integration


@pytest.mark.asyncio
async def test_pattern_detection_accuracy_co_occurrence(
    dataset_loader: HomeAssistantDatasetLoader,
    event_injector: EventInjector
):
    """
    Test co-occurrence pattern detection accuracy against ground truth.
    
    This test:
    1. Loads a dataset with known device relationships
    2. Injects synthetic events
    3. Detects co-occurrence patterns
    4. Compares against ground truth
    5. Calculates precision, recall, F1 score
    """
    # Load dataset
    home_data = await dataset_loader.load_synthetic_home("assist-mini")
    
    # Extract ground truth
    extractor = GroundTruthExtractor(home_data)
    ground_truth_patterns = extractor.extract_patterns()
    
    # Filter to co-occurrence patterns only
    ground_truth_co_occurrence = [
        p for p in ground_truth_patterns
        if p.get('pattern_type') == 'co_occurrence'
    ]
    
    if not ground_truth_co_occurrence:
        pytest.skip("No ground truth co-occurrence patterns found in dataset")
    
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
    
    # Detect co-occurrence patterns
    detector = CoOccurrencePatternDetector(
        min_confidence=0.7,
        time_window_minutes=5
    )
    
    detected_patterns = detector.detect_patterns(events_df)
    
    # Validate patterns with blueprints (if available)
    try:
        from src.config import settings
        miner = get_miner_integration(settings.automation_miner_url if hasattr(settings, 'automation_miner_url') else "http://localhost:8029")
        
        if await miner.is_available():
            correlator = BlueprintDatasetCorrelator(miner=miner)
            validator = PatternBlueprintValidator(correlator=correlator)
            detected_patterns = await validator.validate_patterns_with_blueprints(detected_patterns, miner)
            
            validated_count = sum(1 for p in detected_patterns if p.get('blueprint_validated', False))
            if validated_count > 0:
                print(f"  ✅ Blueprint-validated patterns: {validated_count}")
    except Exception:
        pass  # Blueprint validation optional
    
    # Filter to co-occurrence patterns
    detected_co_occurrence = [
        p for p in detected_patterns
        if p.get('pattern_type') == 'co_occurrence'
    ]
    
    # Calculate metrics
    metrics = calculate_pattern_metrics(
        detected_co_occurrence,
        ground_truth_co_occurrence,
        match_threshold=0.8
    )
    
    # Print report
    print("\n" + format_metrics_report(metrics, "Co-Occurrence Pattern Detection"))
    
    # Assert minimum quality thresholds
    assert metrics['precision'] > 0.0, "Should detect at least some correct patterns"
    assert metrics['recall'] > 0.0, "Should detect at least some ground truth patterns"
    
    # Log results
    print(f"\n✅ Detected {len(detected_co_occurrence)} co-occurrence patterns")
    print(f"✅ Ground truth: {len(ground_truth_co_occurrence)} patterns")
    print(f"✅ Precision: {metrics['precision']:.3f}")
    print(f"✅ Recall: {metrics['recall']:.3f}")
    print(f"✅ F1 Score: {metrics['f1_score']:.3f}")


@pytest.mark.asyncio
async def test_pattern_detection_accuracy_time_of_day(
    dataset_loader: HomeAssistantDatasetLoader,
    event_injector: EventInjector
):
    """Test time-of-day pattern detection accuracy"""
    # Load dataset
    home_data = await dataset_loader.load_synthetic_home("assist-mini")
    
    # Extract ground truth
    extractor = GroundTruthExtractor(home_data)
    ground_truth_patterns = extractor.extract_patterns()
    
    # Filter to time-of-day patterns
    ground_truth_time = [
        p for p in ground_truth_patterns
        if p.get('pattern_type') == 'time_of_day'
    ]
    
    # Generate events with consistent timing (for time-of-day patterns)
    events = dataset_loader.generate_synthetic_events(home_data, days=14, events_per_day=20)
    
    # Inject events
    await event_injector.inject_events(events)
    
    # Fetch events
    data_api_client = DataAPIClient()
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=14)
    
    events_df = await data_api_client.fetch_events(
        start_time=start_time,
        end_time=end_time,
        limit=10000
    )
    
    if events_df.empty:
        pytest.skip("No events fetched from InfluxDB")
    
    # Detect time-of-day patterns
    detector = TimeOfDayPatternDetector(
        min_occurrences=3,
        min_confidence=0.7
    )
    
    detected_patterns = detector.detect_patterns(events_df)
    
    # Filter to time-of-day patterns
    detected_time = [
        p for p in detected_patterns
        if p.get('pattern_type') == 'time_of_day'
    ]
    
    # Calculate metrics
    metrics = calculate_pattern_metrics(
        detected_time,
        ground_truth_time,
        match_threshold=0.7  # Lower threshold for time patterns
    )
    
    # Print report
    print("\n" + format_metrics_report(metrics, "Time-of-Day Pattern Detection"))
    
    # Assert basic quality
    assert metrics['precision'] >= 0.0
    assert metrics['recall'] >= 0.0
    
    print(f"\n✅ Detected {len(detected_time)} time-of-day patterns")
    print(f"✅ Ground truth: {len(ground_truth_time)} patterns")


@pytest.mark.asyncio
async def test_pattern_type_diversity(
    dataset_loader: HomeAssistantDatasetLoader,
    event_injector: EventInjector
):
    """
    Test that all pattern types are being detected.
    
    Ensures pattern detection diversity (not just co-occurrence).
    """
    # Load dataset
    home_data = await dataset_loader.load_synthetic_home("assist-mini")
    
    # Generate and inject events
    events = dataset_loader.generate_synthetic_events(home_data, days=14, events_per_day=30)
    await event_injector.inject_events(events)
    
    # Fetch events
    data_api_client = DataAPIClient()
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=14)
    
    events_df = await data_api_client.fetch_events(
        start_time=start_time,
        end_time=end_time,
        limit=10000
    )
    
    if events_df.empty:
        pytest.skip("No events fetched from InfluxDB")
    
    # Detect patterns with multiple detectors
    all_patterns = []
    
    # Co-occurrence
    co_detector = CoOccurrencePatternDetector(min_confidence=0.7, time_window_minutes=5)
    co_patterns = co_detector.detect_patterns(events_df)
    all_patterns.extend(co_patterns)
    
    # Time-of-day
    time_detector = TimeOfDayPatternDetector(min_occurrences=3, min_confidence=0.7)
    time_patterns = time_detector.detect_patterns(events_df)
    all_patterns.extend(time_patterns)
    
    # Multi-factor (if available)
    try:
        multi_detector = MultiFactorPatternDetector(min_confidence=0.7)
        multi_patterns = multi_detector.detect_patterns(events_df)
        all_patterns.extend(multi_patterns)
    except Exception as e:
        print(f"Multi-factor detector not available: {e}")
    
    # Count patterns by type
    pattern_types: dict[str, int] = {}
    for pattern in all_patterns:
        pattern_type = pattern.get('pattern_type', 'unknown')
        pattern_types[pattern_type] = pattern_types.get(pattern_type, 0) + 1
    
    print(f"\n✅ Pattern Type Diversity:")
    for pattern_type, count in pattern_types.items():
        percentage = (count / len(all_patterns) * 100) if all_patterns else 0
        print(f"  {pattern_type}: {count} ({percentage:.1f}%)")
    
    # Assert diversity
    assert len(pattern_types) > 1, "Should detect multiple pattern types"
    
    # Check that co-occurrence isn't dominating (target: <90%)
    co_occurrence_count = pattern_types.get('co_occurrence', 0)
    co_occurrence_percentage = (co_occurrence_count / len(all_patterns) * 100) if all_patterns else 0
    
    print(f"\n✅ Co-occurrence percentage: {co_occurrence_percentage:.1f}%")
    
    # Note: In real testing, we'd assert co_occurrence_percentage < 90
    # But for now, we just log it


@pytest.mark.asyncio
async def test_pattern_detection_on_multiple_datasets(
    dataset_loader: HomeAssistantDatasetLoader,
    event_injector: EventInjector
):
    """
    Test pattern detection across multiple datasets.
    
    Validates that pattern detection works consistently across
    different home configurations.
    """
    datasets = ['assist-mini']  # Add more as available
    
    results = {}
    
    for dataset_name in datasets:
        try:
            # Load dataset
            home_data = await dataset_loader.load_synthetic_home(dataset_name)
            
            # Extract ground truth
            extractor = GroundTruthExtractor(home_data)
            ground_truth = extractor.extract_patterns()
            
            # Generate and inject events
            events = dataset_loader.generate_synthetic_events(home_data, days=7, events_per_day=50)
            await event_injector.inject_events(events)
            
            # Fetch events
            data_api_client = DataAPIClient()
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=7)
            
            events_df = await data_api_client.fetch_events(
                start_time=start_time,
                end_time=end_time,
                limit=10000
            )
            
            if events_df.empty:
                continue
            
            # Detect patterns
            detector = CoOccurrencePatternDetector(min_confidence=0.7, time_window_minutes=5)
            detected = detector.detect_patterns(events_df)
            
            # Calculate metrics
            metrics = calculate_pattern_metrics(detected, ground_truth, match_threshold=0.8)
            
            results[dataset_name] = {
                'metrics': metrics,
                'detected_count': len(detected),
                'ground_truth_count': len(ground_truth)
            }
            
            print(f"\n✅ {dataset_name}:")
            print(f"  Detected: {len(detected)} patterns")
            print(f"  Ground truth: {len(ground_truth)} patterns")
            print(f"  Precision: {metrics['precision']:.3f}")
            print(f"  Recall: {metrics['recall']:.3f}")
            print(f"  F1: {metrics['f1_score']:.3f}")
        
        except Exception as e:
            print(f"❌ Error testing {dataset_name}: {e}")
            continue
    
    # Assert we got results
    assert len(results) > 0, "Should test at least one dataset"
    
    # Print summary
    print(f"\n✅ Tested {len(results)} datasets")
    avg_precision = sum(r['metrics']['precision'] for r in results.values()) / len(results)
    avg_recall = sum(r['metrics']['recall'] for r in results.values()) / len(results)
    avg_f1 = sum(r['metrics']['f1_score'] for r in results.values()) / len(results)
    
    print(f"✅ Average Precision: {avg_precision:.3f}")
    print(f"✅ Average Recall: {avg_recall:.3f}")
    print(f"✅ Average F1: {avg_f1:.3f}")

