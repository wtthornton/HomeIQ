"""Unit tests for EventHandlerMixin house status aggregation.

Focus: aggregator/publisher failures must surface to operators. A previous
version logged them at DEBUG, so with production log levels at INFO/WARNING
house status could silently stop updating with no operator-facing signal.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

MODULE = "src._event_handlers"

STATE_CHANGED: dict[str, Any] = {
    "event_type": "state_changed",
    "entity_id": "sensor.living_room_temp",
    "new_state": {"state": "21.5"},
    "old_state": {"state": "21.0"},
}


def make_host(aggregator: Any = None, publisher: Any = None) -> Any:
    """Build a minimal host exposing only what _feed_house_status reads."""
    from src._event_handlers import EventHandlerMixin

    class _Host(EventHandlerMixin):
        pass

    host = _Host()
    host.house_status_aggregator = aggregator
    host.house_status_publisher = publisher
    return host


async def test_aggregator_failure_is_logged_as_error() -> None:
    """An aggregator exception must go to the error path, not a DEBUG swallow."""
    aggregator = MagicMock()
    aggregator.process_state_change = AsyncMock(side_effect=ValueError("bad entity data"))
    host = make_host(aggregator=aggregator)

    with patch(f"{MODULE}.log_error_with_context") as mock_log_error:
        await host._feed_house_status(dict(STATE_CHANGED))

    mock_log_error.assert_called_once()
    args, kwargs = mock_log_error.call_args
    assert isinstance(args[2], ValueError)
    assert kwargs["operation"] == "house_status_aggregation"
    assert kwargs["entity_id"] == "sensor.living_room_temp"


async def test_publisher_failure_is_logged_as_error() -> None:
    """A broadcast failure must surface too, not just aggregation failure."""
    aggregator = MagicMock()
    aggregator.process_state_change = AsyncMock(return_value={"changed": True})
    publisher = MagicMock()
    publisher.broadcast = AsyncMock(side_effect=RuntimeError("publisher down"))
    host = make_host(aggregator=aggregator, publisher=publisher)

    with patch(f"{MODULE}.log_error_with_context") as mock_log_error:
        await host._feed_house_status(dict(STATE_CHANGED))

    mock_log_error.assert_called_once()
    assert isinstance(mock_log_error.call_args[0][2], RuntimeError)


async def test_aggregator_failure_does_not_propagate() -> None:
    """House status failures stay isolated from the main event path."""
    aggregator = MagicMock()
    aggregator.process_state_change = AsyncMock(side_effect=ValueError("boom"))
    host = make_host(aggregator=aggregator)

    await host._feed_house_status(dict(STATE_CHANGED))


async def test_delta_is_broadcast_on_success() -> None:
    """The happy path still forwards the delta to the publisher."""
    delta = {"entity_id": "sensor.living_room_temp", "changed": True}
    aggregator = MagicMock()
    aggregator.process_state_change = AsyncMock(return_value=delta)
    publisher = MagicMock()
    publisher.broadcast = AsyncMock()
    host = make_host(aggregator=aggregator, publisher=publisher)

    await host._feed_house_status(dict(STATE_CHANGED))

    aggregator.process_state_change.assert_awaited_once_with(
        "sensor.living_room_temp", {"state": "21.5"}, {"state": "21.0"}
    )
    publisher.broadcast.assert_awaited_once_with(delta)
