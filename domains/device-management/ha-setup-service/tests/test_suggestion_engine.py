"""
Unit tests for Suggestion Engine
Epic 32: Home Assistant Configuration Validation & Suggestions
"""

import pytest
from src.suggestion_engine import NAME_DERIVED_CONFIDENCE_CAP, SuggestionEngine


@pytest.fixture
def suggestion_engine():
    return SuggestionEngine()


@pytest.fixture
def mock_areas():
    return [
        {"area_id": "office", "name": "Office"},
        {"area_id": "living_room", "name": "Living Room"},
        {"area_id": "kitchen", "name": "Kitchen"},
        {"area_id": "bedroom", "name": "Bedroom"},
    ]


@pytest.mark.asyncio
async def test_exact_match_in_entity_id(suggestion_engine, mock_areas):
    """An exact string match still ranks first — and still confers no authority."""
    suggestions = await suggestion_engine.suggest_area(
        entity_id="light.hue_office_back_left", entity_name="Hue Office Back Left", areas=mock_areas
    )

    assert len(suggestions) > 0
    assert suggestions[0]["area_id"] == "office"
    # Ranked first, because ordering candidates for a person is this engine's job.
    assert suggestions[0]["confidence"] == pytest.approx(NAME_DERIVED_CONFIDENCE_CAP)
    # And capped, because every signal it has is a name.
    assert suggestions[0]["confidence"] <= NAME_DERIVED_CONFIDENCE_CAP
    assert suggestions[0]["basis"] == "name_only"
    assert suggestions[0]["actionable"] is False
    assert "name only" in suggestions[0]["reasoning"].lower()


@pytest.mark.asyncio
async def test_exact_match_in_entity_name(suggestion_engine, mock_areas):
    """Test exact match in entity_name (95% confidence)"""
    suggestions = await suggestion_engine.suggest_area(
        entity_id="light.hue_desk", entity_name="Office Desk Light", areas=mock_areas
    )

    assert len(suggestions) > 0
    assert suggestions[0]["area_id"] == "office"
    assert suggestions[0]["confidence"] <= NAME_DERIVED_CONFIDENCE_CAP


@pytest.mark.asyncio
async def test_partial_match(suggestion_engine, mock_areas):
    """A partial match still surfaces the candidate, still under the cap."""
    suggestions = await suggestion_engine.suggest_area(
        entity_id="light.lr_back_ceiling", entity_name="Living Room Back Ceiling", areas=mock_areas
    )

    assert len(suggestions) > 0
    # Should match living_room
    office_suggestion = next((s for s in suggestions if s["area_id"] == "living_room"), None)
    assert office_suggestion is not None
    assert 0 < office_suggestion["confidence"] <= NAME_DERIVED_CONFIDENCE_CAP
    assert office_suggestion["basis"] == "name_only"


@pytest.mark.asyncio
async def test_keyword_match(suggestion_engine, mock_areas):
    """A keyword match ranks lowest and still confers nothing."""
    suggestions = await suggestion_engine.suggest_area(
        entity_id="light.workspace_main", entity_name="Workspace Main Light", areas=mock_areas
    )

    # "workspace" keyword should match "office" area
    office_suggestion = next((s for s in suggestions if s["area_id"] == "office"), None)
    assert office_suggestion is not None
    assert 0 < office_suggestion["confidence"] <= NAME_DERIVED_CONFIDENCE_CAP
    assert office_suggestion["actionable"] is False


@pytest.mark.asyncio
async def test_no_matches(suggestion_engine, mock_areas):
    """Test entity with no area matches"""
    suggestions = await suggestion_engine.suggest_area(
        entity_id="light.random_light_123", entity_name="Random Light", areas=mock_areas
    )

    # Should return empty or low confidence suggestions
    if suggestions:
        assert all(s["confidence"] < 40 for s in suggestions)


@pytest.mark.asyncio
async def test_multiple_suggestions_sorted(suggestion_engine, mock_areas):
    """Test that suggestions are sorted by confidence"""
    suggestions = await suggestion_engine.suggest_area(
        entity_id="light.office_living_room",
        entity_name="Office Living Room Light",
        areas=mock_areas,
    )

    if len(suggestions) > 1:
        confidences = [s["confidence"] for s in suggestions]
        assert confidences == sorted(confidences, reverse=True)


@pytest.mark.asyncio
async def test_top_3_suggestions_limit(suggestion_engine, mock_areas):
    """Test that only top 3 suggestions are returned"""
    # Add more areas to test limit
    extended_areas = mock_areas + [
        {"area_id": "bathroom", "name": "Bathroom"},
        {"area_id": "garage", "name": "Garage"},
        {"area_id": "basement", "name": "Basement"},
    ]

    suggestions = await suggestion_engine.suggest_area(
        entity_id="light.office_main", entity_name="Office Main", areas=extended_areas
    )

    assert len(suggestions) <= 3


@pytest.mark.asyncio
async def test_keyword_extraction(suggestion_engine):
    """Test keyword extraction from entity identifiers"""
    keywords = suggestion_engine._extract_keywords(
        "light.hue_office_back_left", "Hue Office Back Left"
    )

    assert "office" in keywords
    assert "back" in keywords
    assert "left" in keywords
    assert "hue" in keywords


@pytest.mark.asyncio
async def test_confidence_calculation(suggestion_engine):
    """Test confidence calculation logic"""
    confidence, reasoning = suggestion_engine._calculate_confidence(
        entity_id="light.office_desk",
        entity_name="Office Desk",
        entity_keywords={"office", "desk"},
        area_id="office",
        area_name="office",
    )

    assert confidence <= NAME_DERIVED_CONFIDENCE_CAP
    assert "name only" in reasoning.lower()


@pytest.mark.asyncio
async def test_no_name_match_can_ever_reach_a_system_action_threshold(
    suggestion_engine, mock_areas
):
    """The rule, pinned: a name may rank options, never clear a system gate.

    `validation_service` used to raise `incorrect_area_assignment` when a
    name-derived suggestion scored >= 80, and that category feeds a path which
    writes an area to Home Assistant. Two identically-modelled dimmers on this
    instance carried swapped friendly names, so that gate could relocate a device
    on the strength of a string.

    This asserts the cap holds for the most favourable input the engine can be
    given — the area id, the area name, and a keyword all present in both the
    entity_id and the friendly name. If someone raises a confidence constant,
    this fails before the defect ships.
    """
    system_action_threshold = 80.0

    suggestions = await suggestion_engine.suggest_area(
        entity_id="light.office_office_workspace_desk",
        entity_name="Office Office Workspace Desk",
        areas=mock_areas,
    )

    assert suggestions, "the engine should still offer candidates for a person"
    for suggestion in suggestions:
        assert suggestion["confidence"] < system_action_threshold
        assert suggestion["confidence"] <= NAME_DERIVED_CONFIDENCE_CAP
        assert suggestion["basis"] == "name_only"
        assert suggestion["actionable"] is False


@pytest.mark.asyncio
async def test_ranking_is_preserved_so_the_engine_stays_useful(
    suggestion_engine, mock_areas
):
    """Capping confidence must not flatten the ordering — that is the product."""
    exact = await suggestion_engine.suggest_area(
        entity_id="light.office_ceiling", entity_name="Office Ceiling", areas=mock_areas
    )
    keyword = await suggestion_engine.suggest_area(
        entity_id="light.workspace_main", entity_name="Workspace Main Light", areas=mock_areas
    )

    best_exact = next(s for s in exact if s["area_id"] == "office")
    best_keyword = next(s for s in keyword if s["area_id"] == "office")
    assert best_exact["confidence"] > best_keyword["confidence"]
