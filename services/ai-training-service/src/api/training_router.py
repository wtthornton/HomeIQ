"""
Training router for AI Training Service

Epic 39, Story 39.1: Training Service Foundation
Extracted from ai-automation-service admin_router.py
"""

import asyncio
import hashlib
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..crud import (
    create_training_run,
    delete_old_training_runs,
    delete_training_run,
    get_active_training_run,
    list_training_runs,
    update_training_run,
)
from ..database import get_db

logger = logging.getLogger("ai-training-service")

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # Go up to project root
_training_job_lock = asyncio.Lock()


def _resolve_path(path_str: str) -> Path:
    """Resolve path relative to project root or absolute."""
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        return (PROJECT_ROOT / path).resolve()
    return path


def _validate_training_script_path() -> Path:
    """Ensure the configured training script exists, is inside repo, and matches optional hash."""
    script_path = _resolve_path(settings.training_script_path)

    if not script_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Training script not found at {script_path}",
        )

    try:
        script_path.relative_to(PROJECT_ROOT)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Training script must reside within the repository",
        )

    expected_hash = getattr(settings, "training_script_sha256", None)
    if expected_hash:
        actual_hash = hashlib.sha256(script_path.read_bytes()).hexdigest()
        if actual_hash.lower() != expected_hash.lower():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Training script hash mismatch. Refusing to execute.",
            )

    return script_path


class TrainingRunResponse(BaseModel):
    """Serialized representation of a training run entry."""

    id: int
    training_type: str = Field(default='soft_prompt', alias="trainingType")
    status: str
    started_at: datetime = Field(..., alias="startedAt")
    finished_at: datetime | None = Field(None, alias="finishedAt")
    dataset_size: int | None = Field(None, alias="datasetSize")
    base_model: str | None = Field(None, alias="baseModel")
    output_dir: str | None = Field(None, alias="outputDir")
    run_identifier: str | None = Field(None, alias="runIdentifier")
    final_loss: float | None = Field(None, alias="finalLoss")
    error_message: str | None = Field(None, alias="errorMessage")
    metadata_path: str | None = Field(None, alias="metadataPath")
    triggered_by: str = Field(..., alias="triggeredBy")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


async def _update_training_status(run_id: int, updates: dict) -> None:
    """Update training run status."""
    from ..database import get_db
    async for session in get_db():
        await update_training_run(session, run_id, updates)
        break


async def _execute_training_run(
    run_id: int,
    run_identifier: str,
    base_output_dir: Path,
    run_directory: Path,
    script_path: Path,
) -> None:
    """Launch the soft prompt training subprocess and persist its results."""
    db_path = _resolve_path(settings.database_path)
    base_output_dir.mkdir(parents=True, exist_ok=True)
    run_directory.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        str(script_path),
        "--db-path", str(db_path),
        "--output-dir", str(base_output_dir),
        "--run-directory", str(run_directory),
        "--run-id", run_identifier,
    ]

    await _update_training_status(run_id, {"status": "running"})

    try:
        env = os.environ.copy()
        # Set environment variables for model caching if needed
        # (Add model directory setup if required)
        
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(PROJECT_ROOT),
            env=env,
        )
        stdout, stderr = await process.communicate()
        
        if stdout:
            logger.debug("Training script stdout (first 1000 chars):\n%s", stdout[:1000].decode(errors="ignore"))
        if stderr:
            logger.debug("Training script stderr (first 1000 chars):\n%s", stderr[:1000].decode(errors="ignore"))

        metadata_path = run_directory / "training_run.json"
        metadata = {}
        if metadata_path.exists():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.warning("Unable to parse training metadata at %s", metadata_path)

        success = process.returncode == 0
        updates = {
            "status": "completed" if success else "failed",
            "finished_at": datetime.utcnow(),
            "metadata_path": str(metadata_path) if metadata_path.exists() else None,
            "dataset_size": metadata.get("samples_used"),
            "base_model": metadata.get("base_model"),
            "final_loss": metadata.get("final_loss"),
        }

        if not success:
            stdout_text = stdout.decode(errors="ignore") if stdout else ""
            stderr_text = stderr.decode(errors="ignore") if stderr else ""
            
            if stderr_text:
                error_output = f"STDERR:\n{stderr_text}\n\nSTDOUT:\n{stdout_text}"
            else:
                error_output = stdout_text or "No error output captured"
            
            if process.returncode == -9:
                error_output = (
                    "⚠️ OUT OF MEMORY (OOM) KILL DETECTED\n"
                    "The training process was killed by the system due to insufficient memory.\n"
                    "Return code: -9 (SIGKILL)\n\n"
                    "SOLUTIONS:\n"
                    "1. Increase container memory limit in docker-compose.yml\n"
                    "2. Reduce training parameters\n\n"
                    f"Original error output:\n{error_output}"
                )
                logger.error("Training script was killed (OOM). Return code: %d", process.returncode)
            
            logger.error("Training script failed with return code %d. Full output:\n%s", process.returncode, error_output)
            
            if len(error_output) > 5000:
                updates["error_message"] = error_output[:2500] + "\n\n... [truncated] ...\n\n" + error_output[-2500:]
            else:
                updates["error_message"] = error_output

        await _update_training_status(run_id, updates)
    except Exception as exc:
        logger.exception("Training job failed to execute")
        await _update_training_status(
            run_id,
            {
                "status": "failed",
                "finished_at": datetime.utcnow(),
                "error_message": str(exc),
            },
        )


