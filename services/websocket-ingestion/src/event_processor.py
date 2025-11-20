"""
Event Processor for Home Assistant Events
"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class EventProcessor:
    """Processes and validates Home Assistant events"""

    def __init__(self, discovery_service=None):
        self.processed_events = 0
        self.validation_errors = 0
        self.last_processed_time: datetime | None = None
        # Epic 23.2: Discovery service for device/area lookups
        self.discovery_service = discovery_service

        # Event validation rules
        self.required_fields = {
            "state_changed": ["event_type", "new_state"],
            "call_service": ["event_type", "domain", "service", "service_data"],
            "service_registered": ["event_type", "domain", "service"],
            "service_removed": ["event_type", "domain", "service"]
        }

    def validate_event(self, event_data: dict[str, Any]) -> tuple[bool, str]:
        """
        Validate Home Assistant event data
        
        Args:
            event_data: The event data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check if event_data is a dictionary
            if not isinstance(event_data, dict):
                return False, "Event data must be a dictionary"

            # Check for required top-level fields
            if "event_type" not in event_data:
                return False, "Missing required field: event_type"

            event_type = event_data["event_type"]

            # Validate state_changed events specifically (most common)
            if event_type == "state_changed":
                return self._validate_state_changed_event(event_data)

            # For other event types, check for required fields based on event type
            if event_type in self.required_fields:
                required_fields = self.required_fields[event_type]
                for field in required_fields:
                    if field not in event_data:
                        return False, f"Missing required field for {event_type}: {field}"

            # Basic validation passed
            return True, ""

        except Exception as e:
            logger.error(f"Error validating event: {e}")
            return False, f"Validation error: {str(e)}"

    def _validate_state_changed_event(self, event_data: dict[str, Any]) -> tuple[bool, str]:
        """
        Validate state_changed event specifically
        
        Args:
            event_data: The state_changed event data
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Home Assistant state_changed events have this structure:
            # {
            #   "event_type": "state_changed",
            #   "time_fired": "2023-01-01T12:00:00.000Z",
            #   "origin": "LOCAL",
            #   "context": {...},
            #   "data": {
            #     "entity_id": "light.living_room",
            #     "old_state": {...},
            #     "new_state": {...}
            #   }
            # }

            # Check if we have the data field (Home Assistant structure)
            if "data" in event_data:
                data = event_data["data"]
                if not isinstance(data, dict):
                    return False, "data field must be a dictionary"

                # Check for entity_id in data
                entity_id = data.get("entity_id")
                if not entity_id:
                    return False, "entity_id is required in data field"

                if not isinstance(entity_id, str) or "." not in entity_id:
                    return False, "entity_id must be a string in format 'domain.entity'"

                if "new_state" not in data:
                    return False, "new_state key must be present (can be null)"

                # Check new_state in data
                # NOTE: In Home Assistant, new_state can be None when an entity is deleted
                # This is a valid event structure
                new_state = data.get("new_state")
                if new_state is not None and not isinstance(new_state, dict):
                    return False, "new_state must be a dictionary or null"

                # Check required fields in new_state (only if new_state exists)
                # new_state can be None for deleted entities
                if new_state is not None and "state" not in new_state:
                    return False, "state is required in new_state"

                # old_state is optional (can be None for new entities)
                old_state = data.get("old_state")
                if old_state is not None and not isinstance(old_state, dict):
                    return False, "old_state must be a dictionary or null"

                return True, ""

            # Fallback: Check for direct fields (legacy structure)
            else:
                # Check old_state
                old_state = event_data.get("old_state")
                if old_state is not None and not isinstance(old_state, dict):
                    return False, "old_state must be a dictionary or null"

                if "new_state" not in event_data:
                    return False, "new_state key must be present (can be null)"

                # Check new_state
                # NOTE: In Home Assistant, new_state can be None when an entity is deleted
                new_state = event_data.get("new_state")
                if new_state is not None and not isinstance(new_state, dict):
                    return False, "new_state must be a dictionary or null"

                # Check required fields in new_state (only if it exists)
                if new_state is not None:
                    required_new_state_fields = ["entity_id", "state"]
                    for field in required_new_state_fields:
                        if field not in new_state:
                            return False, f"Missing required field in new_state: {field}"

                # Validate entity_id format (only if new_state exists)
                if new_state is not None:
                    entity_id = new_state.get("entity_id")
                    if not isinstance(entity_id, str) or "." not in entity_id:
                        return False, "entity_id must be a string in format 'domain.entity'"

                # Validate state value (only if new_state exists)
                if new_state is not None:
                    state_value = new_state.get("state")
                    if not isinstance(state_value, str):
                        return False, "state must be a string"

                return True, ""

        except Exception as e:
            logger.error(f"Error validating state_changed event: {e}")
            return False, f"State validation error: {str(e)}"

    def extract_event_data(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """
        Extract structured data from Home Assistant event
        
        Args:
            event_data: The raw event data
            
        Returns:
            Dictionary with extracted event data
        """
        try:
            extracted = {
                "event_type": event_data.get("event_type"),
                "timestamp": datetime.now().isoformat(),
                "raw_data": event_data.copy()
            }

            event_type = event_data.get("event_type")

            if event_type == "state_changed":
                extracted.update(self._extract_state_changed_data(event_data))
            elif event_type == "call_service":
                extracted.update(self._extract_call_service_data(event_data))
            else:
                # Generic extraction for other event types
                extracted["generic_data"] = event_data

            return extracted

        except Exception as e:
            logger.error(f"Error extracting event data: {e}")
            return {
                "event_type": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "raw_data": event_data
            }

    def _extract_state_changed_data(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """
        Extract data from state_changed event
        
        Args:
            event_data: The state_changed event data
            
        Returns:
            Dictionary with extracted state_changed data
        """
        time_fired = event_data.get("time_fired")
        origin = event_data.get("origin")
        context = event_data.get("context", {})

        # Handle Home Assistant event structure with data field
        if "data" in event_data:
            data = event_data.get("data") or {}
            entity_id = data.get("entity_id")
            raw_old_state = data.get("old_state")
            raw_new_state = data.get("new_state")  # Can be None for deleted entities
        else:
            # Fallback for legacy structure
            data = event_data
            entity_id = event_data.get("entity_id")
            raw_old_state = event_data.get("old_state")
            raw_new_state = event_data.get("new_state")  # Can be None for deleted entities

        old_state = raw_old_state if isinstance(raw_old_state, dict) else None
        new_state = raw_new_state if isinstance(raw_new_state, dict) else None

        if not entity_id:
            entity_id = (new_state or {}).get("entity_id") or (old_state or {}).get("entity_id")

        # Epic 23.1: Extract context.parent_id for automation causality tracking
        context_id = context.get("id") if context else None
        context_parent_id = context.get("parent_id") if context else None
        context_user_id = context.get("user_id") if context else None

        # Epic 23.2: Look up device_id and area_id for spatial analytics
        device_id = None
        area_id = None
        device_metadata = None
        if self.discovery_service and entity_id:
            device_id = self.discovery_service.get_device_id(entity_id)
            area_id = self.discovery_service.get_area_id(entity_id, device_id)

            if device_id:
                logger.debug(f"Found device_id {device_id} for entity {entity_id}")
                # Epic 23.5: Look up device metadata for reliability analysis
                device_metadata = self.discovery_service.get_device_metadata(device_id)
                if device_metadata:
                    logger.debug(f"Found device metadata for device {device_id}: "
                               f"{device_metadata.get('manufacturer')}/{device_metadata.get('model')}")

            if area_id:
                logger.debug(f"Found area_id {area_id} for entity {entity_id}")

        # Epic 23.3: Calculate duration_in_state for time-based analytics
        duration_in_state = None
        if old_state and isinstance(old_state, dict) and "last_changed" in old_state and new_state and isinstance(new_state, dict) and "last_changed" in new_state:
            try:
                # Parse timestamps (handle both with and without 'Z' suffix)
                old_time_str = old_state["last_changed"].replace("Z", "+00:00")
                new_time_str = new_state["last_changed"].replace("Z", "+00:00")

                old_time = datetime.fromisoformat(old_time_str)
                new_time = datetime.fromisoformat(new_time_str)

                # Calculate duration in seconds
                duration_seconds = (new_time - old_time).total_seconds()

                # Validation: Warn for negative or very long durations
                if duration_seconds < 0:
                    logger.warning(f"Negative duration calculated: {duration_seconds}s for entity {entity_id}")
                    duration_in_state = 0  # Clamp to 0
                elif duration_seconds > 604800:  # 7 days in seconds
                    logger.warning(f"Very long duration detected: {duration_seconds}s ({duration_seconds/86400:.1f} days) for entity {entity_id}")
                    duration_in_state = duration_seconds  # Keep the value but log warning
                else:
                    duration_in_state = duration_seconds

            except Exception as e:
                logger.error(f"Error calculating duration_in_state for {entity_id}: {e}")
                duration_in_state = None

        return {
            "entity_id": entity_id,
            "domain": entity_id.split(".")[0] if entity_id else None,
            "time_fired": time_fired,
            "origin": origin,
            "context": context,
            # Epic 23.1: Add individual context fields for InfluxDB storage
            "context_id": context_id,
            "context_parent_id": context_parent_id,
            "context_user_id": context_user_id,
            # Epic 23.2: Add device_id and area_id for spatial analytics
            "device_id": device_id,
            "area_id": area_id,
            # Epic 23.5: Add device metadata for reliability analysis
            "device_metadata": device_metadata,
            # Epic 23.3: Add duration_in_state for time-based analytics
            "duration_in_state": duration_in_state,
            # CRITICAL FIX: Preserve original Home Assistant event structure
            "old_state": old_state,  # Keep original structure
            "new_state": new_state,  # Keep original structure
            "state_change": {
                "from": old_state.get("state") if isinstance(old_state, dict) else None,
                "to": new_state.get("state") if isinstance(new_state, dict) else None,
                "changed": (old_state.get("state") if isinstance(old_state, dict) else None) != (
                    new_state.get("state") if isinstance(new_state, dict) else None
                )
            }
        }

    def _extract_call_service_data(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """
        Extract data from call_service event
        
        Args:
            event_data: The call_service event data
            
        Returns:
            Dictionary with extracted call_service data
        """
        return {
            "domain": event_data.get("domain"),
            "service": event_data.get("service"),
            "service_data": event_data.get("service_data", {}),
            "entity_id": event_data.get("entity_id")
        }

    def process_event(self, event_data: dict[str, Any]) -> dict[str, Any] | None:
        """
        Process and validate a Home Assistant event
        
        Args:
            event_data: The raw event data
            
        Returns:
            Processed event data if valid, None if invalid
        """
        try:
            # Validate event
            is_valid, error_msg = self.validate_event(event_data)

            if not is_valid:
                self.validation_errors += 1
                logger.warning(f"Event validation failed: {error_msg}")
                logger.debug(f"Invalid event data: {event_data}")
                return None

            # Extract structured data
            processed_data = self.extract_event_data(event_data)

            # Update statistics
            self.processed_events += 1
            self.last_processed_time = datetime.now()

            # Log processed event
            self._log_processed_event(processed_data)

            return processed_data

        except Exception as e:
            logger.error(f"Error processing event: {e}")
            self.validation_errors += 1
            return None

    def _log_processed_event(self, processed_data: dict[str, Any]):
        """
        Log processed event information
        
        Args:
            processed_data: The processed event data
        """
        try:
            event_type = processed_data.get("event_type")

            if event_type == "state_changed":
                entity_id = processed_data.get("entity_id")
                state_change = processed_data.get("state_change", {})
                from_state = state_change.get("from")
                to_state = state_change.get("to")

                logger.info(f"Processed state_changed: {entity_id} ({from_state} -> {to_state})")
            else:
                logger.info(f"Processed {event_type} event")

        except Exception as e:
            logger.error(f"Error logging processed event: {e}")

    def get_processing_statistics(self) -> dict[str, Any]:
        """
        Get event processing statistics
        
        Returns:
            Dictionary with processing statistics
        """
        return {
            "processed_events": self.processed_events,
            "validation_errors": self.validation_errors,
            "success_rate": (self.processed_events / (self.processed_events + self.validation_errors) * 100)
                           if (self.processed_events + self.validation_errors) > 0 else 0,
            "last_processed_time": self.last_processed_time.isoformat() if self.last_processed_time else None
        }

    def reset_statistics(self):
        """Reset processing statistics"""
        self.processed_events = 0
        self.validation_errors = 0
        self.last_processed_time = None
        logger.info("Event processing statistics reset")
