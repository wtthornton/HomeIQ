"""
Metrics Calculation for Pattern and Synergy Detection

Phase 2: Pattern Testing - Metrics Collection

Calculates precision, recall, F1 score, and other metrics for evaluating
pattern detection and synergy detection accuracy against ground truth.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def calculate_pattern_metrics(
    detected_patterns: list[dict[str, Any]],
    ground_truth_patterns: list[dict[str, Any]],
    match_threshold: float = 0.8
) -> dict[str, Any]:
    """
    Calculate precision, recall, and F1 score for pattern detection.
    
    Args:
        detected_patterns: List of detected patterns from pattern detectors
        ground_truth_patterns: List of ground truth patterns from dataset
        match_threshold: Threshold for considering patterns as matching (0.0-1.0)
    
    Returns:
        Dictionary with metrics:
        - precision: TP / (TP + FP)
        - recall: TP / (TP + FN)
        - f1_score: 2 * (precision * recall) / (precision + recall)
        - true_positives: Number of correctly detected patterns
        - false_positives: Number of incorrectly detected patterns
        - false_negatives: Number of missed ground truth patterns
        - total_detected: Total patterns detected
        - total_ground_truth: Total ground truth patterns
        - matches: List of matched pattern pairs
    """
    if not ground_truth_patterns:
        logger.warning("No ground truth patterns provided, cannot calculate metrics")
        return {
            'precision': 0.0,
            'recall': 0.0,
            'f1_score': 0.0,
            'true_positives': 0,
            'false_positives': len(detected_patterns),
            'false_negatives': 0,
            'total_detected': len(detected_patterns),
            'total_ground_truth': 0,
            'matches': []
        }
    
    if not detected_patterns:
        return {
            'precision': 0.0,
            'recall': 0.0,
            'f1_score': 0.0,
            'true_positives': 0,
            'false_positives': 0,
            'false_negatives': len(ground_truth_patterns),
            'total_detected': 0,
            'total_ground_truth': len(ground_truth_patterns),
            'matches': []
        }
    
    # Match detected patterns to ground truth
    matches = []
    matched_gt_indices = set()
    matched_detected_indices = set()
    
    for i, detected in enumerate(detected_patterns):
        best_match = None
        best_score = 0.0
        best_gt_idx = None
        
        for j, ground_truth in enumerate(ground_truth_patterns):
            if j in matched_gt_indices:
                continue
            
            score = _calculate_pattern_similarity(detected, ground_truth)
            if score > best_score and score >= match_threshold:
                best_score = score
                best_match = ground_truth
                best_gt_idx = j
        
        if best_match:
            matches.append({
                'detected': detected,
                'ground_truth': best_match,
                'similarity_score': best_score
            })
            matched_gt_indices.add(best_gt_idx)
            matched_detected_indices.add(i)
    
    # Calculate metrics
    true_positives = len(matches)
    false_positives = len(detected_patterns) - true_positives
    false_negatives = len(ground_truth_patterns) - true_positives
    
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'true_positives': true_positives,
        'false_positives': false_positives,
        'false_negatives': false_negatives,
        'total_detected': len(detected_patterns),
        'total_ground_truth': len(ground_truth_patterns),
        'matches': matches,
        'match_threshold': match_threshold
    }


def _calculate_pattern_similarity(
    detected: dict[str, Any],
    ground_truth: dict[str, Any]
) -> float:
    """
    Calculate similarity score between detected pattern and ground truth.
    
    Compares:
    - Pattern type (must match)
    - Device/entity IDs (must match)
    - Time/conditions (partial match)
    
    Args:
        detected: Detected pattern dictionary
        ground_truth: Ground truth pattern dictionary
    
    Returns:
        Similarity score (0.0-1.0)
    """
    score = 0.0
    max_score = 0.0
    
    # Pattern type match (required, 40% weight)
    detected_type = detected.get('pattern_type', '')
    gt_type = ground_truth.get('pattern_type', '')
    if detected_type == gt_type:
        score += 0.4
    elif not detected_type or not gt_type:
        # If type not specified, don't penalize
        pass
    else:
        # Type mismatch - return low score
        return 0.0
    max_score += 0.4
    
    # Device/entity match (required, 40% weight)
    detected_devices = _extract_devices_from_pattern(detected)
    gt_devices = _extract_devices_from_pattern(ground_truth)
    
    if detected_devices and gt_devices:
        # Check if devices overlap
        detected_set = set(detected_devices)
        gt_set = set(gt_devices)
        
        if detected_set == gt_set:
            score += 0.4  # Perfect match
        elif detected_set.intersection(gt_set):
            # Partial match
            intersection = len(detected_set.intersection(gt_set))
            union = len(detected_set.union(gt_set))
            score += 0.4 * (intersection / union)
        else:
            # No device overlap - return low score
            return 0.0
    max_score += 0.4
    
    # Time/condition match (optional, 20% weight)
    detected_time = detected.get('time', detected.get('time_of_day'))
    gt_time = ground_truth.get('time', ground_truth.get('time_of_day'))
    
    if detected_time and gt_time:
        if detected_time == gt_time:
            score += 0.2  # Perfect time match
        else:
            # Partial time match (within 1 hour)
            score += 0.1
    max_score += 0.2
    
    # Normalize score
    if max_score > 0:
        return score / max_score
    return 0.0


def _extract_devices_from_pattern(pattern: dict[str, Any]) -> list[str]:
    """Extract device/entity IDs from pattern dictionary"""
    devices = []
    
    # Try various field names
    for field in ['device1', 'device2', 'entity_id', 'entity_ids', 'devices']:
        value = pattern.get(field)
        if value:
            if isinstance(value, list):
                devices.extend(value)
            elif isinstance(value, str):
                devices.append(value)
    
    # Remove duplicates and empty strings
    devices = list(set(d for d in devices if d))
    return devices


def calculate_synergy_metrics(
    detected_synergies: list[dict[str, Any]],
    ground_truth_synergies: list[dict[str, Any]],
    match_threshold: float = 0.8
) -> dict[str, Any]:
    """
    Calculate precision, recall, and F1 score for synergy detection.
    
    Args:
        detected_synergies: List of detected synergies
        ground_truth_synergies: List of ground truth synergies
        match_threshold: Threshold for considering synergies as matching
    
    Returns:
        Dictionary with metrics (same format as calculate_pattern_metrics)
    """
    if not ground_truth_synergies:
        return {
            'precision': 0.0,
            'recall': 0.0,
            'f1_score': 0.0,
            'true_positives': 0,
            'false_positives': len(detected_synergies),
            'false_negatives': 0,
            'total_detected': len(detected_synergies),
            'total_ground_truth': 0,
            'matches': []
        }
    
    if not detected_synergies:
        return {
            'precision': 0.0,
            'recall': 0.0,
            'f1_score': 0.0,
            'true_positives': 0,
            'false_positives': 0,
            'false_negatives': len(ground_truth_synergies),
            'total_detected': 0,
            'total_ground_truth': len(ground_truth_synergies),
            'matches': []
        }
    
    # Match synergies by trigger/action entity pair
    matches = []
    matched_gt_indices = set()
    matched_detected_indices = set()
    
    for i, detected in enumerate(detected_synergies):
        trigger = _extract_trigger_entity(detected)
        action = _extract_action_entity(detected)
        
        if not trigger or not action:
            continue
        
        best_match = None
        best_score = 0.0
        best_gt_idx = None
        
        for j, ground_truth in enumerate(ground_truth_synergies):
            if j in matched_gt_indices:
                continue
            
            gt_trigger = _extract_trigger_entity(ground_truth)
            gt_action = _extract_action_entity(ground_truth)
            
            if not gt_trigger or not gt_action:
                continue
            
            # Check if trigger/action pairs match
            if trigger == gt_trigger and action == gt_action:
                # Perfect match
                score = 1.0
            elif (trigger == gt_trigger or action == gt_action):
                # Partial match
                score = 0.5
            else:
                continue
            
            if score > best_score and score >= match_threshold:
                best_score = score
                best_match = ground_truth
                best_gt_idx = j
        
        if best_match:
            matches.append({
                'detected': detected,
                'ground_truth': best_match,
                'similarity_score': best_score
            })
            matched_gt_indices.add(best_gt_idx)
            matched_detected_indices.add(i)
    
    # Calculate metrics
    true_positives = len(matches)
    false_positives = len(detected_synergies) - true_positives
    false_negatives = len(ground_truth_synergies) - true_positives
    
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'true_positives': true_positives,
        'false_positives': false_positives,
        'false_negatives': false_negatives,
        'total_detected': len(detected_synergies),
        'total_ground_truth': len(ground_truth_synergies),
        'matches': matches,
        'match_threshold': match_threshold
    }


def _extract_trigger_entity(synergy: dict[str, Any]) -> str | None:
    """Extract trigger entity ID from synergy dictionary"""
    # Try various field names
    for field in ['trigger_entity', 'trigger_entity_id', 'device1', 'source_entity']:
        value = synergy.get(field)
        if value:
            return str(value)
    
    # Try metadata
    metadata = synergy.get('opportunity_metadata', {})
    return metadata.get('trigger_entity_id') or metadata.get('trigger_entity')


def _extract_action_entity(synergy: dict[str, Any]) -> str | None:
    """Extract action entity ID from synergy dictionary"""
    # Try various field names
    for field in ['action_entity', 'action_entity_id', 'device2', 'target_entity']:
        value = synergy.get(field)
        if value:
            return str(value)
    
    # Try metadata
    metadata = synergy.get('opportunity_metadata', {})
    return metadata.get('action_entity_id') or metadata.get('action_entity')


def format_metrics_report(metrics: dict[str, Any], title: str = "Metrics") -> str:
    """
    Format metrics dictionary as a human-readable report.
    
    Args:
        metrics: Metrics dictionary from calculate_pattern_metrics or calculate_synergy_metrics
        title: Report title
    
    Returns:
        Formatted string report
    """
    lines = [
        f"=== {title} ===",
        f"Precision: {metrics['precision']:.3f} ({metrics['true_positives']}/{metrics['true_positives'] + metrics['false_positives']})",
        f"Recall: {metrics['recall']:.3f} ({metrics['true_positives']}/{metrics['true_positives'] + metrics['false_negatives']})",
        f"F1 Score: {metrics['f1_score']:.3f}",
        f"",
        f"True Positives: {metrics['true_positives']}",
        f"False Positives: {metrics['false_positives']}",
        f"False Negatives: {metrics['false_negatives']}",
        f"",
        f"Total Detected: {metrics['total_detected']}",
        f"Total Ground Truth: {metrics['total_ground_truth']}",
        f"Match Threshold: {metrics.get('match_threshold', 0.8):.2f}",
    ]
    
    return "\n".join(lines)

