"""
Unit tests for HomeGenerator wrapper.
"""

import pytest

from src.data_generation.home_generator import HomeGenerator


@pytest.mark.asyncio
async def test_generate_home():
    """Test single home generation."""
    generator = HomeGenerator()
    
    home = await generator.generate_home(
        home_type="single_family_house",
        event_days=7,
        home_index=0
    )
    
    assert "home_id" in home
    assert "home_type" in home
    assert home["home_type"] == "single_family_house"
    assert "devices" in home or "entities" in home
    assert "events" in home or "event_history" in home


@pytest.mark.asyncio
async def test_generate_homes():
    """Test multiple home generation."""
    generator = HomeGenerator()
    
    homes = await generator.generate_homes(
        home_count=3,
        home_types=["apartment", "condo"],
        event_days=7
    )
    
    assert len(homes) == 3
    assert all("home_id" in h for h in homes)
    assert all("home_type" in h for h in homes)


@pytest.mark.asyncio
async def test_home_types():
    """Test different home types."""
    generator = HomeGenerator()
    
    home_types = ["single_family_house", "apartment", "cottage"]
    
    for home_type in home_types:
        home = await generator.generate_home(
            home_type=home_type,
            event_days=7,
            home_index=0
        )
        assert home["home_type"] == home_type

