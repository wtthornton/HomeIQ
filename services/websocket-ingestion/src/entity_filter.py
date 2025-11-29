"""
Entity Filter for Event Capture (Epic 45.2)

Filters entities before writing to InfluxDB to reduce storage costs.
Supports filtering by entity ID patterns, domain, device class, and area.
"""

import logging
import re
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class EntityFilter:
    """Entity filter for event capture with configurable patterns"""

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize entity filter
        
        Args:
            config: Filter configuration dictionary
                - mode: "exclude" (opt-out) or "include" (opt-in)
                - patterns: List of filter patterns
                - exceptions: List of exceptions (always included/excluded)
        """
        self.config = config or {}
        self.mode = self.config.get("mode", "exclude")  # Default: opt-out
        self.patterns = self.config.get("patterns", [])
        self.exceptions = self.config.get("exceptions", [])
        
        # Statistics tracking
        self.filtered_count = 0
        self.passed_count = 0
        self.exception_count = 0
        self.start_time = datetime.now()
        
        # Compile regex patterns for performance
        self._compiled_patterns: list[tuple[re.Pattern, dict[str, Any]]] = []
        self._compiled_exceptions: list[tuple[re.Pattern, dict[str, Any]]] = []
        self._compile_patterns()
        
        logger.info(f"Entity filter initialized: mode={self.mode}, patterns={len(self.patterns)}, exceptions={len(self.exceptions)}")

    def _compile_patterns(self):
        """Compile regex patterns for performance"""
        # Compile filter patterns
        for pattern in self.patterns:
            compiled = self._compile_pattern(pattern)
            if compiled:
                self._compiled_patterns.append(compiled)
        
        # Compile exception patterns
        for exception in self.exceptions:
            compiled = self._compile_pattern(exception)
            if compiled:
                self._compiled_exceptions.append(compiled)

    def _compile_pattern(self, pattern: dict[str, Any]) -> tuple[re.Pattern, dict[str, Any]] | None:
        """
        Compile a single pattern into regex
        
        Args:
            pattern: Pattern dictionary with entity_id, domain, device_class, or area_id
            
        Returns:
            Tuple of (compiled_regex, pattern_dict) or None if invalid
        """
        entity_id_pattern = pattern.get("entity_id")
        if entity_id_pattern:
            try:
                # Convert glob pattern to regex
                regex_pattern = self._glob_to_regex(entity_id_pattern)
                compiled = re.compile(regex_pattern)
                return (compiled, pattern)
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{entity_id_pattern}': {e}")
                return None
        return None

    def _glob_to_regex(self, pattern: str) -> str:
        """
        Convert glob pattern to regex
        
        Args:
            pattern: Glob pattern (e.g., "sensor.*_battery")
            
        Returns:
            Regex pattern string
        """
        # Escape special regex characters except * and ?
        pattern = re.escape(pattern)
        # Replace escaped * with .*
        pattern = pattern.replace(r'\*', '.*')
        # Replace escaped ? with .
        pattern = pattern.replace(r'\?', '.')
        return f"^{pattern}$"

    def should_include(self, event_data: dict[str, Any]) -> bool:
        """
        Determine if an event should be included (not filtered)
        
        Args:
            event_data: Event data dictionary with entity_id, domain, device_class, area_id
            
        Returns:
            True if event should be included, False if filtered
        """
        # Extract entity information from event
        entity_id = self._extract_entity_id(event_data)
        if not entity_id:
            # If no entity_id, include by default (non-entity events)
            return True
        
        domain = self._extract_domain(entity_id)
        device_class = event_data.get("device_class") or event_data.get("attributes", {}).get("device_class")
        area_id = event_data.get("area_id") or event_data.get("attributes", {}).get("area_id")
        
        # Check exceptions first (always override)
        if self._matches_exceptions(entity_id, domain, device_class, area_id):
            self.exception_count += 1
            logger.debug(f"Entity {entity_id} matches exception - including")
            return True
        
        # Check if entity matches filter patterns
        matches_pattern = self._matches_patterns(entity_id, domain, device_class, area_id)
        
        if self.mode == "exclude":
            # Opt-out: Exclude if matches pattern
            if matches_pattern:
                self.filtered_count += 1
                logger.debug(f"Entity {entity_id} matches exclude pattern - filtering")
                return False
            else:
                self.passed_count += 1
                return True
        else:  # mode == "include"
            # Opt-in: Include only if matches pattern
            if matches_pattern:
                self.passed_count += 1
                return True
            else:
                self.filtered_count += 1
                logger.debug(f"Entity {entity_id} does not match include pattern - filtering")
                return False

    def _extract_entity_id(self, event_data: dict[str, Any]) -> str | None:
        """Extract entity_id from event data"""
        # Try various locations
        if "entity_id" in event_data:
            return event_data["entity_id"]
        if "data" in event_data and isinstance(event_data["data"], dict):
            return event_data["data"].get("entity_id")
        if "new_state" in event_data and isinstance(event_data["new_state"], dict):
            return event_data["new_state"].get("entity_id")
        return None

    def _extract_domain(self, entity_id: str) -> str | None:
        """Extract domain from entity_id"""
        if "." in entity_id:
            return entity_id.split(".")[0]
        return None

    def _matches_exceptions(self, entity_id: str, domain: str | None, device_class: str | None, area_id: str | None) -> bool:
        """Check if entity matches any exception pattern"""
        for compiled_pattern, pattern_dict in self._compiled_exceptions:
            if self._entity_matches_pattern(entity_id, domain, device_class, area_id, compiled_pattern, pattern_dict):
                return True
        return False

    def _matches_patterns(self, entity_id: str, domain: str | None, device_class: str | None, area_id: str | None) -> bool:
        """Check if entity matches any filter pattern"""
        # Check compiled regex patterns
        for compiled_pattern, pattern_dict in self._compiled_patterns:
            if self._entity_matches_pattern(entity_id, domain, device_class, area_id, compiled_pattern, pattern_dict):
                return True
        
        # Also check non-regex patterns (domain, device_class, area_id)
        for pattern in self.patterns:
            if not pattern.get("entity_id"):  # Skip regex patterns (already checked)
                if self._entity_matches_simple_pattern(entity_id, domain, device_class, area_id, pattern):
                    return True
        return False
    
    def _entity_matches_simple_pattern(self, entity_id: str, domain: str | None, device_class: str | None, area_id: str | None, pattern: dict[str, Any]) -> bool:
        """Check if entity matches a simple pattern (non-regex)"""
        # Check domain
        if pattern.get("domain") and domain:
            if pattern["domain"] == domain:
                return True
        
        # Check device_class
        if pattern.get("device_class") and device_class:
            if pattern["device_class"] == device_class:
                return True
        
        # Check area_id
        if pattern.get("area_id") and area_id:
            if pattern["area_id"] == area_id:
                return True
        
        return False

    def _entity_matches_pattern(self, entity_id: str, domain: str | None, device_class: str | None, area_id: str | None, 
                                compiled_pattern: re.Pattern, pattern_dict: dict[str, Any]) -> bool:
        """Check if entity matches a specific pattern"""
        # Check entity_id pattern
        if pattern_dict.get("entity_id") and compiled_pattern:
            if compiled_pattern.match(entity_id):
                return True
        
        # Check domain
        if pattern_dict.get("domain") and domain:
            if pattern_dict["domain"] == domain:
                return True
        
        # Check device_class
        if pattern_dict.get("device_class") and device_class:
            if pattern_dict["device_class"] == device_class:
                return True
        
        # Check area_id
        if pattern_dict.get("area_id") and area_id:
            if pattern_dict["area_id"] == area_id:
                return True
        
        return False

    def get_statistics(self) -> dict[str, Any]:
        """
        Get filter statistics
        
        Returns:
            Dictionary with filter statistics
        """
        uptime = (datetime.now() - self.start_time).total_seconds()
        total_processed = self.filtered_count + self.passed_count + self.exception_count
        
        return {
            "filtered_count": self.filtered_count,
            "passed_count": self.passed_count,
            "exception_count": self.exception_count,
            "total_processed": total_processed,
            "filter_rate": self.filtered_count / total_processed if total_processed > 0 else 0.0,
            "uptime_seconds": uptime,
            "mode": self.mode,
            "patterns_count": len(self.patterns),
            "exceptions_count": len(self.exceptions)
        }

    def reload_config(self, new_config: dict[str, Any]):
        """
        Reload filter configuration without restart
        
        Args:
            new_config: New filter configuration
        """
        self.config = new_config
        self.mode = self.config.get("mode", "exclude")
        self.patterns = self.config.get("patterns", [])
        self.exceptions = self.config.get("exceptions", [])
        
        # Recompile patterns
        self._compiled_patterns.clear()
        self._compiled_exceptions.clear()
        self._compile_patterns()
        
        logger.info(f"Entity filter configuration reloaded: mode={self.mode}, patterns={len(self.patterns)}")

