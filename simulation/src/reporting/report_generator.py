"""
Report Generator

Generate comprehensive reports in JSON, CSV, and HTML formats.
"""

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Report generator for simulation framework.
    
    Generates reports in:
    - JSON format (detailed)
    - CSV format (tabular)
    - HTML format (visual)
    """

    def __init__(self, output_directory: Path):
        """
        Initialize report generator.
        
        Args:
            output_directory: Output directory for reports
        """
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"ReportGenerator initialized: output_directory={output_directory}")

    def generate_json_report(
        self,
        summary: dict[str, Any],
        filename: str | None = None
    ) -> Path:
        """
        Generate JSON report.
        
        Args:
            summary: Summary dictionary
            filename: Optional filename (default: timestamp-based)
            
        Returns:
            Path to generated report
        """
        if filename is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"simulation_report_{timestamp}.json"
        
        filepath = self.output_directory / filename
        
        with open(filepath, "w") as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"JSON report generated: {filepath}")
        return filepath

    def generate_csv_report(
        self,
        summary: dict[str, Any],
        filename: str | None = None
    ) -> Path:
        """
        Generate CSV report.
        
        Args:
            summary: Summary dictionary
            filename: Optional filename (default: timestamp-based)
            
        Returns:
            Path to generated report
        """
        if filename is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"simulation_report_{timestamp}.csv"
        
        filepath = self.output_directory / filename
        
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(["Metric", "Value"])
            
            # Write 3 AM workflow stats
            writer.writerow(["3AM Workflows - Total", summary["3am_workflows"]["total"]])
            writer.writerow(["3AM Workflows - Successful", summary["3am_workflows"]["successful"]])
            writer.writerow(["3AM Workflows - Failed", summary["3am_workflows"]["failed"]])
            writer.writerow(["3AM Workflows - Success Rate", f"{summary['3am_workflows']['success_rate']:.2%}"])
            writer.writerow(["3AM Workflows - Avg Duration (s)", f"{summary['3am_workflows']['avg_duration_seconds']:.2f}"])
            
            # Write Ask AI query stats
            writer.writerow(["Ask AI Queries - Total", summary["ask_ai_queries"]["total"]])
            writer.writerow(["Ask AI Queries - Successful", summary["ask_ai_queries"]["successful"]])
            writer.writerow(["Ask AI Queries - Failed", summary["ask_ai_queries"]["failed"]])
            writer.writerow(["Ask AI Queries - Success Rate", f"{summary['ask_ai_queries']['success_rate']:.2%}"])
            writer.writerow(["Ask AI Queries - Avg Duration (s)", f"{summary['ask_ai_queries']['avg_duration_seconds']:.2f}"])
            
            # Write validation stats
            for validation_type, stats in summary["validation"].items():
                writer.writerow([f"Validation {validation_type} - Total", stats["total"]])
                writer.writerow([f"Validation {validation_type} - Valid", stats["valid"]])
                writer.writerow([f"Validation {validation_type} - Invalid", stats["invalid"]])
                writer.writerow([f"Validation {validation_type} - Validity Rate", f"{stats['validity_rate']:.2%}"])
        
        logger.info(f"CSV report generated: {filepath}")
        return filepath

    def generate_html_report(
        self,
        summary: dict[str, Any],
        filename: str | None = None
    ) -> Path:
        """
        Generate HTML report.
        
        Args:
            summary: Summary dictionary
            filename: Optional filename (default: timestamp-based)
            
        Returns:
            Path to generated report
        """
        if filename is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"simulation_report_{timestamp}.html"
        
        filepath = self.output_directory / filename
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Simulation Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        .stat-box {{
            display: inline-block;
            margin: 10px;
            padding: 15px;
            background-color: #f9f9f9;
            border-left: 4px solid #4CAF50;
            border-radius: 4px;
            min-width: 200px;
        }}
        .stat-label {{
            font-weight: bold;
            color: #666;
            font-size: 14px;
        }}
        .stat-value {{
            font-size: 24px;
            color: #333;
            margin-top: 5px;
        }}
        .success {{
            color: #4CAF50;
        }}
        .error {{
            color: #f44336;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Simulation Report</h1>
        <p>Generated: {summary['timestamp']}</p>
        
        <h2>3 AM Workflows</h2>
        <div class="stat-box">
            <div class="stat-label">Total</div>
            <div class="stat-value">{summary['3am_workflows']['total']}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Successful</div>
            <div class="stat-value success">{summary['3am_workflows']['successful']}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Failed</div>
            <div class="stat-value error">{summary['3am_workflows']['failed']}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Success Rate</div>
            <div class="stat-value">{summary['3am_workflows']['success_rate']:.2%}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Avg Duration</div>
            <div class="stat-value">{summary['3am_workflows']['avg_duration_seconds']:.2f}s</div>
        </div>
        
        <h2>Ask AI Queries</h2>
        <div class="stat-box">
            <div class="stat-label">Total</div>
            <div class="stat-value">{summary['ask_ai_queries']['total']}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Successful</div>
            <div class="stat-value success">{summary['ask_ai_queries']['successful']}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Failed</div>
            <div class="stat-value error">{summary['ask_ai_queries']['failed']}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Success Rate</div>
            <div class="stat-value">{summary['ask_ai_queries']['success_rate']:.2%}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Avg Duration</div>
            <div class="stat-value">{summary['ask_ai_queries']['avg_duration_seconds']:.2f}s</div>
        </div>
        
        <h2>Validation Results</h2>
        <table>
            <tr>
                <th>Validation Type</th>
                <th>Total</th>
                <th>Valid</th>
                <th>Invalid</th>
                <th>Validity Rate</th>
            </tr>
"""
        
        for validation_type, stats in summary["validation"].items():
            html_content += f"""
            <tr>
                <td>{validation_type}</td>
                <td>{stats['total']}</td>
                <td class="success">{stats['valid']}</td>
                <td class="error">{stats['invalid']}</td>
                <td>{stats['validity_rate']:.2%}</td>
            </tr>
"""
        
        html_content += """
        </table>
    </div>
</body>
</html>
"""
        
        with open(filepath, "w") as f:
            f.write(html_content)
        
        logger.info(f"HTML report generated: {filepath}")
        return filepath

