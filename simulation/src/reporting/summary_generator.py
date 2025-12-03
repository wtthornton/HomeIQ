"""
Summary Generator

Generate structured JSON summary files for each pipeline phase.
These summaries are small, focused files for quick review without parsing verbose logs.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SummaryGenerator:
    """
    Generate structured JSON summaries for pipeline phases.
    
    Each phase writes a small, focused summary file that contains:
    - Key metrics
    - Success/failure counts
    - Status information
    - Timestamps
    """
    
    def __init__(self, output_directory: Path):
        """
        Initialize summary generator.
        
        Args:
            output_directory: Base output directory (summaries go in pipeline_summaries/ subdirectory)
        """
        self.output_directory = Path(output_directory)
        self.summaries_dir = self.output_directory / "pipeline_summaries"
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"SummaryGenerator initialized: summaries_dir={self.summaries_dir}")
    
    def generate_data_creation_summary(
        self,
        homes_count: int,
        total_devices: int,
        total_events: int,
        generation_time_seconds: float,
        errors: list[str] | None = None
    ) -> Path:
        """
        Generate data creation phase summary.
        
        Args:
            homes_count: Number of homes created
            total_devices: Total devices across all homes
            total_events: Total events generated
            generation_time_seconds: Time taken to generate data
            errors: List of errors encountered (if any)
            
        Returns:
            Path to generated summary file
        """
        summary = {
            "phase": "data_creation",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "success" if not errors else "partial_success" if homes_count > 0 else "failed",
            "metrics": {
                "homes_created": homes_count,
                "total_devices": total_devices,
                "total_events": total_events,
                "avg_devices_per_home": round(total_devices / homes_count, 2) if homes_count > 0 else 0,
                "avg_events_per_home": round(total_events / homes_count, 2) if homes_count > 0 else 0,
                "generation_time_seconds": round(generation_time_seconds, 2)
            },
            "errors": errors or []
        }
        
        filepath = self.summaries_dir / "data_creation_summary.json"
        with open(filepath, "w") as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Data creation summary generated: {filepath}")
        return filepath
    
    def generate_simulation_summary(
        self,
        homes_count: int,
        queries_count: int,
        workflow_3am_total: int,
        workflow_3am_successful: int,
        workflow_3am_failed: int,
        workflow_3am_avg_duration: float,
        ask_ai_total: int,
        ask_ai_successful: int,
        ask_ai_failed: int,
        ask_ai_avg_duration: float,
        simulation_time_seconds: float,
        errors: list[str] | None = None
    ) -> Path:
        """
        Generate simulation phase summary.
        
        Args:
            homes_count: Number of homes simulated
            queries_count: Number of queries per home
            workflow_3am_total: Total 3AM workflows executed
            workflow_3am_successful: Successful 3AM workflows
            workflow_3am_failed: Failed 3AM workflows
            workflow_3am_avg_duration: Average duration of 3AM workflows
            ask_ai_total: Total Ask AI queries executed
            ask_ai_successful: Successful Ask AI queries
            ask_ai_failed: Failed Ask AI queries
            ask_ai_avg_duration: Average duration of Ask AI queries
            simulation_time_seconds: Total simulation time
            errors: List of errors encountered (if any)
            
        Returns:
            Path to generated summary file
        """
        summary = {
            "phase": "simulation",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "success" if not errors else "partial_success" if workflow_3am_successful > 0 or ask_ai_successful > 0 else "failed",
            "config": {
                "homes_count": homes_count,
                "queries_count": queries_count
            },
            "metrics": {
                "workflow_3am": {
                    "total": workflow_3am_total,
                    "successful": workflow_3am_successful,
                    "failed": workflow_3am_failed,
                    "success_rate": round(workflow_3am_successful / workflow_3am_total, 4) if workflow_3am_total > 0 else 0,
                    "avg_duration_seconds": round(workflow_3am_avg_duration, 2)
                },
                "ask_ai": {
                    "total": ask_ai_total,
                    "successful": ask_ai_successful,
                    "failed": ask_ai_failed,
                    "success_rate": round(ask_ai_successful / ask_ai_total, 4) if ask_ai_total > 0 else 0,
                    "avg_duration_seconds": round(ask_ai_avg_duration, 2)
                },
                "simulation_time_seconds": round(simulation_time_seconds, 2)
            },
            "errors": errors or []
        }
        
        filepath = self.summaries_dir / "simulation_summary.json"
        with open(filepath, "w") as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Simulation summary generated: {filepath}")
        return filepath
    
    def generate_training_summary(
        self,
        model_type: str,
        status: str,
        metrics: dict[str, Any] | None = None,
        model_path: str | None = None,
        training_time_seconds: float | None = None,
        errors: list[str] | None = None
    ) -> Path:
        """
        Generate training phase summary.
        
        Args:
            model_type: Type of model trained (e.g., "gnn_synergy", "soft_prompt")
            status: Training status ("success", "failed", "skipped")
            metrics: Training metrics (loss, accuracy, epochs, etc.)
            model_path: Path to trained model file
            training_time_seconds: Time taken for training
            errors: List of errors encountered (if any)
            
        Returns:
            Path to generated summary file
        """
        summary = {
            "phase": "training",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model_type": model_type,
            "status": status,
            "metrics": metrics or {},
            "model_path": model_path,
            "training_time_seconds": round(training_time_seconds, 2) if training_time_seconds else None,
            "errors": errors or []
        }
        
        filepath = self.summaries_dir / f"training_summary_{model_type}.json"
        with open(filepath, "w") as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Training summary generated: {filepath}")
        return filepath
    
    def generate_pipeline_summary(
        self,
        data_creation_summary_path: Path | None = None,
        simulation_summary_path: Path | None = None,
        training_summaries: list[Path] | None = None
    ) -> Path:
        """
        Generate overall pipeline summary combining all phases.
        
        Args:
            data_creation_summary_path: Path to data creation summary
            simulation_summary_path: Path to simulation summary
            training_summaries: List of paths to training summaries
            
        Returns:
            Path to generated pipeline summary
        """
        pipeline_summary = {
            "pipeline": "complete",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phases": {
                "data_creation": None,
                "simulation": None,
                "training": []
            }
        }
        
        # Load data creation summary if available
        if data_creation_summary_path and data_creation_summary_path.exists():
            with open(data_creation_summary_path) as f:
                pipeline_summary["phases"]["data_creation"] = json.load(f)
        
        # Load simulation summary if available
        if simulation_summary_path and simulation_summary_path.exists():
            with open(simulation_summary_path) as f:
                pipeline_summary["phases"]["simulation"] = json.load(f)
        
        # Load training summaries if available
        if training_summaries:
            for training_path in training_summaries:
                if training_path.exists():
                    with open(training_path) as f:
                        pipeline_summary["phases"]["training"].append(json.load(f))
        
        # Calculate overall status
        phases_status = []
        if pipeline_summary["phases"]["data_creation"]:
            phases_status.append(pipeline_summary["phases"]["data_creation"]["status"])
        if pipeline_summary["phases"]["simulation"]:
            phases_status.append(pipeline_summary["phases"]["simulation"]["status"])
        if pipeline_summary["phases"]["training"]:
            phases_status.extend([t["status"] for t in pipeline_summary["phases"]["training"]])
        
        if all(s == "success" for s in phases_status):
            pipeline_summary["overall_status"] = "success"
        elif any(s == "failed" for s in phases_status):
            pipeline_summary["overall_status"] = "failed"
        else:
            pipeline_summary["overall_status"] = "partial_success"
        
        filepath = self.summaries_dir / "pipeline_summary.json"
        with open(filepath, "w") as f:
            json.dump(pipeline_summary, f, indent=2)
        
        logger.info(f"Pipeline summary generated: {filepath}")
        return filepath

