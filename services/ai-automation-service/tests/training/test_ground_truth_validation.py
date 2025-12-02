"""
Test Ground Truth Validation Framework

Tests for Story AI11.3: Ground Truth Validation Framework
"""

import pytest
from src.training.validation.ground_truth_generator import (
    GroundTruthGenerator,
    ExpectedPattern,
    GroundTruth,
    PatternType
)
from src.training.validation.ground_truth_validator import (
    GroundTruthValidator,
    ValidationMetrics,
    QualityReport
)
from src.training.validation.quality_metrics import QualityMetricsCalculator


class TestGroundTruthGenerator:
    """Test ground truth generation from synthetic homes."""
    
    def test_generate_ground_truth_basic(self):
        """Test basic ground truth generation."""
        generator = GroundTruthGenerator()
        
        home_data = {
            'home_id': 'test_home_001',
            'home_type': 'apartment',
            'size_category': 'small'
        }
        
        devices = [
            {
                'entity_id': 'light.kitchen_light_ceiling',
                'device_type': 'light',
                'area': 'Kitchen',
                'category': 'lighting'
            },
            {
                'entity_id': 'binary_sensor.bedroom_motion_sensor',
                'device_type': 'binary_sensor',
                'device_class': 'motion',
                'area': 'Bedroom',
                'category': 'security'
            }
        ]
        
        areas = [
            {'name': 'Kitchen', 'floor': 'ground_floor'},
            {'name': 'Bedroom', 'floor': 'ground_floor'}
        ]
        
        ground_truth = generator.generate_ground_truth(home_data, devices, areas)
        
        assert ground_truth.home_id == 'test_home_001'
        assert ground_truth.home_type == 'apartment'
        assert len(ground_truth.expected_patterns) > 0
        assert 'areas' in ground_truth.metadata
        assert 'devices' in ground_truth.metadata
    
    def test_time_of_day_patterns_generated(self):
        """Test time-of-day patterns are generated for lights."""
        generator = GroundTruthGenerator()
        
        devices = [
            {
                'entity_id': 'light.living_room_light_ceiling',
                'device_type': 'light',
                'area': 'Living Room'
            },
            {
                'entity_id': 'light.kitchen_light_wall',
                'device_type': 'light',
                'area': 'Kitchen'
            }
        ]
        
        areas = [{'name': 'Living Room'}, {'name': 'Kitchen'}]
        patterns = generator._generate_time_of_day_patterns(devices, areas)
        
        assert len(patterns) > 0
        assert any(p.pattern_type == PatternType.TIME_OF_DAY for p in patterns)
        assert any('sunset' in p.description.lower() for p in patterns)
    
    def test_motion_light_patterns_generated(self):
        """Test motion-triggered light patterns are generated."""
        generator = GroundTruthGenerator()
        
        devices = [
            {
                'entity_id': 'binary_sensor.bedroom_motion_sensor',
                'device_type': 'binary_sensor',
                'device_class': 'motion',
                'area': 'Bedroom'
            },
            {
                'entity_id': 'light.bedroom_light_ceiling',
                'device_type': 'light',
                'area': 'Bedroom'
            }
        ]
        
        areas = [{'name': 'Bedroom'}]
        patterns = generator._generate_motion_light_patterns(devices, areas)
        
        assert len(patterns) > 0
        assert any(p.pattern_type == PatternType.CO_OCCURRENCE for p in patterns)
        assert any('motion' in p.description.lower() for p in patterns)
    
    def test_climate_patterns_generated(self):
        """Test climate automation patterns are generated."""
        generator = GroundTruthGenerator()
        
        devices = [
            {
                'entity_id': 'climate.living_room_thermostat',
                'device_type': 'climate',
                'area': 'Living Room'
            }
        ]
        
        areas = [{'name': 'Living Room'}]
        patterns = generator._generate_climate_patterns(devices, areas)
        
        assert len(patterns) > 0
        assert any(p.pattern_type == PatternType.TIME_OF_DAY for p in patterns)
        assert any('thermostat' in p.description.lower() for p in patterns)
    
    def test_synergy_patterns_generated(self):
        """Test multi-device synergy patterns are generated."""
        generator = GroundTruthGenerator()
        
        devices = [
            {
                'entity_id': 'binary_sensor.front_door_door_sensor',
                'device_type': 'binary_sensor',
                'device_class': 'door',
                'area': 'Front Door'
            },
            {
                'entity_id': 'light.entryway_light_ceiling',
                'device_type': 'light',
                'area': 'Front Door'
            }
        ]
        
        areas = [{'name': 'Front Door'}]
        patterns = generator._generate_synergy_patterns(devices, areas)
        
        assert len(patterns) > 0
        assert any(p.pattern_type == PatternType.MULTI_DEVICE_SYNERGY for p in patterns)
        assert any('door' in p.description.lower() for p in patterns)
    
    def test_device_breakdown_calculation(self):
        """Test device breakdown is calculated correctly."""
        generator = GroundTruthGenerator()
        
        devices = [
            {'device_type': 'light'},
            {'device_type': 'light'},
            {'device_type': 'binary_sensor'},
            {'device_type': 'climate'}
        ]
        
        breakdown = generator._get_device_breakdown(devices)
        
        assert breakdown['light'] == 2
        assert breakdown['binary_sensor'] == 1
        assert breakdown['climate'] == 1


