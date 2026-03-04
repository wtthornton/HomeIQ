"""WebSocket event handler methods extracted from WebSocketIngestionService.

Keeps the main service module lean while preserving all runtime behaviour.
"""

from __future__ import annotations

from typing import Any

from homeiq_observability.logging_config import (
    generate_correlation_id,
    get_correlation_id,
    log_error_with_context,
    log_with_context,
    performance_monitor,
    setup_logging,
)

logger = setup_logging("websocket-ingestion")


class EventHandlerMixin:
    """Mixin providing HA event callback methods.

    Expects the host class to expose:
      - ``entity_filter``  (EntityFilter | None)
      - ``batch_processor`` (BatchProcessor | None)
      - ``async_event_processor`` (AsyncEventProcessor | None)
      - ``influxdb_batch_writer`` (InfluxDBBatchWriter | None)
      - ``home_assistant_url`` (str | None)
    """

    # -- connection callbacks --------------------------------------------------

    async def _on_connect(self) -> None:
        """Handle successful connection and trigger discovery."""
        corr_id = get_correlation_id() or generate_correlation_id()
        log_with_context(
            logger, "INFO", "Successfully connected to Home Assistant",
            operation="ha_connection",
            correlation_id=corr_id,
            status="connected",
            url=self.home_assistant_url,  # type: ignore[attr-defined]
        )

    async def _on_disconnect(self) -> None:
        """Handle disconnection from Home Assistant."""
        corr_id = get_correlation_id() or generate_correlation_id()
        log_with_context(
            logger, "WARNING", "Disconnected from Home Assistant",
            operation="ha_disconnection",
            correlation_id=corr_id,
            status="disconnected",
            url=self.home_assistant_url,  # type: ignore[attr-defined]
        )

    async def _on_message(self, message: Any) -> None:
        """Handle incoming message from Home Assistant WebSocket."""
        corr_id = get_correlation_id() or generate_correlation_id()
        log_with_context(
            logger, "DEBUG", "Received message from Home Assistant",
            operation="message_received",
            correlation_id=corr_id,
            message_type=type(message).__name__,
            message_size=len(str(message)) if message else 0,
        )

    async def _on_error(self, error: Exception) -> None:
        """Handle a service-level error by logging it with context."""
        corr_id = get_correlation_id() or generate_correlation_id()
        log_error_with_context(
            logger, "Service error occurred", error,
            operation="service_error",
            correlation_id=corr_id,
            error_type="service_error",
        )

    # -- event processing ------------------------------------------------------

    @performance_monitor("event_processing")
    async def _on_event(self, processed_event: dict[str, Any]) -> None:
        """Handle a processed event by filtering and batching it."""
        corr_id = get_correlation_id() or generate_correlation_id()
        event_type = processed_event.get("event_type", "unknown")
        entity_id = processed_event.get("entity_id", "N/A")

        try:
            if self.entity_filter and not self.entity_filter.should_include(processed_event):  # type: ignore[attr-defined]
                return

            if self.batch_processor:  # type: ignore[attr-defined]
                await self.batch_processor.add_event(processed_event)  # type: ignore[attr-defined]

            # Epic 28: Feed state_changed events into house status aggregator.
            await self._feed_house_status(processed_event)
        except Exception as e:
            log_error_with_context(
                logger, "Error processing Home Assistant event", e,
                operation="event_processing",
                correlation_id=corr_id,
                event_type=event_type,
                entity_id=entity_id,
            )

    async def _feed_house_status(self, processed_event: dict[str, Any]) -> None:
        """Forward state_changed events to the house status aggregator."""
        aggregator = getattr(self, "house_status_aggregator", None)  # type: ignore[attr-defined]
        if aggregator is None:
            return
        if processed_event.get("event_type") != "state_changed":
            return
        entity_id = processed_event.get("entity_id")
        new_state = processed_event.get("new_state")
        if not entity_id or not isinstance(new_state, dict):
            return
        old_state = processed_event.get("old_state")
        try:
            delta = await aggregator.process_state_change(entity_id, new_state, old_state)
            if delta is not None:
                publisher = getattr(self, "house_status_publisher", None)  # type: ignore[attr-defined]
                if publisher is not None:
                    await publisher.broadcast(delta)
        except Exception:
            logger.debug("House status aggregation error", exc_info=True)

    async def _write_event_to_influxdb(self, event_data: dict[str, Any]) -> None:
        """Write a single event to InfluxDB via the batch writer."""
        try:
            if self.influxdb_batch_writer:  # type: ignore[attr-defined]
                success = await self.influxdb_batch_writer.write_event(event_data)  # type: ignore[attr-defined]
                if not success:
                    logger.warning("Failed to write event to InfluxDB: %s", event_data.get("event_type"))
        except Exception as e:
            logger.error("Error writing event to InfluxDB: %s", e)

    @performance_monitor("batch_processing")
    async def _process_batch(self, batch: list[dict[str, Any]]) -> None:
        """Process a batch of events through the async event processor."""
        corr_id = get_correlation_id() or generate_correlation_id()
        batch_size = len(batch)

        try:
            if self.async_event_processor:  # type: ignore[attr-defined]
                for event in batch:
                    try:
                        await self.async_event_processor.process_event(event)  # type: ignore[attr-defined]
                    except Exception as e:
                        log_error_with_context(
                            logger, "Error processing event in batch", e,
                            operation="batch_processing",
                            correlation_id=corr_id,
                            batch_size=batch_size,
                        )

            log_with_context(
                logger, "DEBUG", "Batch processed",
                operation="batch_processing",
                correlation_id=corr_id,
                batch_size=batch_size,
            )
        except Exception as e:
            log_error_with_context(
                logger, "Error processing batch", e,
                operation="batch_processing",
                correlation_id=corr_id,
                batch_size=batch_size,
            )
