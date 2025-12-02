"""
Ground Truth Validator

Validate pattern detection against ground truth and calculate quality metrics.
"""

import logging
from dataclasses import dataclass, field
from typing import Any
from .ground_truth_generator import GroundTruth, ExpectedPattern, PatternType

logger = logging.getLogger(__name__)


@dataclass
class ValidationMetrics:
    """Validation metrics for pattern detection."""
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    pattern_type_metrics: dict[str, dict[str, float]] = field(default_factory=dict)


@dataclass
class QualityReport:
    """Quality report for training data."""
    total_homes: int
    total_expected_patterns: int
    total_detected_patterns: int
    overall_metrics: ValidationMetrics
    per_home_metrics: list[tuple[str, ValidationMetrics]] = field(default_factory=list)
    quality_gate_passed: bool = False
    issues: list[str] = field(default_factory=list)


class GroundTruthValidator:
    """
    Validate pattern detection against ground truth.
    
    Calculates precision, recall, F1 score and enforces quality gates.
    """
    
    PRECISION_THRESHOLD = 0.80  # 80% minimum precision
    RECALL_THRESHOLD = 0.60     # 60% minimum recall
    SIMILARITY_THRESHOLD = 0.7  # 70% similarity for pattern matching
    
    def __init__(self):
        """Initialize ground truth validator."""
        logger.info("GroundTruthValidator initialized")
    
    def validate_patterns(
        self,
        ground_truth: GroundTruth,
        detected_patterns: list[dict[str, Any]]
    ) -> ValidationMetrics:
        """
        Validate detected patterns against ground truth.
        
        Args:
            ground_truth: Expected patterns for home
            detected_patterns: Patterns detected by AI
        
        Returns:
            Validation metrics
        """
        # Match detected patterns to expected patterns
        matches = self._match_patterns(
            ground_truth.expected_patterns,
            detected_patterns
        )
        
        # Calculate metrics
        tp = matches['true_positives']
        fp = matches['false_positives']
        fn = matches['false_negatives']
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        # Calculate per-pattern-type metrics
        type_metrics = self._calculate_type_metrics(
            ground_truth.expected_patterns,
            detected_patterns,
            matches['matched_patterns']
        )
        
        metrics = ValidationMetrics(
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            f1_score=f1,
            pattern_type_metrics=type_metrics
        )
        
        logger.info(f"✅ Validation complete: P={precision:.1%}, R={recall:.1%}, F1={f1:.2f}")
        return metrics
    
    def validate_batch(
        self,
        ground_truths: list[GroundTruth],
        detected_patterns_per_home: dict[str, list[dict[str, Any]]]
    ) -> QualityReport:
        """
        Validate batch of homes.
        
        Args:
            ground_truths: Ground truth for each home
            detected_patterns_per_home: Detected patterns keyed by home_id
        
        Returns:
            Quality report with aggregate metrics
        """
        per_home_metrics = []
        total_expected = 0
        total_detected = 0
        aggregate_tp = 0
        aggregate_fp = 0
        aggregate_fn = 0
        
        for gt in ground_truths:
            detected = detected_patterns_per_home.get(gt.home_id, [])
            metrics = self.validate_patterns(gt, detected)
            
            per_home_metrics.append((gt.home_id, metrics))
            total_expected += len(gt.expected_patterns)
            total_detected += len(detected)
            aggregate_tp += metrics.true_positives
            aggregate_fp += metrics.false_positives
            aggregate_fn += metrics.false_negatives
        
        # Calculate overall metrics
        overall_precision = aggregate_tp / (aggregate_tp + aggregate_fp) if (aggregate_tp + aggregate_fp) > 0 else 0.0
        overall_recall = aggregate_tp / (aggregate_tp + aggregate_fn) if (aggregate_tp + aggregate_fn) > 0 else 0.0
        overall_f1 = 2 * (overall_precision * overall_recall) / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0.0
        
        overall_metrics = ValidationMetrics(
            true_positives=aggregate_tp,
            false_positives=aggregate_fp,
            false_negatives=aggregate_fn,
            precision=overall_precision,
            recall=overall_recall,
            f1_score=overall_f1
        )
        
        # Enforce quality gates
        passed, issues = self.enforce_quality_gate(overall_metrics)
        
        report = QualityReport(
            total_homes=len(ground_truths),
            total_expected_patterns=total_expected,
            total_detected_patterns=total_detected,
            overall_metrics=overall_metrics,
            per_home_metrics=per_home_metrics,
            quality_gate_passed=passed,
            issues=issues
        )
        
        logger.info(f"✅ Batch validation: {len(ground_truths)} homes, P={overall_precision:.1%}, R={overall_recall:.1%}")
        return report
    
    def enforce_quality_gate(
        self,
        metrics: ValidationMetrics
    ) -> tuple[bool, list[str]]:
        """
        Enforce quality gates on validation metrics.
        
        Args:
            metrics: Validation metrics
        
        Returns:
            (passed, issues)
        """
        passed = True
        issues = []
        
        if metrics.precision < self.PRECISION_THRESHOLD:
            passed = False
            issues.append(
                f"Precision {metrics.precision:.1%} < {self.PRECISION_THRESHOLD:.0%} threshold"
            )
        
        if metrics.recall < self.RECALL_THRESHOLD:
            passed = False
            issues.append(
                f"Recall {metrics.recall:.1%} < {self.RECALL_THRESHOLD:.0%} threshold"
            )
        
        if metrics.f1_score < 0.65:  # F1 should be at least 0.65
            passed = False
            issues.append(
                f"F1 score {metrics.f1_score:.2f} < 0.65 threshold"
            )
        
        return passed, issues
    
    def _match_patterns(
        self,
        expected: list[ExpectedPattern],
        detected: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Match detected patterns to expected patterns.
        
        Args:
            expected: Expected patterns
            detected: Detected patterns
        
        Returns:
            Match statistics and matched patterns
        """
        matched_expected = set()
        matched_detected = set()
        matched_patterns = []
        
        # Try to match each detected pattern to an expected pattern
        for i, det_pattern in enumerate(detected):
            best_match = None
            best_score = 0.0
            
            for j, exp_pattern in enumerate(expected):
                if j in matched_expected:
                    continue  # Already matched
                
                # Calculate similarity
                similarity = self._calculate_similarity(exp_pattern, det_pattern)
                
                if similarity > best_score and similarity >= self.SIMILARITY_THRESHOLD:
                    best_score = similarity
                    best_match = j
            
            if best_match is not None:
                matched_expected.add(best_match)
                matched_detected.add(i)
                matched_patterns.append((expected[best_match], det_pattern, best_score))
        
        true_positives = len(matched_detected)
        false_positives = len(detected) - len(matched_detected)
        false_negatives = len(expected) - len(matched_expected)
        
        return {
            'true_positives': true_positives,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
            'matched_patterns': matched_patterns
        }
    
    def _calculate_similarity(
        self,
        expected: ExpectedPattern,
        detected: dict[str, Any]
    ) -> float:
        """
        Calculate similarity between expected and detected pattern.
        
        Uses Jaccard similarity on devices plus pattern type match.
        
        Args:
            expected: Expected pattern
            detected: Detected pattern
        
        Returns:
            Similarity score (0.0 to 1.0)
        """
        similarity = 0.0
        
        # Pattern type match (30% weight)
        det_type = detected.get('pattern_type', detected.get('type', ''))
        if det_type == expected.pattern_type.value:
            similarity += 0.3
        
        # Device overlap (Jaccard similarity, 50% weight)
        expected_devices = set(expected.devices)
        detected_devices = set(detected.get('devices', []))
        
        if expected_devices and detected_devices:
            intersection = len(expected_devices & detected_devices)
            union = len(expected_devices | detected_devices)
            jaccard = intersection / union if union > 0 else 0.0
            similarity += 0.5 * jaccard
        
        # Trigger device match (20% weight)
        det_trigger = detected.get('trigger_device', detected.get('trigger', None))
        if expected.trigger_device and det_trigger == expected.trigger_device:
            similarity += 0.2
        
        return similarity
    
    def _calculate_type_metrics(
        self,
        expected: list[ExpectedPattern],
        detected: list[dict[str, Any]],
        matched_patterns: list[tuple[ExpectedPattern, dict, float]]
    ) -> dict[str, dict[str, float]]:
        """Calculate metrics per pattern type."""
        type_metrics: dict[str, dict[str, Any]] = {}
        
        # Initialize counters for each pattern type
        for pattern_type in PatternType:
            type_metrics[pattern_type.value] = {
                'expected': 0,
                'detected': 0,
                'matched': 0,
                'precision': 0.0,
                'recall': 0.0
            }
        
        # Count expected patterns by type
        for exp in expected:
            type_metrics[exp.pattern_type.value]['expected'] += 1
        
        # Count detected patterns by type
        for det in detected:
            det_type = det.get('pattern_type', det.get('type', ''))
            if det_type in type_metrics:
                type_metrics[det_type]['detected'] += 1
        
        # Count matched patterns by type
        for exp, det, score in matched_patterns:
            type_metrics[exp.pattern_type.value]['matched'] += 1
        
        # Calculate precision and recall per type
        for ptype, metrics in type_metrics.items():
            if metrics['detected'] > 0:
                metrics['precision'] = metrics['matched'] / metrics['detected']
            if metrics['expected'] > 0:
                metrics['recall'] = metrics['matched'] / metrics['expected']
        
        # Remove types with no expected or detected patterns
        type_metrics = {
            k: v for k, v in type_metrics.items()
            if v['expected'] > 0 or v['detected'] > 0
        }
        
        return type_metrics

