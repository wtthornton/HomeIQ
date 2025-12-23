"""
Pattern Quality Metrics

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.9: Quality Metrics & Reporting

Calculate comprehensive quality metrics for patterns.
"""

import logging
from typing import Any
from collections import Counter

import numpy as np
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    accuracy_score,
    confusion_matrix,
    roc_auc_score
)

logger = logging.getLogger(__name__)


class PatternQualityMetrics:
    """
    Calculate quality metrics for patterns.
    
    Provides metrics for:
    - Precision/recall
    - False positive rate
    - Quality score distribution
    - Model performance
    """
    
    def calculate_precision_recall(
        self,
        predictions: list[float],
        labels: list[int],
        threshold: float = 0.7
    ) -> dict[str, float]:
        """
        Calculate precision and recall.
        
        Args:
            predictions: Predicted quality scores (0.0-1.0)
            labels: True labels (1=high quality, 0=low quality)
            threshold: Quality threshold for binary classification
        
        Returns:
            Dictionary with precision, recall, f1, accuracy, etc.
        """
        if len(predictions) != len(labels):
            raise ValueError("Predictions and labels must have same length")
        
        if not predictions:
            return {
                'precision': 0.0,
                'recall': 0.0,
                'f1': 0.0,
                'accuracy': 0.0,
                'support': 0
            }
        
        # Convert predictions to binary (>= threshold = high quality)
        binary_predictions = [1 if p >= threshold else 0 for p in predictions]
        
        # Calculate metrics
        precision = precision_score(labels, binary_predictions, zero_division=0.0)
        recall = recall_score(labels, binary_predictions, zero_division=0.0)
        f1 = f1_score(labels, binary_predictions, zero_division=0.0)
        accuracy = accuracy_score(labels, binary_predictions)
        
        # Calculate support (number of true positives + false negatives)
        support = sum(labels)
        
        # Confusion matrix
        cm = confusion_matrix(labels, binary_predictions)
        tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
        
        return {
            'precision': float(precision),
            'recall': float(recall),
            'f1': float(f1),
            'accuracy': float(accuracy),
            'support': int(support),
            'true_positives': int(tp),
            'false_positives': int(fp),
            'true_negatives': int(tn),
            'false_negatives': int(fn),
            'threshold': threshold
        }
    
    def calculate_false_positive_rate(
        self,
        predictions: list[float],
        labels: list[int],
        threshold: float = 0.7
    ) -> float:
        """
        Calculate false positive rate.
        
        Args:
            predictions: Predicted quality scores
            labels: True labels (1=high quality, 0=low quality)
            threshold: Quality threshold
        
        Returns:
            False positive rate (0.0-1.0)
        """
        if len(predictions) != len(labels):
            raise ValueError("Predictions and labels must have same length")
        
        if not predictions:
            return 0.0
        
        # Convert predictions to binary
        binary_predictions = [1 if p >= threshold else 0 for p in predictions]
        
        # Calculate FPR = FP / (FP + TN)
        cm = confusion_matrix(labels, binary_predictions)
        if cm.size == 4:
            tn, fp, fn, tp = cm.ravel()
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        else:
            fpr = 0.0
        
        return float(fpr)
    
    def calculate_quality_distribution(
        self,
        quality_scores: list[float]
    ) -> dict[str, Any]:
        """
        Calculate quality score distribution.
        
        Args:
            quality_scores: List of quality scores (0.0-1.0)
        
        Returns:
            Distribution statistics (mean, std, percentiles, histogram, etc.)
        """
        if not quality_scores:
            return {
                'count': 0,
                'mean': 0.0,
                'std': 0.0,
                'min': 0.0,
                'max': 0.0,
                'percentiles': {},
                'histogram': {}
            }
        
        scores_array = np.array(quality_scores)
        
        # Basic statistics
        mean = float(np.mean(scores_array))
        std = float(np.std(scores_array))
        min_score = float(np.min(scores_array))
        max_score = float(np.max(scores_array))
        median = float(np.median(scores_array))
        
        # Percentiles
        percentiles = {
            'p25': float(np.percentile(scores_array, 25)),
            'p50': float(median),
            'p75': float(np.percentile(scores_array, 75)),
            'p90': float(np.percentile(scores_array, 90)),
            'p95': float(np.percentile(scores_array, 95)),
            'p99': float(np.percentile(scores_array, 99))
        }
        
        # Histogram (10 bins)
        hist, bin_edges = np.histogram(scores_array, bins=10, range=(0.0, 1.0))
        histogram = {
            'bins': [float(edge) for edge in bin_edges],
            'counts': [int(count) for count in hist]
        }
        
        # Quality categories
        high_quality = sum(1 for s in quality_scores if s >= 0.7)
        medium_quality = sum(1 for s in quality_scores if 0.5 <= s < 0.7)
        low_quality = sum(1 for s in quality_scores if s < 0.5)
        
        return {
            'count': len(quality_scores),
            'mean': mean,
            'std': std,
            'min': min_score,
            'max': max_score,
            'median': median,
            'percentiles': percentiles,
            'histogram': histogram,
            'categories': {
                'high_quality': high_quality,
                'medium_quality': medium_quality,
                'low_quality': low_quality
            }
        }
    
    def calculate_roc_auc(
        self,
        predictions: list[float],
        labels: list[int]
    ) -> float:
        """
        Calculate ROC AUC score.
        
        Args:
            predictions: Predicted quality scores
            labels: True labels (1=high quality, 0=low quality)
        
        Returns:
            ROC AUC score (0.0-1.0)
        """
        if len(predictions) != len(labels):
            raise ValueError("Predictions and labels must have same length")
        
        if not predictions:
            return 0.0
        
        # Check if we have both classes
        unique_labels = set(labels)
        if len(unique_labels) < 2:
            logger.warning("Only one class present, cannot calculate ROC AUC")
            return 0.0
        
        try:
            auc = roc_auc_score(labels, predictions)
            return float(auc)
        except Exception as e:
            logger.warning(f"Failed to calculate ROC AUC: {e}")
            return 0.0
    
    def calculate_comprehensive_metrics(
        self,
        predictions: list[float],
        labels: list[int],
        threshold: float = 0.7
    ) -> dict[str, Any]:
        """
        Calculate comprehensive quality metrics.
        
        Args:
            predictions: Predicted quality scores
            labels: True labels
            threshold: Quality threshold
        
        Returns:
            Dictionary with all metrics
        """
        precision_recall = self.calculate_precision_recall(predictions, labels, threshold)
        fpr = self.calculate_false_positive_rate(predictions, labels, threshold)
        roc_auc = self.calculate_roc_auc(predictions, labels)
        distribution = self.calculate_quality_distribution(predictions)
        
        return {
            'precision_recall': precision_recall,
            'false_positive_rate': fpr,
            'roc_auc': roc_auc,
            'distribution': distribution,
            'threshold': threshold,
            'sample_count': len(predictions)
        }

