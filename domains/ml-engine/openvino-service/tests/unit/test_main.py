"""Unit tests for openvino-service main module endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_manager():
    """Create a mock OpenVINO manager."""
    manager = MagicMock()
    manager.is_ready.return_value = True
    manager.get_model_status.return_value = {
        "embedding_loaded": True,
        "reranker_loaded": True,
        "classifier_loaded": True,
    }
    manager.inference_timeout = 30.0
    manager.generate_embeddings = AsyncMock(
        return_value=np.array([[0.1, 0.2, 0.3]])
    )
    manager.rerank = AsyncMock(
        return_value=[{"description": "top", "score": 0.95}]
    )
    manager.classify_pattern = AsyncMock(
        return_value={"category": "automation", "priority": "medium"}
    )
    manager.initialize = AsyncMock()
    return manager


@pytest.fixture
def client(mock_manager) -> TestClient:
    """Create a test client with mocked manager."""
    import src.main as main_module

    original = main_module.openvino_manager
    main_module.openvino_manager = mock_manager
    try:
        yield TestClient(main_module.app)
    finally:
        main_module.openvino_manager = original


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_healthy(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["ready"] is True

    def test_health_not_ready_returns_503(self) -> None:
        import src.main as main_module

        original = main_module.openvino_manager
        main_module.openvino_manager = None
        try:
            tc = TestClient(main_module.app)
            response = tc.get("/health")
            assert response.status_code == 503
        finally:
            main_module.openvino_manager = original


class TestEmbeddingsEndpoint:
    """Tests for the /embeddings endpoint."""

    def test_embeddings_success(self, client: TestClient) -> None:
        response = client.post("/embeddings", json={
            "texts": ["hello world"], "normalize": True,
        })
        assert response.status_code == 200
        data = response.json()
        assert "embeddings" in data
        assert data["model_name"] == "BAAI/bge-large-en-v1.5"

    def test_embeddings_empty_texts(self, client: TestClient) -> None:
        response = client.post("/embeddings", json={
            "texts": [], "normalize": True,
        })
        assert response.status_code == 400


class TestRerankEndpoint:
    """Tests for the /rerank endpoint."""

    def test_rerank_success(self, client: TestClient) -> None:
        response = client.post("/rerank", json={
            "query": "test query",
            "candidates": [{"description": "candidate 1"}],
            "top_k": 1,
        })
        assert response.status_code == 200
        data = response.json()
        assert "ranked_candidates" in data

    def test_rerank_empty_query(self, client: TestClient) -> None:
        response = client.post("/rerank", json={
            "query": "",
            "candidates": [{"description": "c1"}],
            "top_k": 1,
        })
        assert response.status_code == 400


class TestClassifyEndpoint:
    """Tests for the /classify endpoint."""

    def test_classify_success(self, client: TestClient) -> None:
        response = client.post("/classify", json={
            "pattern_description": "motion triggers lights in living room",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "automation"
        assert data["model_name"] == "flan-t5-small"

    def test_classify_empty_description(self, client: TestClient) -> None:
        response = client.post("/classify", json={
            "pattern_description": "",
        })
        assert response.status_code == 400
