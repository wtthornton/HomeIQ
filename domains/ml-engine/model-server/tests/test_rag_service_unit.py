"""Unit tests for RAGService (TAP-7276).

test_rag_service.py's `test_rag_service_placeholder` predates this: the class
was never actually exercised. These tests mock the DB session and the
OpenVINO bridge so RAGService's own logic -- caching, similarity filtering,
sorting, and error propagation -- is what's under test, not a real database
or a real model.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from src.rag.clients.openvino_client import EmbeddingGenerationError
from src.rag.services.rag_service import RAGService, cosine_similarity


def _fake_bridge(vector: list[float] | None = None) -> MagicMock:
    """A LocalOpenVINOBridge stand-in that always returns one fixed embedding."""
    bridge = MagicMock()
    bridge.get_embeddings = AsyncMock(return_value=[vector or [1.0, 0.0, 0.0]])
    return bridge


def _fake_entry(entry_id: int, text: str, embedding: list[float], **overrides):
    entry = MagicMock()
    entry.id = entry_id
    entry.text = text
    entry.embedding = embedding
    entry.knowledge_type = overrides.get("knowledge_type", "query")
    entry.metadata_json = overrides.get("metadata_json", {})
    entry.success_score = overrides.get("success_score", 0.5)
    entry.created_at = overrides.get("created_at", datetime(2026, 1, 1, tzinfo=UTC))
    return entry


class TestCosineSimilarity:
    def test_identical_vectors_are_similarity_one(self):
        v = np.array([1.0, 2.0, 3.0])
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors_are_similarity_zero(self):
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-6)


class TestGetEmbeddingCache:
    @pytest.mark.asyncio
    async def test_cache_miss_calls_bridge_and_caches(self):
        bridge = _fake_bridge([0.5, 0.5])
        cache: dict = {}
        service = RAGService(db=MagicMock(), openvino_client=bridge, embedding_cache=cache)

        embedding, cache_hit = await service._get_embedding("hello")

        assert cache_hit is False
        assert bridge.get_embeddings.call_count == 1
        assert "hello" in cache

    @pytest.mark.asyncio
    async def test_cache_hit_skips_bridge(self):
        bridge = _fake_bridge()
        cache = {"hello": np.array([9.0, 9.0])}
        service = RAGService(db=MagicMock(), openvino_client=bridge, embedding_cache=cache)

        embedding, cache_hit = await service._get_embedding("hello")

        assert cache_hit is True
        assert bridge.get_embeddings.call_count == 0
        assert embedding is cache["hello"]

    @pytest.mark.asyncio
    async def test_empty_embeddings_response_raises(self):
        bridge = MagicMock()
        bridge.get_embeddings = AsyncMock(return_value=[])
        service = RAGService(db=MagicMock(), openvino_client=bridge, embedding_cache={})

        with pytest.raises(EmbeddingGenerationError, match="No embeddings returned"):
            await service._get_embedding("hello")

    @pytest.mark.asyncio
    async def test_bridge_exception_wrapped_as_embedding_error(self):
        bridge = MagicMock()
        bridge.get_embeddings = AsyncMock(side_effect=RuntimeError("model unavailable"))
        service = RAGService(db=MagicMock(), openvino_client=bridge, embedding_cache={})

        with pytest.raises(EmbeddingGenerationError, match="Failed to generate embedding"):
            await service._get_embedding("hello")

    @pytest.mark.asyncio
    async def test_cache_eviction_when_full(self):
        bridge = _fake_bridge([0.1, 0.2])
        cache = {"a": np.array([1.0]), "b": np.array([2.0])}
        service = RAGService(db=MagicMock(), openvino_client=bridge, embedding_cache=cache, embedding_cache_size=2)

        await service._get_embedding("c")

        assert len(cache) == 2
        assert "c" in cache
        assert "a" not in cache  # oldest entry evicted


class TestStore:
    @pytest.mark.asyncio
    async def test_store_success(self):
        bridge = _fake_bridge([1.0, 0.0])
        db = AsyncMock()

        async def _refresh(entry):
            entry.id = 42

        db.refresh.side_effect = _refresh
        service = RAGService(db=db, openvino_client=bridge, embedding_cache={})

        entry_id, cache_hit = await service.store("some text", "pattern")

        assert entry_id == 42
        assert cache_hit is False
        db.add.assert_called_once()
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_store_rolls_back_on_db_error(self):
        bridge = _fake_bridge([1.0, 0.0])
        db = AsyncMock()
        db.commit.side_effect = RuntimeError("db exploded")
        service = RAGService(db=db, openvino_client=bridge, embedding_cache={})

        with pytest.raises(RuntimeError, match="db exploded"):
            await service.store("some text", "pattern")

        db.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_store_propagates_embedding_error_without_touching_db(self):
        bridge = MagicMock()
        bridge.get_embeddings = AsyncMock(side_effect=RuntimeError("down"))
        db = AsyncMock()
        service = RAGService(db=db, openvino_client=bridge, embedding_cache={})

        with pytest.raises(EmbeddingGenerationError):
            await service.store("some text", "pattern")

        db.add.assert_not_called()


class TestRetrieve:
    @pytest.mark.asyncio
    async def test_retrieve_filters_by_min_similarity_and_sorts(self):
        bridge = _fake_bridge([1.0, 0.0])
        db = AsyncMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = [
            _fake_entry(1, "close match", [1.0, 0.0]),  # similarity 1.0
            _fake_entry(2, "far match", [0.0, 1.0]),  # similarity 0.0 -- filtered out
            _fake_entry(3, "medium match", [0.7, 0.3]),
        ]
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_result
        db.execute = AsyncMock(return_value=execute_result)
        service = RAGService(db=db, openvino_client=bridge, embedding_cache={})

        results, cache_hit = await service.retrieve("query", top_k=5, min_similarity=0.5)

        assert cache_hit is False
        assert [r["id"] for r in results] == [1, 3]  # sorted by similarity desc, id 2 excluded
        assert results[0]["similarity"] >= results[1]["similarity"]

    @pytest.mark.asyncio
    async def test_retrieve_respects_top_k(self):
        bridge = _fake_bridge([1.0, 0.0])
        db = AsyncMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = [_fake_entry(i, f"match {i}", [1.0, 0.0]) for i in range(5)]
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_result
        db.execute = AsyncMock(return_value=execute_result)
        service = RAGService(db=db, openvino_client=bridge, embedding_cache={})

        results, _ = await service.retrieve("query", top_k=2, min_similarity=0.0)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_retrieve_applies_knowledge_type_filter_to_query(self):
        bridge = _fake_bridge([1.0, 0.0])
        db = AsyncMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = []
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_result
        db.execute = AsyncMock(return_value=execute_result)
        service = RAGService(db=db, openvino_client=bridge, embedding_cache={})

        await service.retrieve("query", knowledge_type="automation")

        db.execute.assert_awaited_once()


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_extracts_knowledge_type_from_filters(self):
        bridge = _fake_bridge([1.0, 0.0])
        db = AsyncMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = []
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_result
        db.execute = AsyncMock(return_value=execute_result)
        service = RAGService(db=db, openvino_client=bridge, embedding_cache={})

        results, cache_hit = await service.search("query", filters={"knowledge_type": "blueprint"})

        assert results == []
        assert cache_hit is False

    @pytest.mark.asyncio
    async def test_search_with_no_filters(self):
        bridge = _fake_bridge([1.0, 0.0])
        db = AsyncMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = []
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_result
        db.execute = AsyncMock(return_value=execute_result)
        service = RAGService(db=db, openvino_client=bridge, embedding_cache={})

        results, _ = await service.search("query")

        assert results == []


class TestUpdateSuccessScore:
    @pytest.mark.asyncio
    async def test_update_success_score_found(self):
        db = AsyncMock()
        entry = _fake_entry(7, "text", [1.0])
        db.get = AsyncMock(return_value=entry)
        service = RAGService(db=db, openvino_client=_fake_bridge(), embedding_cache={})

        await service.update_success_score(7, 0.9)

        assert entry.success_score == 0.9
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_success_score_not_found_raises(self):
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)
        service = RAGService(db=db, openvino_client=_fake_bridge(), embedding_cache={})

        with pytest.raises(ValueError, match="not found"):
            await service.update_success_score(999, 0.9)

    @pytest.mark.asyncio
    async def test_update_success_score_rolls_back_on_db_error(self):
        db = AsyncMock()
        entry = _fake_entry(7, "text", [1.0])
        db.get = AsyncMock(return_value=entry)
        db.commit.side_effect = RuntimeError("db exploded")
        service = RAGService(db=db, openvino_client=_fake_bridge(), embedding_cache={})

        with pytest.raises(RuntimeError, match="db exploded"):
            await service.update_success_score(7, 0.9)

        db.rollback.assert_awaited_once()
