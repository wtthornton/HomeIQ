import pytest
from utils import TestOpenVINOManager


@pytest.fixture
def rerank_manager(tmp_path):
    return TestOpenVINOManager(models_dir=str(tmp_path))


@pytest.mark.asyncio
async def test_reranking_orders_by_similarity(rerank_manager):
    query = "Turn on the living room lights when motion is detected"
    candidates = [
        {"id": 1, "description": "Dim the bedroom lamp when the shades close"},
        {"id": 2, "description": "Lock the garage door when motion is detected"},
        {"id": 3, "description": "Turn on the living room lights automatically"},
    ]

    ranked = await rerank_manager.rerank(query, candidates, top_k=3)

    assert ranked[0]["id"] == 3  # semantic match
    assert len(ranked) == 3


@pytest.mark.asyncio
async def test_reranking_respects_top_k_limits(rerank_manager):
    query = "Water the garden when the soil moisture is low"
    candidates = [{"id": idx, "description": f"Automation {idx}"} for idx in range(10)]

    ranked = await rerank_manager.rerank(query, candidates, top_k=2)

    assert len(ranked) == 2
    assert ranked[0]["id"] in range(10)
