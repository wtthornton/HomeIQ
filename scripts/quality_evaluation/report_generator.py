"""
Report Generator for Quality Evaluation

Generates quality evaluation reports in multiple formats.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates quality evaluation reports."""
    
    def generate_json_report(
        self,
        results: Dict[str, Any],
        output_path: Path
    ) -> None:
        """
        Generate JSON report.
        
        Args:
            results: Evaluation results dictionary
            output_path: Output file path
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"JSON report generated: {output_path}")
        except Exception as e:
            logger.error(f"Failed to generate JSON report: {e}", exc_info=True)
            raise
    
    def generate_markdown_report(
        self,
        results: Dict[str, Any],
        output_path: Path
    ) -> None:
        """
        Generate Markdown report.
        
        Args:
            results: Evaluation results dictionary
            output_path: Output file path
        """
        try:
            lines = []
            lines.append("# Pattern & Synergy Quality Evaluation Report\n")
            lines.append(f"**Evaluation Date:** {results.get('evaluation_date', 'Unknown')}\n")
            lines.append(f"**Time Window:** {results.get('time_window_days', 0)} days\n")
            lines.append("\n")
            
            # Summary
            summary = results.get('summary', {})
            lines.append("## Summary\n")
            lines.append(f"- **Total Patterns:** {summary.get('total_patterns', 0)}\n")
            lines.append(f"- **Total Synergies:** {summary.get('total_synergies', 0)}\n")
            lines.append(f"- **Overall Quality Score:** {summary.get('overall_quality_score', 0.0):.2%}\n")
            lines.append(f"- **Pattern Quality Score:** {summary.get('pattern_quality_score', 0.0):.2%}\n")
            lines.append(f"- **Synergy Quality Score:** {summary.get('synergy_quality_score', 0.0):.2%}\n")
            lines.append("\n")
            
            # Pattern Validation
            if 'pattern_validation' in results:
                pattern_val = results['pattern_validation']
                if isinstance(pattern_val, dict) and pattern_val.get('status') != 'skipped':
                    lines.append("## Pattern Validation\n")
                    lines.append(f"- **Precision:** {pattern_val.get('precision', 0.0):.2%}\n")
                    lines.append(f"- **Recall:** {pattern_val.get('recall', 0.0):.2%}\n")
                    lines.append(f"- **F1 Score:** {pattern_val.get('f1_score', 0.0):.2%}\n")
                    lines.append(f"- **False Positives:** {len(pattern_val.get('false_positives', []))}\n")
                    lines.append("\n")
            
            # Synergy Validation
            if 'synergy_validation' in results:
                synergy_val = results['synergy_validation']
                if isinstance(synergy_val, dict) and synergy_val.get('status') != 'skipped':
                    lines.append("## Synergy Validation\n")
                    lines.append(f"- **Precision:** {synergy_val.get('precision', 0.0):.2%}\n")
                    lines.append(f"- **Recall:** {synergy_val.get('recall', 0.0):.2%}\n")
                    lines.append(f"- **F1 Score:** {synergy_val.get('f1_score', 0.0):.2%}\n")
                    lines.append(f"- **False Positives:** {len(synergy_val.get('false_positives', []))}\n")
                    lines.append("\n")
            
            # Data Quality
            if 'data_quality' in results:
                lines.append("## Data Quality\n")
                pattern_quality = results['data_quality'].get('patterns', {})
                synergy_quality = results['data_quality'].get('synergies', {})
                lines.append(f"- **Pattern Quality Score:** {pattern_quality.get('quality_score', 0.0):.2%}\n")
                lines.append(f"- **Synergy Quality Score:** {synergy_quality.get('quality_score', 0.0):.2%}\n")
                lines.append("\n")
            
            # Recommendations
            if 'recommendations' in results:
                lines.append("## Recommendations\n")
                for rec in results['recommendations']:
                    lines.append(f"- {rec}\n")
                lines.append("\n")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(''.join(lines))
            logger.info(f"Markdown report generated: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to generate Markdown report: {e}", exc_info=True)
            raise
    
    def generate_html_report(
        self,
        results: Dict[str, Any],
        output_path: Path
    ) -> None:
        """
        Generate HTML report.
        
        Args:
            results: Evaluation results dictionary
            output_path: Output file path
        """
        try:
            # Simple HTML report (can be enhanced with charts later)
            html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Pattern & Synergy Quality Evaluation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; margin-top: 30px; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .metric {{ margin: 10px 0; }}
        .score {{ font-size: 24px; font-weight: bold; color: #0066cc; }}
    </style>
</head>
<body>
    <h1>Pattern & Synergy Quality Evaluation Report</h1>
    <p><strong>Evaluation Date:</strong> {results.get('evaluation_date', 'Unknown')}</p>
    <p><strong>Time Window:</strong> {results.get('time_window_days', 0)} days</p>
    
    <div class="summary">
        <h2>Summary</h2>
        <div class="metric">Total Patterns: {results.get('summary', {}).get('total_patterns', 0)}</div>
        <div class="metric">Total Synergies: {results.get('summary', {}).get('total_synergies', 0)}</div>
        <div class="metric">Overall Quality Score: <span class="score">{results.get('summary', {}).get('overall_quality_score', 0.0):.2%}</span></div>
    </div>
    
    <h2>Recommendations</h2>
    <ul>
"""
            for rec in results.get('recommendations', []):
                html += f"        <li>{rec}</li>\n"
            
            html += """    </ul>
</body>
</html>"""
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            logger.info(f"HTML report generated: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}", exc_info=True)
            raise
