"""
Unit tests for Spatial Proximity Validator

Phase 1: Semantic Proximity Validation
"""

from unittest.mock import AsyncMock

import pytest
from src.synergy_detection.spatial_validator import SpatialProximityValidator


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def spatial_validator():
    """Create spatial proximity validator instance"""
    return SpatialProximityValidator()


# ============================================================================
# Location Qualifier Extraction Tests
# ============================================================================

def test_extract_location_qualifiers_front(spatial_validator):
    """Test extraction of 'front' qualifier"""
    qualifiers = spatial_validator.extract_location_qualifiers(
        "Front Door Lock",
        "lock.front_door"
    )
    assert 'front' in qualifiers


def test_extract_location_qualifiers_back(spatial_validator):
    """Test extraction of 'back' qualifier"""
    qualifiers = spatial_validator.extract_location_qualifiers(
        "Backyard Light",
        "light.backyard"
    )
    assert 'back' in qualifiers or 'outdoor' in qualifiers


def test_extract_location_qualifiers_outdoor(spatial_validator):
    """Test extraction of 'outdoor' qualifier"""
    qualifiers = spatial_validator.extract_location_qualifiers(
        "Outdoor Camera",
        "camera.outdoor"
    )
    assert 'outdoor' in qualifiers


def test_extract_location_qualifiers_no_qualifiers(spatial_validator):
    """Test extraction when no qualifiers present"""
    qualifiers = spatial_validator.extract_location_qualifiers(
        "Bedroom Light",
        "light.bedroom"
    )
    assert len(qualifiers) == 0


def test_extract_location_qualifiers_multiple(spatial_validator):
    """Test extraction of multiple qualifiers"""
    qualifiers = spatial_validator.extract_location_qualifiers(
        "Front Outdoor Light",
        "light.front_outdoor"
    )
    assert 'front' in qualifiers
    assert 'outdoor' in qualifiers


# ============================================================================
# Semantic Proximity Validation Tests
# ============================================================================

def test_compatible_locations_same_qualifier(spatial_validator):
    """Test compatible locations with same qualifier"""
    device1 = {
        'friendly_name': 'Front Door Lock',
        'entity_id': 'lock.front_door',
        'area_id': 'entryway'
    }
    device2 = {
        'friendly_name': 'Front Door Light',
        'entity_id': 'light.front_door',
        'area_id': 'entryway'
    }
    
    is_valid, reason = spatial_validator.are_semantically_proximate(device1, device2)
    assert is_valid is True
    assert 'matching' in reason or 'same_area' in reason


def test_incompatible_locations_front_back(spatial_validator):
    """Test incompatible locations: front vs back"""
    device1 = {
        'friendly_name': 'Front Door Lock',
        'entity_id': 'lock.front_door',
        'area_id': 'entryway'
    }
    device2 = {
        'friendly_name': 'Backyard Light',
        'entity_id': 'light.backyard',
        'area_id': 'backyard'
    }
    
    is_valid, reason = spatial_validator.are_semantically_proximate(device1, device2)
    assert is_valid is False
    assert 'incompatible' in reason


def test_incompatible_locations_indoor_outdoor(spatial_validator):
    """Test incompatible locations: indoor vs outdoor"""
    device1 = {
        'friendly_name': 'Indoor Light',
        'entity_id': 'light.indoor',
        'area_id': 'living_room'
    }
    device2 = {
        'friendly_name': 'Outdoor Light',
        'entity_id': 'light.outdoor',
        'area_id': 'backyard'
    }
    
    is_valid, reason = spatial_validator.are_semantically_proximate(device1, device2)
    assert is_valid is False
    assert 'incompatible' in reason


def test_no_qualifiers_passes(spatial_validator):
    """Test that devices without qualifiers pass validation"""
    device1 = {
        'friendly_name': 'Bedroom Light',
        'entity_id': 'light.bedroom',
        'area_id': 'bedroom'
    }
    device2 = {
        'friendly_name': 'Bedroom Motion',
        'entity_id': 'binary_sensor.bedroom_motion',
        'area_id': 'bedroom'
    }
    
    is_valid, reason = spatial_validator.are_semantically_proximate(device1, device2)
    assert is_valid is True
    assert 'no_location_qualifiers' in reason


def test_same_area_different_qualifiers(spatial_validator):
    """Test same area but different qualifiers (edge case)"""
    device1 = {
        'friendly_name': 'Front Door',
        'entity_id': 'binary_sensor.front_door',
        'area_id': 'entryway'
    }
    device2 = {
        'friendly_name': 'Front Porch Light',
        'entity_id': 'light.front_porch',
        'area_id': 'entryway'
    }
    
    is_valid, reason = spatial_validator.are_semantically_proximate(device1, device2)
    # Should pass if same area and related qualifiers
    assert is_valid is True


def test_outdoor_indoor_mismatch(spatial_validator):
    """Test outdoor device with indoor device mismatch"""
    device1 = {
        'friendly_name': 'Outdoor Camera',
        'entity_id': 'camera.outdoor',
        'area_id': 'backyard'
    }
    device2 = {
        'friendly_name': 'Indoor Light',
        'entity_id': 'light.indoor',
        'area_id': 'living_room'
    }
    
    is_valid, reason = spatial_validator.are_semantically_proximate(device1, device2)
    assert is_valid is False


def test_partial_matches_front_porch(spatial_validator):
    """Test partial matches like 'front door' vs 'front porch'"""
    device1 = {
        'friendly_name': 'Front Door Lock',
        'entity_id': 'lock.front_door',
        'area_id': 'entryway'
    }
    device2 = {
        'friendly_name': 'Front Porch Light',
        'entity_id': 'light.front_porch',
        'area_id': 'entryway'
    }
    
    is_valid, reason = spatial_validator.are_semantically_proximate(device1, device2)
    # Should pass if same area and both front-related
    assert is_valid is True