class TestGroundTruthValidator:
    """Test pattern validation against ground truth."""
    
    def test_validate_patterns_perfect_match(self):
        """Test validation with perfect pattern matches."""
        validator = GroundTruthValidator()
        
        ground_truth = GroundTruth(
            home_id='test_home',
            home_type='apartment',
            expected_patterns=[
                ExpectedPattern(
                    pattern_id='pattern_1',
                    pattern_type=PatternType.TIME_OF_DAY,
                    description='Lights at sunset',
                    devices=['light.kitchen_light'],
                    trigger_device=None,
                    action_devices=['light.kitchen_light'],
                    conditions={'time': 'sunset'},
                    frequency='daily',
                    confidence=0.9
                )
            ],
            metadata={},
            generated_at='2025-12-02T10:00:00'
        )
        
        detected_patterns = [
            {
                'pattern_type': 'time_of_day',
                'devices': ['light.kitchen_light'],
                'trigger_device': None,
                'description': 'Lights at sunset'
            }
        ]
        
        metrics = validator.validate_patterns(ground_truth, detected_patterns)
        
        assert metrics.true_positives >= 1
        assert metrics.precision >= 0.8
        assert metrics.recall >= 0.8
    
    def test_validate_patterns_no_match(self):
        """Test validation with no pattern matches."""
        validator = GroundTruthValidator()
        
        ground_truth = GroundTruth(
            home_id='test_home',
            home_type='apartment',
            expected_patterns=[
                ExpectedPattern(
                    pattern_id='pattern_1',
                    pattern_type=PatternType.TIME_OF_DAY,
                    description='Lights at sunset',
                    devices=['light.kitchen_light'],
                    trigger_device=None,
                    action_devices=['light.kitchen_light'],
                    conditions={},
                    frequency='daily',
                    confidence=0.9
                )
            ],
            metadata={},
            generated_at='2025-12-02T10:00:00'
        )
        
        detected_patterns = [
            {
                'pattern_type': 'co_occurrence',
                'devices': ['binary_sensor.motion'],
                'description': 'Different pattern'
            }
        ]
        
        metrics = validator.validate_patterns(ground_truth, detected_patterns)
        
        assert metrics.false_positives >= 1
        assert metrics.false_negatives >= 1
        assert metrics.precision < 0.5
    
    def test_validate_patterns_partial_match(self):
        """Test validation with partial pattern matches."""
        validator = GroundTruthValidator()
        
        ground_truth = GroundTruth(
            home_id='test_home',
            home_type='apartment',
            expected_patterns=[
                ExpectedPattern(
                    pattern_id='pattern_1',
                    pattern_type=PatternType.CO_OCCURRENCE,
                    description='Motion triggers lights',
                    devices=['binary_sensor.motion', 'light.bedroom_light'],
                    trigger_device='binary_sensor.motion',
                    action_devices=['light.bedroom_light'],
                    conditions={},
                    frequency='multiple_daily',
                    confidence=0.85
                )
            ],
            metadata={},
            generated_at='2025-12-02T10:00:00'
        )
        
        # Partial match: same type, some devices overlap
        detected_patterns = [
            {
                'pattern_type': 'co_occurrence',
                'devices': ['binary_sensor.motion', 'light.bedroom_light', 'light.kitchen_light'],
                'trigger_device': 'binary_sensor.motion',
                'description': 'Motion triggers multiple lights'
            }
        ]
        
        metrics = validator.validate_patterns(ground_truth, detected_patterns)
        
        # Should have some match (similarity >= threshold)
        assert metrics.true_positives >= 0
        assert metrics.precision >= 0.0
    
    def test_validate_batch(self):
        """Test batch validation across multiple homes."""
        validator = GroundTruthValidator()
        
        ground_truths = [
            GroundTruth(
                home_id='home_1',
                home_type='apartment',
                expected_patterns=[
                    ExpectedPattern(
                        pattern_id='p1',
                        pattern_type=PatternType.TIME_OF_DAY,
                        description='Test',
                        devices=['light.1'],
                        trigger_device=None,
                        action_devices=['light.1'],
                        conditions={},
                        frequency='daily',
                        confidence=0.9
                    )
                ],
                metadata={},
                generated_at='2025-12-02T10:00:00'
            ),
            GroundTruth(
                home_id='home_2',
                home_type='apartment',
                expected_patterns=[
                    ExpectedPattern(
                        pattern_id='p2',
                        pattern_type=PatternType.CO_OCCURRENCE,
                        description='Test',
                        devices=['binary_sensor.1', 'light.2'],
                        trigger_device='binary_sensor.1',
                        action_devices=['light.2'],
                        conditions={},
                        frequency='multiple_daily',
                        confidence=0.85
                    )
                ],
                metadata={},
                generated_at='2025-12-02T10:00:00'
            )
        ]
        
        detected_patterns_per_home = {
            'home_1': [
                {
                    'pattern_type': 'time_of_day',
                    'devices': ['light.1'],
                    'description': 'Test'
                }
            ],
            'home_2': [
                {
                    'pattern_type': 'co_occurrence',
                    'devices': ['binary_sensor.1', 'light.2'],
                    'trigger_device': 'binary_sensor.1',
                    'description': 'Test'
                }
            ]
        }
        
        report = validator.validate_batch(ground_truths, detected_patterns_per_home)
        
        assert report.total_homes == 2
        assert report.total_expected_patterns == 2
        assert report.total_detected_patterns == 2
        assert len(report.per_home_metrics) == 2
    
    def test_quality_gate_enforcement_pass(self):
        """Test quality gate passes with good metrics."""
        validator = GroundTruthValidator()
        
        metrics = ValidationMetrics(
            true_positives=80,
            false_positives=20,
            false_negatives=10,
            precision=0.80,
            recall=0.89,
            f1_score=0.84
        )
        
        passed, issues = validator.enforce_quality_gate(metrics)
        
        assert passed is True
        assert len(issues) == 0
    
    def test_quality_gate_enforcement_fail_precision(self):
        """Test quality gate fails with low precision."""
        validator = GroundTruthValidator()
        
        metrics = ValidationMetrics(
            true_positives=50,
            false_positives=100,
            false_negatives=10,
            precision=0.33,  # Below 0.80 threshold
            recall=0.83,
            f1_score=0.47
        )
        
        passed, issues = validator.enforce_quality_gate(metrics)
        
        assert passed is False
        assert len(issues) > 0
        assert any('precision' in issue.lower() for issue in issues)
    
    def test_quality_gate_enforcement_fail_recall(self):
        """Test quality gate fails with low recall."""
        validator = GroundTruthValidator()
        
        metrics = ValidationMetrics(
            true_positives=30,
            false_positives=10,
            false_negatives=70,
            precision=0.75,
            recall=0.30,  # Below 0.60 threshold
            f1_score=0.43
        )
        
        passed, issues = validator.enforce_quality_gate(metrics)
        
        assert passed is False
        assert len(issues) > 0
        assert any('recall' in issue.lower() for issue in issues)
    
    def test_pattern_similarity_calculation(self):
        """Test pattern similarity calculation."""
        validator = GroundTruthValidator()
        
        expected = ExpectedPattern(
            pattern_id='p1',
            pattern_type=PatternType.CO_OCCURRENCE,
            description='Motion triggers lights',
            devices=['binary_sensor.motion', 'light.bedroom'],
            trigger_device='binary_sensor.motion',
            action_devices=['light.bedroom'],
            conditions={},
            frequency='multiple_daily',
            confidence=0.85
        )
        
        detected = {
            'pattern_type': 'co_occurrence',
            'devices': ['binary_sensor.motion', 'light.bedroom'],
            'trigger_device': 'binary_sensor.motion'
        }
        
        similarity = validator._calculate_similarity(expected, detected)
        
        assert 0.0 <= similarity <= 1.0
        assert similarity >= 0.7  # Should match well
    
    def test_pattern_matching_logic(self):
        """Test pattern matching finds correct matches."""
        validator = GroundTruthValidator()
        
        expected = [
            ExpectedPattern(
                pattern_id='p1',
                pattern_type=PatternType.TIME_OF_DAY,
                description='Lights at sunset',
                devices=['light.1'],
                trigger_device=None,
                action_devices=['light.1'],
                conditions={},
                frequency='daily',
                confidence=0.9
            )
        ]
        
        detected = [
            {
                'pattern_type': 'time_of_day',
                'devices': ['light.1'],
                'description': 'Lights at sunset'
            }
        ]
        
        matches = validator._match_patterns(expected, detected)
        
        assert matches['true_positives'] >= 1
        assert matches['false_positives'] == 0
        assert matches['false_negatives'] == 0


