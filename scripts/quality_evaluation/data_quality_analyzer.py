"""
Data Quality Analyzer for Quality Evaluation

Analyzes data quality metrics for patterns and synergies.
"""

import json
import logging
import statistics
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class DataQualityAnalyzer:
    """Analyzes data quality metrics for patterns and synergies."""
    
    def analyze_pattern_quality(
        self,
        patterns: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze pattern data quality.
        
        Args:
            patterns: List of pattern dictionaries
            
        Returns:
            Quality metrics dictionary
        """
        if not patterns:
            return {
                'total_patterns': 0,
                'quality_score': 0.0
            }
        
        total = len(patterns)
        
        # Completeness analysis
        completeness = {
            'pattern_type': self._check_field_completeness(patterns, 'pattern_type'),
            'device_id': self._check_field_completeness(patterns, 'device_id'),
            'confidence': self._check_field_completeness(patterns, 'confidence'),
            'occurrences': self._check_field_completeness(patterns, 'occurrences'),
            'metadata': self._check_field_completeness(patterns, 'pattern_metadata', allow_empty=True)
        }
        
        # Confidence distribution
        confidences = [p.get('confidence', 0.0) for p in patterns if 'confidence' in p and p['confidence'] is not None]
        confidence_distribution = {}
        if confidences:
            confidence_distribution = {
                'mean': statistics.mean(confidences),
                'median': statistics.median(confidences),
                'std': statistics.stdev(confidences) if len(confidences) > 1 else 0.0,
                'min': min(confidences),
                'max': max(confidences),
                'count': len(confidences)
            }
        
        # Occurrence validation
        occurrences = [p.get('occurrences', 0) for p in patterns]
        occurrence_validation = {
            'zero_occurrences': sum(1 for o in occurrences if o == 0),
            'negative_occurrences': sum(1 for o in occurrences if o < 0),
            'unusual_high': sum(1 for o in occurrences if o > 10000)  # Arbitrary threshold
        }
        
        # Metadata quality
        metadata_quality = {
            'empty_metadata': sum(1 for p in patterns if not p.get('pattern_metadata')),
            'missing_fields': {}
        }
        
        # Calculate overall quality score
        completeness_score = sum(completeness.values()) / len(completeness) if completeness else 0.0
        confidence_score = 1.0 if confidence_distribution else 0.0
        occurrence_score = 1.0 - (occurrence_validation['negative_occurrences'] / total) if total > 0 else 1.0
        
        quality_score = (completeness_score * 0.4 + confidence_score * 0.3 + occurrence_score * 0.3)
        
        return {
            'total_patterns': total,
            'completeness': completeness,
            'confidence_distribution': confidence_distribution,
            'occurrence_validation': occurrence_validation,
            'metadata_quality': metadata_quality,
            'quality_score': quality_score
        }
    
    def analyze_synergy_quality(
        self,
        synergies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze synergy data quality.
        
        Args:
            synergies: List of synergy dictionaries
            
        Returns:
            Quality metrics dictionary
        """
        if not synergies:
            return {
                'total_synergies': 0,
                'quality_score': 0.0
            }
        
        total = len(synergies)
        
        # Completeness analysis
        completeness = {
            'synergy_id': self._check_field_completeness(synergies, 'synergy_id'),
            'synergy_type': self._check_field_completeness(synergies, 'synergy_type'),
            'device_ids': self._check_field_completeness(synergies, 'device_ids'),
            'confidence': self._check_field_completeness(synergies, 'confidence'),
            'impact_score': self._check_field_completeness(synergies, 'impact_score'),
            'pattern_support_score': self._check_field_completeness(synergies, 'pattern_support_score', allow_none=True)
        }
        
        # Confidence distribution
        confidences = [s.get('confidence', 0.0) for s in synergies if 'confidence' in s and s['confidence'] is not None]
        confidence_distribution = {}
        if confidences:
            confidence_distribution = {
                'mean': statistics.mean(confidences),
                'median': statistics.median(confidences),
                'std': statistics.stdev(confidences) if len(confidences) > 1 else 0.0,
                'min': min(confidences),
                'max': max(confidences),
                'count': len(confidences)
            }
        
        # Impact score distribution
        impact_scores = [s.get('impact_score', 0.0) for s in synergies if 'impact_score' in s and s['impact_score'] is not None]
        impact_distribution = {}
        if impact_scores:
            impact_distribution = {
                'mean': statistics.mean(impact_scores),
                'median': statistics.median(impact_scores),
                'std': statistics.stdev(impact_scores) if len(impact_scores) > 1 else 0.0,
                'min': min(impact_scores),
                'max': max(impact_scores)
            }
        
        # Pattern support validation
        pattern_support_validation = {
            'missing_support_score': sum(1 for s in synergies if 'pattern_support_score' not in s or s.get('pattern_support_score') is None),
            'high_support_not_validated': sum(1 for s in synergies 
                                             if s.get('pattern_support_score', 0.0) > 0.7 
                                             and not s.get('validated_by_patterns', False))
        }
        
        # Calculate overall quality score
        completeness_score = sum(completeness.values()) / len(completeness) if completeness else 0.0
        confidence_score = 1.0 if confidence_distribution else 0.0
        support_score = 1.0 - (pattern_support_validation['missing_support_score'] / total) if total > 0 else 1.0
        
        quality_score = (completeness_score * 0.4 + confidence_score * 0.3 + support_score * 0.3)
        
        return {
            'total_synergies': total,
            'completeness': completeness,
            'confidence_distribution': confidence_distribution,
            'impact_distribution': impact_distribution,
            'pattern_support_validation': pattern_support_validation,
            'quality_score': quality_score
        }
    
    def _check_field_completeness(
        self,
        items: List[Dict[str, Any]],
        field: str,
        allow_empty: bool = False,
        allow_none: bool = False
    ) -> float:
        """Check field completeness percentage."""
        if not items:
            return 0.0
        
        complete = 0
        for item in items:
            if field in item:
                value = item[field]
                if value is None and allow_none:
                    complete += 1
                elif value is not None:
                    if allow_empty or (isinstance(value, (list, dict)) and value) or (not isinstance(value, (list, dict)) and value):
                        complete += 1
        
        return complete / len(items) if items else 0.0
