"""
Events Endpoints for Data API
Migrated from admin-api as part of Epic 13 Story 13.2
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import aiohttp
import os
import sys

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)


def sanitize_flux_value(value: str) -> str:
    """
    Sanitize values for Flux queries to prevent injection attacks

    Security: Prevents Flux query injection by escaping special characters

    Args:
        value: Raw input value

    Returns:
        Sanitized value safe for Flux queries
    """
    if value is None:
        return ""

    # Remove or escape potentially dangerous characters
    # Allow alphanumeric, spaces, dots, hyphens, underscores
    sanitized = re.sub(r'[^\w\s.\-]', '', str(value))

    # Escape double quotes
    sanitized = sanitized.replace('"', '\\"')

    return sanitized


class EventData(BaseModel):
    """Event data model"""
    id: str
    timestamp: datetime
    entity_id: str
    event_type: str
    old_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    attributes: Dict[str, Any] = {}
    tags: Dict[str, str] = {}


class EventFilter(BaseModel):
    """Event filter model"""
    entity_id: Optional[str] = None
    event_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    tags: Dict[str, str] = {}
    # Epic 23.2: Device and area filtering
    device_id: Optional[str] = None
    area_id: Optional[str] = None
    # Epic 23.4: Entity classification filtering
    entity_category: Optional[str] = None
    exclude_category: Optional[str] = None


class EventSearch(BaseModel):
    """Event search model"""
    query: str
    fields: List[str] = ["entity_id", "event_type", "attributes"]
    limit: int = 100


class EventsEndpoints:
    """Events endpoints for feature data access"""
    
    def __init__(self):
        """Initialize events endpoints"""
        self.router = APIRouter()
        self.service_urls = {
            "websocket-ingestion": os.getenv("WEBSOCKET_INGESTION_URL", "http://websocket-ingestion:8001"),
            "enrichment-pipeline": os.getenv("ENRICHMENT_PIPELINE_URL", "http://enrichment-pipeline:8002")
        }
        
        self._add_routes()
    
    def _add_routes(self):
        """Add events routes"""
        
        # IMPORTANT: Register specific routes BEFORE parameterized routes
        # to prevent path parameter matching issues
        
        @self.router.get("/events/stats", response_model=Dict[str, Any])
        async def get_events_stats(
            period: str = Query("1h", description="Time period for statistics"),
            service: Optional[str] = Query(None, description="Specific service")
        ):
            """Get event statistics"""
            try:
                if service and service in self.service_urls:
                    stats = await self._get_service_events_stats(service, period)
                else:
                    stats = await self._get_all_events_stats(period)
                
                return stats
                
            except Exception as e:
                logger.error(f"Error getting events stats: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get events statistics"
                )
        
        @self.router.post("/events/search", response_model=List[EventData])
        async def search_events(search: EventSearch):
            """Search events with text query"""
            try:
                events = await self._search_events(search)
                return events
                
            except Exception as e:
                logger.error(f"Error searching events: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to search events"
                )
        
        @self.router.get("/events/stream", response_model=Dict[str, Any])
        async def get_events_stream(
            duration: int = Query(60, description="Stream duration in seconds"),
            entity_id: Optional[str] = Query(None, description="Filter by entity ID")
        ):
            """Get real-time event stream"""
            try:
                stream_data = await self._get_events_stream(duration, entity_id)
                return stream_data
                
            except Exception as e:
                logger.error(f"Error getting events stream: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get events stream"
                )
        
        @self.router.get("/events/entities", response_model=List[Dict[str, Any]])
        async def get_active_entities(
            limit: int = Query(100, description="Maximum number of entities to return"),
            service: Optional[str] = Query(None, description="Specific service")
        ):
            """Get list of active entities"""
            try:
                if service and service in self.service_urls:
                    entities = await self._get_service_active_entities(service, limit)
                else:
                    entities = await self._get_all_active_entities(limit)
                
                return entities
                
            except Exception as e:
                logger.error(f"Error getting active entities: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get active entities"
                )
        
        @self.router.get("/events/types", response_model=List[Dict[str, Any]])
        async def get_event_types(
            limit: int = Query(50, description="Maximum number of event types to return"),
            service: Optional[str] = Query(None, description="Specific service")
        ):
            """Get list of event types"""
            try:
                if service and service in self.service_urls:
                    event_types = await self._get_service_event_types(service, limit)
                else:
                    event_types = await self._get_all_event_types(limit)
                
                return event_types
                
            except Exception as e:
                logger.error(f"Error getting event types: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get event types"
                )
        
        # Epic 23.1: Automation Trace Endpoint
        @self.router.get("/events/automation-trace/{context_id}", response_model=List[Dict[str, Any]])
        async def trace_automation_chain(
            context_id: str,
            max_depth: int = Query(10, description="Maximum chain depth to traverse"),
            include_details: bool = Query(True, description="Include event details")
        ):
            """
            Trace automation chain by following context.parent_id relationships
            
            This endpoint finds all events in an automation chain by:
            1. Starting with the provided context_id
            2. Finding all events that have this context_id as their parent
            3. Recursively following the chain up to max_depth levels
            
            Args:
                context_id: The context ID to trace
                max_depth: Maximum depth to traverse (default: 10)
                include_details: Whether to include full event details (default: True)
            
            Returns:
                List of events in the automation chain, ordered by depth
            """
            try:
                chain = await self._trace_automation_chain(context_id, max_depth, include_details)
                return chain
                
            except Exception as e:
                logger.error(f"Error tracing automation chain: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to trace automation chain: {str(e)}"
                )
        
        # General /events route - should come after specific routes
        @self.router.get("/events", response_model=List[EventData])
        async def get_recent_events(
            limit: int = Query(100, description="Maximum number of events to return"),
            offset: int = Query(0, description="Number of events to skip"),
            entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
            event_type: Optional[str] = Query(None, description="Filter by event type"),
            start_time: Optional[datetime] = Query(None, description="Start time filter"),
            end_time: Optional[datetime] = Query(None, description="End time filter"),
            service: Optional[str] = Query(None, description="Specific service to query"),
            # Epic 23.2: Device and area filtering
            device_id: Optional[str] = Query(None, description="Filter by device ID"),
            area_id: Optional[str] = Query(None, description="Filter by area ID (room)"),
            # Epic 23.4: Entity classification filtering
            entity_category: Optional[str] = Query(None, description="Filter by entity category (config, diagnostic)"),
            exclude_category: Optional[str] = Query(None, description="Exclude entity category (config, diagnostic)")
        ):
            """
            Get recent events with optional filtering
            
            Epic 23.2: Supports filtering by device_id and area_id for spatial analytics
            - device_id: Filter events from a specific device
            - area_id: Filter events from a specific room/area
            
            Epic 23.4: Supports filtering by entity_category to show/hide diagnostic and config entities
            - entity_category: Include only entities with this category
            - exclude_category: Exclude entities with this category (commonly 'diagnostic')
            """
            try:
                # Build filter
                event_filter = EventFilter(
                    entity_id=entity_id,
                    event_type=event_type,
                    start_time=start_time,
                    end_time=end_time,
                    device_id=device_id,
                    area_id=area_id,
                    entity_category=entity_category,
                    exclude_category=exclude_category
                )
                
                if service and service in self.service_urls:
                    # Get events from specific service
                    events = await self._get_service_events(service, event_filter, limit, offset)
                else:
                    # Get events from all services
                    events = await self._get_all_events(event_filter, limit, offset)
                
                return events
                
            except Exception as e:
                logger.error(f"Error getting recent events: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get recent events"
                )
        
        # Parameterized route MUST be last to avoid matching specific routes
        @self.router.get("/events/{event_id}", response_model=EventData)
        async def get_event_by_id(event_id: str):
            """Get a specific event by ID"""
            try:
                event = await self._get_event_by_id(event_id)
                if not event:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Event {event_id} not found"
                    )
                
                return event
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting event {event_id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get event"
                )
    
    async def _get_all_events(self, event_filter: EventFilter, limit: int, offset: int) -> List[EventData]:
        """Get events from InfluxDB directly"""
        try:
            logger.info(f"_get_all_events called: limit={limit}, offset={offset}")
            # Get events directly from InfluxDB
            events = await self._get_events_from_influxdb(event_filter, limit, offset)
            logger.info(f"_get_all_events returning {len(events)} events")
            return events
        except Exception as e:
            logger.error(f"Error getting events from InfluxDB: {e}", exc_info=True)
            # Return proper error instead of mock data
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"InfluxDB service unavailable: {str(e)}"
            )
    
    async def _get_service_events(self, service: str, event_filter: EventFilter, limit: int, offset: int) -> List[EventData]:
        """Get events from a specific service"""
        service_url = self.service_urls[service]
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                params = {
                    "limit": limit,
                    "offset": offset
                }
                
                if event_filter.entity_id:
                    params["entity_id"] = event_filter.entity_id
                if event_filter.event_type:
                    params["event_type"] = event_filter.event_type
                if event_filter.start_time:
                    params["start_time"] = event_filter.start_time.isoformat()
                if event_filter.end_time:
                    params["end_time"] = event_filter.end_time.isoformat()
                
                async with session.get(f"{service_url}/events", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [EventData(**event) for event in data]
                    else:
                        raise Exception(f"HTTP {response.status}")
        except Exception as e:
            logger.error(f"Error getting events from {service}: {e}")
            return []
    
    async def _get_event_by_id(self, event_id: str) -> Optional[EventData]:
        """Get a specific event by ID"""
        # First, attempt to fetch the event directly from InfluxDB for rich details
        event = await self._get_event_from_influxdb(event_id)
        if event:
            return event
        
        # Fallback: query downstream services (legacy compatibility)
        for service_name, service_url in self.service_urls.items():
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    async with session.get(f"{service_url}/events/{event_id}") as response:
                        if response.status == 200:
                            data = await response.json()
                            event = EventData(**data)
                            event.tags["service"] = service_name
                            return event
                        elif response.status == 404:
                            continue  # Try next service
                        else:
                            raise Exception(f"HTTP {response.status}")
            except Exception as e:
                logger.warning(f"Failed to get event {event_id} from {service_name}: {e}")
        
        return None

    async def _get_event_from_influxdb(self, event_id: str) -> Optional[EventData]:
        """
        Retrieve a single event from InfluxDB with full detail payload.
        
        Strategy:
            - If the identifier is a context_id (default HA pattern), query by context_id
            - If the identifier is the synthetic `event_<timestamp>_<entity>` format,
              parse the timestamp/entity and query within a narrow time range
        """
        try:
            from influxdb_client import InfluxDBClient
        except ImportError:
            logger.warning("InfluxDB client unavailable; cannot fetch event detail")
            return None
        
        influxdb_url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
        influxdb_token = os.getenv("INFLUXDB_TOKEN", "homeiq-token")
        influxdb_org = os.getenv("INFLUXDB_ORG", "homeiq")
        influxdb_bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")
        
        context_id = None
        entity_id = None
        timestamp_window = None
        
        if event_id.startswith("event_"):
            # Synthetic identifier -> parse timestamp and entity_id
            try:
                _, ts_part, entity_part = event_id.split("_", 2)
                event_ts = datetime.fromtimestamp(float(ts_part), tz=timezone.utc)
                timestamp_window = (
                    event_ts - timedelta(seconds=5),
                    event_ts + timedelta(seconds=5)
                )
                entity_id = entity_part.replace("_", ".")
            except Exception as parse_err:
                logger.debug(f"Failed to parse synthetic event id {event_id}: {parse_err}")
        else:
            context_id = event_id
        
        client = None
        try:
            client = InfluxDBClient(url=influxdb_url, token=influxdb_token, org=influxdb_org)
            query_api = client.query_api()
            
            if context_id:
                # Query based on context_id
                query = f'''
from(bucket: "{influxdb_bucket}")
  |> range(start: -30d)
  |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
  |> filter(fn: (r) => r["_field"] == "context_id")
  |> filter(fn: (r) => r["_value"] == "{context_id}")
  |> limit(n: 1)
'''
                context_result = query_api.query(query)
                
                event_time = None
                event_entity = None
                
                for table in context_result:
                    for record in table.records:
                        event_time = record.get_time()
                        event_entity = record.values.get("entity_id")
                
                if event_time:
                    timestamp_window = (
                        event_time - timedelta(seconds=5),
                        event_time + timedelta(seconds=5)
                    )
                    entity_id = event_entity
            
            if not timestamp_window:
                logger.debug(f"Unable to determine timestamp range for event {event_id}")
                return None
            
            start_iso = self._format_flux_time(timestamp_window[0])
            stop_iso = self._format_flux_time(timestamp_window[1])
            
            filter_entity_clause = ""
            if entity_id:
                filter_entity_clause = f'  |> filter(fn: (r) => r["entity_id"] == "{entity_id}")\n'
            
            detail_query = f'''
from(bucket: "{influxdb_bucket}")
  |> range(start: time(v: "{start_iso}"), stop: time(v: "{stop_iso}"))
  |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
{filter_entity_clause}  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: 1)
'''
            logger.debug(f"Executing event detail query:\n{detail_query}")
            detail_result = query_api.query(detail_query)
            
            for table in detail_result:
                for record in table.records:
                    event_payload = self._build_event_from_record(record, event_id)
                    if event_payload:
                        return event_payload
            
            return None
        except Exception as e:
            logger.error(f"Error fetching event {event_id} from InfluxDB: {e}", exc_info=True)
            return None
        finally:
            try:
                client.close()
            except Exception:
                pass

    def _build_event_from_record(self, record, fallback_id: str) -> Optional[EventData]:
        """Build EventData object from a pivoted Flux record."""
        try:
            values = record.values
            timestamp = record.get_time()
            entity_id = values.get("entity_id", "unknown")
            event_type = values.get("event_type", "unknown")
            context_id = values.get("context_id") or fallback_id
            
            def _parse_state(state_value: Optional[str]) -> Optional[Dict[str, Any]]:
                if state_value is None:
                    return None
                if isinstance(state_value, dict):
                    return state_value
                # Try JSON parsing first
                if isinstance(state_value, str):
                    try:
                        return json.loads(state_value)
                    except json.JSONDecodeError:
                        # Best-effort fallback: wrap raw string
                        return {"raw": state_value}
                return {"value": state_value}
            
            def _parse_attributes(attr_value: Optional[str]) -> Dict[str, Any]:
                if attr_value is None:
                    return {}
                if isinstance(attr_value, dict):
                    return attr_value
                if isinstance(attr_value, str):
                    try:
                        return json.loads(attr_value)
                    except json.JSONDecodeError:
                        return {"raw": attr_value}
                return {}
            
            event = EventData(
                id=context_id,
                timestamp=timestamp,
                entity_id=entity_id,
                event_type=event_type,
                old_state=_parse_state(values.get("old_state")),
                new_state=_parse_state(values.get("state")),
                attributes=_parse_attributes(values.get("attributes")),
                tags={
                    "domain": values.get("domain") or "unknown",
                    "device_class": values.get("device_class") or "unknown",
                    "service": "home-assistant"
                }
            )
            return event
        except Exception as e:
            logger.error(f"Failed to build EventData from record: {e}", exc_info=True)
            return None
    
    async def _search_events(self, search: EventSearch) -> List[EventData]:
        """Search events with text query"""
        all_events = []
        
        for service_name, service_url in self.service_urls.items():
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    async with session.post(f"{service_url}/events/search", json=search.model_dump()) as response:
                        if response.status == 200:
                            data = await response.json()
                            events = [EventData(**event) for event in data]
                            for event in events:
                                event.tags["service"] = service_name
                            all_events.extend(events)
                        else:
                            raise Exception(f"HTTP {response.status}")
            except Exception as e:
                logger.warning(f"Failed to search events in {service_name}: {e}")
        
        # Sort by timestamp (newest first)
        all_events.sort(key=lambda x: x.timestamp, reverse=True)
        
        return all_events[:search.limit]
    
    async def _get_all_events_stats(self, period: str) -> Dict[str, Any]:
        """Get event statistics for all services"""
        all_stats = {
            "total_events": 0,
            "events_per_minute": 0,
            "unique_entities": 0,
            "event_types": {},
            "services": {}
        }
        
        for service_name, service_url in self.service_urls.items():
            try:
                stats = await self._get_service_events_stats(service_name, period)
                all_stats["services"][service_name] = stats
                all_stats["total_events"] += stats.get("total_events", 0)
                all_stats["events_per_minute"] += stats.get("events_per_minute", 0)
                all_stats["unique_entities"] += stats.get("unique_entities", 0)
                
                # Merge event types
                for event_type, count in stats.get("event_types", {}).items():
                    all_stats["event_types"][event_type] = all_stats["event_types"].get(event_type, 0) + count
            except Exception as e:
                logger.warning(f"Failed to get stats from {service_name}: {e}")
                all_stats["services"][service_name] = {"error": str(e)}
        
        return all_stats
    
    async def _get_service_events_stats(self, service: str, period: str) -> Dict[str, Any]:
        """Get event statistics for a specific service"""
        service_url = self.service_urls[service]
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                params = {"period": period}
                async with session.get(f"{service_url}/events/stats", params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise Exception(f"HTTP {response.status}")
        except Exception as e:
            logger.error(f"Error getting events stats from {service}: {e}")
            return {"error": str(e)}
    
    async def _get_all_active_entities(self, limit: int) -> List[Dict[str, Any]]:
        """Get active entities from all services"""
        all_entities = []
        
        for service_name, service_url in self.service_urls.items():
            try:
                entities = await self._get_service_active_entities(service_name, limit)
                for entity in entities:
                    entity["service"] = service_name
                all_entities.extend(entities)
            except Exception as e:
                logger.warning(f"Failed to get active entities from {service_name}: {e}")
        
        # Remove duplicates and sort by activity
        unique_entities = {}
        for entity in all_entities:
            entity_id = entity["entity_id"]
            if entity_id not in unique_entities or entity["last_activity"] > unique_entities[entity_id]["last_activity"]:
                unique_entities[entity_id] = entity
        
        # Sort by last activity (most recent first)
        sorted_entities = sorted(unique_entities.values(), key=lambda x: x["last_activity"], reverse=True)
        
        return sorted_entities[:limit]
    
    async def _get_service_active_entities(self, service: str, limit: int) -> List[Dict[str, Any]]:
        """Get active entities from a specific service"""
        service_url = self.service_urls[service]
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                params = {"limit": limit}
                async with session.get(f"{service_url}/events/entities", params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise Exception(f"HTTP {response.status}")
        except Exception as e:
            logger.error(f"Error getting active entities from {service}: {e}")
            return []
    
    async def _get_all_event_types(self, limit: int) -> List[Dict[str, Any]]:
        """Get event types from all services"""
        all_event_types = {}
        
        for service_name, service_url in self.service_urls.items():
            try:
                event_types = await self._get_service_event_types(service_name, limit)
                for event_type in event_types:
                    event_type_name = event_type["event_type"]
                    if event_type_name not in all_event_types:
                        all_event_types[event_type_name] = {
                            "event_type": event_type_name,
                            "count": 0,
                            "services": []
                        }
                    all_event_types[event_type_name]["count"] += event_type["count"]
                    all_event_types[event_type_name]["services"].append(service_name)
            except Exception as e:
                logger.warning(f"Failed to get event types from {service_name}: {e}")
        
        # Sort by count (most frequent first)
        sorted_event_types = sorted(all_event_types.values(), key=lambda x: x["count"], reverse=True)
        
        return sorted_event_types[:limit]
    
    async def _get_service_event_types(self, service: str, limit: int) -> List[Dict[str, Any]]:
        """Get event types from a specific service"""
        service_url = self.service_urls[service]
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                params = {"limit": limit}
                async with session.get(f"{service_url}/events/types", params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise Exception(f"HTTP {response.status}")
        except Exception as e:
            logger.error(f"Error getting event types from {service}: {e}")
            return []
    
    async def _get_events_stream(self, duration: int, entity_id: Optional[str]) -> Dict[str, Any]:
        """Get real-time event stream"""
        stream_data = {
            "duration": duration,
            "entity_id": entity_id,
            "events": [],
            "start_time": datetime.now().isoformat(),
            "end_time": None
        }
        
        # This would typically involve WebSocket connections or Server-Sent Events
        # For now, we'll simulate by getting recent events
        end_time = datetime.now()
        start_time = end_time - timedelta(seconds=duration)
        
        event_filter = EventFilter(
            entity_id=entity_id,
            start_time=start_time,
            end_time=end_time
        )
        
        events = await self._get_all_events(event_filter, limit=1000, offset=0)
        stream_data["events"] = [event.dict() for event in events]
        stream_data["end_time"] = end_time.isoformat()
        
        return stream_data
    
    def _format_flux_time(self, value: datetime) -> str:
        """Format datetime for Flux queries in UTC."""
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)
        return value.isoformat().replace("+00:00", "Z")

    async def _get_events_from_influxdb(self, event_filter: EventFilter, limit: int, offset: int) -> List[EventData]:
        """
        Retrieve and transform events from InfluxDB using Flux query language.
        
        Builds optimized Flux queries with tag-based filtering for efficient event retrieval.
        Handles schema transformation from InfluxDB time-series format to EventData objects.
        
        Complexity: C (20) - High complexity due to query building and data transformation
        
        Args:
            event_filter (EventFilter): Filter criteria including:
                - entity_id: Filter by specific Home Assistant entity
                - event_type: Filter by event type (state_changed, etc.)
                - domain: Filter by domain (light, switch, etc.)
                - device_id: Filter by device ID (Epic 23.2)
                - area_id: Filter by area ID (Epic 23.2)
            limit (int): Maximum number of events to return
            offset (int): Number of events to skip (pagination)
            
        Returns:
            List[EventData]: List of transformed event objects with:
                - id: Event identifier
                - timestamp: ISO format timestamp
                - event_type: Type of event
                - entity_id: Home Assistant entity
                - state_value: Current state
                - attributes: Event metadata
                - domain, device_id, area_id, integration (if available)
        
        Query Strategy:
            1. Filter to single _field (context_id) to avoid duplicates
            2. Use tag-based filtering for efficiency (entity_id, event_type, domain)
            3. Apply time range (-24h default)
            4. Limit and offset for pagination
            5. Sort by _time descending (newest first)
        
        Example:
            >>> filter = EventFilter(entity_id="light.living_room", event_type="state_changed")
            >>> events = await endpoints._get_events_from_influxdb(filter, limit=10, offset=0)
            >>> print(f"Found {len(events)} events")
            >>> for event in events:
            ...     print(f"{event.timestamp}: {event.entity_id} = {event.state_value}")
        
        Note:
            High complexity arises from:
            - Dynamic Flux query construction based on filters
            - Multiple optional filter conditions
            - Schema transformation (InfluxDB record → EventData)
            - Null handling for optional fields
            - Pagination logic
            - Error handling for network/query failures
            
        Performance:
            - Tag-based filters are indexed (fast)
            - Field filter reduces duplicate records
            - Limit/offset support for large result sets
        """
        try:
            # Import InfluxDB client
            from influxdb_client import InfluxDBClient
            
            # Get InfluxDB configuration
            influxdb_url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
            influxdb_token = os.getenv("INFLUXDB_TOKEN", "homeiq-token")
            influxdb_org = os.getenv("INFLUXDB_ORG", "homeiq")
            influxdb_bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")
            
            # Create InfluxDB client
            client = InfluxDBClient(url=influxdb_url, token=influxdb_token, org=influxdb_org)
            query_api = client.query_api()
            
            # Build Flux query - SIMPLIFIED APPROACH (Context7 KB Pattern)
            # Context7 KB: /websites/influxdata-influxdb-v2
            # KEY INSIGHT: entity_id and event_type are TAGS (not fields)
            # PROBLEM: Without _field filter, we get one record PER FIELD (state_value, context_id, attributes, etc.)
            # SOLUTION: Filter to EXACTLY ONE field to get one record per event
            #           Tags (entity_id, event_type, domain) are automatically included

            # Determine time range. When callers provide explicit start/end times (e.g., nightly
            # analytics fetching the last 30 days), honor those values instead of defaulting to a
            # 24 hour window.
            if event_filter.start_time or event_filter.end_time:
                start_dt = event_filter.start_time or (datetime.now(timezone.utc) - timedelta(hours=24))
                start_iso = self._format_flux_time(start_dt)

                query = f'''
                from(bucket: "{influxdb_bucket}")
                  |> range(start: time(v: "{start_iso}"))
                '''

                if event_filter.end_time:
                    end_iso = self._format_flux_time(event_filter.end_time)
                    query = f'''
                from(bucket: "{influxdb_bucket}")
                  |> range(start: time(v: "{start_iso}"), stop: time(v: "{end_iso}"))
                '''
            else:
                query = f'''
                from(bucket: "{influxdb_bucket}")
                  |> range(start: -24h)
                '''

            query += '''
              |> filter(fn: (r) => r._measurement == "home_assistant_events")
              |> filter(fn: (r) => r._field == "context_id")
            '''
            
            # Add tag-based filters (these are indexed and efficient) - SANITIZED
            if event_filter.entity_id:
                entity_id_safe = sanitize_flux_value(event_filter.entity_id)
                query += f'  |> filter(fn: (r) => r.entity_id == "{entity_id_safe}")\n'
            if event_filter.event_type:
                event_type_safe = sanitize_flux_value(event_filter.event_type)
                query += f'  |> filter(fn: (r) => r.event_type == "{event_type_safe}")\n'

            # Epic 23.2: Add device_id and area_id filtering for spatial analytics - SANITIZED
            if event_filter.device_id:
                device_id_safe = sanitize_flux_value(event_filter.device_id)
                query += f'  |> filter(fn: (r) => r.device_id == "{device_id_safe}")\n'
            if event_filter.area_id:
                area_id_safe = sanitize_flux_value(event_filter.area_id)
                query += f'  |> filter(fn: (r) => r.area_id == "{area_id_safe}")\n'

            # Epic 23.4: Add entity_category filtering - SANITIZED
            if event_filter.entity_category:
                category_safe = sanitize_flux_value(event_filter.entity_category)
                query += f'  |> filter(fn: (r) => r.entity_category == "{category_safe}")\n'

            # Epic 23.4: Add exclude_category filtering (commonly used to hide diagnostic entities) - SANITIZED
            if event_filter.exclude_category:
                exclude_safe = sanitize_flux_value(event_filter.exclude_category)
                query += f'  |> filter(fn: (r) => r.entity_category != "{exclude_safe}")\n'
            
            # Group all tag-based series together, then get distinct records
            query += f'  |> group()\n'
            query += f'  |> sort(columns: ["_time"], desc: true)\n'
            query += f'  |> limit(n: {limit})\n'
            
            if offset > 0:
                query += f'  |> offset(n: {offset})\n'
            
            # Log the query for debugging
            logger.debug(f"Executing Flux query:\n{query}")
            
            # Execute query
            result = query_api.query(query)
            
            events = []
            seen_event_ids = set()  # Deduplication safety check
            table_count = 0
            record_count = 0
            
            for table in result:
                table_count += 1
                for record in table.records:
                    record_count += 1
                    # Context7 KB Approach: Filter to single field gives one record per event
                    # Tags (entity_id, event_type, domain) are present as record.values keys
                    # Field value is in _value column
                    
                    # Get tags from record (these are always present)
                    entity_id_val = record.values.get("entity_id") or "unknown"
                    event_type_val = record.values.get("event_type") or "unknown"
                    
                    # Generate unique event ID from timestamp + entity_id
                    timestamp = record.get_time().timestamp()
                    event_id = f"event_{timestamp}_{entity_id_val.replace('.', '_')}"
                    
                    # Skip if we've already seen this event (safety check)
                    if event_id in seen_event_ids:
                        continue
                    seen_event_ids.add(event_id)
                    
                    # Get the context_id field value (_value column)
                    context_id = record.values.get("_value") or event_id
                    
                    # Create event object with available data
                    # Note: Single-field query means old_state, new_state, attributes not available
                    # Trade-off: 1000x less bandwidth vs. complete event details
                    # All critical data (entity_id, event_type, timestamp) comes from tags
                    event = EventData(
                        id=context_id,
                        timestamp=record.get_time(),
                        entity_id=entity_id_val,
                        event_type=event_type_val,
                        old_state=None,  # Not available (would need second query or pivot)
                        new_state=None,  # Not available (would need second query or pivot)
                        attributes={},  # Not available (would need second query or pivot)
                        tags={
                            "domain": record.values.get("domain") or "unknown",
                            "device_class": record.values.get("device_class") or "unknown"
                        }
                    )
                    events.append(event)
            
            client.close()
            logger.info(f"InfluxDB Query Stats: {table_count} tables, {record_count} records, {len(events)} unique events (before final dedup)")
            
            # PRAGMATIC FIX: Python-level deduplication as final safety net
            # Even with field filtering, InfluxDB may return duplicates due to series grouping
            # This ensures we return exactly what was requested
            unique_events = []
            final_seen_ids = set()
            for event in events:
                if event.id not in final_seen_ids:
                    final_seen_ids.add(event.id)
                    unique_events.append(event)
                    if len(unique_events) >= limit:
                        break
            
            logger.info(f"Final: Returning {len(unique_events)} unique events (requested: {limit})")
            return unique_events
            
        except Exception as e:
            logger.error(f"Error querying InfluxDB: {e}")
            return []
    
    async def _trace_automation_chain(self, context_id: str, max_depth: int, include_details: bool) -> List[Dict[str, Any]]:
        """
        Trace automation chain by following context.parent_id relationships
        
        Epic 23.1: Implementation of automation causality tracking
        
        Args:
            context_id: Starting context ID
            max_depth: Maximum depth to traverse
            include_details: Whether to include full event details
        
        Returns:
            List of events in the automation chain
        """
        try:
            from influxdb_client import InfluxDBClient
            
            # Initialize InfluxDB client
            influxdb_url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
            influxdb_token = os.getenv("INFLUXDB_TOKEN")
            influxdb_org = os.getenv("INFLUXDB_ORG", "homeassistant")
            influxdb_bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")
            
            client = InfluxDBClient(url=influxdb_url, token=influxdb_token, org=influxdb_org)
            query_api = client.query_api()
            
            chain = []
            visited_contexts = set()
            current_context = context_id
            depth = 0
            
            while current_context and depth < max_depth:
                # Avoid circular references
                if current_context in visited_contexts:
                    logger.warning(f"Circular reference detected in automation chain: {current_context}")
                    break
                
                visited_contexts.add(current_context)
                
                # Query for events with this context_parent_id (children)
                query = f'''
                from(bucket: "{influxdb_bucket}")
                    |> range(start: -30d)
                    |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
                    |> filter(fn: (r) => r["_field"] == "context_parent_id")
                    |> filter(fn: (r) => r["_value"] == "{current_context}")
                    |> limit(n: 100)
                '''
                
                result = query_api.query(query)
                
                found_events = []
                next_context = None
                
                for table in result:
                    for record in table.records:
                        # Get the event context_id for next iteration
                        event_context_id = record.values.get("context_id")
                        
                        if include_details:
                            # Query full event details
                            event_detail_query = f'''
                            from(bucket: "{influxdb_bucket}")
                                |> range(start: -30d)
                                |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
                                |> filter(fn: (r) => r["context_id"] == "{event_context_id}")
                                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                                |> limit(n: 1)
                            '''
                            detail_result = query_api.query(event_detail_query)
                            
                            for detail_table in detail_result:
                                for detail_record in detail_table.records:
                                    event_info = {
                                        "depth": depth,
                                        "context_id": event_context_id,
                                        "context_parent_id": current_context,
                                        "timestamp": detail_record.get_time().isoformat(),
                                        "entity_id": detail_record.values.get("entity_id", "unknown"),
                                        "event_type": detail_record.values.get("event_type", "unknown"),
                                        "state": detail_record.values.get("state"),
                                        "old_state": detail_record.values.get("old_state")
                                    }
                                    found_events.append(event_info)
                        else:
                            # Minimal info
                            event_info = {
                                "depth": depth,
                                "context_id": event_context_id,
                                "context_parent_id": current_context,
                                "timestamp": record.get_time().isoformat()
                            }
                            found_events.append(event_info)
                        
                        # Use first event's context_id for next iteration
                        if not next_context:
                            next_context = event_context_id
                
                chain.extend(found_events)
                
                # Move to next level (follow first child)
                current_context = next_context
                depth += 1
            
            client.close()
            
            logger.info(f"Traced automation chain for {context_id}: {len(chain)} events, {depth} levels deep")
            return chain
            
        except Exception as e:
            logger.error(f"Error tracing automation chain: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

