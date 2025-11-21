"""Admin dashboard endpoints."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import (
    create_training_run,
    get_active_training_run,
    get_db,
    get_system_settings,
    list_training_runs,
    update_training_run,
)
from src.database.models import Suggestion, get_db_session

from .ask_ai_router import (
    get_guardrail_checker_instance,
    get_soft_prompt,
)
from .dependencies.auth import require_admin_user
from .health import health_check

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin"],
    dependencies=[Depends(require_admin_user)],
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_training_job_lock = asyncio.Lock()


def _resolve_path(path_str: str) -> Path:
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        return (PROJECT_ROOT / path).resolve()
    return path


def _validate_training_script_path() -> Path:
    """Ensure the configured training script exists, is inside repo, and matches optional hash."""

    script_path = _resolve_path(settings.training_script_path).resolve()

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


class AdminOverviewResponse(BaseModel):
    """Aggregated data for admin dashboard cards."""

    total_suggestions: int = Field(..., alias="totalSuggestions")
    active_automations: int = Field(..., alias="activeAutomations")
    system_status: str = Field(..., alias="systemStatus")
    api_status: str = Field(..., alias="apiStatus")
    soft_prompt_enabled: bool = Field(..., alias="softPromptEnabled")
    soft_prompt_loaded: bool = Field(..., alias="softPromptLoaded")
    soft_prompt_model_id: str | None = Field(None, alias="softPromptModelId")
    guardrail_enabled: bool = Field(..., alias="guardrailEnabled")
    guardrail_loaded: bool = Field(..., alias="guardrailLoaded")
    guardrail_model_name: str | None = Field(None, alias="guardrailModelName")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class AdminConfigResponse(BaseModel):
    """Static configuration metadata for admin panels."""

    data_api_url: str = Field(..., alias="dataApiUrl")
    database_path: str = Field(..., alias="databasePath")
    log_level: str = Field(..., alias="logLevel")
    openai_model: str = Field(..., alias="openaiModel")
    soft_prompt_model_dir: str = Field(..., alias="softPromptModelDir")
    guardrail_model_name: str = Field(..., alias="guardrailModelName")

    model_config = ConfigDict(populate_by_name=True)


class TrainingRunResponse(BaseModel):
    """Serialized representation of a training run entry."""

    id: int
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
    async with get_db_session() as db:
        await update_training_run(db, run_id, updates)


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
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(PROJECT_ROOT),
        )
        stdout, stderr = await process.communicate()

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
            error_output = (stderr or stdout or b"").decode(errors="ignore")
            updates["error_message"] = error_output[-2000:]

        await _update_training_status(run_id, updates)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Training job failed to execute")
        await _update_training_status(
            run_id,
            {
                "status": "failed",
                "finished_at": datetime.utcnow(),
                "error_message": str(exc),
            },
        )


@router.get("/overview", response_model=AdminOverviewResponse)
async def get_admin_overview(db: AsyncSession = Depends(get_db)) -> AdminOverviewResponse:
    """Return aggregated metrics and runtime status for the admin dashboard."""

    try:
        total_result = await db.execute(select(func.count(Suggestion.id)))
        total_suggestions = total_result.scalar_one() or 0

        active_result = await db.execute(
            select(func.count(Suggestion.id)).where(Suggestion.status == "deployed"),
        )
        active_automations = active_result.scalar_one() or 0

        health = await health_check()
        system_status = health.get("status", "unknown")
        api_status = "online"

        settings_record = await get_system_settings(db)

        soft_prompt_adapter = get_soft_prompt()
        guardrail_checker = get_guardrail_checker_instance()

        return AdminOverviewResponse(
            totalSuggestions=total_suggestions,
            activeAutomations=active_automations,
            systemStatus=system_status,
            apiStatus=api_status,
            softPromptEnabled=settings_record.soft_prompt_enabled,
            softPromptLoaded=bool(soft_prompt_adapter and soft_prompt_adapter.is_ready),
            softPromptModelId=getattr(soft_prompt_adapter, "model_id", None),
            guardrailEnabled=settings_record.guardrail_enabled,
            guardrailLoaded=bool(guardrail_checker and guardrail_checker.is_ready),
            guardrailModelName=getattr(guardrail_checker, "model_name", settings_record.guardrail_model_name),
            updatedAt=settings_record.updated_at,
        )

    except Exception as exc:
        logger.error("Failed to build admin overview: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load admin overview",
        ) from exc


@router.get("/config", response_model=AdminConfigResponse)
async def get_admin_config(db: AsyncSession = Depends(get_db)) -> AdminConfigResponse:
    """Return read-only system configuration metadata."""

    try:
        settings_record = await get_system_settings(db)

        return AdminConfigResponse(
            dataApiUrl=settings.data_api_url,
            databasePath=settings.database_path,
            logLevel=settings.log_level,
            openaiModel=settings.openai_model,
            softPromptModelDir=settings_record.soft_prompt_model_dir,
            guardrailModelName=settings_record.guardrail_model_name,
        )
    except Exception as exc:
        logger.error("Failed to load admin config: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load admin configuration",
        ) from exc


@router.get("/training/runs", response_model=list[TrainingRunResponse])
async def list_training_runs_endpoint(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[TrainingRunResponse]:
    """Return recent training runs for display in the admin dashboard."""

    try:
        runs = await list_training_runs(db, limit=limit)
        return [TrainingRunResponse.model_validate(run, from_attributes=True) for run in runs]
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to list training runs: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load training history",
        ) from exc


@router.post(
    "/training/trigger",
    response_model=TrainingRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_training_run(db: AsyncSession = Depends(get_db)) -> TrainingRunResponse:
    """Start a new soft prompt training job if none is currently running."""

    async with _training_job_lock:
        script_path = _validate_training_script_path()
        active = await get_active_training_run(db)
        if active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A training job is already running",
            )

        run_identifier = datetime.utcnow().strftime("run_%Y%m%d_%H%M%S")
        base_output_dir = _resolve_path(settings.soft_prompt_model_dir)
        run_directory = base_output_dir / run_identifier

        run_record = await create_training_run(
            db,
            {
                "status": "queued",
                "started_at": datetime.utcnow(),
                "output_dir": str(run_directory),
                "run_identifier": run_identifier,
                "triggered_by": "admin",
            },
        )

        asyncio.create_task(
            _execute_training_run(
                run_record.id,
                run_identifier,
                base_output_dir,
                run_directory,
                script_path,
            ),
        )

        return TrainingRunResponse.model_validate(run_record, from_attributes=True)

