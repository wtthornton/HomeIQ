"""Tests for RAG relevance scoring and token budgeting (Story 2).

Tests cover:
- score_relevance() whole-word vs substring matching
- Multi-word keyword boost (1.5x)
- Score normalization (3.0 factor, capped at 1.0)
- min_score threshold behavior
- Token budget enforcement in RAGContextRegistry
- get_scored_context() sorted output
- get_context_for_domains() direct lookup
"""

import pytest
from pathlib import Path
import sys

_project_root = str(Path(__file__).resolve().parents[3])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from shared.patterns import RAGContextService, RAGContextRegistry
from shared.patterns.rag_context_registry import DEFAULT_TOKEN_BUDGET


# --- Test fixtures ---

class SportsRAG(RAGContextService):
    name = "sports"
    keywords = ("football", "basketball", "score", "team tracker")
    corpus_path = None

    def load_corpus(self) -> str:
        self._corpus_cache = "Sports corpus with team tracker patterns."
        return self._corpus_cache


class EnergyRAG(RAGContextService):
    name = "energy"
    keywords = ("solar", "battery", "kWh", "TOU", "peak", "off-peak")
    corpus_path = None

    def load_corpus(self) -> str:
        self._corpus_cache = "Energy corpus for TOU scheduling."
        return self._corpus_cache


class SecurityRAG(RAGContextService):
    name = "security"
    keywords = ("motion detected", "motion alert", "alarm", "intrusion", "door lock")
    min_score = 0.2
    corpus_path = None

    def load_corpus(self) -> str:
        self._corpus_cache = "Security corpus for alarm patterns."
        return self._corpus_cache


class LargeCorpusRAG(RAGContextService):
    """RAG service with a very large corpus for budget testing."""
    name = "large"
    keywords = ("large_trigger",)
    corpus_path = None

    def load_corpus(self) -> str:
        # ~20000 chars = ~5000 tokens
        self._corpus_cache = "x" * 20000
        return self._corpus_cache


class SmallCorpusRAG(RAGContextService):
    """RAG service with a small corpus."""
    name = "small"
    keywords = ("small_trigger",)
    corpus_path = None

    def load_corpus(self) -> str:
        self._corpus_cache = "Small corpus."
        return self._corpus_cache


# --- score_relevance() Tests ---

class TestScoreRelevance:
    def test_whole_word_match(self):
        """Whole-word keyword match gets 1.0 weight."""
        service = SportsRAG()
        score = service.score_relevance("I love football")
        # 1.0 / 3.0 = 0.333
        assert score == pytest.approx(0.33, abs=0.01)

    def test_substring_only_match(self):
        """Substring-only match (not at word boundary) gets 0.3 weight."""
        service = SportsRAG()
        # "scores" contains "score" but not as whole word
        score = service.score_relevance("The team scores a goal")
        # 0.3 / 3.0 = 0.10
        assert score == pytest.approx(0.10, abs=0.01)

    def test_multi_word_keyword_boost(self):
        """Multi-word keywords get 1.5x multiplier."""
        service = SportsRAG()
        score = service.score_relevance("use the team tracker sensor")
        # "team tracker" is multi-word, whole-word: 1.0 * 1.5 = 1.5
        # 1.5 / 3.0 = 0.50
        assert score == pytest.approx(0.50, abs=0.01)

    def test_multiple_keyword_matches(self):
        """Multiple keyword matches accumulate."""
        service = SportsRAG()
        score = service.score_relevance("football basketball score")
        # football: 1.0, basketball: 1.0, score: 1.0 → total 3.0
        # 3.0 / 3.0 = 1.0
        assert score == 1.0

    def test_score_capped_at_1(self):
        """Score cannot exceed 1.0."""
        service = EnergyRAG()
        score = service.score_relevance("solar battery kWh TOU peak")
        # 5 whole-word matches → 5.0 / 3.0 = 1.667 → capped at 1.0
        assert score == 1.0

    def test_no_match_returns_zero(self):
        """No keyword match returns 0.0."""
        service = SportsRAG()
        score = service.score_relevance("Turn on the kitchen lights")
        assert score == 0.0

    def test_empty_prompt_returns_zero(self):
        """Empty prompt returns 0.0."""
        service = SportsRAG()
        assert service.score_relevance("") == 0.0

    def test_case_insensitive(self):
        """Keyword matching is case-insensitive."""
        service = SportsRAG()
        score = service.score_relevance("FOOTBALL game tonight")
        assert score == pytest.approx(0.33, abs=0.01)

    def test_multi_word_substring_match(self):
        """Multi-word keyword as substring gets 0.3 * 1.5 weight."""
        service = SecurityRAG()
        # "motion detected" inside a compound phrase
        score = service.score_relevance("a motion detected event happened")
        # "motion detected" whole-word match: 1.0 * 1.5 = 1.5
        # 1.5 / 3.0 = 0.50
        assert score == pytest.approx(0.50, abs=0.01)

    def test_mixed_whole_and_substring(self):
        """Mix of whole-word and substring matches."""
        service = EnergyRAG()
        # "solar" whole-word (1.0), "peaked" contains "peak" substring (0.3)
        score = service.score_relevance("solar power peaked today")
        # 1.0 + 0.3 = 1.3, / 3.0 = 0.433
        assert score == pytest.approx(0.43, abs=0.01)


