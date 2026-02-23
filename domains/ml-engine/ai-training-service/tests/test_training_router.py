"""
Unit tests for Training Router

Epic 39, Story 39.4: Training Service Testing & Validation
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from src.main import app
from src.database import get_db
from src.database.models import TrainingRun
from src.crud.training import create_training_run


@pytest.fixture
def client(test_db: AsyncSession):
    """Create test client with database dependency override."""
    def override_get_db():
        return test_db
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestTrainingRouter:
    """Test suite for training endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_training_runs_empty(self, client: TestClient, test_db: AsyncSession):
        """Test listing training runs when none exist."""
        response = client.get("/api/v1/training/runs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    @pytest.mark.asyncio
    async def test_list_training_runs_with_data(
        self, client: TestClient, test_db: AsyncSession, sample_training_run_data
    ):
        """Test listing training runs with existing data."""
        # Create a training run
        await create_training_run(test_db, sample_training_run_data)
        
        response = client.get("/api/v1/training/runs")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["trainingType"] == "soft_prompt"
        assert data[0]["status"] == "queued"
    
    @pytest.mark.asyncio
    async def test_list_training_runs_filter_by_type(
        self, client: TestClient, test_db: AsyncSession, sample_training_run_data
    ):
        """Test filtering training runs by type."""
        # Create soft_prompt run
        await create_training_run(test_db, sample_training_run_data)
        
        # Create gnn_synergy run
        gnn_data = sample_training_run_data.copy()
        gnn_data["training_type"] = "gnn_synergy"
        await create_training_run(test_db, gnn_data)
        
        # Filter by soft_prompt
        response = client.get("/api/v1/training/runs?training_type=soft_prompt")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["trainingType"] == "soft_prompt"
    
    @pytest.mark.asyncio
    async def test_list_training_runs_limit(
        self, client: TestClient, test_db: AsyncSession, sample_training_run_data
    ):
        """Test limiting number of training runs returned."""
        # Create multiple runs
        for i in range(5):
            run_data = sample_training_run_data.copy()
            run_data["run_identifier"] = f"test_run_{i}"
            await create_training_run(test_db, run_data)
        
        # Request with limit
        response = client.get("/api/v1/training/runs?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_trigger_training_run_invalid_type(self, client: TestClient):
        """Test triggering training run with invalid type."""
        response = client.post("/api/v1/training/trigger?training_type=invalid_type")
        assert response.status_code == 400
        data = response.json()
        assert "Invalid training_type" in data["detail"]
    
    def test_delete_training_run_not_found(self, client: TestClient):
        """Test deleting non-existent training run."""
        response = client.delete("/api/v1/training/runs/999")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_training_run_success(
        self, client: TestClient, test_db: AsyncSession, sample_training_run_data
    ):
        """Test successfully deleting a training run."""
        # Create a training run
        run = await create_training_run(test_db, sample_training_run_data)
        
        # Delete it
        response = client.delete(f"/api/v1/training/runs/{run.id}")
        assert response.status_code == 204
        
        # Verify it's gone
        response = client.get("/api/v1/training/runs")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
    
    @pytest.mark.asyncio
    async def test_clear_old_training_runs(
        self, client: TestClient, test_db: AsyncSession, sample_training_run_data
    ):
        """Test clearing old training runs."""
        # Create a training run
        await create_training_run(test_db, sample_training_run_data)
        
        # Clear old runs (should keep recent)
        response = client.delete("/api/v1/training/runs?older_than_days=30&keep_recent=10")
        assert response.status_code == 200
        data = response.json()
        assert "deleted_count" in data
        assert "message" in data

