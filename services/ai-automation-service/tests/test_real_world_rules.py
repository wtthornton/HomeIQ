"""
Unit tests for Real-World Rules

Phase 2: Real-World Rules Database
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.synergy_detection.real_world_rules import RealWorldRulesValidator, REAL_WORLD_DEVICE_RULES
from src.synergy_detection.rules_manager import RulesManager
from src.database.models import HomeLayoutRule


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def real_world_validator():
    """Create real-world rules validator instance"""
    return RealWorldRulesValidator()


@pytest.fixture
def mock_db_session():
    """Create mock database session"""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def rules_manager(mock_db_session):
    """Create rules manager instance"""
    return RulesManager(mock_db_session)


# ============================================================================
# Real-World Rules Validator Tests
# ============================================================================

def test_door_lock_rules_front_door_compatible(real_world_validator):
    """Test front door lock with compatible light"""
    device1 = {
        'friendly_name': 'Front Door Lock',
        'entity_id': 'lock.front_door'
    }
    device2 = {
        'friendly_name': 'Front Door Light',
        'entity_id': 'light.front_door'
    }
    
    is_valid, reason = real_world_validator.validate_device_pair(device1, device2)
    assert is_valid is True
    assert reason is not None


def test_door_lock_rules_front_door_incompatible(real_world_validator):
    """Test front door lock with incompatible backyard light"""
    device1 = {
        'friendly_name': 'Front Door Lock',
        'entity_id': 'lock.front_door'
    }
    device2 = {
        'friendly_name': 'Backyard Light',
        'entity_id': 'light.backyard'
    }
    
    is_valid, reason = real_world_validator.validate_device_pair(device1, device2)
    assert is_valid is False
    assert 'incompatible' in reason


def test_motion_sensor_rules_kitchen_compatible(real_world_validator):
    """Test kitchen motion with compatible kitchen light"""
    device1 = {
        'friendly_name': 'Kitchen Motion',
        'entity_id': 'binary_sensor.kitchen_motion'
    }
    device2 = {
        'friendly_name': 'Kitchen Light',
        'entity_id': 'light.kitchen'
    }
    
    is_valid, reason = real_world_validator.validate_device_pair(device1, device2)
    assert is_valid is True


def test_motion_sensor_rules_outdoor_incompatible(real_world_validator):
    """Test outdoor motion with incompatible indoor light"""
    device1 = {
        'friendly_name': 'Outdoor Motion',
        'entity_id': 'binary_sensor.outdoor_motion'
    }
    device2 = {
        'friendly_name': 'Bedroom Light',
        'entity_id': 'light.bedroom'
    }
    
    is_valid, reason = real_world_validator.validate_device_pair(device1, device2)
    assert is_valid is False
    assert 'incompatible' in reason


def test_get_compatible_devices(real_world_validator):
    """Test getting compatible devices for a device"""
    device = {
        'friendly_name': 'Front Door Lock',
        'entity_id': 'lock.front_door'
    }
    
    compatible = real_world_validator.get_compatible_devices(device)
    assert len(compatible) > 0
    assert any('front' in c or 'entryway' in c for c in compatible)


def test_get_incompatible_devices(real_world_validator):
    """Test getting incompatible devices for a device"""
    device = {
        'friendly_name': 'Front Door Lock',
        'entity_id': 'lock.front_door'
    }
    
    incompatible = real_world_validator.get_incompatible_devices(device)
    assert len(incompatible) > 0
    assert any('backyard' in c or 'back' in c for c in incompatible)


# ============================================================================
# Rules Manager Tests
# ============================================================================

@pytest.mark.asyncio
async def test_load_default_rules(rules_manager):
    """Test loading default rules"""
    rules = await rules_manager.load_default_rules()
    
    assert len(rules) > 0
    assert all(r['home_id'] == 'default' for r in rules)
    assert all(r['source'] == 'system_default' for r in rules)


@pytest.mark.asyncio
async def test_load_home_rules(rules_manager, mock_db_session):
    """Test loading home-specific rules"""
    # Mock database query result
    mock_rule = HomeLayoutRule(
        id=1,
        home_id='test_home',
        rule_type='exclusion',
        device1_pattern='front_door*',
        device2_pattern='backyard*',
        relationship='incompatible',
        confidence=1.0,
        source='user_defined'
    )
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_rule]
    mock_db_session.execute.return_value = mock_result
    
    rules = await rules_manager.load_home_rules('test_home')
    
    assert len(rules) == 1
    assert rules[0].home_id == 'test_home'


@pytest.mark.asyncio
async def test_add_home_rule(rules_manager, mock_db_session):
    """Test adding a new home rule"""
    rule = await rules_manager.add_home_rule(
        home_id='test_home',
        rule_type='exclusion',
        device1_pattern='front_door*',
        device2_pattern='backyard*',
        relationship='incompatible',
        confidence=1.0,
        source='user_defined'
    )
    
    assert rule is not None
    assert rule.home_id == 'test_home'
    assert rule.relationship == 'incompatible'
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_home_rule(rules_manager, mock_db_session):
    """Test updating an existing home rule"""
    # Mock existing rule
    mock_rule = HomeLayoutRule(
        id=1,
        home_id='test_home',
        rule_type='exclusion',
        device1_pattern='front_door*',
        device2_pattern='backyard*',
        relationship='incompatible',
        confidence=1.0
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_rule
    mock_db_session.execute.return_value = mock_result
    
    updated = await rules_manager.update_home_rule(
        rule_id=1,
        confidence=0.9
    )
    
    assert updated is not None
    assert updated.confidence == 0.9
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_home_rule(rules_manager, mock_db_session):
    """Test deleting a home rule"""
    # Mock existing rule
    mock_rule = HomeLayoutRule(id=1)
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_rule
    mock_db_session.execute.return_value = mock_result
    
    deleted = await rules_manager.delete_home_rule(rule_id=1)
    
    assert deleted is True
    mock_db_session.delete.assert_called_once_with(mock_rule)
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_learn_from_feedback(rules_manager, mock_db_session):
    """Test learning rule from user feedback"""
    device1 = {
        'friendly_name': 'Front Door Lock',
        'entity_id': 'lock.front_door'
    }
    device2 = {
        'friendly_name': 'Backyard Light',
        'entity_id': 'light.backyard'
    }
    
    # Mock no existing rule
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result
    
    # Mock add_home_rule
    mock_rule = HomeLayoutRule(id=1)
    rules_manager.add_home_rule = AsyncMock(return_value=mock_rule)
    
    learned = await rules_manager.learn_from_feedback(
        home_id='test_home',
        device1=device1,
        device2=device2,
        user_rejected=True
    )
    
    assert learned is not None
    rules_manager.add_home_rule.assert_called_once()
    call_kwargs = rules_manager.add_home_rule.call_args[1]
    assert call_kwargs['relationship'] == 'incompatible'
    assert call_kwargs['source'] == 'learned'


@pytest.mark.asyncio
async def test_learn_from_feedback_no_rejection(rules_manager):
    """Test that learning doesn't happen if user didn't reject"""
    device1 = {'friendly_name': 'Device 1'}
    device2 = {'friendly_name': 'Device 2'}
    
    learned = await rules_manager.learn_from_feedback(
        home_id='test_home',
        device1=device1,
        device2=device2,
        user_rejected=False
    )
    
    assert learned is None


# ============================================================================
# Integration Test
# ============================================================================

@pytest.mark.asyncio
async def test_spatial_validator_with_rules(mock_db_session):
    """Test spatial validator integration with rules"""
    from src.synergy_detection.spatial_validator import SpatialProximityValidator
    
    # Create validator with database session
    validator = SpatialProximityValidator(db_session=mock_db_session, home_id='test_home')
    
    # Mock home rules
    mock_rule = HomeLayoutRule(
        id=1,
        home_id='test_home',
        rule_type='exclusion',
        device1_pattern='front_door',
        device2_pattern='backyard',
        relationship='incompatible',
        confidence=1.0
    )
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_rule]
    mock_db_session.execute.return_value = mock_result
    
    device1 = {
        'friendly_name': 'Front Door Lock',
        'entity_id': 'lock.front_door'
    }
    device2 = {
        'friendly_name': 'Backyard Light',
        'entity_id': 'light.backyard'
    }
    
    # Should use home rule (highest priority)
    is_valid, reason = await validator.are_semantically_proximate(device1, device2)
    
    # Should be invalid due to home rule
    assert is_valid is False
    assert 'home_rule' in reason

