"""Comprehensive tests for homeiq-memory library.

Tests cover: decay engine, embeddings, models, memory injector, and RRF search.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeiq_memory import (
    ACCESS_CONFIDENCE_BUMP,
    HALF_LIVES,
    MAX_CONFIDENCE,
    Memory,
    MemoryType,
    SourceChannel,
    effective_confidence,
    record_access,
    reinforce,
    should_archive,
)
from homeiq_memory.decay import contradict
from homeiq_memory.injector import MemoryInjector
from homeiq_memory.search import MemorySearch, MemorySearchResult


@pytest.fixture
def sample_memory():
    """Create a sample memory for testing."""
    memory = Memory(
        id=1,
        content="User prefers warm evenings",
        memory_type=MemoryType.PREFERENCE,
        confidence=0.7,
        source_channel=SourceChannel.EXPLICIT,
        source_service="ha-ai-agent",
        entity_ids=["climate.living_room"],
        area_ids=["living_room"],
        tags=["temperature", "evening"],
    )
    memory.updated_at = datetime.now(UTC)
    memory.created_at = datetime.now(UTC)
    memory.access_count = 0
    memory.last_accessed = None
    memory.superseded_by = None
    memory.metadata_ = None
    memory.embedding = None
    return memory


@pytest.fixture
def behavioral_memory():
    """Create a behavioral memory for decay testing."""
    memory = Memory(
        id=2,
        content="User turns on lights at 6pm",
        memory_type=MemoryType.BEHAVIORAL,
        confidence=0.8,
        source_channel=SourceChannel.IMPLICIT,
        source_service="pattern-detector",
        entity_ids=["light.living_room"],
        area_ids=["living_room"],
        tags=["lighting", "evening"],
    )
    memory.updated_at = datetime.now(UTC)
    memory.created_at = datetime.now(UTC)
    memory.access_count = 5
    memory.last_accessed = datetime.now(UTC)
    memory.superseded_by = None
    memory.metadata_ = None
    memory.embedding = None
    return memory


@pytest.fixture
def boundary_memory():
    """Create a boundary memory (no decay)."""
    memory = Memory(
        id=3,
        content="Never automate garage door",
        memory_type=MemoryType.BOUNDARY,
        confidence=0.95,
        source_channel=SourceChannel.EXPLICIT,
        source_service="ha-ai-agent",
        entity_ids=["cover.garage_door"],
        area_ids=["garage"],
        tags=["safety", "boundary"],
    )
    memory.updated_at = datetime.now(UTC) - timedelta(days=365)
    memory.created_at = datetime.now(UTC) - timedelta(days=365)
    memory.access_count = 10
    memory.last_accessed = datetime.now(UTC)
    memory.superseded_by = None
    memory.metadata_ = None
    memory.embedding = None
    return memory


@pytest.fixture
def routine_memory():
    """Create a routine memory (no decay)."""
    memory = Memory(
        id=4,
        content="Morning routine starts at 6:30 AM",
        memory_type=MemoryType.ROUTINE,
        confidence=0.9,
        source_channel=SourceChannel.SYNTHESIZED,
        source_service="routine-analyzer",
        entity_ids=[],
        area_ids=[],
        tags=["routine", "morning"],
    )
    memory.updated_at = datetime.now(UTC) - timedelta(days=200)
    memory.created_at = datetime.now(UTC) - timedelta(days=200)
    memory.access_count = 50
    memory.last_accessed = datetime.now(UTC)
    memory.superseded_by = None
    memory.metadata_ = None
    memory.embedding = None
    return memory


class TestDecay:
    """Tests for decay engine functions."""

    def test_effective_confidence_no_decay_boundary(self, boundary_memory):
        """Boundary memories should not decay regardless of age."""
        result = effective_confidence(boundary_memory)
        assert result == boundary_memory.confidence
        assert result == 0.95

    def test_effective_confidence_no_decay_routine(self, routine_memory):
        """Routine memories should not decay regardless of age."""
        result = effective_confidence(routine_memory)
        assert result == routine_memory.confidence
        assert result == 0.9

    def test_effective_confidence_behavioral(self, behavioral_memory):
        """Behavioral memories should decay with 90-day half-life."""
        behavioral_memory.updated_at = datetime.now(UTC) - timedelta(days=90)
        result = effective_confidence(behavioral_memory)
        expected = behavioral_memory.confidence * 0.5
        assert abs(result - expected) < 0.01

    def test_effective_confidence_preference(self, sample_memory):
        """Preference memories should decay with 180-day half-life."""
        sample_memory.updated_at = datetime.now(UTC) - timedelta(days=180)
        result = effective_confidence(sample_memory)
        expected = sample_memory.confidence * 0.5
        assert abs(result - expected) < 0.01

    def test_effective_confidence_recent_no_decay(self, sample_memory):
        """Recent memories should have minimal decay."""
        sample_memory.updated_at = datetime.now(UTC) - timedelta(hours=1)
        result = effective_confidence(sample_memory)
        assert abs(result - sample_memory.confidence) < 0.01

    def test_effective_confidence_outcome_memory(self):
        """Outcome memories should decay with 120-day half-life."""
        memory = Memory(
            id=5,
            content="Automation caused power surge",
            memory_type=MemoryType.OUTCOME,
            confidence=0.75,
            source_channel=SourceChannel.IMPLICIT,
            source_service="outcome-tracker",
        )
        memory.updated_at = datetime.now(UTC) - timedelta(days=120)
        memory.created_at = datetime.now(UTC) - timedelta(days=120)
        memory.access_count = 0
        memory.last_accessed = None
        memory.superseded_by = None
        memory.metadata_ = None
        memory.embedding = None
        memory.entity_ids = None
        memory.area_ids = None
        memory.tags = None

        result = effective_confidence(memory)
        expected = memory.confidence * 0.5
        assert abs(result - expected) < 0.01

    def test_reinforce_increases_confidence(self, sample_memory):
        """Reinforce should increase confidence."""
        original = sample_memory.confidence
        result = reinforce(sample_memory, amount=0.1)
        assert result.confidence == original + 0.1

    def test_reinforce_caps_at_95(self, boundary_memory):
        """Reinforce should cap confidence at MAX_CONFIDENCE (0.95)."""
        boundary_memory.confidence = 0.92
        result = reinforce(boundary_memory, amount=0.1)
        assert result.confidence == MAX_CONFIDENCE
        assert result.confidence == 0.95

    def test_reinforce_updates_timestamp(self, sample_memory):
        """Reinforce should update the updated_at timestamp."""
        old_timestamp = sample_memory.updated_at
        result = reinforce(sample_memory, amount=0.05)
        assert result.updated_at >= old_timestamp

    def test_record_access_increments_count(self, sample_memory):
        """Record access should increment access_count."""
        original_count = sample_memory.access_count
        result = record_access(sample_memory)
        assert result.access_count == original_count + 1

    def test_record_access_updates_last_accessed(self, sample_memory):
        """Record access should update last_accessed timestamp."""
        result = record_access(sample_memory)
        assert result.last_accessed is not None
        assert (datetime.now(UTC) - result.last_accessed).total_seconds() < 1

    def test_record_access_bumps_confidence(self, sample_memory):
        """Record access should bump confidence by ACCESS_CONFIDENCE_BUMP."""
        original = sample_memory.confidence
        result = record_access(sample_memory)
        assert result.confidence == original + ACCESS_CONFIDENCE_BUMP

    def test_record_access_respects_max_confidence(self, boundary_memory):
        """Record access should not exceed MAX_CONFIDENCE."""
        boundary_memory.confidence = 0.94
        result = record_access(boundary_memory)
        assert result.confidence <= MAX_CONFIDENCE

    def test_should_archive_below_threshold(self, sample_memory):
        """Should archive when effective confidence is below threshold."""
        sample_memory.confidence = 0.1
        sample_memory.updated_at = datetime.now(UTC) - timedelta(days=365)
        result = should_archive(sample_memory, threshold=0.15)
        assert result is True

    def test_should_not_archive_above_threshold(self, sample_memory):
        """Should not archive when effective confidence is above threshold."""
        result = should_archive(sample_memory, threshold=0.15)
        assert result is False

    def test_should_archive_boundary_never(self, boundary_memory):
        """Boundary memories should not be archived due to decay."""
        boundary_memory.updated_at = datetime.now(UTC) - timedelta(days=1000)
        result = should_archive(boundary_memory, threshold=0.15)
        assert result is False

    def test_contradict_reduces_confidence(self, sample_memory):
        """Contradict should reduce confidence to the specified value."""
        result = contradict(sample_memory, new_confidence=0.1)
        assert result.confidence == 0.1

    def test_half_lives_values(self):
        """Verify half-life values for each memory type."""
        assert HALF_LIVES[MemoryType.BEHAVIORAL] == 90
        assert HALF_LIVES[MemoryType.PREFERENCE] == 180
        assert HALF_LIVES[MemoryType.BOUNDARY] is None
        assert HALF_LIVES[MemoryType.OUTCOME] == 120
        assert HALF_LIVES[MemoryType.ROUTINE] is None

    def test_max_confidence_constant(self):
        """Verify MAX_CONFIDENCE constant."""
        assert MAX_CONFIDENCE == 0.95

    def test_access_confidence_bump_constant(self):
        """Verify ACCESS_CONFIDENCE_BUMP constant."""
        assert ACCESS_CONFIDENCE_BUMP == 0.02


class TestEmbeddings:
    """Integration tests for embedding generation."""

    @pytest.fixture
    def embedding_generator(self):
        """Create an embedding generator instance."""
        from homeiq_memory.embeddings import EmbeddingGenerator

        return EmbeddingGenerator()

    def test_embedding_dimension_default_model(self, embedding_generator):
        """Default model should have 384 dimensions."""
        dimension = embedding_generator.dimension
        assert dimension == 384

    def test_embedding_dimension_alternative_model(self):
        """Alternative model should have 768 dimensions."""
        from homeiq_memory.embeddings import EmbeddingGenerator

        generator = EmbeddingGenerator(model_name="nomic-ai/nomic-embed-text-v1.5")
        dimension = generator.dimension
        assert dimension == 768

    def test_model_name_property(self, embedding_generator):
        """Model name property should return the configured model."""
        assert embedding_generator.model_name == "all-MiniLM-L6-v2"

    def test_is_loaded_initially_false(self, embedding_generator):
        """Model should not be loaded until first use."""
        assert embedding_generator.is_loaded() is False

    @pytest.mark.skipif(
        "sentence_transformers" not in sys.modules,
        reason="sentence-transformers not installed",
    )
    @pytest.mark.asyncio
    async def test_generate_returns_list(self, embedding_generator):
        """Generate should return a list of floats."""
        result = await embedding_generator.generate("Hello world")
        assert isinstance(result, list)
        assert len(result) == 384
        assert all(isinstance(x, float) for x in result)

    @pytest.mark.skipif(
        "sentence_transformers" not in sys.modules,
        reason="sentence-transformers not installed",
    )
    @pytest.mark.asyncio
    async def test_generate_batch_consistent(self, embedding_generator):
        """Batch generation should be consistent with single generation."""
        texts = ["Hello world", "Good morning"]
        batch_results = await embedding_generator.generate_batch(texts)

        assert len(batch_results) == 2
        assert all(len(emb) == 384 for emb in batch_results)

    @pytest.mark.skipif(
        "sentence_transformers" not in sys.modules,
        reason="sentence-transformers not installed",
    )
    @pytest.mark.asyncio
    async def test_generate_batch_empty_list(self, embedding_generator):
        """Batch generation with empty list should return empty list."""
        result = await embedding_generator.generate_batch([])
        assert result == []


class TestMemoryModel:
    """Tests for Memory model and enums."""

    def test_memory_type_enum_values(self):
        """MemoryType enum should have correct values."""
        assert MemoryType.BEHAVIORAL.value == "behavioral"
        assert MemoryType.PREFERENCE.value == "preference"
        assert MemoryType.BOUNDARY.value == "boundary"
        assert MemoryType.OUTCOME.value == "outcome"
        assert MemoryType.ROUTINE.value == "routine"

    def test_memory_type_enum_count(self):
        """MemoryType should have exactly 5 values."""
        assert len(MemoryType) == 5

    def test_source_channel_enum_values(self):
        """SourceChannel enum should have correct values."""
        assert SourceChannel.EXPLICIT.value == "explicit"
        assert SourceChannel.IMPLICIT.value == "implicit"
        assert SourceChannel.SYNTHESIZED.value == "synthesized"

    def test_source_channel_enum_count(self):
        """SourceChannel should have exactly 3 values."""
        assert len(SourceChannel) == 3

    def test_memory_repr(self, sample_memory):
        """Memory repr should include id, type, and confidence."""
        repr_str = repr(sample_memory)
        assert "Memory" in repr_str
        assert "id=1" in repr_str
        assert "type=preference" in repr_str
        assert "confidence=0.70" in repr_str

    def test_memory_repr_boundary(self, boundary_memory):
        """Memory repr should work for boundary type."""
        repr_str = repr(boundary_memory)
        assert "type=boundary" in repr_str

    def test_memory_type_is_string_enum(self):
        """MemoryType should be a string enum."""
        assert isinstance(MemoryType.BEHAVIORAL, str)
        assert MemoryType.BEHAVIORAL == "behavioral"

    def test_source_channel_is_string_enum(self):
        """SourceChannel should be a string enum."""
        assert isinstance(SourceChannel.EXPLICIT, str)
        assert SourceChannel.EXPLICIT == "explicit"


class TestMemoryInjector:
    """Tests for MemoryInjector class."""

    @pytest.fixture
    def mock_search(self):
        """Create a mock MemorySearch."""
        return AsyncMock(spec=MemorySearch)

    @pytest.fixture
    def injector(self, mock_search):
        """Create a MemoryInjector with mock search."""
        return MemoryInjector(search=mock_search, token_budget=2000)

    @pytest.fixture
    def mock_search_result(self, sample_memory):
        """Create a mock search result."""
        return MemorySearchResult(
            memory=sample_memory,
            relevance_score=0.85,
            fts_rank=1,
            vector_rank=2,
        )

    def test_format_memory_basic(self, injector, mock_search_result):
        """Format memory should produce expected output."""
        mock_search_result.memory.entity_ids = None
        mock_search_result.memory.area_ids = None
        result = injector.format_memory(mock_search_result)
        assert "User prefers warm evenings" in result
        assert "preference" in result
        assert "confidence: 0.70" in result
        assert result.startswith("- ")

    def test_format_memory_with_entities(self, injector, mock_search_result):
        """Format memory should include entity context."""
        result = injector.format_memory(mock_search_result)
        assert "entities: climate.living_room" in result

    def test_format_memory_with_areas(self, injector, sample_memory):
        """Format memory should include area context."""
        sample_memory.entity_ids = None
        search_result = MemorySearchResult(
            memory=sample_memory,
            relevance_score=0.8,
            fts_rank=1,
            vector_rank=None,
        )
        result = injector.format_memory(search_result)
        assert "areas: living_room" in result

    def test_format_memory_with_multiple_entities(self, injector, sample_memory):
        """Format memory should truncate many entities."""
        sample_memory.entity_ids = [
            "light.living_room",
            "light.kitchen",
            "light.bedroom",
        ]
        sample_memory.area_ids = None
        search_result = MemorySearchResult(
            memory=sample_memory,
            relevance_score=0.8,
            fts_rank=1,
            vector_rank=None,
        )
        result = injector.format_memory(search_result)
        assert "light.living_room" in result
        assert "light.kitchen" in result
        assert "..." in result

    def test_format_context_block_respects_token_budget(self, mock_search):
        """Context block should respect token budget by truncating."""
        small_budget_injector = MemoryInjector(search=mock_search, token_budget=50)

        results = []
        for i in range(10):
            mem = Memory(
                id=i,
                content=f"Memory content number {i} with some extra text",
                memory_type=MemoryType.PREFERENCE,
                confidence=0.7 - (i * 0.05),
                source_channel=SourceChannel.EXPLICIT,
                source_service="test",
            )
            mem.updated_at = datetime.now(UTC)
            mem.created_at = datetime.now(UTC)
            mem.access_count = 0
            mem.last_accessed = None
            mem.superseded_by = None
            mem.metadata_ = None
            mem.embedding = None
            mem.entity_ids = None
            mem.area_ids = None
            mem.tags = None

            results.append(
                MemorySearchResult(
                    memory=mem,
                    relevance_score=0.9 - (i * 0.1),
                    fts_rank=i + 1,
                    vector_rank=i + 1,
                )
            )

        block = small_budget_injector.format_context_block(results)
        assert len(block) < 50 * 4 + 100

    def test_empty_results_returns_empty_string(self, mock_search):
        """Empty results should return empty string by default."""
        injector = MemoryInjector(
            search=mock_search, include_no_memories_message=False
        )
        result = injector.format_context_block([])
        assert result == ""

    def test_empty_results_returns_no_memories_message(self, mock_search):
        """Empty results should return message when configured."""
        injector = MemoryInjector(search=mock_search, include_no_memories_message=True)
        result = injector.format_context_block([])
        assert result == "[No relevant memories]"

    def test_token_budget_property(self, injector):
        """Token budget property should return configured value."""
        assert injector.token_budget == 2000

    def test_token_budget_setter(self, injector):
        """Token budget setter should update value."""
        injector.token_budget = 3000
        assert injector.token_budget == 3000

    def test_token_budget_setter_rejects_negative(self, injector):
        """Token budget setter should reject non-positive values."""
        with pytest.raises(ValueError, match="must be positive"):
            injector.token_budget = -100

    def test_token_budget_setter_rejects_zero(self, injector):
        """Token budget setter should reject zero."""
        with pytest.raises(ValueError, match="must be positive"):
            injector.token_budget = 0

    @pytest.mark.asyncio
    async def test_get_context_returns_formatted_block(
        self, mock_search, sample_memory
    ):
        """get_context should return formatted context block."""
        search_result = MemorySearchResult(
            memory=sample_memory,
            relevance_score=0.85,
            fts_rank=1,
            vector_rank=2,
        )
        mock_search.search.return_value = [search_result]

        injector = MemoryInjector(search=mock_search)
        result = await injector.get_context("temperature preferences")

        assert "[Memory Context]" in result
        assert "User prefers warm evenings" in result
        mock_search.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_context_empty_query_results(self, mock_search):
        """get_context should handle empty search results."""
        mock_search.search.return_value = []

        injector = MemoryInjector(search=mock_search, include_no_memories_message=False)
        result = await injector.get_context("nonexistent topic")

        assert result == ""

    @pytest.mark.asyncio
    async def test_get_context_with_memory_types_filter(
        self, mock_search, sample_memory
    ):
        """get_context should pass memory types filter to search."""
        search_result = MemorySearchResult(
            memory=sample_memory,
            relevance_score=0.85,
            fts_rank=1,
            vector_rank=2,
        )
        mock_search.search.return_value = [search_result]

        injector = MemoryInjector(search=mock_search)
        await injector.get_context(
            "preferences",
            memory_types=[MemoryType.PREFERENCE],
        )

        call_args = mock_search.search.call_args
        assert call_args.kwargs.get("memory_types") == [MemoryType.PREFERENCE]

    @pytest.mark.asyncio
    async def test_get_context_with_exclude_types(self, mock_search, sample_memory):
        """get_context should exclude specified memory types."""
        search_result = MemorySearchResult(
            memory=sample_memory,
            relevance_score=0.85,
            fts_rank=1,
            vector_rank=2,
        )
        mock_search.search.return_value = [search_result]

        injector = MemoryInjector(search=mock_search)
        await injector.get_context(
            "preferences",
            exclude_types=[MemoryType.BOUNDARY],
        )

        call_args = mock_search.search.call_args
        filtered_types = call_args.kwargs.get("memory_types")
        assert MemoryType.BOUNDARY not in filtered_types


class TestRRF:
    """Tests for Reciprocal Rank Fusion in MemorySearch."""

    @pytest.fixture
    def mock_session_factory(self):
        """Create a mock async session factory."""
        return AsyncMock()

    @pytest.fixture
    def search(self, mock_session_factory):
        """Create a MemorySearch instance with mock dependencies."""
        return MemorySearch(
            session_factory=mock_session_factory,
            embedding_generator=None,
            fts_weight=0.6,
            vector_weight=0.4,
        )

    def test_rrf_fusion_combines_scores(self, search):
        """RRF should combine scores from both sources."""
        fts_results = [(1, 1), (2, 2), (3, 3)]
        vector_results = [(1, 2), (2, 1), (4, 3)]

        result = search._reciprocal_rank_fusion(
            fts_results, vector_results, fts_weight=0.6, vector_weight=0.4
        )

        result_dict = dict(result)
        assert 1 in result_dict
        assert 2 in result_dict
        assert 3 in result_dict
        assert 4 in result_dict

    def test_rrf_fusion_memory_in_both_sources_scores_higher(self, search):
        """Memory appearing in both sources should score higher."""
        fts_results = [(1, 1), (2, 2)]
        vector_results = [(1, 1), (3, 2)]

        result = search._reciprocal_rank_fusion(
            fts_results, vector_results, fts_weight=0.6, vector_weight=0.4
        )

        result_dict = dict(result)
        assert result_dict[1] > result_dict[2]
        assert result_dict[1] > result_dict[3]

    def test_rrf_fusion_sorted_by_score_descending(self, search):
        """RRF results should be sorted by score descending."""
        fts_results = [(1, 3), (2, 1), (3, 2)]
        vector_results = [(1, 3), (2, 1), (3, 2)]

        result = search._reciprocal_rank_fusion(
            fts_results, vector_results, fts_weight=0.5, vector_weight=0.5
        )

        scores = [score for _, score in result]
        assert scores == sorted(scores, reverse=True)

    def test_fts_weight_dominates(self, search):
        """Higher FTS weight should favor FTS-ranked results."""
        fts_results = [(1, 1), (2, 2)]
        vector_results = [(2, 1), (1, 2)]

        result = search._reciprocal_rank_fusion(
            fts_results, vector_results, fts_weight=0.9, vector_weight=0.1
        )

        result_list = list(result)
        top_memory_id = result_list[0][0]
        assert top_memory_id == 1

    def test_vector_weight_dominates(self, search):
        """Higher vector weight should favor vector-ranked results."""
        fts_results = [(1, 1), (2, 2)]
        vector_results = [(2, 1), (1, 2)]

        result = search._reciprocal_rank_fusion(
            fts_results, vector_results, fts_weight=0.1, vector_weight=0.9
        )

        result_list = list(result)
        top_memory_id = result_list[0][0]
        assert top_memory_id == 2

    def test_rrf_single_source_fts_only(self, search):
        """RRF should work with only FTS results."""
        fts_results = [(1, 1), (2, 2), (3, 3)]
        vector_results = []

        result = search._reciprocal_rank_fusion(
            fts_results, vector_results, fts_weight=0.6, vector_weight=0.4
        )

        result_dict = dict(result)
        assert len(result_dict) == 3
        assert result_dict[1] > result_dict[2] > result_dict[3]

    def test_rrf_single_source_vector_only(self, search):
        """RRF should work with only vector results."""
        fts_results = []
        vector_results = [(1, 1), (2, 2), (3, 3)]

        result = search._reciprocal_rank_fusion(
            fts_results, vector_results, fts_weight=0.6, vector_weight=0.4
        )

        result_dict = dict(result)
        assert len(result_dict) == 3
        assert result_dict[1] > result_dict[2] > result_dict[3]

    def test_rrf_empty_both_sources(self, search):
        """RRF should return empty list when both sources are empty."""
        result = search._reciprocal_rank_fusion([], [], fts_weight=0.6, vector_weight=0.4)
        assert result == []

    def test_rrf_k_constant(self, search):
        """K constant should be 60 (standard RRF)."""
        assert search.K == 60

    def test_rrf_score_calculation(self, search):
        """Verify RRF score calculation formula."""
        fts_results = [(1, 1)]
        vector_results = [(1, 1)]

        result = search._reciprocal_rank_fusion(
            fts_results, vector_results, fts_weight=0.6, vector_weight=0.4
        )

        expected_fts_score = 0.6 / (60 + 1)
        expected_vector_score = 0.4 / (60 + 1)
        expected_total = expected_fts_score + expected_vector_score

        result_dict = dict(result)
        assert abs(result_dict[1] - expected_total) < 0.0001

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_empty(
        self, mock_session_factory
    ):
        """Search with empty query should return empty list."""
        search = MemorySearch(
            session_factory=mock_session_factory,
            embedding_generator=None,
        )
        result = await search.search("   ")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_filters_by_min_confidence(
        self, mock_session_factory
    ):
        """Search should filter results by minimum effective confidence."""
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        search = MemorySearch(
            session_factory=mock_session_factory,
            embedding_generator=None,
        )

        with patch.object(search, "_fts_search", return_value=[]):
            result = await search.search("test query", min_confidence=0.5)
            assert result == []


class TestMemorySearchResult:
    """Tests for MemorySearchResult dataclass."""

    def test_search_result_creation(self, sample_memory):
        """MemorySearchResult should store all fields correctly."""
        result = MemorySearchResult(
            memory=sample_memory,
            relevance_score=0.85,
            fts_rank=1,
            vector_rank=2,
        )

        assert result.memory == sample_memory
        assert result.relevance_score == 0.85
        assert result.fts_rank == 1
        assert result.vector_rank == 2

    def test_search_result_optional_ranks(self, sample_memory):
        """MemorySearchResult should allow None ranks."""
        result = MemorySearchResult(
            memory=sample_memory,
            relevance_score=0.75,
            fts_rank=None,
            vector_rank=3,
        )

        assert result.fts_rank is None
        assert result.vector_rank == 3