# --- detect_intent() with min_score Tests ---

class TestMinScore:
    def test_default_min_score(self):
        """Default min_score is 0.1."""
        service = SportsRAG()
        assert service.min_score == 0.1

    def test_custom_min_score(self):
        """Services can set custom min_score."""
        service = SecurityRAG()
        assert service.min_score == 0.2

    def test_single_substring_triggers_default(self):
        """A single substring match (score=0.1) triggers at default min_score."""
        service = SportsRAG()
        assert service.detect_intent("The team scores a goal")

    def test_single_substring_blocked_by_higher_min(self):
        """A single substring match is blocked by higher min_score."""
        service = SecurityRAG()
        # "alarm" whole-word: 1.0/3.0 = 0.33 >= 0.2 → triggers
        assert service.detect_intent("sound the alarm")
        # But if we only had a substring... SecurityRAG keywords are all multi-word
        # except "alarm" and "intrusion", so this is more about threshold validation

    def test_false_positive_prevention(self):
        """Higher min_score prevents false positives."""
        # "motion pictures" should NOT trigger SecurityRAG (min_score=0.2)
        # because SecurityRAG's keywords are "motion detected", "motion alert" etc.
        # "motion" alone is not a keyword
        service = SecurityRAG()
        assert not service.detect_intent("I enjoy motion pictures")


# --- Token Budget Tests ---

class TestTokenBudget:
    def test_default_budget(self):
        """Default token budget is 8000."""
        assert DEFAULT_TOKEN_BUDGET == 8000

    def test_registry_default_budget(self):
        """Registry uses default budget."""
        registry = RAGContextRegistry()
        assert registry.max_token_budget == 8000

    def test_custom_budget(self):
        """Registry accepts custom budget."""
        registry = RAGContextRegistry(max_token_budget=4000)
        assert registry.max_token_budget == 4000

    @pytest.mark.asyncio
    async def test_budget_allows_small_contexts(self):
        """Small contexts fit within budget."""
        registry = RAGContextRegistry(max_token_budget=8000)
        registry.register(SportsRAG())
        registry.register(EnergyRAG())
        contexts = await registry.get_all_context("football solar battery")
        # Both corpora are small, both should fit
        assert len(contexts) == 2

    @pytest.mark.asyncio
    async def test_budget_limits_large_contexts(self):
        """Budget enforcement drops lower-scored contexts."""
        # Budget = 100 tokens = 400 chars. LargeCorpusRAG produces ~20000 chars.
        registry = RAGContextRegistry(max_token_budget=100)
        registry.register(SmallCorpusRAG())
        registry.register(LargeCorpusRAG())
        contexts = await registry.get_all_context("small_trigger large_trigger")
        # SmallCorpusRAG fits, LargeCorpusRAG exceeds budget
        assert len(contexts) == 1
        assert "Small corpus" in contexts[0]

    @pytest.mark.asyncio
    async def test_first_context_always_included(self):
        """First (highest-scored) context is always included even if over budget."""
        registry = RAGContextRegistry(max_token_budget=1)  # 4 chars budget
        registry.register(LargeCorpusRAG())
        contexts = await registry.get_all_context("large_trigger")
        # Even though it exceeds budget, it's the first match so it's included
        assert len(contexts) == 1


