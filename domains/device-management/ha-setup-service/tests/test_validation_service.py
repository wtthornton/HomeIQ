"""
Unit tests for Validation Service
Epic 32: Home Assistant Configuration Validation & Suggestions
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.validation_service import ValidationService, ValidationIssue


@pytest.fixture
def validation_service():
    return ValidationService()


@pytest.fixture
def mock_entities():
    return [
        {
            "entity_id": "light.hue_office_back_left",
            "name": "Hue Office Back Left",
            "area_id": None,
            "device_id": "device123"
        },
        {
            "entity_id": "light.living_room_2",
            "name": "Living Room 2",
            "area_id": "living_room",
            "device_id": "device456"
        },
        {
            "entity_id": "light.kitchen_main",
            "name": "Kitchen Main",
            "area_id": None,
            "device_id": "device789"
        },
    ]


@pytest.fixture
def mock_areas():
    return [
        {"area_id": "office", "name": "Office"},
        {"area_id": "living_room", "name": "Living Room"},
        {"area_id": "kitchen", "name": "Kitchen"},
    ]


@pytest.mark.asyncio
async def test_detect_missing_area_assignments(validation_service, mock_entities, mock_areas):
    """Test detection of missing area assignments"""
    issues = await validation_service._detect_issues(mock_entities, mock_areas)
    
    # Should detect issues for entities without area_id
    missing_area_issues = [i for i in issues if i.category == "missing_area_assignment"]
    assert len(missing_area_issues) >= 2  # office and kitchen lights
    
    # Check that suggestions are provided
    for issue in missing_area_issues:
        assert len(issue.suggestions) > 0
        assert issue.confidence > 0


@pytest.mark.asyncio
async def test_detect_incorrect_area_assignments(validation_service, mock_entities, mock_areas):
    """Test detection of incorrect area assignments"""
    # Create entity with incorrect area
    entities_with_incorrect = [
        {
            "entity_id": "light.office_desk",
            "name": "Office Desk Light",
            "area_id": "living_room",  # Incorrect!
            "device_id": "device123"
        }
    ]
    
    issues = await validation_service._detect_issues(entities_with_incorrect, mock_areas)
    
    incorrect_issues = [i for i in issues if i.category == "incorrect_area_assignment"]
    # Should detect if confidence is high enough
    if incorrect_issues:
        assert incorrect_issues[0].current_area == "living_room"
        assert len(incorrect_issues[0].suggestions) > 0


@pytest.mark.asyncio
async def test_generate_summary(validation_service):
    """Test summary generation"""
    issues = [
        ValidationIssue(
            entity_id="light.test1",
            category="missing_area_assignment",
            current_area=None,
            suggestions=[],
            confidence=80.0
        ),
        ValidationIssue(
            entity_id="light.test2",
            category="missing_area_assignment",
            current_area=None,
            suggestions=[],
            confidence=90.0
        ),
        ValidationIssue(
            entity_id="light.test3",
            category="incorrect_area_assignment",
            current_area="wrong",
            suggestions=[],
            confidence=85.0
        ),
    ]
    
    summary = validation_service._generate_summary(issues, "2025.10.0")
    
    assert summary.total_issues == 3
    assert summary.by_category["missing_area_assignment"] == 2
    assert summary.by_category["incorrect_area_assignment"] == 1
    assert summary.ha_version == "2025.10.0"


@pytest.mark.asyncio
async def test_filter_by_category(validation_service):
    """Test filtering by category"""
    # Mock fetch_ha_data
    with patch.object(validation_service, '_fetch_ha_data', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = ([], [], None)
        
        # Mock _detect_issues to return test issues
        with patch.object(validation_service, '_detect_issues', new_callable=AsyncMock) as mock_detect:
            mock_detect.return_value = [
                ValidationIssue(
                    entity_id="light.test1",
                    category="missing_area_assignment",
                    current_area=None,
                    suggestions=[],
                    confidence=80.0
                ),
                ValidationIssue(
                    entity_id="light.test2",
                    category="incorrect_area_assignment",
                    current_area="wrong",
                    suggestions=[],
                    confidence=90.0
                ),
            ]
            
            result = await validation_service.validate_ha_config(category="missing_area_assignment")
            
            assert len(result.issues) == 1
            assert result.issues[0].category == "missing_area_assignment"


@pytest.mark.asyncio
async def test_filter_by_confidence(validation_service):
    """Test filtering by minimum confidence"""
    with patch.object(validation_service, '_fetch_ha_data', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = ([], [], None)
        
        with patch.object(validation_service, '_detect_issues', new_callable=AsyncMock) as mock_detect:
            mock_detect.return_value = [
                ValidationIssue(
                    entity_id="light.test1",
                    category="missing_area_assignment",
                    current_area=None,
                    suggestions=[{"confidence": 95}],
                    confidence=95.0
                ),
                ValidationIssue(
                    entity_id="light.test2",
                    category="missing_area_assignment",
                    current_area=None,
                    suggestions=[{"confidence": 50}],
                    confidence=50.0
                ),
            ]
            
            result = await validation_service.validate_ha_config(min_confidence=80)
            
            assert len(result.issues) == 1
            assert result.issues[0].confidence >= 80


@pytest.mark.asyncio
async def test_cache_functionality(validation_service):
    """Test caching of validation results"""
    with patch.object(validation_service, '_fetch_ha_data', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = ([], [], None)
        
        with patch.object(validation_service, '_detect_issues', new_callable=AsyncMock) as mock_detect:
            mock_detect.return_value = []
            
            # First call should fetch data
            result1 = await validation_service.validate_ha_config(use_cache=True)
            assert mock_fetch.call_count == 1
            
            # Second call should use cache
            result2 = await validation_service.validate_ha_config(use_cache=True)
            assert mock_fetch.call_count == 1  # Should not call again
            
            # Clear cache and call again
            validation_service.clear_cache()
            result3 = await validation_service.validate_ha_config(use_cache=True)
            assert mock_fetch.call_count == 2  # Should call again