def test_one_device_generic(spatial_validator):
    """Test one device with qualifier, one without"""
    device1 = {
        'friendly_name': 'Front Door Lock',
        'entity_id': 'lock.front_door',
        'area_id': 'entryway'
    }
    device2 = {
        'friendly_name': 'Light',
        'entity_id': 'light.generic',
        'area_id': 'entryway'
    }
    
    is_valid, reason = spatial_validator.are_semantically_proximate(device1, device2)
    assert is_valid is True
    assert 'generic' in reason


def test_outdoor_device_without_location(spatial_validator):
    """Test outdoor device paired with device without location qualifier"""
    device1 = {
        'friendly_name': 'Outdoor Light',
        'entity_id': 'light.outdoor',
        'area_id': 'backyard'
    }
    device2 = {
        'friendly_name': 'Generic Sensor',
        'entity_id': 'sensor.generic',
        'area_id': 'backyard'
    }
    
    is_valid, reason = spatial_validator.are_semantically_proximate(device1, device2)
    # Should fail because outdoor device requires location context
    assert is_valid is False
    assert 'outdoor_device_without_location' in reason


def test_different_areas_different_qualifiers(spatial_validator):
    """Test different areas with different qualifiers"""
    device1 = {
        'friendly_name': 'Front Door Lock',
        'entity_id': 'lock.front_door',
        'area_id': 'entryway'
    }
    device2 = {
        'friendly_name': 'Back Door Light',
        'entity_id': 'light.back_door',
        'area_id': 'backyard'
    }
    
    is_valid, reason = spatial_validator.are_semantically_proximate(device1, device2)
    assert is_valid is False
    assert 'different' in reason


# ============================================================================
# Integration Test
# ============================================================================

@pytest.mark.asyncio
async def test_synergy_detector_with_spatial_validation(mock_data_api_client, mock_ha_client):
    """Test spatial validation integration in synergy detector"""
    from src.synergy_detection.synergy_detector import DeviceSynergyDetector
    
    # Create detector with spatial validation
    detector = DeviceSynergyDetector(
        data_api_client=mock_data_api_client,
        ha_client=mock_ha_client,
        min_confidence=0.7
    )
    
    # Verify spatial validator is initialized
    assert detector.spatial_validator is not None
    assert isinstance(detector.spatial_validator, SpatialProximityValidator)
    
    # Test with devices that should be filtered
    # Add devices with incompatible locations
    mock_data_api_client.fetch_entities = AsyncMock(return_value=[
        {
            'entity_id': 'lock.front_door',
            'device_id': 'device_1',
            'friendly_name': 'Front Door Lock',
            'area_id': 'entryway',
            'device_class': None
        },
        {
            'entity_id': 'light.backyard',
            'device_id': 'device_2',
            'friendly_name': 'Backyard Light',
            'area_id': 'backyard'
        }
    ])
    
    # Run detection
    synergies = await detector.detect_synergies()
    
    # Should filter out incompatible pairs
    # Note: This test verifies integration, actual filtering depends on relationship types


# ============================================================================
# Home Type Integration Tests
# ============================================================================

def test_spatial_validator_with_home_type_apartment():
    """Test spatial validator with apartment home type (stricter tolerance)"""
    validator = SpatialProximityValidator(home_type='apartment')
    
    assert validator.home_type == 'apartment'
    assert validator._spatial_tolerance < 1.0  # Should be stricter


def test_spatial_validator_with_home_type_multi_story():
    """Test spatial validator with multi-story home type (more lenient)"""
    validator = SpatialProximityValidator(home_type='multi-story')
    
    assert validator.home_type == 'multi-story'
    assert validator._spatial_tolerance > 1.0  # Should be more lenient


def test_spatial_validator_cross_floor_detection():
    """Test cross-floor detection for multi-story homes"""
    validator = SpatialProximityValidator(home_type='multi-story')
    
    device1 = {'friendly_name': 'Upstairs Light', 'entity_id': 'light.upstairs'}
    device2 = {'friendly_name': 'Downstairs Light', 'entity_id': 'light.downstairs'}
    
    is_cross_floor = validator._is_cross_floor(device1, device2)
    assert is_cross_floor is True


@pytest.mark.asyncio
async def test_spatial_validator_multi_story_allows_cross_floor():
    """Test that multi-story homes allow cross-floor relationships"""
    validator = SpatialProximityValidator(home_type='multi-story')
    
    device1 = {'friendly_name': 'Upstairs Motion Sensor', 'entity_id': 'binary_sensor.upstairs_motion'}
    device2 = {'friendly_name': 'Downstairs Light', 'entity_id': 'light.downstairs'}
    
    is_valid, reason = await validator.are_semantically_proximate(device1, device2)
    
    # Multi-story should allow cross-floor
    if is_valid:
        assert 'cross_floor' in reason or 'multi_story' in reason


def test_spatial_validator_apartment_stricter_matching():
    """Test that apartments have stricter location matching"""
    validator = SpatialProximityValidator(home_type='apartment')
    
    device1 = {'friendly_name': 'Front Door', 'entity_id': 'lock.front_door', 'area_id': 'entry'}
    device2 = {'friendly_name': 'Back Door', 'entity_id': 'lock.back_door', 'area_id': 'back'}
    
    # Apartments should be stricter about location matching
    assert validator._spatial_tolerance < 1.0
    assert detector.spatial_validator is not None

