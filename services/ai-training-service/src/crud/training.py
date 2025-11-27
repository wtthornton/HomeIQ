"""
Training CRUD operations

Epic 39, Story 39.1: Training Service Foundation
Extracted from ai-automation-service database/crud.py
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import TrainingRun

logger = logging.getLogger("ai-training-service")


async def get_active_training_run(db: AsyncSession, training_type: str | None = None) -> TrainingRun | None:
    """Fetch the currently running training run if one exists.
    
    Args:
        db: Database session
        training_type: Optional filter by training type (e.g., 'gnn_synergy', 'soft_prompt')
    """
    query = select(TrainingRun).where(TrainingRun.status == 'running')
    if training_type:
        query = query.where(TrainingRun.training_type == training_type)
    query = query.limit(1)
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_training_run(db: AsyncSession, values: dict[str, Any]) -> TrainingRun:
    """Create and persist a new training run entry."""
    run = TrainingRun(**values)
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


async def update_training_run(db: AsyncSession, run_id: int, updates: dict[str, Any]) -> TrainingRun | None:
    """Update an existing training run record."""
    result = await db.execute(select(TrainingRun).where(TrainingRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        return None

    for field, value in updates.items():
        if hasattr(run, field):
            setattr(run, field, value)

    await db.commit()
    await db.refresh(run)
    return run


async def list_training_runs(db: AsyncSession, limit: int = 20, training_type: str | None = None) -> list[TrainingRun]:
    """Return recent training runs ordered by newest first.
    
    Args:
        db: Database session
        limit: Maximum number of runs to return
        training_type: Optional filter by training type (e.g., 'gnn_synergy', 'soft_prompt')
    """
    query = select(TrainingRun)
    if training_type:
        query = query.where(TrainingRun.training_type == training_type)
    query = query.order_by(TrainingRun.started_at.desc()).limit(limit)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def delete_training_run(db: AsyncSession, run_id: int) -> bool:
    """Delete a training run by ID. Returns True if deleted, False if not found."""
    result = await db.execute(select(TrainingRun).where(TrainingRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        return False
    
    await db.delete(run)
    await db.commit()
    return True


async def delete_old_training_runs(
    db: AsyncSession,
    training_type: str | None = None,
    older_than_days: int = 30,
    keep_recent: int = 10,
) -> int:
    """
    Delete old training runs, keeping the most recent N runs.
    
    Args:
        db: Database session
        training_type: Optional filter by training type
        older_than_days: Delete runs older than this many days
        keep_recent: Always keep this many most recent runs
    
    Returns:
        Number of runs deleted
    """
    cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
    
    # Get IDs of runs to keep (most recent N)
    keep_query = select(TrainingRun.id)
    if training_type:
        keep_query = keep_query.where(TrainingRun.training_type == training_type)
    keep_query = keep_query.order_by(TrainingRun.started_at.desc()).limit(keep_recent)
    keep_result = await db.execute(keep_query)
    keep_ids = {row[0] for row in keep_result.all()}
    
    # Delete runs older than cutoff, excluding keep_ids
    delete_query = select(TrainingRun).where(
        TrainingRun.started_at < cutoff_date
    )
    if training_type:
        delete_query = delete_query.where(TrainingRun.training_type == training_type)
    
    result = await db.execute(delete_query)
    runs_to_delete = [run for run in result.scalars().all() if run.id not in keep_ids]
    
    for run in runs_to_delete:
        await db.delete(run)
    
    await db.commit()
    return len(runs_to_delete)

