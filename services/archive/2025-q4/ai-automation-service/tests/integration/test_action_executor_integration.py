"""
Integration tests for ActionExecutor

Tests end-to-end action execution with real or mocked Home Assistant.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from services.automation.action_executor import ActionExecutor
from services.automation.action_parser import ActionParser
from services.clients.ha_client import HomeAssistantClient


@pytest.fixture
def mock_ha_client():
    """Mock Home Assistant client"""
    client = MagicMock(spec=HomeAssistantClient)
    client._get_session = MagicMock()
    session = AsyncMock()
    client._get_session.return_value = session

    # Mock successful service call
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value=[{"entity_id": "light.office", "state": "on"}])
    session.post = AsyncMock(return_value=response)

    return client


@pytest.fixture
async def action_executor(mock_ha_client):
    """Create ActionExecutor instance"""
    executor = ActionExecutor(
        ha_client=mock_ha_client,
        num_workers=2,
        max_retries=3,
        retry_delay=0.1  # Short delay for tests
    )
    await executor.start()
    yield executor
    await executor.shutdown()


@pytest.mark.asyncio
async def test_execute_simple_action(action_executor, mock_ha_client):
    """Test executing a simple service call action"""
    yaml_str = """
actions:
  - action: light.turn_on
    target:
      entity_id: light.office
    data:
      brightness_pct: 100
"""

    parser = ActionParser()
    actions = parser.parse_actions_from_yaml(yaml_str)

    context = {"test": True}
    result = await action_executor.execute_actions(actions, context)

    assert result.summary.total_actions == 1
    assert result.summary.successful_actions == 1
    assert result.summary.failed_actions == 0

    # Verify service was called
    mock_ha_client._get_session.return_value.post.assert_called_once()


@pytest.mark.asyncio
async def test_execute_multiple_actions_sequence(action_executor, mock_ha_client):
    """Test executing multiple actions in sequence"""
    yaml_str = """
actions:
  - action: light.turn_on
    target:
      entity_id: light.office
  - delay: '00:00:01'
  - action: light.turn_off
    target:
      entity_id: light.office
"""

    parser = ActionParser()
    actions = parser.parse_actions_from_yaml(yaml_str)

    context = {"test": True}
    result = await action_executor.execute_actions(actions, context)

    assert result.summary.total_actions == 3  # 2 actions + 1 delay
    assert result.summary.successful_actions == 3
    assert result.summary.failed_actions == 0


@pytest.mark.asyncio
async def test_retry_on_failure(action_executor, mock_ha_client):
    """Test retry logic on service call failure"""
    # Mock first two calls to fail, third to succeed
    response_fail = AsyncMock()
    response_fail.status = 500
    response_fail.json = AsyncMock(return_value={"error": "Internal server error"})

    response_success = AsyncMock()
    response_success.status = 200
    response_success.json = AsyncMock(return_value=[{"entity_id": "light.office", "state": "on"}])

    mock_ha_client._get_session.return_value.post = AsyncMock(
        side_effect=[response_fail, response_fail, response_success]
    )

    yaml_str = """
actions:
  - action: light.turn_on
    target:
      entity_id: light.office
"""

    parser = ActionParser()
    actions = parser.parse_actions_from_yaml(yaml_str)

    context = {"test": True}
    result = await action_executor.execute_actions(actions, context)

    # Should succeed after retries
    assert result.summary.total_actions == 1
    assert result.summary.successful_actions == 1
    assert result.summary.failed_actions == 0

    # Should have been called 3 times (initial + 2 retries)
    assert mock_ha_client._get_session.return_value.post.call_count == 3


@pytest.mark.asyncio
async def test_failure_after_max_retries(action_executor, mock_ha_client):
    """Test that action fails after max retries"""
    # Mock all calls to fail
    response_fail = AsyncMock()
    response_fail.status = 500
    response_fail.json = AsyncMock(return_value={"error": "Internal server error"})

    mock_ha_client._get_session.return_value.post = AsyncMock(return_value=response_fail)

    yaml_str = """
actions:
  - action: light.turn_on
    target:
      entity_id: light.office
"""

    parser = ActionParser()
    actions = parser.parse_actions_from_yaml(yaml_str)

    context = {"test": True}
    result = await action_executor.execute_actions(actions, context)

    # Should fail after all retries
    assert result.summary.total_actions == 1
    assert result.summary.successful_actions == 0
    assert result.summary.failed_actions == 1

    # Should have been called max_retries + 1 times (initial + retries)
    assert mock_ha_client._get_session.return_value.post.call_count == 4  # 1 initial + 3 retries


@pytest.mark.asyncio
async def test_parallel_execution(action_executor, mock_ha_client):
    """Test parallel action execution"""
    yaml_str = """
actions:
  - parallel:
      - action: light.turn_on
        target:
          entity_id: light.office
      - action: light.turn_on
        target:
          entity_id: light.kitchen
"""

    parser = ActionParser()
    actions = parser.parse_actions_from_yaml(yaml_str)

    context = {"test": True}
    result = await action_executor.execute_actions(actions, context)

    assert result.summary.total_actions >= 2
    assert result.summary.successful_actions >= 2


@pytest.mark.asyncio
async def test_execution_context_tracking(action_executor, mock_ha_client):
    """Test that execution context is properly tracked"""
    yaml_str = """
actions:
  - action: light.turn_on
    target:
      entity_id: light.office
"""

    parser = ActionParser()
    actions = parser.parse_actions_from_yaml(yaml_str)

    context = {
        "query_id": "test-query-123",
        "suggestion_id": "test-suggestion-456"
    }
    result = await action_executor.execute_actions(actions, context)

    assert result.summary.total_actions == 1
    # Verify context is preserved in results
    assert len(result.results) == 1
    assert result.results[0].context == context

