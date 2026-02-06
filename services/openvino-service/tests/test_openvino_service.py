from __future__ import annotations

# Ensure path setup before imports
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

test_dir = Path(__file__).resolve().parent
service_dir = test_dir.parent
# Add service_dir to path so we can import from src package
if str(service_dir) not in sys.path:
    sys.path.insert(0, str(service_dir))
# Also add src_dir for utils imports
src_dir = service_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Import from src package to preserve relative imports in main.py
from src.main import (
    ClassifyRequest,
    EmbeddingRequest,
    RerankRequest,
    classify_pattern,
    generate_embeddings,
    get_model_status,
    health_check,
    rerank_candidates,
    warmup_models,
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
    assert "models_ready" in result  # MED-3: new field


@pytest.mark.asyncio
async def test_model_status_endpoint(wired_manager):
    status = await get_model_status()
    # MED-1: Fixed model name assertion to match actual EMBEDDING_MODEL_NAME
    assert status["embedding_model"] == "BAAI/bge-large-en-v1.5"
    assert status["embedding_dimension"] == 1024
    assert status["ready_for_requests"] is True


@pytest.mark.asyncio
async def test_embeddings_endpoint(wired_manager):
    request = EmbeddingRequest(texts=["Turn on the hallway lights"], normalize=True)
    response = await generate_embeddings(request)
    assert len(response.embeddings) == 1
    assert len(response.embeddings[0]) == 1024
    # MED-1: Fixed model name assertion to match actual response
    assert response.model_name == "BAAI/bge-large-en-v1.5"


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


# --------------------------------------------------------------------------
# Additional test coverage (from REVIEW_AND_FIXES.md testing improvements)
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_endpoint_partial_initialization(tmp_path, monkeypatch):
    """Test health endpoint when only some models are loaded."""
    from src import main as service_main

    manager = TestOpenVINOManager(models_dir=str(tmp_path))
    # Only load embedding model
    await manager._load_embedding_model()
    monkeypatch.setattr(service_main, "openvino_manager", manager)

    result = await health_check()
    assert result["status"] == "healthy"
    assert result["models_ready"] is True  # at least one model loaded
    assert result["models_loaded"]["embedding_loaded"] is True
    assert result["models_loaded"]["reranker_loaded"] is False
    assert result["models_loaded"]["classifier_loaded"] is False


@pytest.mark.asyncio
async def test_warmup_endpoint(wired_manager):
    """ENH-2: Test the model warmup endpoint."""
    result = await warmup_models()
    assert result["status"] == "all_models_loaded"
    assert "models" in result


@pytest.mark.asyncio
async def test_embedding_empty_texts_rejected(wired_manager):
    """Boundary test: empty text list should be rejected."""
    request = EmbeddingRequest(texts=[], normalize=True)
    with pytest.raises(HTTPException) as exc_info:
        await generate_embeddings(request)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_embedding_whitespace_only_rejected(wired_manager):
    """Boundary test: whitespace-only text should be rejected."""
    request = EmbeddingRequest(texts=["   "], normalize=True)
    with pytest.raises(HTTPException) as exc_info:
        await generate_embeddings(request)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_classify_empty_description_rejected(wired_manager):
    """Boundary test: empty pattern description should be rejected."""
    request = ClassifyRequest(pattern_description="")
    with pytest.raises(HTTPException) as exc_info:
        await classify_pattern(request)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_rerank_empty_query_rejected(wired_manager):
    """Boundary test: empty query should be rejected."""
    request = RerankRequest(
        query="",
        candidates=[{"id": 1, "description": "test"}],
        top_k=1,
    )
    with pytest.raises(HTTPException) as exc_info:
        await rerank_candidates(request)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_rerank_empty_candidates_rejected(wired_manager):
    """Boundary test: empty candidates list should be rejected."""
    request = RerankRequest(
        query="test query",
        candidates=[],
        top_k=1,
    )
    with pytest.raises(HTTPException) as exc_info:
        await rerank_candidates(request)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_embedding_unicode_input(wired_manager):
    """Boundary test: unicode text should work correctly."""
    request = EmbeddingRequest(
        texts=["Schalte das Licht ein", "Allume la lumiere"],
        normalize=True,
    )
    response = await generate_embeddings(request)
    assert len(response.embeddings) == 2
    assert len(response.embeddings[0]) == 1024


@pytest.mark.asyncio
async def test_health_endpoint_no_manager_returns_503(monkeypatch):
    """Test that health endpoint returns 503 when manager is None."""
    from src import main as service_main

    monkeypatch.setattr(service_main, "openvino_manager", None)
    with pytest.raises(HTTPException) as exc_info:
        await health_check()
    assert exc_info.value.status_code == 503
