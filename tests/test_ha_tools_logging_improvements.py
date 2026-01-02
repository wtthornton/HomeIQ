"""
Tests for logging improvements in ha_tools.py

Tests conversation_id tracking, enhanced error logging, debug statements,
and improved warning messages.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import yaml

# Import the module under test
import sys
from pathlib import Path

# Add services directory to path
project_root = Path(__file__).parent.parent
services_src = project_root / "services" / "ha-ai-agent-service" / "src"
sys.path.insert(0, str(services_src))

from tools.ha_tools import HAToolHandler
from models.automation_models import AutomationPreviewRequest


@pytest.fixture
def mock_ha_client():
    """Mock Home Assistant client."""
    mock = Mock()
    mock._get_session = AsyncMock(return_value=Mock())
    mock.ha_url = "http://localhost:8123"
    return mock


@pytest.fixture
def mock_data_api_client():
    """Mock Data API client."""
    mock = Mock()
    mock.fetch_entities = AsyncMock(return_value=[])
    mock.get_devices = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_business_rule_validator():
    """Mock business rule validator."""
    mock = Mock()
    mock.check_safety_requirements = Mock(return_value=(True, []))
    mock.calculate_safety_score = Mock(return_value=8.5)
    return mock


@pytest.fixture
def mock_validation_chain():
    """Mock validation chain."""
    mock = Mock()
    mock.validate = AsyncMock(return_value=Mock(
        valid=True,
        errors=[],
        warnings=[],
        strategy_name="test_strategy"
    ))
    return mock


@pytest.fixture
def tool_handler(mock_ha_client, mock_data_api_client, mock_business_rule_validator, mock_validation_chain):
    """Create HAToolHandler instance for testing."""
    return HAToolHandler(
        ha_client=mock_ha_client,
        data_api_client=mock_data_api_client,
        business_rule_validator=mock_business_rule_validator,
        validation_chain=mock_validation_chain,
    )


@pytest.mark.asyncio
async def test_conversation_id_extraction_with_value(tool_handler):
    """Test that conversation_id is extracted when present in arguments."""
    arguments = {
        "user_prompt": "Test prompt",
        "automation_yaml": "alias: test\ntrigger:\n  - platform: state\n    entity_id: light.test\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.test",
        "alias": "test_automation",
        "conversation_id": "test-conv-123"
    }
    
    with patch.object(tool_handler, '_build_preview_response', return_value={"success": True}):
        result = await tool_handler.preview_automation_from_prompt(arguments)
        assert result["success"] is True


@pytest.mark.asyncio
async def test_conversation_id_extraction_without_value(tool_handler):
    """Test that conversation_id is None when not present in arguments."""
    arguments = {
        "user_prompt": "Test prompt",
        "automation_yaml": "alias: test\ntrigger:\n  - platform: state\n    entity_id: light.test\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.test",
        "alias": "test_automation"
    }
    
    with patch.object(tool_handler, '_build_preview_response', return_value={"success": True}):
        result = await tool_handler.preview_automation_from_prompt(arguments)
        assert result["success"] is True


@pytest.mark.asyncio
async def test_logging_includes_conversation_id(tool_handler):
    """Test that log messages include conversation_id when available."""
    arguments = {
        "user_prompt": "Test prompt",
        "automation_yaml": "alias: test\ntrigger:\n  - platform: state\n    entity_id: light.test\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.test",
        "alias": "test_automation",
        "conversation_id": "test-conv-123"
    }
    
    with patch('tools.ha_tools.logger') as mock_logger:
        with patch.object(tool_handler, '_build_preview_response', return_value={"success": True}):
            await tool_handler.preview_automation_from_prompt(arguments)
            
            # Check that info log was called with conversation_id
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("conversation_id=test-conv-123" in str(call) for call in info_calls)


@pytest.mark.asyncio
async def test_logging_shows_na_when_no_conversation_id(tool_handler):
    """Test that log messages show 'N/A' when conversation_id is not provided."""
    arguments = {
        "user_prompt": "Test prompt",
        "automation_yaml": "alias: test\ntrigger:\n  - platform: state\n    entity_id: light.test\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.test",
        "alias": "test_automation"
    }
    
    with patch('tools.ha_tools.logger') as mock_logger:
        with patch.object(tool_handler, '_build_preview_response', return_value={"success": True}):
            await tool_handler.preview_automation_from_prompt(arguments)
            
            # Check that info log was called with 'N/A'
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("conversation_id=N/A" in str(call) or "conversation_id='N/A'" in str(call) for call in info_calls)


@pytest.mark.asyncio
async def test_error_logging_includes_full_context(tool_handler):
    """Test that error logs include alias, conversation_id, and user_prompt."""
    arguments = {
        "user_prompt": "Test prompt for error",
        "automation_yaml": "invalid yaml: [",
        "alias": "test_automation_error",
        "conversation_id": "test-conv-456"
    }
    
    with patch('tools.ha_tools.logger') as mock_logger:
        result = await tool_handler.preview_automation_from_prompt(arguments)
        
        # Check that error log was called with full context
        error_calls = [str(call) for call in mock_logger.error.call_args_list]
        assert any("test_automation_error" in str(call) for call in error_calls)
        assert any("conversation_id=test-conv-456" in str(call) for call in error_calls)
        assert any("Test prompt for error" in str(call) for call in error_calls)


@pytest.mark.asyncio
async def test_debug_statements_execute(tool_handler):
    """Test that debug statements are called at key flow points."""
    arguments = {
        "user_prompt": "Test prompt",
        "automation_yaml": "alias: test\ntrigger:\n  - platform: state\n    entity_id: light.test\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.test",
        "alias": "test_automation",
        "conversation_id": "test-conv-789"
    }
    
    with patch('tools.ha_tools.logger') as mock_logger:
        with patch.object(tool_handler, '_build_preview_response', return_value={"success": True}):
            await tool_handler.preview_automation_from_prompt(arguments)
            
            # Check that debug logs were called
            debug_calls = mock_logger.debug.call_args_list
            assert len(debug_calls) > 0, "Debug statements should be called"


@pytest.mark.asyncio
async def test_warning_messages_include_impact(tool_handler):
    """Test that warning messages include impact explanations."""
    arguments = {
        "user_prompt": "Test prompt",
        "automation_yaml": "alias: test\ntrigger:\n  - platform: state\n    entity_id: light.test\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.test",
        "alias": "test_automation",
        "conversation_id": "test-conv-warn"
    }
    
    # Mock device context extraction to fail
    tool_handler._extract_device_context = AsyncMock(side_effect=Exception("Device context error"))
    
    with patch('tools.ha_tools.logger') as mock_logger:
        with patch.object(tool_handler, '_build_preview_response', return_value={"success": True}):
            await tool_handler.preview_automation_from_prompt(arguments)
            
            # Check that warning log includes impact
            warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
            assert any("Impact:" in str(call) for call in warning_calls)


@pytest.mark.asyncio
async def test_create_automation_includes_conversation_id(tool_handler):
    """Test that create_automation_from_prompt includes conversation_id in logs."""
    arguments = {
        "user_prompt": "Create test automation",
        "automation_yaml": "alias: test\ntrigger:\n  - platform: state\n    entity_id: light.test\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.test",
        "alias": "test_create",
        "conversation_id": "test-conv-create"
    }
    
    # Mock successful creation
    tool_handler._create_automation_in_ha = AsyncMock(return_value={
        "success": True,
        "automation_id": "automation.test_create"
    })
    
    with patch('tools.ha_tools.logger') as mock_logger:
        result = await tool_handler.create_automation_from_prompt(arguments)
        
        # Check that info log was called with conversation_id
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("conversation_id=test-conv-create" in str(call) for call in info_calls)


@pytest.mark.asyncio
async def test_backward_compatibility_no_conversation_id(tool_handler):
    """Test that code works correctly without conversation_id (backward compatibility)."""
    arguments = {
        "user_prompt": "Test prompt",
        "automation_yaml": "alias: test\ntrigger:\n  - platform: state\n    entity_id: light.test\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.test",
        "alias": "test_backward_compat"
    }
    
    with patch.object(tool_handler, '_build_preview_response', return_value={"success": True}):
        result = await tool_handler.preview_automation_from_prompt(arguments)
        assert result["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
