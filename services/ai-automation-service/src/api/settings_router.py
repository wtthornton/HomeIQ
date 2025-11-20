"""Settings API endpoints."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings as runtime_settings
from ..database import (
    get_db,
)
from ..database import (
    get_system_settings as db_get_system_settings,
)
from ..database import (
    update_system_settings as db_update_system_settings,
)
from .ask_ai_router import (
    reload_guardrail_checker,
    reload_soft_prompt_adapter,
    reset_guardrail_checker,
    reset_soft_prompt_adapter,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])


class EnabledCategoriesModel(BaseModel):
    """Nested representation of enabled suggestion categories."""

    energy: bool = True
    comfort: bool = True
    security: bool = True
    convenience: bool = True

    model_config = ConfigDict(populate_by_name=True)


class ParallelTestingModelsModel(BaseModel):
    """Nested representation of parallel testing model configuration."""

    suggestion: list[str] = Field(default=["gpt-5.1"])
    yaml: list[str] = Field(default=["gpt-5.1"])

    model_config = ConfigDict(populate_by_name=True)


class SystemSettingsSchema(BaseModel):
    """DTO for system settings payloads."""

    schedule_enabled: bool = Field(..., alias="scheduleEnabled")
    schedule_time: str = Field(..., alias="scheduleTime")
    min_confidence: int = Field(..., alias="minConfidence")
    max_suggestions: int = Field(..., alias="maxSuggestions")
    enabled_categories: EnabledCategoriesModel = Field(..., alias="enabledCategories")
    budget_limit: float = Field(..., alias="budgetLimit")
    notifications_enabled: bool = Field(..., alias="notificationsEnabled")
    notification_email: str = Field(..., alias="notificationEmail")
    soft_prompt_enabled: bool = Field(..., alias="softPromptEnabled")
    soft_prompt_model_dir: str = Field(..., alias="softPromptModelDir")
    soft_prompt_confidence_threshold: float = Field(..., alias="softPromptConfidenceThreshold")
    guardrail_enabled: bool = Field(..., alias="guardrailEnabled")
    guardrail_model_name: str = Field(..., alias="guardrailModelName")
    guardrail_threshold: float = Field(..., alias="guardrailThreshold")
    enable_parallel_model_testing: bool = Field(default=False, alias="enableParallelModelTesting")
    parallel_testing_models: ParallelTestingModelsModel | None = Field(
        default_factory=lambda: ParallelTestingModelsModel(),
        alias="parallelTestingModels"
    )
    enable_answer_caching: bool = Field(default=True, alias="enableAnswerCaching")  # NEW: Enable/disable answer caching

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


def _validate_payload(payload: SystemSettingsSchema) -> dict:
    """Validate user-provided settings and normalise values."""

    errors: list[str] = []

    model_dir_path = Path(payload.soft_prompt_model_dir).expanduser()
    if payload.soft_prompt_enabled:
        # Create directory if it doesn't exist (user is enabling the feature)
        if not model_dir_path.exists():
            try:
                model_dir_path.mkdir(parents=True, exist_ok=True)
                logger.info("Created soft prompt model directory: %s", model_dir_path)
            except Exception as exc:
                errors.append(
                    f"Failed to create soft prompt model directory '{model_dir_path}': {exc}"
                )
        elif not model_dir_path.is_dir():
            errors.append(
                f"Soft prompt model directory path '{model_dir_path}' exists but is not a directory."
            )

    if not 0 <= payload.soft_prompt_confidence_threshold <= 1:
        errors.append("Soft prompt confidence threshold must be between 0 and 1.")

    if payload.guardrail_enabled and not payload.guardrail_model_name.strip():
        errors.append("Guardrail model name cannot be empty when guardrails are enabled.")

    if not 0 <= payload.guardrail_threshold <= 1:
        errors.append("Guardrail threshold must be between 0 and 1.")

    if errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=errors)

    normalised_payload = payload.model_dump(by_alias=False)
    normalised_payload["soft_prompt_model_dir"] = str(model_dir_path)

    return normalised_payload


def _apply_runtime_settings(updated_record, previous_record) -> None:
    """Keep runtime config and adapters aligned with persisted values."""

    mutable_fields = (
        "soft_prompt_enabled",
        "soft_prompt_model_dir",
        "soft_prompt_confidence_threshold",
        "guardrail_enabled",
        "guardrail_model_name",
        "guardrail_threshold",
    )

    for field in mutable_fields:
        value = getattr(updated_record, field)
        try:
            setattr(runtime_settings, field, value)
        except (AttributeError, TypeError):
            object.__setattr__(runtime_settings, field, value)

    soft_prompt_changed = (
        updated_record.soft_prompt_enabled != previous_record.soft_prompt_enabled
        or updated_record.soft_prompt_model_dir != previous_record.soft_prompt_model_dir
        or updated_record.soft_prompt_confidence_threshold != previous_record.soft_prompt_confidence_threshold
    )

    guardrail_changed = (
        updated_record.guardrail_enabled != previous_record.guardrail_enabled
        or updated_record.guardrail_model_name != previous_record.guardrail_model_name
        or updated_record.guardrail_threshold != previous_record.guardrail_threshold
    )

    if updated_record.soft_prompt_enabled:
        if soft_prompt_changed:
            reload_soft_prompt_adapter()
    else:
        if previous_record.soft_prompt_enabled:
            reset_soft_prompt_adapter()

    if updated_record.guardrail_enabled:
        if guardrail_changed:
            reload_guardrail_checker()
    else:
        if previous_record.guardrail_enabled:
            reset_guardrail_checker()


@router.get("", response_model=SystemSettingsSchema)
async def get_settings(db: AsyncSession = Depends(get_db)) -> SystemSettingsSchema:
    """Fetch the current persisted system settings."""

    try:
        settings_record = await db_get_system_settings(db)
        return SystemSettingsSchema.model_validate(settings_record, from_attributes=True)
    except Exception as exc:
        logger.error("Failed to load system settings: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load system settings",
        ) from exc


@router.put("", response_model=SystemSettingsSchema)
async def update_settings(payload: SystemSettingsSchema, db: AsyncSession = Depends(get_db)) -> SystemSettingsSchema:
    """Persist updated system settings."""

    try:
        current_record = await db_get_system_settings(db)
        update_payload = _validate_payload(payload)
        update_payload["enabled_categories"] = payload.enabled_categories.model_dump(by_alias=False)
        # Handle parallel_testing_models - always include it
        if payload.parallel_testing_models:
            update_payload["parallel_testing_models"] = payload.parallel_testing_models.model_dump(by_alias=False)
        else:
            # Use default if not provided
            update_payload["parallel_testing_models"] = {
                "suggestion": ["gpt-5.1"],
                "yaml": ["gpt-5.1"]
            }

        updated_record = await db_update_system_settings(db, update_payload)
        _apply_runtime_settings(updated_record, current_record)
        return SystemSettingsSchema.model_validate(updated_record, from_attributes=True)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to update system settings: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update system settings",
        ) from exc

