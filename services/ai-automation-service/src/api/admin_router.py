"""Admin dashboard endpoints."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import (
    create_training_run,
    delete_old_training_runs,
    delete_training_run,
    get_active_training_run,
    get_db,
    get_system_settings,
    list_training_runs,
    update_training_run,
)
from ..database.models import Suggestion, get_db_session
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
    dependencies=[Depends(require_admin_user)]
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
        # Set environment variables for model caching
        # Note: TRANSFORMERS_CACHE is deprecated, use HF_HOME only to avoid FutureWarning
        env = os.environ.copy()
        models_dir = str(Path(settings.gnn_model_path).parent)
        env['HF_HOME'] = models_dir  # Use models directory
        # Remove TRANSFORMERS_CACHE to avoid deprecation warnings (HF_HOME is sufficient)
        if 'TRANSFORMERS_CACHE' in env:
            del env['TRANSFORMERS_CACHE']
        
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,  # Capture stderr separately for better error tracking
            cwd=str(PROJECT_ROOT),
            env=env,
        )
        stdout, stderr = await process.communicate()
        
        # Log output for debugging (even on success, to help diagnose issues)
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
            # Capture full error output for better debugging
            # Combine stdout and stderr, prioritizing stderr for errors
            stdout_text = stdout.decode(errors="ignore") if stdout else ""
            stderr_text = stderr.decode(errors="ignore") if stderr else ""
            
            # Combine outputs, with stderr first (usually contains the actual error)
            if stderr_text:
                error_output = f"STDERR:\n{stderr_text}\n\nSTDOUT:\n{stdout_text}"
            else:
                error_output = stdout_text or "No error output captured"
            
            # Check for OOM kill (return code -9)
            if process.returncode == -9:
                error_output = (
                    "⚠️ OUT OF MEMORY (OOM) KILL DETECTED\n"
                    "The training process was killed by the system due to insufficient memory.\n"
                    "Return code: -9 (SIGKILL)\n\n"
                    "SOLUTIONS:\n"
                    "1. Increase container memory limit in docker-compose.yml (recommended: 2GB)\n"
                    "2. Reduce training parameters:\n"
                    "   - Reduce --max-samples (e.g., 200 instead of 2000)\n"
                    "   - Reduce --batch-size (already at minimum: 1)\n"
                    "   - Reduce --epochs (e.g., 1 instead of 3)\n\n"
                    f"Original error output:\n{error_output}"
                )
                logger.error("Training script was killed (OOM). Return code: %d", process.returncode)
            
            # Log full error for debugging
            logger.error("Training script failed with return code %d. Full output:\n%s", process.returncode, error_output)
            
            # Store full error (limit to 5000 chars for database, but keep the beginning which often has the actual error)
            if len(error_output) > 5000:
                # Keep first 2500 chars (usually has the actual error) and last 2500 chars (has the traceback)
                updates["error_message"] = error_output[:2500] + "\n\n... [truncated middle section] ...\n\n" + error_output[-2500:]
            else:
                updates["error_message"] = error_output

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
            select(func.count(Suggestion.id)).where(Suggestion.status == 'deployed')
        )
        active_automations = active_result.scalar_one() or 0

        health = await health_check()
        system_status = health.get('status', 'unknown')
        api_status = 'online'

        settings_record = await get_system_settings(db)

        soft_prompt_adapter = get_soft_prompt()
        guardrail_checker = get_guardrail_checker_instance()

        response = AdminOverviewResponse(
            totalSuggestions=total_suggestions,
            activeAutomations=active_automations,
            systemStatus=system_status,
            apiStatus=api_status,
            softPromptEnabled=settings_record.soft_prompt_enabled,
            softPromptLoaded=bool(soft_prompt_adapter and soft_prompt_adapter.is_ready),
            softPromptModelId=getattr(soft_prompt_adapter, 'model_id', None),
            guardrailEnabled=settings_record.guardrail_enabled,
            guardrailLoaded=bool(guardrail_checker and guardrail_checker.is_ready),
            guardrailModelName=getattr(guardrail_checker, 'model_name', settings_record.guardrail_model_name),
            updatedAt=settings_record.updated_at,
        )

        return response
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
        # Default to soft_prompt for backward compatibility
        runs = await list_training_runs(db, limit=limit, training_type='soft_prompt')
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
                "training_type": "soft_prompt",
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
            )
        )

        return TrainingRunResponse.model_validate(run_record, from_attributes=True)


def _generate_synthetic_synergies(entities: list[dict]) -> list[dict]:
    """
    Generate synthetic synergies from entities when no real synergies exist.
    
    Uses compatible relationship rules to create realistic device pairs for training.
    This enables cold start GNN training when no synergies have been detected yet.
    
    Args:
        entities: List of device entities
        
    Returns:
        List of synthetic synergy dictionaries
    """
    import uuid
    
    from ..synergy_detection.synergy_detector import COMPATIBLE_RELATIONSHIPS
    
    if not entities:
        return []
    
    # Group entities by domain and area
    entities_by_domain = {}
    entities_by_area = {}
    
    for entity in entities:
        entity_id = entity.get('entity_id', '')
        if not entity_id:
            continue
            
        domain = entity_id.split('.')[0]
        area = entity.get('area_id') or 'unknown'
        device_class = entity.get('device_class') or ''
        
        # Group by domain
        if domain not in entities_by_domain:
            entities_by_domain[domain] = []
        entities_by_domain[domain].append(entity)
        
        # Group by area
        if area not in entities_by_area:
            entities_by_area[area] = []
        entities_by_area[area].append(entity)
    
    synthetic_synergies = []
    
    # Generate synergies based on compatible relationships
    for rel_name, rel_config in COMPATIBLE_RELATIONSHIPS.items():
        trigger_domain = rel_config['trigger_domain']
        action_domain = rel_config['action_domain']
        trigger_device_class = rel_config.get('trigger_device_class')
        benefit_score = rel_config.get('benefit_score', 0.6)
        complexity = rel_config.get('complexity', 'medium')
        
        # Get trigger entities
        trigger_entities = entities_by_domain.get(trigger_domain, [])
        if trigger_device_class:
            trigger_entities = [
                e for e in trigger_entities 
                if e.get('device_class') == trigger_device_class
            ]
        
        # Get action entities
        action_entities = entities_by_domain.get(action_domain, [])
        
        if not trigger_entities or not action_entities:
            continue
        
        # Find pairs in same area (prefer same area, but allow cross-area)
        for trigger_entity in trigger_entities[:10]:  # Limit to avoid too many
            trigger_area = trigger_entity.get('area_id') or 'unknown'
            
            # Prefer same area
            same_area_actions = [
                e for e in action_entities 
                if (e.get('area_id') or 'unknown') == trigger_area
            ]
            
            # Fallback to any area if none in same area
            candidate_actions = same_area_actions if same_area_actions else action_entities
            
            for action_entity in candidate_actions[:3]:  # Limit pairs per trigger
                trigger_id = trigger_entity.get('entity_id')
                action_id = action_entity.get('entity_id')
                
                if trigger_id and action_id and trigger_id != action_id:
                    # Generate synthetic synergy
                    confidence = min(0.8, max(0.6, benefit_score))  # 0.6-0.8 range
                    
                    synthetic_synergy = {
                        'synergy_id': str(uuid.uuid4()),
                        'device_ids': [trigger_id, action_id],
                        'impact_score': float(benefit_score),
                        'confidence': float(confidence),
                        'area': trigger_area if trigger_area != 'unknown' else None,
                        'validated_by_patterns': False,  # Synthetic, not validated
                        'synergy_type': 'device_pair',
                        'complexity': complexity
                    }
                    
                    synthetic_synergies.append(synthetic_synergy)
                    
                    # Limit total synergies to avoid excessive pairs
                    if len(synthetic_synergies) >= 100:
                        break
            
            if len(synthetic_synergies) >= 100:
                break
    
    logger.info(f"Generated {len(synthetic_synergies)} synthetic synergies from {len(entities)} entities")
    return synthetic_synergies


async def _execute_gnn_training_run(run_id: int, run_identifier: str, epochs: int | None = None, force: bool = False) -> None:
    """Execute GNN synergy training in background."""
    
    await _update_training_status(run_id, {"status": "running"})
    
    try:
        from ..clients.data_api_client import DataAPIClient
        from ..synergy_detection.gnn_synergy_detector import GNNSynergyDetector
        
        # Initialize clients
        data_api_client = DataAPIClient(base_url=settings.data_api_url)
        detector = GNNSynergyDetector(
            hidden_dim=settings.gnn_hidden_dim,
            num_layers=settings.gnn_num_layers,
            learning_rate=settings.gnn_learning_rate,
            batch_size=settings.gnn_batch_size,
            epochs=epochs or settings.gnn_epochs,
            early_stopping_patience=settings.gnn_early_stopping_patience,
            model_path=settings.gnn_model_path
        )
        
        # Load entities
        logger.info("Loading entities for GNN training...")
        entities = await data_api_client.fetch_entities(limit=10000)
        logger.info(f"Loaded {len(entities)} entities")
        
        if not entities:
            raise ValueError(f"Insufficient data: 0 entities")
        
        # Load synergies from database
        from ..database.models import get_db_session
        async with get_db_session() as db:
            synergies = await detector._load_synergies_from_database(db)
        logger.info(f"Loaded {len(synergies)} synergies from database")
        
        # Generate synthetic synergies if none exist (cold start scenario)
        if not synergies:
            logger.info("No synergies found in database. Generating synthetic synergies for training...")
            synergies = _generate_synthetic_synergies(entities)
            if synergies:
                logger.info(f"✅ Generated {len(synergies)} synthetic synergies for cold start training")
            else:
                raise ValueError(f"Could not generate synthetic synergies from {len(entities)} entities")
        
        if not synergies:
            raise ValueError(f"Insufficient data: {len(entities)} entities, 0 synergies (could not generate synthetic)")
        
        # Train model
        async with get_db_session() as db:
            result = await detector.learn_from_data(
                entities=entities,
                known_synergies=synergies,
                db_session=db
            )
        
        # Update training run with results
        updates = {
            "status": "completed" if result.get('status') == 'complete' else "failed",
            "finished_at": datetime.utcnow(),
            "dataset_size": result.get('training_pairs', 0) + result.get('validation_pairs', 0),
            "base_model": f"GNN-{settings.gnn_hidden_dim}D-{settings.gnn_num_layers}L",
            "final_loss": result.get('final_val_loss'),
            "metadata_path": settings.gnn_model_path.replace('.pth', '_metadata.json'),
        }
        
        if result.get('status') != 'complete':
            updates["error_message"] = result.get('reason', 'Training failed')
        
        await _update_training_status(run_id, updates)
        
    except Exception as exc:
        logger.exception("GNN training job failed to execute")
        await _update_training_status(
            run_id,
            {
                "status": "failed",
                "finished_at": datetime.utcnow(),
                "error_message": str(exc)[:2000],  # Limit error message length
            },
        )


@router.post(
    "/training/gnn/trigger",
    response_model=TrainingRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_gnn_training_run(
    epochs: int | None = None,
    force: bool = False,
    db: AsyncSession = Depends(get_db)
) -> TrainingRunResponse:
    """Start a new GNN synergy training job if none is currently running."""
    
    async with _training_job_lock:
        active = await get_active_training_run(db, training_type='gnn_synergy')
        if active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A GNN training job is already running",
            )
        
        run_identifier = datetime.utcnow().strftime("gnn_run_%Y%m%d_%H%M%S")
        
        run_record = await create_training_run(
            db,
            {
                "training_type": "gnn_synergy",
                "status": "queued",
                "started_at": datetime.utcnow(),
                "output_dir": str(Path(settings.gnn_model_path).parent),
                "run_identifier": run_identifier,
                "triggered_by": "admin",
            },
        )
        
        asyncio.create_task(
            _execute_gnn_training_run(
                run_record.id,
                run_identifier,
                epochs=epochs,
                force=force
            )
        )
        
        return TrainingRunResponse.model_validate(run_record, from_attributes=True)


@router.get("/training/gnn/runs", response_model=list[TrainingRunResponse])
async def list_gnn_training_runs_endpoint(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[TrainingRunResponse]:
    """Return recent GNN training runs for display in the admin dashboard."""
    
    try:
        runs = await list_training_runs(db, limit=limit, training_type='gnn_synergy')
        return [TrainingRunResponse.model_validate(run, from_attributes=True) for run in runs]
    except Exception as exc:
        logger.error("Failed to list GNN training runs: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load GNN training history",
        ) from exc


@router.get("/training/gnn/status", response_model=dict)
async def get_gnn_training_status(db: AsyncSession = Depends(get_db)) -> dict:
    """Get current GNN training status and model info."""
    
    try:
        active_run = await get_active_training_run(db, training_type='gnn_synergy')
        
        # Check if model exists
        model_path = Path(settings.gnn_model_path)
        model_exists = model_path.exists()
        metadata_path = model_path.parent / f"{model_path.stem}_metadata.json"
        metadata_exists = metadata_path.exists()
        
        model_info = {}
        if model_exists and metadata_exists:
            try:
                with open(metadata_path, 'r') as f:
                    model_info = json.load(f)
            except Exception:
                pass
        
        return {
            "has_active_run": active_run is not None,
            "active_run": TrainingRunResponse.model_validate(active_run, from_attributes=True).model_dump() if active_run else None,
            "model_exists": model_exists,
            "model_path": str(model_path),
            "model_info": model_info
        }
    except Exception as exc:
        logger.error("Failed to get GNN training status: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get GNN training status",
        ) from exc


@router.delete("/training/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
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


@router.delete("/training/runs", status_code=status.HTTP_200_OK)
async def clear_old_training_runs_endpoint(
    training_type: str | None = None,
    older_than_days: int = 30,
    keep_recent: int = 10,
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

