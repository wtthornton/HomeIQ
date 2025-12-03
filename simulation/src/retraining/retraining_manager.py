"""
Retraining Manager

Model retraining manager with automatic triggers and orchestration.
"""

import asyncio
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .data_sufficiency import DataSufficiencyChecker

logger = logging.getLogger(__name__)


class RetrainingManager:
    """
    Model retraining manager for simulation framework.
    
    Features:
    - Automatic retraining triggers
    - Data sufficiency checks
    - Retraining orchestration
    - Model version management
    - Retraining history tracking
    """

    def __init__(
        self,
        training_data_directory: Path,
        model_directory: Path,
        data_sufficiency_checker: DataSufficiencyChecker | None = None
    ):
        """
        Initialize retraining manager.
        
        Args:
            training_data_directory: Directory with training data
            model_directory: Directory for trained models
            data_sufficiency_checker: Data sufficiency checker instance
        """
        self.training_data_directory = Path(training_data_directory)
        self.model_directory = Path(model_directory)
        self.model_directory.mkdir(parents=True, exist_ok=True)
        
        self.data_sufficiency_checker = (
            data_sufficiency_checker or DataSufficiencyChecker()
        )
        
        self.retraining_history: list[dict[str, Any]] = []
        
        # Production training script paths (relative to project root)
        self.production_service_path = Path(__file__).parent.parent.parent.parent / "services" / "ai-automation-service"
        self.training_scripts = {
            "gnn_synergy": self.production_service_path / "scripts" / "train_gnn_synergy.py",
            "soft_prompt": self.production_service_path / "scripts" / "train_soft_prompt.py"
        }
        
        logger.info("RetrainingManager initialized")

    def check_retraining_trigger(
        self,
        data_counts: dict[str, int],
        quality_metrics: dict[str, dict[str, Any]] | None = None
    ) -> dict[str, bool]:
        """
        Check if retraining should be triggered for each model.
        
        Args:
            data_counts: Dictionary of model_type -> data_count
            quality_metrics: Dictionary of model_type -> quality_metrics
            
        Returns:
            Dictionary of model_type -> should_retrain
        """
        sufficiency_results = self.data_sufficiency_checker.check_all_models(
            data_counts,
            quality_metrics
        )
        
        triggers = {
            model_type: is_sufficient
            for model_type, (is_sufficient, _) in sufficiency_results.items()
        }
        
        logger.info(f"Retraining triggers: {triggers}")
        return triggers

    async def retrain_model(
        self,
        model_type: str,
        force: bool = False
    ) -> dict[str, Any]:
        """
        Retrain a specific model.
        
        Args:
            model_type: Model type to retrain
            force: Force retraining even if model exists
            
        Returns:
            Retraining result dictionary
        """
        logger.info(f"Retraining model: {model_type}")
        
        start_time = datetime.now(timezone.utc)
        
        # Get training script path
        script_path = self.training_scripts.get(model_type)
        if not script_path or not script_path.exists():
            error_msg = f"Training script not found: {script_path}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "model_type": model_type
            }
        
        try:
            # Run training script
            cmd = [
                sys.executable,
                str(script_path),
                "--force" if force else ""
            ]
            cmd = [c for c in cmd if c]  # Remove empty strings
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.production_service_path)
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = f"Training failed: {stderr.decode()}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "model_type": model_type,
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode()
                }
            
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            result = {
                "success": True,
                "model_type": model_type,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "stdout": stdout.decode()
            }
            
            # Track in history
            self.retraining_history.append(result)
            
            logger.info(f"Model retraining complete: {model_type} ({duration:.2f}s)")
            return result
            
        except Exception as e:
            error_msg = f"Retraining exception: {e}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "model_type": model_type
            }

    async def retrain_all_models(
        self,
        data_counts: dict[str, int],
        quality_metrics: dict[str, dict[str, Any]] | None = None,
        force: bool = False
    ) -> dict[str, dict[str, Any]]:
        """
        Retrain all models that meet sufficiency criteria.
        
        Args:
            data_counts: Dictionary of model_type -> data_count
            quality_metrics: Dictionary of model_type -> quality_metrics
            force: Force retraining for all models
            
        Returns:
            Dictionary of model_type -> retraining_result
        """
        triggers = self.check_retraining_trigger(data_counts, quality_metrics)
        
        results = {}
        
        for model_type, should_retrain in triggers.items():
            if should_retrain or force:
                result = await self.retrain_model(model_type, force=force)
                results[model_type] = result
            else:
                results[model_type] = {
                    "success": False,
                    "skipped": True,
                    "reason": "Insufficient data or quality"
                }
        
        return results

    def get_retraining_history(
        self,
        model_type: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Get retraining history.
        
        Args:
            model_type: Filter by model type (None for all)
            
        Returns:
            List of retraining history entries
        """
        if model_type:
            return [
                entry for entry in self.retraining_history
                if entry.get("model_type") == model_type
            ]
        else:
            return list(self.retraining_history)