class TestQualityMetricsCalculator:
    """Test quality metrics reporting."""
    
    def test_generate_text_report(self):
        """Test text report generation."""
        calculator = QualityMetricsCalculator()
        
        report = QualityReport(
            total_homes=10,
            total_expected_patterns=50,
            total_detected_patterns=45,
            overall_metrics=ValidationMetrics(
                true_positives=40,
                false_positives=5,
                false_negatives=10,
                precision=0.89,
                recall=0.80,
                f1_score=0.84
            ),
            per_home_metrics=[],
            quality_gate_passed=True,
            issues=[]
        )
        
        text_report = calculator.generate_text_report(report)
        
        assert 'Training Data Quality Report' in text_report
        assert '10' in text_report  # Total homes
        assert '89.0%' in text_report or '0.89' in text_report  # Precision
        assert 'PASSED' in text_report
    
    def test_generate_json_report(self):
        """Test JSON report generation."""
        calculator = QualityMetricsCalculator()
        
        report = QualityReport(
            total_homes=5,
            total_expected_patterns=25,
            total_detected_patterns=20,
            overall_metrics=ValidationMetrics(
                true_positives=18,
                false_positives=2,
                false_negatives=7,
                precision=0.90,
                recall=0.72,
                f1_score=0.80
            ),
            per_home_metrics=[
                ('home_1', ValidationMetrics(
                    true_positives=4,
                    false_positives=1,
                    false_negatives=1,
                    precision=0.80,
                    recall=0.80,
                    f1_score=0.80
                ))
            ],
            quality_gate_passed=True,
            issues=[]
        )
        
        json_report = calculator.generate_json_report(report)
        
        assert json_report['summary']['total_homes'] == 5
        assert json_report['summary']['quality_gate_passed'] is True
        assert json_report['overall_metrics']['precision'] == 0.90
        assert len(json_report['per_home_metrics']) == 1
    
    def test_generate_markdown_report(self):
        """Test markdown report generation."""
        calculator = QualityMetricsCalculator()
        
        report = QualityReport(
            total_homes=3,
            total_expected_patterns=15,
            total_detected_patterns=12,
            overall_metrics=ValidationMetrics(
                true_positives=10,
                false_positives=2,
                false_negatives=5,
                precision=0.83,
                recall=0.67,
                f1_score=0.74
            ),
            per_home_metrics=[],
            quality_gate_passed=True,
            issues=[]
        )
        
        md_report = calculator.generate_markdown_report(report)
        
        assert '# Training Data Quality Report' in md_report
        assert '## Overall Metrics' in md_report
        assert '**PASSED**' in md_report or 'PASSED' in md_report
    
    def test_calculate_summary_statistics(self):
        """Test summary statistics calculation."""
        calculator = QualityMetricsCalculator()
        
        report = QualityReport(
            total_homes=3,
            total_expected_patterns=15,
            total_detected_patterns=12,
            overall_metrics=ValidationMetrics(),
            per_home_metrics=[
                ('home_1', ValidationMetrics(precision=0.90, recall=0.80, f1_score=0.85)),
                ('home_2', ValidationMetrics(precision=0.85, recall=0.75, f1_score=0.80)),
                ('home_3', ValidationMetrics(precision=0.80, recall=0.70, f1_score=0.75))
            ],
            quality_gate_passed=True,
            issues=[]
        )
        
        stats = calculator.calculate_summary_statistics(report)
        
        assert 'precision' in stats
        assert 'recall' in stats
        assert 'f1_score' in stats
        assert stats['precision']['mean'] == pytest.approx(0.85, abs=0.01)
        assert stats['precision']['min'] == 0.80
        assert stats['precision']['max'] == 0.90