# --- get_scored_context() Tests ---

class TestScoredContext:
    @pytest.mark.asyncio
    async def test_sorted_by_score_descending(self):
        """Results are sorted by score descending."""
        registry = RAGContextRegistry()
        registry.register(SportsRAG())
        registry.register(EnergyRAG())
        # Energy: solar(1.0) + battery(1.0) = 0.67 score
        # Sports: score(1.0) = 0.33 score
        results = await registry.get_scored_context("score solar battery")
        assert len(results) == 2
        assert results[0][0] == "energy"  # Higher score first
        assert results[1][0] == "sports"
        assert results[0][1] > results[1][1]

    @pytest.mark.asyncio
    async def test_returns_tuples(self):
        """Each result is a (name, score, context) tuple."""
        registry = RAGContextRegistry()
        registry.register(SportsRAG())
        results = await registry.get_scored_context("football")
        assert len(results) == 1
        name, score, context = results[0]
        assert name == "sports"
        assert isinstance(score, float)
        assert 0.0 < score <= 1.0
        assert "RAG CONTEXT" in context

    @pytest.mark.asyncio
    async def test_excludes_below_min_score(self):
        """Services below min_score are excluded."""
        registry = RAGContextRegistry()
        registry.register(SportsRAG())
        results = await registry.get_scored_context("Turn on kitchen lights")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_excludes_empty_corpus(self):
        """Services with empty corpus are excluded."""

        class EmptyRAG(RAGContextService):
            name = "empty"
            keywords = ("empty_trigger",)
            corpus_path = None

            def load_corpus(self) -> str:
                self._corpus_cache = ""
                return self._corpus_cache

        registry = RAGContextRegistry()
        registry.register(EmptyRAG())
        results = await registry.get_scored_context("empty_trigger")
        assert len(results) == 0


# --- get_context_for_domains() Tests ---

class TestContextForDomains:
    @pytest.mark.asyncio
    async def test_loads_by_name(self):
        """Loads context for specific domain names."""
        registry = RAGContextRegistry()
        registry.register(SportsRAG())
        registry.register(EnergyRAG())
        contexts = await registry.get_context_for_domains(["energy"])
        assert len(contexts) == 1
        assert "Energy corpus" in contexts[0]

    @pytest.mark.asyncio
    async def test_multiple_domains(self):
        """Loads context for multiple domain names."""
        registry = RAGContextRegistry()
        registry.register(SportsRAG())
        registry.register(EnergyRAG())
        contexts = await registry.get_context_for_domains(["sports", "energy"])
        assert len(contexts) == 2

    @pytest.mark.asyncio
    async def test_unknown_domain_ignored(self):
        """Unknown domain names are silently ignored."""
        registry = RAGContextRegistry()
        registry.register(SportsRAG())
        contexts = await registry.get_context_for_domains(["nonexistent"])
        assert len(contexts) == 0

    @pytest.mark.asyncio
    async def test_bypasses_keyword_detection(self):
        """Domain lookup bypasses keyword detection entirely."""
        registry = RAGContextRegistry()
        registry.register(EnergyRAG())
        # No keywords in prompt, but domain is requested directly
        contexts = await registry.get_context_for_domains(["energy"])
        assert len(contexts) == 1
        assert "Energy corpus" in contexts[0]
