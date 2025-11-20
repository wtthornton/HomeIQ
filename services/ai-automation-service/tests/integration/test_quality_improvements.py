"""
Integration tests for quality improvements to patterns and synergies system.

Quality Improvement: All Priorities
"""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest
from src.integration.pattern_synergy_validator import PatternSynergyValidator

# Import quality improvement modules
from src.pattern_analyzer.co_occurrence import (
    CoOccurrencePatternDetector,
)
from src.pattern_analyzer.confidence_calibrator import ConfidenceCalibrator
from src.pattern_analyzer.pattern_cross_validator import PatternCrossValidator
from src.pattern_analyzer.pattern_deduplicator import PatternDeduplicator


class TestNoiseFiltering:
    """Test comprehensive noise filtering"""

    def test_excluded_domains_filtered(self):
        """Test that excluded domains are filtered out"""
        detector = CoOccurrencePatternDetector(filter_system_noise=True)

        # Test image domain
        assert not detector._is_actionable_entity('image.roborock_map')
        assert not detector._is_actionable_entity('camera.front_door')
        assert not detector._is_actionable_entity('button.emergency')

        # Test actionable domains
        assert detector._is_actionable_entity('light.kitchen')
        assert detector._is_actionable_entity('switch.living_room')

    def test_system_sensors_filtered(self):
        """Test that system sensors are filtered"""
        detector = CoOccurrencePatternDetector(filter_system_noise=True)

        # System sensors should be filtered
        assert not detector._is_actionable_entity('sensor.home_assistant_cpu')
        assert not detector._is_actionable_entity('sensor.slzb_coordinator')
        assert not detector._is_actionable_entity('sensor.device_battery')
        assert not detector._is_actionable_entity('sensor.device_signal_strength')

        # Regular sensors should pass
        assert detector._is_actionable_entity('sensor.temperature')
        assert detector._is_actionable_entity('binary_sensor.motion')

    def test_meaningful_automation_pattern(self):
        """Test that only meaningful automation patterns are kept"""
        detector = CoOccurrencePatternDetector(filter_system_noise=True)

        # Valid: trigger + actionable
        assert detector._is_meaningful_automation_pattern(
            'binary_sensor.motion', 'light.kitchen'
        )

        # Valid: both actionable
        assert detector._is_meaningful_automation_pattern(
            'light.kitchen', 'switch.living_room'
        )

        # Invalid: both sensors (no action possible)
        assert not detector._is_meaningful_automation_pattern(
            'sensor.temperature', 'sensor.humidity'
        )

        # Invalid: both passive
        assert not detector._is_meaningful_automation_pattern(
            'image.map', 'camera.door'
        )

    def test_noise_filtering_in_detection(self):
        """Test that noise filtering works in actual detection"""
        detector = CoOccurrencePatternDetector(
            filter_system_noise=True,
            min_support=1,
            min_confidence=0.5
        )

        # Create test events with noise
        events = pd.DataFrame([
            {'device_id': 'light.kitchen', 'timestamp': datetime.now(timezone.utc), 'state': 'on'},
            {'device_id': 'binary_sensor.motion', 'timestamp': datetime.now(timezone.utc) + timedelta(seconds=10), 'state': 'on'},
            {'device_id': 'image.roborock_map', 'timestamp': datetime.now(timezone.utc) + timedelta(seconds=20), 'state': 'updated'},
            {'device_id': 'sensor.home_assistant_cpu', 'timestamp': datetime.now(timezone.utc) + timedelta(seconds=30), 'state': '50'},
        ])

        patterns = detector.detect_patterns(events)

        # Should not include patterns with image or system sensors
        for pattern in patterns:
            device1 = pattern.get('device1', '')
            device2 = pattern.get('device2', '')
            assert 'image.' not in device1 and 'image.' not in device2
            assert 'sensor.home_assistant_' not in device1 and 'sensor.home_assistant_' not in device2


class TestPatternBalancing:
    """Test pattern type balancing"""

    def test_co_occurrence_threshold_increased(self):
        """Test that co-occurrence thresholds are increased"""
        # This is tested via daily_analysis.py configuration
        # min_support should be at least 10, min_confidence at least 0.75
        detector = CoOccurrencePatternDetector(
            min_support=10,  # Increased from 5
            min_confidence=0.75  # Increased from 0.7
        )

        assert detector.min_support >= 10
        assert detector.min_confidence >= 0.75


