"""
Internal endpoints for automation-trace-service to upsert automation
registry and execution records.

Follows the pattern from devices_endpoints.py /internal/devices/bulk_upsert.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .models import Automation, AutomationExecution

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/internal/automations/bulk_upsert")
async def bulk_upsert_automations(
    automations: list[dict[str, Any]],
    db: AsyncSession = Depends(get_db),
):
    """Upsert automation registry records from automation-trace-service."""
    try:
        upserted = 0
        for data in automations:
            automation_id = data.get("automation_id")
            if not automation_id:
                continue

            result = await db.execute(
                select(Automation).where(Automation.automation_id == automation_id)
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update mutable fields only
                if data.get("alias"):
                    existing.alias = data["alias"]
                if "enabled" in data:
                    existing.enabled = data["enabled"]
                if data.get("description"):
                    existing.description = data["description"]
                if data.get("mode"):
                    existing.mode = data["mode"]
                existing.updated_at = datetime.now(UTC)
            else:
                new_automation = Automation(
                    automation_id=automation_id,
                    alias=data.get("alias", automation_id),
                    description=data.get("description"),
                    mode=data.get("mode"),
                    enabled=data.get("enabled", True),
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
                db.add(new_automation)

            upserted += 1

        await db.commit()
        logger.info("Bulk upserted %d automations", upserted)
        return {"success": True, "upserted": upserted, "timestamp": datetime.now(UTC).isoformat()}

    except Exception as e:
        await db.rollback()
        logger.error("Error bulk upserting automations: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk upsert automations: {e}",
        ) from e


@router.post("/internal/automations/executions/bulk_upsert")
async def bulk_upsert_executions(
    executions: list[dict[str, Any]],
    db: AsyncSession = Depends(get_db),
):
    """Upsert automation execution records and update parent automation stats."""
    try:
        upserted = 0
        for data in executions:
            run_id = data.get("run_id")
            automation_id = data.get("automation_id")
            if not run_id or not automation_id:
                continue

            # Check for duplicate run_id
            result = await db.execute(
                select(AutomationExecution).where(AutomationExecution.run_id == run_id)
            )
            if result.scalar_one_or_none():
                continue  # Already exists

            # Ensure parent automation exists
            auto_result = await db.execute(
                select(Automation).where(Automation.automation_id == automation_id)
            )
            automation = auto_result.scalar_one_or_none()
            if not automation:
                automation = Automation(
                    automation_id=automation_id,
                    alias=automation_id,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
                db.add(automation)
                await db.flush()

            # Parse timestamps
            started_at = None
            finished_at = None
            if data.get("started_at"):
                try:
                    started_at = datetime.fromisoformat(data["started_at"])
                except (ValueError, TypeError):
                    started_at = datetime.now(UTC)
            if data.get("finished_at"):
                try:
                    finished_at = datetime.fromisoformat(data["finished_at"])
                except (ValueError, TypeError):
                    pass

            execution = AutomationExecution(
                automation_id=automation_id,
                run_id=run_id,
                started_at=started_at or datetime.now(UTC),
                finished_at=finished_at,
                duration_seconds=data.get("duration_seconds", 0.0),
                execution_result=data.get("execution_result", "unknown"),
                trigger_type=data.get("trigger_type"),
                trigger_entity=data.get("trigger_entity"),
                error_message=data.get("error_message"),
                step_count=data.get("step_count"),
                last_step=data.get("last_step"),
                context_id=data.get("context_id"),
            )
            db.add(execution)

            # Update parent automation rolling stats
            automation.total_executions = (automation.total_executions or 0) + 1
            is_error = data.get("execution_result", "").lower() in ("error", "aborted")
            if is_error:
                automation.total_errors = (automation.total_errors or 0) + 1
            if started_at:
                automation.last_triggered = started_at

            # Recalculate success rate
            total = automation.total_executions or 1
            errors = automation.total_errors or 0
            automation.success_rate = round(((total - errors) / total) * 100, 1)

            # Update running average duration
            duration = data.get("duration_seconds", 0.0)
            if duration and automation.avg_duration_seconds:
                # Incremental average
                automation.avg_duration_seconds = round(
                    automation.avg_duration_seconds
                    + (duration - automation.avg_duration_seconds) / total,
                    3,
                )
            elif duration:
                automation.avg_duration_seconds = round(duration, 3)

            automation.updated_at = datetime.now(UTC)
            upserted += 1

        await db.commit()
        if upserted:
            logger.info("Bulk upserted %d automation executions", upserted)
        return {"success": True, "upserted": upserted, "timestamp": datetime.now(UTC).isoformat()}

    except Exception as e:
        await db.rollback()
        logger.error("Error bulk upserting executions: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk upsert executions: {e}",
        ) from e