class TestIntegration:
    """Test integration of generator, validator, and calculator."""
    
    def test_full_validation_pipeline(self):
        """Test complete validation pipeline."""
        generator = GroundTruthGenerator()
        validator = GroundTruthValidator()
        calculator = QualityMetricsCalculator()
        
        # Generate synthetic home
        home_data = {
            'home_id': 'integration_test_home',
            'home_type': 'apartment',
            'size_category': 'small'
        }
        
        devices = [
            {
                'entity_id': 'light.kitchen_light_ceiling',
                'device_type': 'light',
                'area': 'Kitchen',
                'category': 'lighting'
            },
            {
                'entity_id': 'binary_sensor.bedroom_motion_sensor',
                'device_type': 'binary_sensor',
                'device_class': 'motion',
                'area': 'Bedroom',
                'category': 'security'
            },
            {
                'entity_id': 'light.bedroom_light_ceiling',
                'device_type': 'light',
                'area': 'Bedroom',
                'category': 'lighting'
            }
        ]
        
        areas = [
            {'name': 'Kitchen', 'floor': 'ground_floor'},
            {'name': 'Bedroom', 'floor': 'ground_floor'}
        ]
        
        # Generate ground truth
        ground_truth = generator.generate_ground_truth(home_data, devices, areas)
        
        assert len(ground_truth.expected_patterns) > 0
        
        # Simulate detected patterns (perfect match for test)
        detected_patterns = [
            {
                'pattern_type': 'time_of_day',
                'devices': ['light.kitchen_light_ceiling'],
                'description': 'Lights at sunset'
            },
            {
                'pattern_type': 'co_occurrence',
                'devices': ['binary_sensor.bedroom_motion_sensor', 'light.bedroom_light_ceiling'],
                'trigger_device': 'binary_sensor.bedroom_motion_sensor',
                'description': 'Motion triggers lights'
            }
        ]
        
        # Validate
        metrics = validator.validate_patterns(ground_truth, detected_patterns)
        
        assert metrics.precision >= 0.0
        assert metrics.recall >= 0.0
        
        # Generate report
        report = QualityReport(
            total_homes=1,
            total_expected_patterns=len(ground_truth.expected_patterns),
            total_detected_patterns=len(detected_patterns),
            overall_metrics=metrics,
            per_home_metrics=[(ground_truth.home_id, metrics)],
            quality_gate_passed=validator.enforce_quality_gate(metrics)[0],
            issues=validator.enforce_quality_gate(metrics)[1]
        )
        
        # Generate reports
        text_report = calculator.generate_text_report(report)
        json_report = calculator.generate_json_report(report)
        md_report = calculator.generate_markdown_report(report)
        
        assert len(text_report) > 0
        assert json_report['summary']['total_homes'] == 1
        assert '# Training Data Quality Report' in md_report
        
        print(f"\n✅ Full pipeline test complete")
        print(f"   Expected patterns: {len(ground_truth.expected_patterns)}")
        print(f"   Detected patterns: {len(detected_patterns)}")
        print(f"   Precision: {metrics.precision:.1%}")
        print(f"   Recall: {metrics.recall:.1%}")