class TestConfidenceCalibration:
    """Test confidence calibration"""

    @pytest.mark.asyncio
    async def test_calibration_without_data(self):
        """Test calibration when no historical data exists"""
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        # Create in-memory database
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as db:
            calibrator = ConfidenceCalibrator(db)

            pattern = {
                'pattern_type': 'co_occurrence',
                'confidence': 0.8
            }

            calibrated = await calibrator.calibrate_pattern_confidence(pattern)

            # Should apply conservative adjustment (0.95x) when no data
            assert calibrated == pytest.approx(0.8 * 0.95, abs=0.01)

    @pytest.mark.asyncio
    async def test_calibration_report(self):
        """Test calibration report generation"""
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as db:
            calibrator = ConfidenceCalibrator(db)
            report = await calibrator.generate_calibration_report()

            # Should have entries for all pattern types
            assert 'co_occurrence' in report
            assert 'time_of_day' in report
            assert 'sequence' in report


class TestPatternCrossValidation:
    """Test pattern cross-validation"""

    @pytest.mark.asyncio
    async def test_cross_validation_contradictions(self):
        """Test that contradictions are detected"""
        validator = PatternCrossValidator()

        patterns = [
            {
                'pattern_type': 'time_of_day',
                'device_id': 'light.kitchen',
                'confidence': 0.6,
                'metadata': {'hour': 7, 'minute': 0}
            },
            {
                'pattern_type': 'co_occurrence',
                'device_id': 'light.kitchen',
                'device1': 'binary_sensor.motion',
                'device2': 'light.kitchen',
                'confidence': 0.95
            }
        ]

        results = await validator.cross_validate(patterns)

        # Should detect contradiction (high co-occurrence, low time confidence)
        assert len(results['contradictions']) > 0

    @pytest.mark.asyncio
    async def test_cross_validation_reinforcements(self):
        """Test that reinforcements are detected"""
        validator = PatternCrossValidator()

        patterns = [
            {
                'pattern_type': 'time_of_day',
                'device_id': 'light.kitchen',
                'confidence': 0.8,
                'metadata': {'hour': 7, 'minute': 0}
            },
            {
                'pattern_type': 'time_of_day',
                'device_id': 'light.kitchen',
                'confidence': 0.75,
                'metadata': {'hour': 7, 'minute': 10}  # Within 15 minutes
            }
        ]

        results = await validator.cross_validate(patterns)

        # Should detect reinforcement (similar times)
        assert len(results['reinforcements']) > 0

    @pytest.mark.asyncio
    async def test_quality_score_calculation(self):
        """Test quality score calculation"""
        validator = PatternCrossValidator()

        patterns = [
            {
                'pattern_type': 'co_occurrence',
                'device_id': 'light.kitchen',
                'device1': 'binary_sensor.motion',
                'device2': 'light.kitchen',
                'confidence': 0.8
            }
        ]

        results = await validator.cross_validate(patterns)

        # Should have quality score between 0 and 1
        assert 0.0 <= results['quality_score'] <= 1.0


class TestPatternDeduplication:
    """Test pattern deduplication"""

    def test_time_pattern_consolidation(self):
        """Test that time patterns within 15 minutes are consolidated"""
        deduplicator = PatternDeduplicator()

        patterns = [
            {
                'pattern_type': 'time_of_day',
                'device_id': 'light.kitchen',
                'confidence': 0.8,
                'occurrences': 5,
                'metadata': {'hour': 7, 'minute': 0}
            },
            {
                'pattern_type': 'time_of_day',
                'device_id': 'light.kitchen',
                'confidence': 0.75,
                'occurrences': 3,
                'metadata': {'hour': 7, 'minute': 10}  # Within 15 minutes
            },
            {
                'pattern_type': 'time_of_day',
                'device_id': 'light.kitchen',
                'confidence': 0.7,
                'occurrences': 4,
                'metadata': {'hour': 8, 'minute': 0}  # More than 15 minutes away
            }
        ]

        deduplicated = deduplicator.deduplicate_patterns(patterns)

        # Should consolidate first two (within 15 min), keep third separate
        assert len(deduplicated) == 2

        # First should have combined occurrences
        consolidated = [p for p in deduplicated if p['metadata']['hour'] == 7][0]
        assert consolidated['occurrences'] == 8  # 5 + 3

    def test_exact_duplicate_removal(self):
        """Test that exact duplicates are removed"""
        deduplicator = PatternDeduplicator()

        patterns = [
            {
                'pattern_type': 'co_occurrence',
                'device_id': 'light.kitchen+switch.living_room',
                'device1': 'light.kitchen',
                'device2': 'switch.living_room',
                'confidence': 0.8,
                'occurrences': 5
            },
            {
                'pattern_type': 'co_occurrence',
                'device_id': 'light.kitchen+switch.living_room',
                'device1': 'light.kitchen',
                'device2': 'switch.living_room',
                'confidence': 0.8,
                'occurrences': 5
            }
        ]

        deduplicated = deduplicator.deduplicate_patterns(patterns)

        # Should remove duplicate
        assert len(deduplicated) == 1


