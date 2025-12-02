"""
Quality Metrics Calculator

Generate quality reports and visualizations for training data validation.
"""

import logging
from typing import Any
from .ground_truth_validator import QualityReport, ValidationMetrics

logger = logging.getLogger(__name__)


class QualityMetricsCalculator:
    """
    Calculate and format quality metrics for training data.
    
    Generates reports in text, JSON, and markdown formats.
    """
    
    def __init__(self):
        """Initialize quality metrics calculator."""
        logger.info("QualityMetricsCalculator initialized")
    
    def generate_text_report(
        self,
        report: QualityReport
    ) -> str:
        """
        Generate text format quality report.
        
        Args:
            report: Quality report from validation
        
        Returns:
            Formatted text report
        """
        lines = []
        lines.append("=" * 60)
        lines.append("Training Data Quality Report")
        lines.append("=" * 60)
        lines.append("")
        
        # Overall metrics
        lines.append("Overall Metrics:")
        lines.append(f"  Homes: {report.total_homes}")
        lines.append(f"  Expected Patterns: {report.total_expected_patterns}")
        lines.append(f"  Detected Patterns: {report.total_detected_patterns}")
        lines.append("")
        
        m = report.overall_metrics
        lines.append(f"  True Positives:  {m.true_positives}")
        lines.append(f"  False Positives: {m.false_positives}")
        lines.append(f"  False Negatives: {m.false_negatives}")
        lines.append("")
        
        # Metrics with pass/fail indicators
        prec_status = "✅" if m.precision >= 0.80 else "❌"
        rec_status = "✅" if m.recall >= 0.60 else "❌"
        f1_status = "✅" if m.f1_score >= 0.65 else "❌"
        
        lines.append(f"  Precision: {m.precision:.1%} {prec_status}")
        lines.append(f"  Recall:    {m.recall:.1%} {rec_status}")
        lines.append(f"  F1 Score:  {m.f1_score:.2f} {f1_status}")
        lines.append("")
        
        # Pattern type breakdown
        if m.pattern_type_metrics:
            lines.append("Pattern Type Breakdown:")
            for ptype, metrics in m.pattern_type_metrics.items():
                prec = metrics.get('precision', 0.0)
                rec = metrics.get('recall', 0.0)
                expected = metrics.get('expected', 0)
                detected = metrics.get('detected', 0)
                matched = metrics.get('matched', 0)
                
                lines.append(f"  {ptype}:")
                lines.append(f"    Expected: {expected}, Detected: {detected}, Matched: {matched}")
                lines.append(f"    Precision: {prec:.1%}, Recall: {rec:.1%}")
            lines.append("")
        
        # Quality gate status
        gate_status = "PASSED ✅" if report.quality_gate_passed else "FAILED ❌"
        lines.append(f"Quality Gate: {gate_status}")
        lines.append("")
        
        # Issues
        if report.issues:
            lines.append("Issues:")
            for issue in report.issues:
                lines.append(f"  - {issue}")
            lines.append("")
        
        # Per-home summary (top/bottom performers)
        if report.per_home_metrics:
            lines.append("Home Performance Summary:")
            
            # Sort by precision
            sorted_homes = sorted(
                report.per_home_metrics,
                key=lambda x: x[1].precision,
                reverse=True
            )
            
            # Top 3 performers
            lines.append("  Top Performers:")
            for home_id, metrics in sorted_homes[:3]:
                lines.append(f"    {home_id}: P={metrics.precision:.1%}, R={metrics.recall:.1%}")
            
            # Bottom 3 performers
            if len(sorted_homes) > 3:
                lines.append("  Bottom Performers:")
                for home_id, metrics in sorted_homes[-3:]:
                    lines.append(f"    {home_id}: P={metrics.precision:.1%}, R={metrics.recall:.1%}")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def generate_json_report(
        self,
        report: QualityReport
    ) -> dict[str, Any]:
        """
        Generate JSON format quality report.
        
        Args:
            report: Quality report from validation
        
        Returns:
            JSON-serializable dictionary
        """
        return {
            'summary': {
                'total_homes': report.total_homes,
                'total_expected_patterns': report.total_expected_patterns,
                'total_detected_patterns': report.total_detected_patterns,
                'quality_gate_passed': report.quality_gate_passed
            },
            'overall_metrics': {
                'true_positives': report.overall_metrics.true_positives,
                'false_positives': report.overall_metrics.false_positives,
                'false_negatives': report.overall_metrics.false_negatives,
                'precision': report.overall_metrics.precision,
                'recall': report.overall_metrics.recall,
                'f1_score': report.overall_metrics.f1_score
            },
            'pattern_type_metrics': report.overall_metrics.pattern_type_metrics,
            'issues': report.issues,
            'per_home_metrics': [
                {
                    'home_id': home_id,
                    'metrics': {
                        'true_positives': m.true_positives,
                        'false_positives': m.false_positives,
                        'false_negatives': m.false_negatives,
                        'precision': m.precision,
                        'recall': m.recall,
                        'f1_score': m.f1_score
                    }
                }
                for home_id, m in report.per_home_metrics
            ]
        }
    
    def generate_markdown_report(
        self,
        report: QualityReport
    ) -> str:
        """
        Generate markdown format quality report.
        
        Args:
            report: Quality report from validation
        
        Returns:
            Markdown formatted report
        """
        lines = []
        lines.append("# Training Data Quality Report")
        lines.append("")
        
        # Overall metrics
        lines.append("## Overall Metrics")
        lines.append("")
        lines.append(f"- **Homes:** {report.total_homes}")
        lines.append(f"- **Expected Patterns:** {report.total_expected_patterns}")
        lines.append(f"- **Detected Patterns:** {report.total_detected_patterns}")
        lines.append("")
        
        m = report.overall_metrics
        prec_status = "✅" if m.precision >= 0.80 else "❌"
        rec_status = "✅" if m.recall >= 0.60 else "❌"
        f1_status = "✅" if m.f1_score >= 0.65 else "❌"
        
        lines.append(f"- **Precision:** {m.precision:.1%} {prec_status}")
        lines.append(f"- **Recall:** {m.recall:.1%} {rec_status}")
        lines.append(f"- **F1 Score:** {m.f1_score:.2f} {f1_status}")
        lines.append("")
        
        # Pattern type breakdown table
        if m.pattern_type_metrics:
            lines.append("## Pattern Type Breakdown")
            lines.append("")
            lines.append("| Pattern Type | Expected | Detected | Matched | Precision | Recall |")
            lines.append("|--------------|----------|----------|---------|-----------|--------|")
            
            for ptype, metrics in m.pattern_type_metrics.items():
                expected = metrics.get('expected', 0)
                detected = metrics.get('detected', 0)
                matched = metrics.get('matched', 0)
                prec = metrics.get('precision', 0.0)
                rec = metrics.get('recall', 0.0)
                
                lines.append(
                    f"| {ptype} | {expected} | {detected} | {matched} | "
                    f"{prec:.1%} | {rec:.1%} |"
                )
            lines.append("")
        
        # Quality gate
        gate_status = "**PASSED** ✅" if report.quality_gate_passed else "**FAILED** ❌"
        lines.append(f"## Quality Gate: {gate_status}")
        lines.append("")
        
        if report.issues:
            lines.append("### Issues")
            lines.append("")
            for issue in report.issues:
                lines.append(f"- {issue}")
            lines.append("")
        
        return "\n".join(lines)
    
    def calculate_summary_statistics(
        self,
        report: QualityReport
    ) -> dict[str, Any]:
        """
        Calculate summary statistics across all homes.
        
        Args:
            report: Quality report from validation
        
        Returns:
            Summary statistics dictionary
        """
        if not report.per_home_metrics:
            return {}
        
        precisions = [m.precision for _, m in report.per_home_metrics]
        recalls = [m.recall for _, m in report.per_home_metrics]
        f1_scores = [m.f1_score for _, m in report.per_home_metrics]
        
        return {
            'precision': {
                'mean': sum(precisions) / len(precisions),
                'min': min(precisions),
                'max': max(precisions),
                'median': sorted(precisions)[len(precisions) // 2]
            },
            'recall': {
                'mean': sum(recalls) / len(recalls),
                'min': min(recalls),
                'max': max(recalls),
                'median': sorted(recalls)[len(recalls) // 2]
            },
            'f1_score': {
                'mean': sum(f1_scores) / len(f1_scores),
                'min': min(f1_scores),
                'max': max(f1_scores),
                'median': sorted(f1_scores)[len(f1_scores) // 2]
            },
            'homes_below_precision_threshold': sum(1 for p in precisions if p < 0.80),
            'homes_below_recall_threshold': sum(1 for r in recalls if r < 0.60)
        }

