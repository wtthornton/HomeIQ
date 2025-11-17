"""
InfluxDB Schema Design and Data Models

IMPORTANT SCHEMA NOTE:
----------------------
This schema defines the ORIGINAL DESIGN for Home Assistant events. However, the 
ACTUAL PRODUCTION SCHEMA used by the enrichment-pipeline is different:

- This schema (websocket-ingestion): Used for direct writes and fallback scenarios
- Enrichment pipeline schema: PRIMARY writer with flattened attributes (attr_* fields)

Key Differences:
- This: state_value, previous_state, attributes (JSON)
- Enrichment: state, old_state, attr_* (150+ flattened fields)

This schema IS actively used for:
- weather_data measurement
- sports_data measurement  
- system_metrics measurement
- Fallback/direct writes when enrichment is bypassed

For Home Assistant events (home_assistant_events measurement), see:
services/enrichment-pipeline/src/influxdb_wrapper.py (Line 180-257)

Last Updated: October 18, 2025
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import re

try:
    from influxdb_client import Point, WritePrecision
except ImportError:
    # Fallback for development without InfluxDB
    Point = None
    WritePrecision = None

logger = logging.getLogger(__name__)


class InfluxDBSchema:
    """InfluxDB schema design and data models"""
    
    def __init__(self):
        """Initialize schema design"""
        # Measurement names (Updated January 2025)
        self.MEASUREMENT_EVENTS = "home_assistant_events"  # Primary bucket
        self.MEASUREMENT_WEATHER = "weather_data"          # weather_data bucket
        self.MEASUREMENT_SPORTS = "sports_data"            # sports_data bucket
        self.MEASUREMENT_SYSTEM = "system_metrics"         # system_metrics bucket
        
        # Tag keys for efficient querying (Epic 23 Enhanced)
        self.TAG_ENTITY_ID = "entity_id"
        self.TAG_DOMAIN = "domain"
        self.TAG_DEVICE_CLASS = "device_class"
        self.TAG_AREA = "area"
        self.TAG_LOCATION = "location"
        self.TAG_WEATHER_CONDITION = "weather_condition"
        self.TAG_EVENT_TYPE = "event_type"
        # Epic 23.2: Device-level aggregation
        self.TAG_DEVICE_ID = "device_id"
        self.TAG_AREA_ID = "area_id"
        # Epic 23.4: Entity classification
        self.TAG_ENTITY_CATEGORY = "entity_category"
        
        # Field keys for data storage (Epic 23 Enhanced)
        self.FIELD_STATE = "state_value"
        self.FIELD_OLD_STATE = "previous_state"
        self.FIELD_ATTRIBUTES = "attributes"
        self.FIELD_TEMPERATURE = "weather_temp"
        self.FIELD_HUMIDITY = "weather_humidity"
        self.FIELD_PRESSURE = "weather_pressure"
        self.FIELD_WIND_SPEED = "wind_speed"
        self.FIELD_WEATHER_DESCRIPTION = "weather_description"
        # Epic 23.1: Context tracking
        self.FIELD_CONTEXT_ID = "context_id"
        self.FIELD_CONTEXT_PARENT_ID = "context_parent_id"
        self.FIELD_CONTEXT_USER_ID = "context_user_id"
        # Epic 23.3: Duration tracking
        self.FIELD_DURATION_IN_STATE = "duration_in_state_seconds"
        # Epic 23.5: Device metadata
        self.FIELD_MANUFACTURER = "manufacturer"
        self.FIELD_MODEL = "model"
        self.FIELD_SW_VERSION = "sw_version"
        
        # Retention policies (Current Configuration - January 2025)
        self.RETENTION_HA_EVENTS = "365d"        # home_assistant_events bucket
        self.RETENTION_SPORTS_DATA = "90d"       # sports_data bucket  
        self.RETENTION_WEATHER_DATA = "180d"     # weather_data bucket
        self.RETENTION_SYSTEM_METRICS = "30d"    # system_metrics bucket
    
    def create_event_point(self, event_data: Dict[str, Any]) -> Optional[Point]:
        """
        Create InfluxDB Point for Home Assistant event
        
        Args:
            event_data: Processed event data
            
        Returns:
            InfluxDB Point object or None if invalid
        """
        if not Point:
            logger.warning("InfluxDB Point not available")
            return None
        
        try:
            # Extract basic event information
            event_type = event_data.get("event_type")
            entity_id = event_data.get("entity_id")
            timestamp = event_data.get("time_fired")
            
            if not event_type or not entity_id:
                logger.warning("Missing required event data: event_type or entity_id")
                return None
            
            # Parse timestamp
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = timestamp
                except Exception as e:
                    logger.warning(f"Invalid timestamp format: {timestamp}, using current time")
                    dt = datetime.now()
            else:
                dt = datetime.now()
            
            # Create point
            point = Point(self.MEASUREMENT_EVENTS) \
                .time(dt, WritePrecision.MS)
            
            # Add tags for efficient querying
            point = self._add_event_tags(point, event_data)
            
            # Add fields for data storage
            point = self._add_event_fields(point, event_data)
            
            return point
            
        except Exception as e:
            logger.error(f"Error creating event point: {e}")
            return None
    
    def create_weather_point(self, weather_data: Dict[str, Any], location: str) -> Optional[Point]:
        """
        Create InfluxDB Point for weather data
        
        Args:
            weather_data: Weather data dictionary
            location: Location string
            
        Returns:
            InfluxDB Point object or None if invalid
        """
        if not Point:
            logger.warning("InfluxDB Point not available")
            return None
        
        try:
            # Parse timestamp
            timestamp = weather_data.get("timestamp")
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = timestamp
                except Exception:
                    dt = datetime.now()
            else:
                dt = datetime.now()
            
            # Create point
            point = Point(self.MEASUREMENT_WEATHER) \
                .time(dt, WritePrecision.MS)
            
            # Add tags
            point = point.tag(self.TAG_LOCATION, location)
            
            weather_condition = weather_data.get("weather_condition")
            if weather_condition:
                point = point.tag(self.TAG_WEATHER_CONDITION, weather_condition)
            
            # Add fields
            if weather_data.get("temperature") is not None:
                point = point.field(self.FIELD_TEMPERATURE, float(weather_data["temperature"]))
            
            if weather_data.get("humidity") is not None:
                point = point.field(self.FIELD_HUMIDITY, int(weather_data["humidity"]))
            
            if weather_data.get("pressure") is not None:
                point = point.field(self.FIELD_PRESSURE, float(weather_data["pressure"]))
            
            if weather_data.get("wind_speed") is not None:
                point = point.field(self.FIELD_WIND_SPEED, float(weather_data["wind_speed"]))
            
            weather_description = weather_data.get("weather_description")
            if weather_description:
                point = point.field(self.FIELD_WEATHER_DESCRIPTION, weather_description)
            
            return point
            
        except Exception as e:
            logger.error(f"Error creating weather point: {e}")
            return None
    
    def _add_event_tags(self, point: Point, event_data: Dict[str, Any]) -> Point:
        """Add tags to event point"""
        # Entity ID tag
        entity_id = event_data.get("entity_id")
        if entity_id:
            point = point.tag(self.TAG_ENTITY_ID, entity_id)
            
            # Extract domain from entity_id (e.g., "sensor.temperature" -> "sensor")
            domain = entity_id.split('.')[0] if '.' in entity_id else "unknown"
            point = point.tag(self.TAG_DOMAIN, domain)
        
        # Event type tag
        event_type = event_data.get("event_type")
        if event_type:
            point = point.tag(self.TAG_EVENT_TYPE, event_type)
        
        # Epic 23.2: Add device_id and area_id tags for spatial analytics
        device_id = event_data.get("device_id")
        if device_id:
            point = point.tag(self.TAG_DEVICE_ID, device_id)
        
        area_id = event_data.get("area_id")
        if area_id:
            point = point.tag(self.TAG_AREA_ID, area_id)
        
        # Device class tag (from attributes)
        attributes = event_data.get("attributes", {})
        device_class = attributes.get("device_class")
        if device_class:
            point = point.tag(self.TAG_DEVICE_CLASS, device_class)
        
        # Area tag (from attributes) - legacy support
        area = attributes.get("area")
        if area:
            point = point.tag(self.TAG_AREA, area)
        
        # Location tag (from weather data)
        weather = event_data.get("weather", {})
        location = weather.get("location")
        if location:
            point = point.tag(self.TAG_LOCATION, location)
        
        return point
    
    def _add_event_fields(self, point: Point, event_data: Dict[str, Any]) -> Point:
        """Add fields to event point"""
        # State fields
        state = event_data.get("new_state")
        if state is not None:
            point = point.field(self.FIELD_STATE, str(state))
        
        old_state = event_data.get("old_state")
        if old_state is not None:
            point = point.field(self.FIELD_OLD_STATE, str(old_state))
        
        # Attributes field (as JSON string)
        attributes = event_data.get("attributes", {})
        if attributes:
            point = point.field(self.FIELD_ATTRIBUTES, json.dumps(attributes))
        
        # Context fields
        context_id = event_data.get("context_id")
        if context_id:
            point = point.field(self.FIELD_CONTEXT_ID, context_id)
        
        context_user_id = event_data.get("context_user_id")
        if context_user_id:
            point = point.field(self.FIELD_CONTEXT_USER_ID, context_user_id)
        
        # Epic 23.3: Add duration_in_state for time-based analytics
        duration_in_state = event_data.get("duration_in_state")
        if duration_in_state is not None:
            point = point.field(self.FIELD_DURATION_IN_STATE, float(duration_in_state))
        
        # Epic 23.5: Add device metadata fields for reliability analysis
        device_metadata = event_data.get("device_metadata")
        if device_metadata:
            manufacturer = device_metadata.get("manufacturer")
            if manufacturer:
                point = point.field(self.FIELD_MANUFACTURER, manufacturer)
            
            model = device_metadata.get("model")
            if model:
                point = point.field(self.FIELD_MODEL, model)
            
            sw_version = device_metadata.get("sw_version")
            if sw_version:
                point = point.field(self.FIELD_SW_VERSION, sw_version)
        
        # Weather fields
        weather = event_data.get("weather", {})
        if weather:
            if weather.get("temperature") is not None:
                point = point.field(self.FIELD_TEMPERATURE, float(weather["temperature"]))
            
            if weather.get("humidity") is not None:
                point = point.field(self.FIELD_HUMIDITY, int(weather["humidity"]))
            
            if weather.get("pressure") is not None:
                point = point.field(self.FIELD_PRESSURE, float(weather["pressure"]))
            
            if weather.get("wind_speed") is not None:
                point = point.field(self.FIELD_WIND_SPEED, float(weather["wind_speed"]))
            
            weather_description = weather.get("weather_description")
            if weather_description:
                point = point.field(self.FIELD_WEATHER_DESCRIPTION, weather_description)
        
        return point
    
    def create_summary_point(self, 
                           measurement: str,
                           tags: Dict[str, str],
                           fields: Dict[str, Any],
                           timestamp: datetime) -> Optional[Point]:
        """
        Create InfluxDB Point for summary data
        
        Args:
            measurement: Measurement name
            tags: Dictionary of tags
            fields: Dictionary of fields
            timestamp: Timestamp for the point
            
        Returns:
            InfluxDB Point object or None if invalid
        """
        if not Point:
            logger.warning("InfluxDB Point not available")
            return None
        
        try:
            point = Point(measurement).time(timestamp, WritePrecision.MS)
            
            # Add tags
            for key, value in tags.items():
                if value is not None:
                    point = point.tag(key, str(value))
            
            # Add fields
            for key, value in fields.items():
                if value is not None:
                    if isinstance(value, (int, float)):
                        point = point.field(key, value)
                    else:
                        point = point.field(key, str(value))
            
            return point
            
        except Exception as e:
            logger.error(f"Error creating summary point: {e}")
            return None
    
    def get_retention_policies(self) -> List[Dict[str, Any]]:
        """Get retention policy definitions"""
        return [
            {
                "name": self.RETENTION_RAW_DATA,
                "duration": "365d",
                "shard_duration": "7d",
                "replication": 1,
                "description": "Raw event data retention for 1 year"
            },
            {
                "name": self.RETENTION_HOURLY_SUMMARY,
                "duration": "730d",
                "shard_duration": "30d",
                "replication": 1,
                "description": "Hourly summary data retention for 2 years"
            },
            {
                "name": self.RETENTION_DAILY_SUMMARY,
                "duration": "1825d",
                "shard_duration": "90d",
                "replication": 1,
                "description": "Daily summary data retention for 5 years"
            }
        ]
    
    def get_schema_validation_rules(self) -> Dict[str, Any]:
        """Get schema validation rules"""
        return {
            "required_tags": [self.TAG_ENTITY_ID, self.TAG_DOMAIN],
            "required_fields": [self.FIELD_STATE],
            "tag_patterns": {
                self.TAG_ENTITY_ID: r"^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+$",
                self.TAG_DOMAIN: r"^[a-zA-Z0-9_]+$",
                self.TAG_DEVICE_CLASS: r"^[a-zA-Z0-9_]+$"
            },
            "field_types": {
                self.FIELD_STATE: "string",
                self.FIELD_OLD_STATE: "string",
                self.FIELD_ATTRIBUTES: "string",
                self.FIELD_TEMPERATURE: "float",
                self.FIELD_HUMIDITY: "integer",
                self.FIELD_PRESSURE: "float",
                self.FIELD_WIND_SPEED: "float",
                self.FIELD_WEATHER_DESCRIPTION: "string",
                self.FIELD_CONTEXT_ID: "string",
                self.FIELD_CONTEXT_USER_ID: "string"
            }
        }
    
    def validate_point(self, point: Point) -> Tuple[bool, List[str]]:
        """
        Validate InfluxDB point against schema
        
        Args:
            point: InfluxDB Point to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        try:
            # Check measurement
            measurement = point._name
            if not measurement:
                errors.append("Missing measurement name")
            
            # Check required tags
            tags = point._tags
            required_tags = self.get_schema_validation_rules()["required_tags"]
            
            for required_tag in required_tags:
                if required_tag not in tags:
                    errors.append(f"Missing required tag: {required_tag}")
            
            # Check tag patterns
            tag_patterns = self.get_schema_validation_rules()["tag_patterns"]
            for tag_key, pattern in tag_patterns.items():
                if tag_key in tags:
                    tag_value = tags[tag_key]
                    if not re.match(pattern, str(tag_value)):
                        errors.append(f"Invalid tag pattern for {tag_key}: {tag_value}")
            
            # Check required fields
            fields = point._fields
            required_fields = self.get_schema_validation_rules()["required_fields"]
            
            for required_field in required_fields:
                if required_field not in fields:
                    errors.append(f"Missing required field: {required_field}")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"Validation error: {e}")
            return False, errors


# Import json for attributes serialization
import json
