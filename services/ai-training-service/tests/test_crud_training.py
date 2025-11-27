"""
Unit tests for Training CRUD operations

Epic 39, Story 39.4: Training Service Testing & Validation
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.training import (
    get_active_training_run,
    create_training_run,
    update_training_run,
    list_training_runs,
    delete_training_run,
    delete_old_training_runs,
)
from src.database.models import TrainingRun


class TestTrainingCRUD:
    """Test suite for training CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_training_run(
        self, test_db: AsyncSession, sample_training_run_data
    ):
        """Test creating a training run."""
        run = await create_training_run(test_db, sample_training_run_data)
        
        assert run.id is not None
        assert run.training_type == "soft_prompt"
        assert run.status == "queued"
        assert run.run_identifier == "test_run_20250101_120000"
    
    @pytest.mark.asyncio
    async def test_get_active_training_run_none(
        self, test_db: AsyncSession
    ):
        """Test getting active training run when none exists."""
        active = await get_active_training_run(test_db)
        assert active is None
    
    @pytest.mark.asyncio
    async def test_get_active_training_run_exists(
        self, test_db: AsyncSession, sample_training_run_data
    ):
        """Test getting active training run when one exists."""
        # Create a running training run
        run_data = sample_training_run_data.copy()
        run_data["status"] = "running"
        await create_training_run(test_db, run_data)
        
        active = await get_active_training_run(test_db)
        assert active is not None
        assert active.status == "running"
    
    @pytest.mark.asyncio
    async def test_get_active_training_run_filtered_by_type(
        self, test_db: AsyncSession, sample_training_run_data
    ):
        """Test filtering active training run by type."""
        # Create running soft_prompt run
        soft_prompt_data = sample_training_run_data.copy()
        soft_prompt_data["status"] = "running"
        await create_training_run(test_db, soft_prompt_data)
        
        # Create running gnn_synergy run
        gnn_data = sample_training_run_data.copy()
        gnn_data["training_type"] = "gnn_synergy"
        gnn_data["status"] = "running"
        await create_training_run(test_db, gnn_data)
        
        # Get active soft_prompt run
        active = await get_active_training_run(test_db, training_type="soft_prompt")
        assert active is not None
        assert active.training_type == "soft_prompt"
    
    @pytest.mark.asyncio
    async def test_update_training_run(
        self, test_db: AsyncSession, sample_training_run_data
    ):
        """Test updating a training run."""
        # Create a training run
        run = await create_training_run(test_db, sample_training_run_data)
        
        # Update it
        updates = {
            "status": "running",
            "finished_at": datetime.utcnow(),
        }
        updated = await update_training_run(test_db, run.id, updates)
        
        assert updated is not None
        assert updated.status == "running"
        assert updated.finished_at is not None
    
    @pytest.mark.asyncio
    async def test_update_training_run_not_found(
        self, test_db: AsyncSession
    ):
        """Test updating a non-existent training run."""
        updates = {"status": "running"}
        updated = await update_training_run(test_db, 999, updates)
        assert updated is None
    
    @pytest.mark.asyncio
    async def test_list_training_runs(
        self, test_db: AsyncSession, sample_training_run_data
    ):
        """Test listing training runs."""
        # Create multiple runs
        for i in range(3):
            run_data = sample_training_run_data.copy()
            run_data["run_identifier"] = f"test_run_{i}"
            await create_training_run(test_db, run_data)
        
        runs = await list_training_runs(test_db, limit=10)
        assert len(runs) == 3
    
    @pytest.mark.asyncio
    async def test_list_training_runs_with_limit(
        self, test_db: AsyncSession, sample_training_run_data
    ):
        """Test listing training runs with limit."""
        # Create multiple runs
        for i in range(5):
            run_data = sample_training_run_data.copy()
            run_data["run_identifier"] = f"test_run_{i}"
            await create_training_run(test_db, run_data)
        
        runs = await list_training_runs(test_db, limit=2)
        assert len(runs) == 2
    
    @pytest.mark.asyncio
    async def test_list_training_runs_filtered_by_type(
        self, test_db: AsyncSession, sample_training_run_data
    ):
        """Test listing training runs filtered by type."""
        # Create soft_prompt runs
        for i in range(2):
            run_data = sample_training_run_data.copy()
            run_data["run_identifier"] = f"soft_prompt_run_{i}"
            await create_training_run(test_db, run_data)
        
        # Create gnn_synergy run
        gnn_data = sample_training_run_data.copy()
        gnn_data["training_type"] = "gnn_synergy"
        gnn_data["run_identifier"] = "gnn_run_0"
        await create_training_run(test_db, gnn_data)
        
        # List only soft_prompt
        runs = await list_training_runs(test_db, limit=10, training_type="soft_prompt")
        assert len(runs) == 2
        assert all(r.training_type == "soft_prompt" for r in runs)
    
    @pytest.mark.asyncio
    async def test_delete_training_run(
        self, test_db: AsyncSession, sample_training_run_data
    ):
        """Test deleting a training run."""
        # Create a training run
        run = await create_training_run(test_db, sample_training_run_data)
        
        # Delete it
        deleted = await delete_training_run(test_db, run.id)
        assert deleted is True
        
        # Verify it's gone
        runs = await list_training_runs(test_db, limit=10)
        assert len(runs) == 0
    
    @pytest.mark.asyncio
    async def test_delete_training_run_not_found(
        self, test_db: AsyncSession
    ):
        """Test deleting a non-existent training run."""
        deleted = await delete_training_run(test_db, 999)
        assert deleted is False
    
    @pytest.mark.asyncio
    async def test_delete_old_training_runs(
        self, test_db: AsyncSession, sample_training_run_data
    ):
        """Test deleting old training runs."""
        # Create old run (30+ days ago)
        old_data = sample_training_run_data.copy()
        old_data["started_at"] = datetime.utcnow() - timedelta(days=35)
        old_data["run_identifier"] = "old_run"
        await create_training_run(test_db, old_data)
        
        # Create recent run
        recent_data = sample_training_run_data.copy()
        recent_data["run_identifier"] = "recent_run"
        await create_training_run(test_db, recent_data)
        
        # Delete old runs (keep 10 recent)
        deleted_count = await delete_old_training_runs(
            test_db,
            older_than_days=30,
            keep_recent=10
        )
        
        assert deleted_count == 1
        
        # Verify old run is gone, recent run remains
        runs = await list_training_runs(test_db, limit=10)
        assert len(runs) == 1
        assert runs[0].run_identifier == "recent_run"

