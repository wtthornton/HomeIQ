from __future__ import annotations

import pytest
from fastapi import HTTPException

from src.main import (
    ClassifyRequest,
    EmbeddingRequest,
    RerankRequest,
    classify_pattern,
    generate_embeddings,
    get_model_status,
    health_check,
    rerank_candidates,
)

from utils import TestOpenVINOManager, cosine_similarity, deterministic_embedding


@pytest.fixture
def wired_manager(tmp_path, monkeypatch):
    manager = TestOpenVINOManager(models_dir=str(tmp_path))

    from src import main as service_main

    monkeypatch.setattr(service_main, "openvino_manager", manager)
    return manager


@pytest.mark.asyncio
async def test_health_endpoint_reports_ready(wired_manager):
    result = await health_check()
    assert result["service"] == "openvino-service"
    assert "models_loaded" in result


@pytest.mark.asyncio
async def test_model_status_endpoint(wired_manager):
    status = await get_model_status()
    assert status["embedding_model"] == "all-MiniLM-L6-v2"
    assert status["ready_for_requests"] is True


@pytest.mark.asyncio
async def test_embeddings_endpoint(wired_manager):
    request = EmbeddingRequest(texts=["Turn on the hallway lights"], normalize=True)
    response = await generate_embeddings(request)
    assert len(response.embeddings) == 1
    assert len(response.embeddings[0]) == 384
    assert response.model_name == "all-MiniLM-L6-v2"


@pytest.mark.asyncio
async def test_rerank_endpoint(wired_manager):
    request = RerankRequest(
        query="Turn on hallway lights",
        candidates=[
            {"id": 1, "description": "Open the garage door"},
            {"id": 2, "description": "Turn on hallway lights automatically"},
        ],
        top_k=1,
    )
    response = await rerank_candidates(request)
    assert len(response.ranked_candidates) == 1

    query_vec = deterministic_embedding(request.query)
    expected_top = max(
        request.candidates,
        key=lambda candidate: cosine_similarity(
            query_vec, deterministic_embedding(candidate["description"])
        ),
    )
    assert response.ranked_candidates[0]["id"] == expected_top["id"]
    assert response.model_name == "bge-reranker-base"


@pytest.mark.asyncio
async def test_classification_endpoint(wired_manager):
    request = ClassifyRequest(pattern_description="Lock the front door when motion is detected")
    response = await classify_pattern(request)
    assert response.category in {"energy", "comfort", "security", "convenience"}
    assert response.priority in {"high", "medium", "low"}
    assert response.model_name == "flan-t5-small"


@pytest.mark.asyncio
async def test_embedding_validation_errors(monkeypatch):
    from src import main as service_main

    # Remove manager to trigger 503 guard
    monkeypatch.setattr(service_main, "openvino_manager", None)
    request = EmbeddingRequest(texts=["hello"], normalize=True)
    with pytest.raises(HTTPException):
        await generate_embeddings(request)
