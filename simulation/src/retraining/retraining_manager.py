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

try:
    from .adapters import GNNDataAdapter, SoftPromptDataAdapter
except ImportError:
    # Fallback if adapters not available
    GNNDataAdapter = None
    SoftPromptDataAdapter = None

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
        
        # Models that support --force flag
        self.models_supporting_force = {"gnn_synergy"}
        
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
        
        # Prepare training data using adapters if JSON data exists
        if model_type == "gnn_synergy":
            json_path = self.training_data_directory / "gnn_synergy_data.json"
            if json_path.exists():
                if GNNDataAdapter is None:
                    logger.error("GNNDataAdapter not available - adapters module not found")
                    return {
                        "success": False,
                        "error": "GNNDataAdapter not available",
                        "model_type": model_type
                    }
                logger.info(f"Using simulation data adapter for {model_type}")
                try:
                    adapter = GNNDataAdapter(self.model_directory / "training.db")
                    entities, db_path = adapter.prepare_training_environment(json_path)
                    
                    # Create entities JSON for training script
                    entities_json_path = self.model_directory / "entities.json"
                    adapter.create_entities_json(entities, entities_json_path)
                    
                    # Set environment variable for training script to use JSON
                    import os
                    os.environ["SIMULATION_ENTITIES_JSON"] = str(entities_json_path)
                    os.environ["SIMULATION_SYNERGY_DB"] = str(db_path)
                    logger.info(f"Prepared training environment: {len(entities)} entities, DB: {db_path}")
                except Exception as e:
                    logger.error(f"Failed to prepare training environment: {e}", exc_info=True)
                    return {
                        "success": False,
                        "error": f"Adapter failed: {e}",
                        "model_type": model_type
                    }
        
        elif model_type == "soft_prompt":
            json_path = self.training_data_directory / "soft_prompt_data.json"
            if json_path.exists():
                logger.info(f"Using simulation data adapter for {model_type}")
                try:
                    # Use production database path - default to data/ai_automation.db
                    db_path = self.production_service_path / "data" / "ai_automation.db"
                    db_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    adapter = SoftPromptDataAdapter(db_path)
                    adapter.prepare_training_database(json_path)
                    logger.info(f"Prepared training database: {db_path}")
                except Exception as e:
                    logger.error(f"Failed to prepare training database: {e}", exc_info=True)
                    return {
                        "success": False,
                        "error": f"Adapter failed: {e}",
                        "model_type": model_type
                    }
        
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
            # Build command - use -u flag for unbuffered output
            cmd = [sys.executable, "-u", str(script_path)]
            
            # Add --force flag only if requested and model supports it
            if force and model_type in self.models_supporting_force:
                cmd.append("--force")
            
            # Add --db-path for soft_prompt if using simulation data
            if model_type == "soft_prompt":
                db_path = self.production_service_path / "data" / "ai_automation.db"
                if db_path.exists():
                    cmd.extend(["--db-path", str(db_path)])
            
            logger.info(f"Running training command: {' '.join(cmd)}")
            logger.info("  [Streaming training progress...]")
            
            # Prepare environment variables for simulation mode
            import os
            env = os.environ.copy()
            if model_type == "gnn_synergy":
                entities_json = self.model_directory / "entities.json"
                synergy_db = self.model_directory / "training.db"
                if entities_json.exists():
                    env["SIMULATION_ENTITIES_JSON"] = str(entities_json)
                if synergy_db.exists():
                    env["SIMULATION_SYNERGY_DB"] = str(synergy_db)
            
            # Set unbuffered output for real-time progress
            import os
            env['PYTHONUNBUFFERED'] = '1'
            
            # Create process with real-time output
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # Merge stderr to stdout
                cwd=str(self.production_service_path),
                env=env,
                bufsize=0  # Unbuffered
            )
            
            # Read output line by line for progress feedback
            stdout_lines = []
            last_progress_time = datetime.now(timezone.utc)
            
            async def read_output(stream, lines_list):
                """Read stream line by line and show ALL progress output."""
                nonlocal last_progress_time
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    try:
                        decoded = line.decode('utf-8', errors='replace').strip()
                        if decoded:
                            lines_list.append(decoded)
                            
                            # Filter out only truly problematic lines
                            if ("UnicodeEncodeError" not in decoded and 
                                "Logging error" not in decoded):
                                
                                # Clean up emoji for Windows compatibility
                                clean_line = ''.join(c for c in decoded if ord(c) < 128)
                                
                                # Show all meaningful lines (not just keywords)
                                if clean_line and len(clean_line.strip()) > 3:
                                    # Show with timestamp for clarity
                                    logger.info(f"  {clean_line[:100]}")
                                    last_progress_time = datetime.now(timezone.utc)
                    except Exception:
                        pass  # Skip problematic lines
            
            # Read stdout and show progress
            logger.info("  [Training output stream starting...]")
            await read_output(process.stdout, stdout_lines)
            
            # Wait for process to complete
            await process.wait()
            
            stdout = "\n".join(stdout_lines).encode()
            stderr = b""  # Already merged to stdout
            
            if process.returncode != 0:
                # Extract meaningful error from output
                error_lines = stdout_lines[-10:]  # Last 10 lines
                error_msg = "\n".join(error_lines)
                if not error_msg or len(error_msg) < 20:
                    error_msg = f"Training failed with exit code {process.returncode}"
                else:
                    # Find first actual error line
                    for line in reversed(error_lines):
                        if "Error" in line or "Failed" in line or "Exception" in line:
                            error_msg = line
                            break
                
                logger.error(f"Training failed (exit code {process.returncode})")
                return {
                    "success": False,
                    "error": error_msg,
                    "model_type": model_type,
                    "stdout": "\n".join(stdout_lines),
                    "stderr": ""
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