class TestEnhancedSynergyValidation:
    """Test enhanced synergy-pattern validation"""

    @pytest.mark.asyncio
    async def test_multi_criteria_validation(self):
        """Test that validation uses multiple criteria"""
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from src.database.models import Pattern as PatternModel

        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        # Create test patterns
        async with async_session() as db:
            # Add test patterns
            co_pattern = PatternModel(
                pattern_type='co_occurrence',
                device_id='binary_sensor.motion+light.kitchen',
                confidence=0.85,
                occurrences=10,
                pattern_metadata={'device1': 'binary_sensor.motion', 'device2': 'light.kitchen'}
            )
            db.add(co_pattern)
            await db.commit()

            # Test synergy validation
            validator = PatternSynergyValidator(db)

            synergy = {
                'synergy_id': 'test-1',
                'synergy_type': 'device_pair',
                'devices': ['binary_sensor.motion', 'light.kitchen'],
                'opportunity_metadata': {
                    'trigger_entity_id': 'binary_sensor.motion',
                    'action_entity_id': 'light.kitchen'
                }
            }

            result = await validator.validate_synergy_with_patterns(synergy)

            # Should have support score > 0 (direct co-occurrence match)
            assert result['pattern_support_score'] > 0
            assert len(result['supporting_patterns']) > 0


class TestMLSynergyStorage:
    """Test ML-discovered synergy storage"""

    @pytest.mark.asyncio
    async def test_discovered_synergy_storage(self):
        """Test that discovered synergies can be stored"""
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from src.database.models import Base
        from src.database.models import DiscoveredSynergy as DiscoveredSynergyDB
        from src.synergy_detection.ml_synergy_miner import DiscoveredSynergy

        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as db:
            from src.synergy_detection.ml_enhanced_synergy_detector import MLEnhancedSynergyDetector

            # Create mock detector
            ml_detector = MLEnhancedSynergyDetector(
                base_synergy_detector=None,  # Mock
                influxdb_client=None,  # Mock
                enable_ml_discovery=True
            )

            # Create test discovered synergy
            discovered = DiscoveredSynergy(
                trigger_entity='binary_sensor.motion',
                action_entity='light.kitchen',
                support=0.1,
                confidence=0.85,
                lift=2.5,
                frequency=25,
                consistency=0.9,
                time_window_seconds=60,
                discovered_at=datetime.now(timezone.utc)
            )

            # Store
            stored_count = await ml_detector._store_discovered_synergies([discovered], db)

            assert stored_count == 1

            # Verify stored
            from sqlalchemy import select
            result = await db.execute(select(DiscoveredSynergyDB))
            stored = result.scalars().all()

            assert len(stored) == 1
            assert stored[0].trigger_entity == 'binary_sensor.motion'
            assert stored[0].action_entity == 'light.kitchen'


class TestEndToEndQuality:
    """End-to-end tests for quality improvements"""

    @pytest.mark.asyncio
    async def test_full_quality_pipeline(self):
        """Test the full quality improvement pipeline"""
        # Create sample events
        events = pd.DataFrame([
            {'device_id': 'light.kitchen', 'timestamp': datetime.now(timezone.utc), 'state': 'on'},
            {'device_id': 'binary_sensor.motion', 'timestamp': datetime.now(timezone.utc) + timedelta(seconds=10), 'state': 'on'},
            {'device_id': 'image.roborock_map', 'timestamp': datetime.now(timezone.utc) + timedelta(seconds=20), 'state': 'updated'},
        ])

        # Step 1: Detect patterns with noise filtering
        detector = CoOccurrencePatternDetector(
            filter_system_noise=True,
            min_support=1,
            min_confidence=0.5
        )
        patterns = detector.detect_patterns(events)

        # Should filter out image patterns
        assert all('image.' not in p.get('device1', '') and 'image.' not in p.get('device2', '')
                  for p in patterns)

        # Step 2: Deduplicate
        deduplicator = PatternDeduplicator()
        deduplicated = deduplicator.deduplicate_patterns(patterns)

        assert len(deduplicated) <= len(patterns)

        # Step 3: Cross-validate
        validator = PatternCrossValidator()
        validation_results = await validator.cross_validate(deduplicated)

        assert 'quality_score' in validation_results
        assert 0.0 <= validation_results['quality_score'] <= 1.0

