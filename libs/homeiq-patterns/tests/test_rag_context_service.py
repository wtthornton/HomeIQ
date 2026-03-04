"""Tests for RAGContextService and RAGContextRegistry."""

import sys
from pathlib import Path

import pytest

_project_root = str(Path(__file__).resolve().parents[3])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from homeiq_patterns import RAGContextRegistry, RAGContextService

# --- Test fixtures: concrete RAGContextService implementations ---

class MockSportsRAG(RAGContextService):
    name = "sports"
    keywords = ("football", "basketball", "score", "team tracker")
    corpus_path = None  # Will use dynamic corpus

    def load_corpus(self) -> str:
        self._corpus_cache = "Use team tracker sensor for sports automations."
        return self._corpus_cache


class MockEnergyRAG(RAGContextService):
    name = "energy"
    keywords = ("solar", "battery", "kWh", "TOU", "peak")
    corpus_path = None

    def load_corpus(self) -> str:
        self._corpus_cache = "Shift load to off-peak hours for cost savings."
        return self._corpus_cache


class EmptyCorpusRAG(RAGContextService):
    name = "empty"
    keywords = ("empty_test",)
    corpus_path = None

    def load_corpus(self) -> str:
        self._corpus_cache = ""
        return self._corpus_cache


# --- RAGContextService Tests ---

class TestRAGContextService:
    def test_detect_intent_match(self):
        service = MockSportsRAG()
        assert service.detect_intent("Flash lights when team scores a touchdown")
        assert service.detect_intent("BASKETBALL game lights")  # case-insensitive

    def test_detect_intent_no_match(self):
        service = MockSportsRAG()
        assert not service.detect_intent("Turn on the kitchen lights")
        assert not service.detect_intent("")

    def test_load_corpus_dynamic(self):
        service = MockSportsRAG()
        corpus = service.load_corpus()
        assert "team tracker" in corpus

    def test_load_corpus_caching(self):
        service = MockSportsRAG()
        first = service.load_corpus()
        second = service.load_corpus()
        assert first == second
        assert first is second  # Same cached object

    def test_load_corpus_from_file(self, tmp_path):
        corpus_file = tmp_path / "test_corpus.md"
        corpus_file.write_text("Energy patterns for TOU scheduling.", encoding="utf-8")

        class FileCorpusRAG(RAGContextService):
            name = "file_test"
            keywords = ("test_kw",)
            corpus_path = corpus_file

        service = FileCorpusRAG()
        corpus = service.load_corpus()
        assert "TOU scheduling" in corpus

    def test_load_corpus_missing_file(self):
        class MissingFileRAG(RAGContextService):
            name = "missing"
            keywords = ("missing_kw",)
            corpus_path = Path("/nonexistent/corpus.md")

        service = MissingFileRAG()
        corpus = service.load_corpus()
        assert corpus == ""

    def test_format_context_default(self):
        service = MockSportsRAG()
        formatted = service.format_context("Some corpus text")
        assert "RAG CONTEXT (sports patterns)" in formatted
        assert "Some corpus text" in formatted

    @pytest.mark.asyncio
    async def test_get_context_match(self):
        service = MockSportsRAG()
        result = await service.get_context("Flash lights when team scores")
        assert "team tracker" in result
        assert "RAG CONTEXT" in result

    @pytest.mark.asyncio
    async def test_get_context_no_match(self):
        service = MockSportsRAG()
        result = await service.get_context("Turn on kitchen lights")
        assert result == ""

    @pytest.mark.asyncio
    async def test_get_context_empty_corpus(self):
        service = EmptyCorpusRAG()
        result = await service.get_context("empty_test prompt")
        assert result == ""


# --- RAGContextRegistry Tests ---

class TestRAGContextRegistry:
    def test_register_service(self):
        registry = RAGContextRegistry()
        sports = MockSportsRAG()
        registry.register(sports)
        assert len(registry.services) == 1
        assert registry.services[0].name == "sports"

    def test_register_multiple(self):
        registry = RAGContextRegistry()
        registry.register(MockSportsRAG())
        registry.register(MockEnergyRAG())
        assert len(registry.services) == 2

    def test_unregister(self):
        registry = RAGContextRegistry()
        registry.register(MockSportsRAG())
        registry.register(MockEnergyRAG())
        removed = registry.unregister("sports")
        assert removed is True
        assert len(registry.services) == 1
        assert registry.services[0].name == "energy"

    def test_unregister_nonexistent(self):
        registry = RAGContextRegistry()
        removed = registry.unregister("nonexistent")
        assert removed is False

    @pytest.mark.asyncio
    async def test_get_all_context_single_match(self):
        registry = RAGContextRegistry()
        registry.register(MockSportsRAG())
        registry.register(MockEnergyRAG())
        contexts = await registry.get_all_context("Flash lights when team scores")
        assert len(contexts) == 1
        assert "team tracker" in contexts[0]

    @pytest.mark.asyncio
    async def test_get_all_context_multiple_matches(self):
        registry = RAGContextRegistry()
        registry.register(MockSportsRAG())
        registry.register(MockEnergyRAG())
        # Prompt matches both sports ("score") and energy ("solar")
        contexts = await registry.get_all_context("score solar battery")
        assert len(contexts) == 2

    @pytest.mark.asyncio
    async def test_get_all_context_no_matches(self):
        registry = RAGContextRegistry()
        registry.register(MockSportsRAG())
        registry.register(MockEnergyRAG())
        contexts = await registry.get_all_context("Turn on kitchen lights")
        assert len(contexts) == 0

    @pytest.mark.asyncio
    async def test_get_merged_context(self):
        registry = RAGContextRegistry()
        registry.register(MockSportsRAG())
        registry.register(MockEnergyRAG())
        merged = await registry.get_merged_context("score solar battery")
        assert "team tracker" in merged
        assert "off-peak" in merged

    @pytest.mark.asyncio
    async def test_get_merged_context_empty(self):
        registry = RAGContextRegistry()
        merged = await registry.get_merged_context("anything")
        assert merged == ""

    @pytest.mark.asyncio
    async def test_registration_order_preserved(self):
        registry = RAGContextRegistry()
        registry.register(MockEnergyRAG())
        registry.register(MockSportsRAG())
        contexts = await registry.get_all_context("score solar battery")
        # Energy registered first, should be first in results
        assert "off-peak" in contexts[0]
        assert "team tracker" in contexts[1]

    @pytest.mark.asyncio
    async def test_service_failure_graceful(self):
        """A failing service should not break the registry."""
        class FailingRAG(RAGContextService):
            name = "failing"
            keywords = ("fail_trigger",)

            async def get_context(self, _prompt: str) -> str:
                raise RuntimeError("Corpus loading failed")

        registry = RAGContextRegistry()
        registry.register(FailingRAG())
        registry.register(MockSportsRAG())
        contexts = await registry.get_all_context("fail_trigger score")
        # Failing service skipped, sports still works
        assert len(contexts) == 1
        assert "team tracker" in contexts[0]
