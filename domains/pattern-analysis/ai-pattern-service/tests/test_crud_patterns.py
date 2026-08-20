"""
Unit tests for Pattern CRUD operations

Epic 39, Story 39.8: Pattern Service Testing & Validation
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.crud.patterns import get_patterns, store_patterns


class TestPatternCRUD:
    """Test suite for pattern CRUD operations."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.requires_db
    async def test_store_patterns(self, test_db: AsyncSession, sample_pattern_data):
        """Test storing patterns."""
        patterns = [sample_pattern_data]
        stored_count = await store_patterns(test_db, patterns)

        assert stored_count == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.requires_db
    async def test_store_empty_patterns(self, test_db: AsyncSession):
        """Test storing empty pattern list."""
        stored_count = await store_patterns(test_db, [])
        assert stored_count == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.requires_db
    async def test_store_multiple_patterns(self, test_db: AsyncSession, sample_pattern_data):
        """Test storing multiple patterns."""
        patterns = [
            sample_pattern_data,
            {**sample_pattern_data, "device_id": "light.kitchen", "pattern_type": "co_occurrence"},
        ]
        stored_count = await store_patterns(test_db, patterns)
        assert stored_count == 2

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.requires_db
    async def test_get_patterns(self, test_db: AsyncSession, sample_pattern_data):
        """Test retrieving patterns."""
        # Store a pattern first
        await store_patterns(test_db, [sample_pattern_data])

        # Retrieve patterns
        patterns = await get_patterns(test_db)
        assert len(patterns) >= 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.requires_db
    async def test_get_patterns_filtered_by_type(self, test_db: AsyncSession, sample_pattern_data):
        """Test retrieving patterns filtered by type."""
        # Store patterns of different types
        patterns = [
            sample_pattern_data,
            {**sample_pattern_data, "device_id": "light.kitchen", "pattern_type": "co_occurrence"},
        ]
        await store_patterns(test_db, patterns)

        # Get only time_of_day patterns
        tod_patterns = await get_patterns(test_db, pattern_type="time_of_day")
        assert len(tod_patterns) >= 1
        # Handle both dict and object access (raw SQL returns dicts)
        assert all(
            (p.pattern_type if hasattr(p, "pattern_type") else p["pattern_type"]) == "time_of_day"
            for p in tod_patterns
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.requires_db
    async def test_get_patterns_filtered_by_device(
        self, test_db: AsyncSession, sample_pattern_data
    ):
        """Test retrieving patterns filtered by device."""
        # Store pattern
        await store_patterns(test_db, [sample_pattern_data])

        # Get patterns for specific device
        patterns = await get_patterns(test_db, device_id="light.office_lamp")
        assert len(patterns) >= 1
        # Handle both dict and object access (raw SQL returns dicts)
        assert all(
            (p.device_id if hasattr(p, "device_id") else p["device_id"]) == "light.office_lamp"
            for p in patterns
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.requires_db
    async def test_get_patterns_min_confidence(self, test_db: AsyncSession, sample_pattern_data):
        """Test retrieving patterns with minimum confidence filter."""
        # Store pattern with high confidence
        await store_patterns(test_db, [sample_pattern_data])

        # Get patterns with min confidence
        patterns = await get_patterns(test_db, min_confidence=0.8)
        # Handle both dict and object access (raw SQL returns dicts)
        assert all(
            (p.confidence if hasattr(p, "confidence") else p["confidence"]) >= 0.8 for p in patterns
        )


@pytest.mark.asyncio
async def test_updating_an_existing_pattern_lands(test_db: AsyncSession, sample_pattern_data):
    """Re-storing a known pattern must UPDATE, not silently fail (TAP-6171).

    The raw-SQL path used SQLite's two-argument MAX() — Postgres has no such
    function, so every update of an already-known pattern raised
    UndefinedFunctionError and was swallowed into a warning; only first
    inserts ever landed. GREATEST() is the Postgres spelling.
    """
    first = dict(sample_pattern_data)
    first["confidence"] = 0.4
    assert await store_patterns(test_db, [first]) == 1

    second = dict(sample_pattern_data)
    second["confidence"] = 0.9
    assert await store_patterns(test_db, [second]) == 1  # update counts as stored

    rows = await get_patterns(test_db)
    matching = [r for r in rows if r["device_id"] == sample_pattern_data["device_id"]]
    assert len(matching) == 1  # updated in place, not duplicated
    assert matching[0]["confidence"] == pytest.approx(0.9)  # GREATEST kept the max