@router.get("/runs", response_model=list[TrainingRunResponse])
async def list_training_runs_endpoint(
    limit: int = Query(20, ge=1, le=100),
    training_type: str | None = Query(None, description="Filter by training type: soft_prompt, gnn_synergy, or home_type_classifier"),
    db: AsyncSession = Depends(get_db),
) -> list[TrainingRunResponse]:
    """Return recent training runs for display."""
    try:
        runs = await list_training_runs(db, limit=limit, training_type=training_type)
        return [TrainingRunResponse.model_validate(run, from_attributes=True) for run in runs]
    except Exception as exc:
        logger.error("Failed to list training runs: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load training history",
        ) from exc


@router.post(
    "/trigger",
    response_model=TrainingRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_training_run(
    training_type: str = Query('soft_prompt', description="Type of training to trigger: soft_prompt, gnn_synergy, or home_type_classifier"),
    db: AsyncSession = Depends(get_db)
) -> TrainingRunResponse:
    """Start a new training job if none is currently running for the specified type."""
    async with _training_job_lock:
        # Validate training type
        valid_types = ['soft_prompt', 'gnn_synergy', 'home_type_classifier']
        if training_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid training_type. Must be one of: {', '.join(valid_types)}"
            )
        
        # Get script path based on training type
        if training_type == 'soft_prompt':
            script_path = _resolve_path(settings.training_script_path)
            base_output_dir = _resolve_path(settings.soft_prompt_model_dir)
        elif training_type == 'gnn_synergy':
            script_path = _resolve_path(settings.gnn_training_script_path)
            base_output_dir = _resolve_path(Path(settings.gnn_model_path).parent)
        elif training_type == 'home_type_classifier':
            script_path = _resolve_path(settings.home_type_training_script_path)
            base_output_dir = _resolve_path(Path(settings.home_type_model_path).parent)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported training type: {training_type}"
            )
        
        # Validate script exists
        if not script_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Training script not found at {script_path}",
            )
        
        # Check for active training of this type
        active = await get_active_training_run(db, training_type=training_type)
        if active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A {training_type} training job is already running",
            )

        run_identifier = datetime.utcnow().strftime(f"{training_type}_run_%Y%m%d_%H%M%S")
        run_directory = base_output_dir / run_identifier

        run_record = await create_training_run(
            db,
            {
                "training_type": training_type,
                "status": "queued",
                "started_at": datetime.utcnow(),
                "output_dir": str(run_directory),
                "run_identifier": run_identifier,
                "triggered_by": "admin",
            },
        )

        # Execute training based on type
        if training_type == 'soft_prompt':
            asyncio.create_task(
                _execute_training_run(
                    run_record.id,
                    run_identifier,
                    base_output_dir,
                    run_directory,
                    script_path,
                )
            )
        elif training_type == 'gnn_synergy':
            # GNN training uses different execution pattern (async function, not subprocess)
            # For now, log that it needs implementation
            logger.warning(f"GNN training execution not yet fully implemented. Run ID: {run_identifier}")
            await update_training_run(db, run_record.id, {
                "status": "failed",
                "error_message": "GNN training execution not yet implemented in training service"
            })
        elif training_type == 'home_type_classifier':
            # Home type classifier training uses different execution pattern
            logger.warning(f"Home type classifier training execution not yet fully implemented. Run ID: {run_identifier}")
            await update_training_run(db, run_record.id, {
                "status": "failed",
                "error_message": "Home type classifier training execution not yet implemented in training service"
            })

        return TrainingRunResponse.model_validate(run_record, from_attributes=True)


@router.delete("/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_training_run_endpoint(
    run_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a specific training run by ID."""
    try:
        deleted = await delete_training_run(db, run_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Training run {run_id} not found",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to delete training run %d: %s", run_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete training run",
        ) from exc


@router.delete("/runs", status_code=status.HTTP_200_OK)
async def clear_old_training_runs_endpoint(
    training_type: str | None = Query(None),
    older_than_days: int = Query(30, ge=1),
    keep_recent: int = Query(10, ge=1),
    db: AsyncSession = Depends(get_db),
):
    """Delete old training runs, keeping the most recent N runs."""
    try:
        count = await delete_old_training_runs(
            db,
            training_type=training_type,
            older_than_days=older_than_days,
            keep_recent=keep_recent,
        )
        return {"deleted_count": count, "message": f"Deleted {count} old training run(s)"}
    except Exception as exc:
        logger.error("Failed to clear old training runs: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear old training runs",
        ) from exc

