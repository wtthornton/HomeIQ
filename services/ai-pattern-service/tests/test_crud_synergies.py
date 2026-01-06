"""
Unit tests for Synergy CRUD operations

Epic 39, Story 39.8: Pattern Service Testing & Validation
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.synergies import store_synergy_opportunities, get_synergy_opportunities


class TestSynergyCRUD:
    """Test suite for synergy CRUD operations."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.requires_db
    async def test_store_synergy_opportunities(
        self, test_db: AsyncSession, sample_synergy_data
    ):
        """Test storing synergy opportunities."""
        synergies = [sample_synergy_data]
        stored_count = await store_synergy_opportunities(test_db, synergies)
        
        assert stored_count >= 1
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.requires_db
    async def test_store_empty_synergies(
        self, test_db: AsyncSession
    ):
        """Test storing empty synergy list."""
        stored_count = await store_synergy_opportunities(test_db, [])
        assert stored_count == 0
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.requires_db
    async def test_store_multiple_synergies(
        self, test_db: AsyncSession, sample_synergy_data
    ):
        """Test storing multiple synergies."""
        synergies = [
            sample_synergy_data,
            {
                **sample_synergy_data,
                "synergy_id": "test-synergy-456",
                "devices": ["binary_sensor.motion_kitchen", "light.kitchen"]
            }
        ]
        stored_count = await store_synergy_opportunities(test_db, synergies)
        assert stored_count >= 2
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.requires_db
    async def test_get_synergy_opportunities(
        self, test_db: AsyncSession, sample_synergy_data
    ):
        """Test retrieving synergy opportunities."""
        # Store a synergy first
        await store_synergy_opportunities(test_db, [sample_synergy_data])
        
        # Retrieve synergies
        synergies = await get_synergy_opportunities(test_db)
        assert len(synergies) >= 1
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.requires_db
    async def test_get_synergies_filtered_by_type(
        self, test_db: AsyncSession, sample_synergy_data
    ):
        """Test retrieving synergies filtered by type."""
        # Store synergies
        await store_synergy_opportunities(test_db, [sample_synergy_data])
        
        # Get synergies by type
        synergies = await get_synergy_opportunities(
            test_db,
            synergy_type="device_pair"
        )
        assert len(synergies) >= 1
        # Handle both dict and object access (raw SQL returns dicts)
        assert all(
            (s.synergy_type if hasattr(s, 'synergy_type') else s['synergy_type']) == "device_pair"
            for s in synergies
        )
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.requires_db
    async def test_get_synergies_min_confidence(
        self, test_db: AsyncSession, sample_synergy_data
    ):
        """Test retrieving synergies with minimum confidence filter."""
        # Store synergy
        await store_synergy_opportunities(test_db, [sample_synergy_data])
        
        # Get synergies with min confidence
        synergies = await get_synergy_opportunities(test_db, min_confidence=0.75)
        # Handle both dict and object access (raw SQL returns dicts)
        assert all(
            (s.confidence if hasattr(s, 'confidence') else s['confidence']) >= 0.75
            for s in synergies
        )

