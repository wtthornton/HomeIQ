"""
Devices and Entities Endpoints for Data API
Migrated from admin-api as part of Epic 13 Story 13.2
Story 22.2: Updated to use SQLite storage
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# Add shared directory to path
from pathlib import Path
sys.path.append(str(Path(__file__).parent / '../../shared'))

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from shared.influxdb_query_client import InfluxDBQueryClient

from .cache import cache

# Story 22.2: SQLite models and database
from .database import get_db
from .flux_utils import sanitize_flux_value
from .models import Device, Entity, Service
from .services.entity_registry import EntityRegistry
from .services.device_health import get_health_service
from .services.device_classifier import get_classifier_service
from .services.setup_assistant import get_setup_assistant
from .services.device_database import get_device_database_service
from .services.capability_discovery import get_capability_service
from .services.device_recommender import get_recommender_service

logger = logging.getLogger(__name__)




# Response Models
class DeviceResponse(BaseModel):
    """Device response model"""
    device_id: str = Field(description="Unique device identifier")
    name: str = Field(description="Device name")
    manufacturer: str = Field(description="Device manufacturer")
    model: str = Field(description="Device model")
    integration: str | None = Field(default=None, description="Integration/platform name")
    sw_version: str | None = Field(default=None, description="Software/firmware version")
    area_id: str | None = Field(default=None, description="Area/room ID")
    config_entry_id: str | None = Field(default=None, description="Config entry ID (source tracking)")
    via_device: str | None = Field(default=None, description="Parent device ID (via_device relationship)")
    # Phase 1.1: Device intelligence fields
    device_type: str | None = Field(default=None, description="Device classification: fridge, light, sensor, etc.")
    device_category: str | None = Field(default=None, description="Device category: appliance, lighting, security, climate")
    power_consumption_idle_w: float | None = Field(default=None, description="Standby power consumption (W)")
    power_consumption_active_w: float | None = Field(default=None, description="Active power consumption (W)")
    power_consumption_max_w: float | None = Field(default=None, description="Peak power consumption (W)")
    setup_instructions_url: str | None = Field(default=None, description="Link to setup guide")
    troubleshooting_notes: str | None = Field(default=None, description="Common issues and solutions")
    device_features_json: str | None = Field(default=None, description="Structured capabilities (JSON string)")
    community_rating: float | None = Field(default=None, description="Rating from Device Database")
    last_capability_sync: str | None = Field(default=None, description="When capabilities were last updated")
    entity_count: int = Field(default=0, description="Number of entities")
    timestamp: str = Field(description="Last update timestamp")
    # Phase 2: Device Registry 2025 Attributes (Important)
    labels: list[str] | None = Field(default=None, description="Array of label IDs for organizational filtering")
    # Phase 3: Device Registry 2025 Attributes (Nice to Have)
    serial_number: str | None = Field(default=None, description="Optional serial number (if available from integration)")
    model_id: str | None = Field(default=None, description="Optional model ID (manufacturer identifier, may differ from model)")
    # Device status (computed based on last_seen)
    status: str = Field(default="active", description="Device status: 'active' if seen within 30 days, 'inactive' otherwise")


class EntityResponse(BaseModel):
    """Entity response model"""
    entity_id: str = Field(description="Unique entity identifier")
    device_id: str | None = Field(default=None, description="Associated device ID")
    domain: str = Field(description="Entity domain (light, sensor, etc)")
    platform: str = Field(description="Integration platform")
    unique_id: str | None = Field(default=None, description="Unique ID within platform")
    area_id: str | None = Field(default=None, description="Area/room ID")
    disabled: bool = Field(default=False, description="Whether entity is disabled")
    config_entry_id: str | None = Field(default=None, description="Config entry ID (source tracking)")
    timestamp: str = Field(description="Last update timestamp")
    # Entity Registry Name Fields (2025 HA API)
    name: str | None = Field(default=None, description="Entity Registry name (source of truth)")
    name_by_user: str | None = Field(default=None, description="User-customized name (highest priority)")
    original_name: str | None = Field(default=None, description="Original name from integration")
    friendly_name: str | None = Field(default=None, description="Computed friendly name (name_by_user > name > original_name)")
    # Entity Capabilities
    supported_features: int | None = Field(default=None, description="Bitmask of supported features")
    capabilities: list[str] | None = Field(default=None, description="Parsed capabilities list")
    available_services: list[str] | None = Field(default=None, description="List of available service calls")
    # Entity Attributes
    icon: str | None = Field(default=None, description="Current icon (may be user-customized)")
    original_icon: str | None = Field(default=None, description="Original icon from integration/platform")
    device_class: str | None = Field(default=None, description="Device class (motion, door, temperature, etc)")
    unit_of_measurement: str | None = Field(default=None, description="Unit of measurement for sensors")
    # Phase 1: Entity Registry 2025 Attributes (Critical)
    aliases: list[str] | None = Field(default=None, description="Array of alternative names for entity resolution")
    # Phase 2: Entity Registry 2025 Attributes (Important)
    labels: list[str] | None = Field(default=None, description="Array of label IDs for organizational filtering")
    options: dict[str, Any] | None = Field(default=None, description="Entity-specific options/config (e.g., default brightness)")


class IntegrationResponse(BaseModel):
    """Integration/Config Entry response model"""
    entry_id: str = Field(description="Config entry ID")
    domain: str = Field(description="Integration domain")
    title: str = Field(description="Integration title")
    state: str = Field(description="Setup state")
    version: int = Field(default=1, description="Config version")
    timestamp: str = Field(description="Last update timestamp")


class DevicesListResponse(BaseModel):
    """Devices list response"""
    devices: list[DeviceResponse]
    count: int
    limit: int


class EntitiesListResponse(BaseModel):
    """Entities list response"""
    entities: list[EntityResponse]
    count: int
    limit: int


class IntegrationsListResponse(BaseModel):
    """Integrations list response"""
    integrations: list[IntegrationResponse]
    count: int


# Create router
router = APIRouter(tags=["Devices & Entities"])


# InfluxDB client (initialized on first use to avoid circular imports)
influxdb_client = InfluxDBQueryClient()


def compute_device_status(last_seen: datetime | None, inactive_days: int = 30) -> str:
    """
    Compute device status based on last_seen timestamp.
    
    Args:
        last_seen: Last time device was seen (datetime or None)
        inactive_days: Number of days after which device is considered inactive (default: 30)
    
    Returns:
        "active" if device was seen within inactive_days, "inactive" otherwise
    """
    if last_seen is None:
        return "inactive"
    
    # Calculate days since last seen
    days_ago = (datetime.utcnow() - last_seen.replace(tzinfo=None)).days
    
    # Device is active if seen within inactive_days
    return "active" if days_ago <= inactive_days else "inactive"


@router.get("/api/devices", response_model=DevicesListResponse)
async def list_devices(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of devices to return"),
    manufacturer: str | None = Query(default=None, description="Filter by manufacturer"),
    model: str | None = Query(default=None, description="Filter by model"),
    area_id: str | None = Query(default=None, description="Filter by area/room"),
    platform: str | None = Query(default=None, description="Filter by integration platform"),
    device_type: str | None = Query(default=None, description="Filter by device type (Phase 1.1)"),
    device_category: str | None = Query(default=None, description="Filter by device category (Phase 1.1)"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all discovered devices from Home Assistant (SQLite storage)

    Story 22.2: Simple, fast SQLite queries with JOIN for entity counts
    Enhanced: Platform filtering support for Top Integrations feature
    Cached: 5-minute cache for improved performance
    """
    try:
        # Create cache key from query parameters (Phase 1.1: include device_type and device_category)
        cache_key = f"devices:{limit}:{manufacturer}:{model}:{area_id}:{platform}:{device_type}:{device_category}"

        # Try to get from cache
        cached_result = await cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for {cache_key}")
            return cached_result
        # Build query with entity count
        # SQLAlchemy 2.0: When using group_by with aggregates, select specific columns
        # Only select columns that exist in the current database schema
        # Phase 1.1 columns (device_type, device_category, etc.) may not exist yet
        device_columns = [
            Device.device_id,
            Device.name,
            Device.manufacturer,
            Device.model,
            Device.integration,
            Device.sw_version,
            Device.area_id,
            Device.config_entry_id,
            Device.via_device,
            Device.last_seen,
            # Phase 1.1: Device intelligence fields (for filtering and response)
            Device.device_type,
            Device.device_category,
            # Phase 2-3: Device Registry 2025 Attributes (may not exist before migration)
            Device.labels,
            Device.serial_number,
            Device.model_id
        ]
        
        if platform:
            # Join with entities to filter by platform
            query = select(*device_columns, func.count(Entity.entity_id).label('entity_count'))\
                .join(Entity, Device.device_id == Entity.device_id)\
                .where(Entity.platform == platform)\
                .group_by(*device_columns)
        else:
            # Standard query without platform filter
            query = select(*device_columns, func.count(Entity.entity_id).label('entity_count'))\
                .outerjoin(Entity, Device.device_id == Entity.device_id)\
                .group_by(*device_columns)

        # Apply additional filters (simple WHERE clauses)
        if manufacturer:
            query = query.where(Device.manufacturer == manufacturer)
        if model:
            query = query.where(Device.model == model)
        if area_id:
            query = query.where(Device.area_id == area_id)
        # Phase 1.1: Device intelligence filters
        # Only filter if value is provided and not empty string
        # Exclude NULL and empty string values when filtering
        if device_type:
            query = query.where(
                and_(
                    Device.device_type.isnot(None),
                    Device.device_type != '',
                    Device.device_type == device_type
                )
            )
        if device_category:
            query = query.where(
                and_(
                    Device.device_category.isnot(None),
                    Device.device_category != '',
                    Device.device_category == device_category
                )
            )

        # Apply limit
        query = query.limit(limit)

        # Execute
        result = await db.execute(query)
        rows = result.all()

        # Convert to response
        # Schema: device columns + entity_count
        # Note: Phase 2-3 fields (labels, serial_number, model_id) may not exist before migration
        device_responses = []
        for row in rows:
            try:
                # Unpack row - handle variable length based on schema version
                row_len = len(row)
                device_id = row[0]
                name = row[1]
                manufacturer = row[2] or "Unknown"
                model = row[3] or "Unknown"
                integration = row[4]
                sw_version = row[5]
                area_id = row[6]
                config_entry_id = row[7]
                via_device = row[8]
                last_seen = row[9] if row_len > 9 else None
                # Phase 1.1: Device intelligence fields
                device_type = row[10] if row_len > 10 else None
                device_category = row[11] if row_len > 11 else None
                # Phase 2-3: New fields (may not exist before migration)
                labels = row[12] if row_len > 12 and hasattr(Device, 'labels') else None
                serial_number = row[13] if row_len > 13 and hasattr(Device, 'serial_number') else None
                model_id = row[14] if row_len > 14 and hasattr(Device, 'model_id') else None
                entity_count = row[-1]  # Last column is always entity_count
                
                # Compute device status based on last_seen
                device_status = compute_device_status(last_seen)
                
                device_responses.append(DeviceResponse(
                    device_id=device_id,
                    name=name,
                    manufacturer=manufacturer,
                    model=model,
                    integration=integration,
                    sw_version=sw_version,
                    area_id=area_id,
                    config_entry_id=config_entry_id,
                    via_device=via_device,
                    device_type=device_type,  # Phase 1.1: from database
                    device_category=device_category,  # Phase 1.1: from database
                    power_consumption_idle_w=None,  # Phase 1.1: not in current schema
                    power_consumption_active_w=None,  # Phase 1.1: not in current schema
                    power_consumption_max_w=None,  # Phase 1.1: not in current schema
                    setup_instructions_url=None,  # Phase 1.1: not in current schema
                    troubleshooting_notes=None,  # Phase 1.1: not in current schema
                    device_features_json=None,  # Phase 1.1: not in current schema
                    community_rating=None,  # Phase 1.1: not in current schema
                    last_capability_sync=None,  # Phase 1.1: not in current schema
                    # Phase 2-3: Device Registry 2025 Attributes
                    labels=labels if isinstance(labels, list) else None,
                    serial_number=serial_number,
                    model_id=model_id,
                    status=device_status,
                    entity_count=entity_count,
                    timestamp=last_seen.isoformat() if last_seen else datetime.now().isoformat()
                ))
            except (IndexError, AttributeError) as e:
                # Handle case where new columns don't exist yet (before migration)
                logger.debug(f"Row unpacking error (may be pre-migration schema): {e}")
                # Fallback to basic fields only
                last_seen_fallback = row[9] if len(row) > 9 and row[9] else None
                device_status_fallback = compute_device_status(last_seen_fallback)
                
                # Fallback: try to extract device_type and device_category if available
                fallback_device_type = row[10] if len(row) > 10 else None
                fallback_device_category = row[11] if len(row) > 11 else None
                
                device_responses.append(DeviceResponse(
                    device_id=row[0],
                    name=row[1],
                    manufacturer=row[2] or "Unknown",
                    model=row[3] or "Unknown",
                    integration=row[4],
                    sw_version=row[5],
                    area_id=row[6],
                    config_entry_id=row[7],
                    via_device=row[8],
                    device_type=fallback_device_type,
                    device_category=fallback_device_category,
                    power_consumption_idle_w=None,
                    power_consumption_active_w=None,
                    power_consumption_max_w=None,
                    setup_instructions_url=None,
                    troubleshooting_notes=None,
                    device_features_json=None,
                    community_rating=None,
                    last_capability_sync=None,
                    labels=None,  # Will be populated after migration
                    serial_number=None,  # Will be populated after migration
                    model_id=None,  # Will be populated after migration
                    status=device_status_fallback,
                    entity_count=row[-1],
                    timestamp=last_seen_fallback.isoformat() if last_seen_fallback else datetime.now().isoformat()
                ))

        result = DevicesListResponse(
            devices=device_responses,
            count=len(device_responses),
            limit=limit
        )

        # Cache the result
        await cache.set(cache_key, result, ttl=300)  # 5 minutes

        return result

    except Exception as e:
        logger.error(f"Error listing devices from SQLite: {e}", exc_info=True)
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Full traceback: {error_details}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve devices: {str(e)}"
        ) from e


@router.get("/api/devices/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: str, db: AsyncSession = Depends(get_db)):
    """Get device by ID (SQLite) - Story 22.2"""
    try:
        # Simple SELECT with entity count (including Phase 1.1 device intelligence fields)
        device_columns = [
            Device.device_id,
            Device.name,
            Device.manufacturer,
            Device.model,
            Device.sw_version,
            Device.area_id,
            Device.integration,
            Device.config_entry_id,
            Device.via_device,
            Device.device_type,
            Device.device_category,
            Device.power_consumption_idle_w,
            Device.power_consumption_active_w,
            Device.power_consumption_max_w,
            Device.setup_instructions_url,
            Device.troubleshooting_notes,
            Device.device_features_json,
            Device.community_rating,
            Device.last_capability_sync,
            Device.last_seen,
            # Phase 2-3: Device Registry 2025 Attributes (may not exist before migration)
            Device.labels,
            Device.serial_number,
            Device.model_id
        ]
        
        query = select(*device_columns, func.count(Entity.entity_id).label('entity_count'))\
            .outerjoin(Entity, Device.device_id == Entity.device_id)\
            .where(Device.device_id == device_id)\
            .group_by(*device_columns)

        result = await db.execute(query)
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

        # Unpack row tuple (including Phase 1.1 fields and Phase 2-3 2025 attributes)
        (device_id_col, name, manufacturer, model, sw_version, area_id,
         integration, config_entry_id, via_device, device_type, device_category,
         power_consumption_idle_w, power_consumption_active_w, power_consumption_max_w,
         setup_instructions_url, troubleshooting_notes, device_features_json,
         community_rating, last_capability_sync, last_seen,
         labels, serial_number, model_id, entity_count) = row

        # Compute device status based on last_seen
        device_status = compute_device_status(last_seen)

        return DeviceResponse(
            device_id=device_id_col,
            name=name,
            manufacturer=manufacturer or "Unknown",
            model=model or "Unknown",
            integration=integration,
            sw_version=sw_version,
            area_id=area_id,
            config_entry_id=config_entry_id,
            via_device=via_device,
            device_type=device_type,
            device_category=device_category,
            power_consumption_idle_w=power_consumption_idle_w,
            power_consumption_active_w=power_consumption_active_w,
            power_consumption_max_w=power_consumption_max_w,
            setup_instructions_url=setup_instructions_url,
            troubleshooting_notes=troubleshooting_notes,
            device_features_json=device_features_json,
            community_rating=community_rating,
            last_capability_sync=last_capability_sync.isoformat() if last_capability_sync else None,
            # Phase 2-3: Device Registry 2025 Attributes
            labels=labels if isinstance(labels, list) else None,
            serial_number=serial_number,
            model_id=model_id,
            status=device_status,
            entity_count=entity_count,
            timestamp=last_seen.isoformat() if last_seen else datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve device: {str(e)}") from e


# Epic 23.5: Device Reliability Endpoint
@router.get("/api/devices/reliability", response_model=dict[str, Any])
async def get_device_reliability(
    period: str = Query(default="7d", description="Time period for analysis (1d, 7d, 30d)"),
    group_by: str = Query(default="manufacturer", description="Group by manufacturer or model")
):
    """
    Get device reliability metrics grouped by manufacturer or model
    
    Epic 23.5: Analyzes event data from InfluxDB to identify device reliability patterns
    
    Returns:
    - Event counts by manufacturer/model
    - Coverage percentage (% of events with device metadata)
    - Top manufacturers/models by event volume
    """
    client = None
    try:
        from influxdb_client import InfluxDBClient

        # Get InfluxDB configuration
        influxdb_url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
        influxdb_token = os.getenv("INFLUXDB_TOKEN")
        influxdb_org = os.getenv("INFLUXDB_ORG", "homeassistant")
        influxdb_bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")

        # Create client
        client = InfluxDBClient(url=influxdb_url, token=influxdb_token, org=influxdb_org)
        query_api = client.query_api()

        # Build query based on group_by parameter (sanitized)
        field_name = sanitize_flux_value("manufacturer" if group_by == "manufacturer" else "model")
        period_sanitized = sanitize_flux_value(period)
        if not period_sanitized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid period supplied"
            )

        query = f'''
        from(bucket: "{influxdb_bucket}")
          |> range(start: -{period_sanitized})
          |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
          |> filter(fn: (r) => r["_field"] == "{field_name}")
          |> group(columns: ["_value"])
          |> count()
          |> sort(desc: true)
        '''

        result = query_api.query(query)

        # Parse results
        reliability_data = []
        total_events = 0

        for table in result:
            for record in table.records:
                group_value = record.values.get("_value", "Unknown")
                count = record.get_value()
                total_events += count

                reliability_data.append({
                    field_name: group_value,
                    "event_count": count,
                    "percentage": 0  # Will calculate after total is known
                })

        # Calculate percentages
        for item in reliability_data:
            if total_events > 0:
                item["percentage"] = round((item["event_count"] / total_events) * 100, 2)

        # Get total event count for coverage calculation
        # Total events count - OPTIMIZED (Context7 KB Pattern)
        # FIX: Add _field filter to count unique events, not field instances
        total_query = f'''
        from(bucket: "{influxdb_bucket}")
          |> range(start: -{period_sanitized})
          |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
          |> filter(fn: (r) => r._field == "context_id")
          |> count()
        '''

        total_result = query_api.query(total_query)
        all_events_count = 0
        for table in total_result:
            for record in table.records:
                all_events_count += record.get_value()

        # Calculate coverage
        coverage = round((total_events / all_events_count) * 100, 2) if all_events_count > 0 else 0

        return {
            "period": period,
            "group_by": group_by,
            "total_events_analyzed": total_events,
            "total_events_in_period": all_events_count,
            "metadata_coverage_percentage": coverage,
            "reliability_data": reliability_data[:20],  # Top 20
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting device reliability: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get device reliability metrics: {str(e)}"
        ) from e
    finally:
        if client:
            try:
                client.close()
            except Exception as close_err:
                logger.warning(f"Failed to close InfluxDB client: {close_err}")


@router.get("/api/entities", response_model=EntitiesListResponse)
async def list_entities(
    request: Request,
    limit: int = Query(default=100, ge=1, le=10000, description="Maximum number of entities to return"),
    domain: str | None = Query(default=None, description="Filter by domain (light, sensor, etc)"),
    platform: str | None = Query(default=None, description="Filter by platform"),
    device_id: str | None = Query(default=None, description="Filter by device ID"),
    db: AsyncSession = Depends(get_db)
):
    """List entities (SQLite) - Story 22.2"""
    try:
        # Debug: Check raw query parameters
        raw_query = dict(request.query_params)
        logger.info(f"🔍 [list_entities] Raw query params: {raw_query}")
        logger.info(f"🔍 [list_entities] Parsed params: limit={limit}, domain={domain}, platform={platform}, device_id={device_id}")

        # Override with raw query params if FastAPI didn't parse them
        if 'device_id' in raw_query and not device_id:
            device_id = raw_query.get('device_id')
            logger.warning(f"⚠️ [list_entities] Using device_id from raw query: {device_id}")
        if 'limit' in raw_query and limit == 100:
            try:
                limit = int(raw_query.get('limit', 100))
                logger.warning(f"⚠️ [list_entities] Using limit from raw query: {limit}")
            except (ValueError, TypeError):
                pass

        # Build query
        query = select(Entity)

        # Apply filters
        if domain:
            query = query.where(Entity.domain == domain)
            logger.debug(f"🔍 [list_entities] Applied domain filter: {domain}")
        if platform:
            query = query.where(Entity.platform == platform)
            logger.debug(f"🔍 [list_entities] Applied platform filter: {platform}")
        if device_id:
            # Use case-insensitive comparison to handle potential case mismatches
            # SQLite's default comparison is case-sensitive, so we normalize both sides
            query = query.where(func.lower(Entity.device_id) == func.lower(device_id))
            logger.info(f"🔍 [list_entities] Applied device_id filter (case-insensitive): {device_id}")

        # Apply limit
        query = query.limit(limit)

        # Execute
        result = await db.execute(query)
        entities_data = result.scalars().all()

        # Convert to response
        entity_responses = [
            EntityResponse(
                entity_id=entity.entity_id,
                device_id=entity.device_id,
                domain=entity.domain,
                platform=entity.platform or "unknown",
                unique_id=entity.unique_id,
                area_id=entity.area_id,
                disabled=entity.disabled,
                # Entity Registry Name Fields (2025 HA API)
                name=entity.name,
                name_by_user=entity.name_by_user,
                original_name=entity.original_name,
                friendly_name=entity.friendly_name,
                # Entity Capabilities
                supported_features=entity.supported_features,
                capabilities=entity.capabilities if isinstance(entity.capabilities, list) else None,
                available_services=entity.available_services if isinstance(entity.available_services, list) else None,
                # Entity Attributes
                icon=entity.icon,  # Current icon
                original_icon=entity.original_icon,  # Phase 1: Original icon
                device_class=entity.device_class,
                unit_of_measurement=entity.unit_of_measurement,
                # Phase 1: Entity Registry 2025 Attributes (Critical)
                aliases=entity.aliases if isinstance(entity.aliases, list) else None,
                # Phase 2: Entity Registry 2025 Attributes (Important)
                labels=entity.labels if isinstance(entity.labels, list) else None,
                options=entity.options if isinstance(entity.options, dict) else None,
                timestamp=entity.updated_at.isoformat() if entity.updated_at else (entity.created_at.isoformat() if entity.created_at else datetime.now().isoformat())
            )
            for entity in entities_data
        ]

        return EntitiesListResponse(
            entities=entity_responses,
            count=len(entity_responses),
            limit=limit
        )
    except Exception as e:
        logger.error(f"Error listing entities from SQLite: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve entities: {str(e)}") from e


@router.get("/api/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(entity_id: str, db: AsyncSession = Depends(get_db)):
    """Get entity by ID (SQLite) - Story 22.2"""
    try:
        # Simple SELECT
        result = await db.execute(select(Entity).where(Entity.entity_id == entity_id))
        entity = result.scalar_one_or_none()

        if not entity:
            raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")

        return EntityResponse(
            entity_id=entity.entity_id,
            device_id=entity.device_id,
            domain=entity.domain,
            platform=entity.platform or "unknown",
            unique_id=entity.unique_id,
            area_id=entity.area_id,
            disabled=entity.disabled,
            config_entry_id=entity.config_entry_id,
                # Entity Registry Name Fields (2025 HA API)
                name=entity.name,
                name_by_user=entity.name_by_user,
                original_name=entity.original_name,
                friendly_name=entity.friendly_name,
                # Entity Capabilities
                supported_features=entity.supported_features,
                capabilities=entity.capabilities if isinstance(entity.capabilities, list) else None,
                available_services=entity.available_services if isinstance(entity.available_services, list) else None,
                # Entity Attributes
                icon=entity.icon,  # Current icon
                original_icon=entity.original_icon,  # Phase 1: Original icon
                device_class=entity.device_class,
                unit_of_measurement=entity.unit_of_measurement,
                # Phase 1: Entity Registry 2025 Attributes (Critical)
                aliases=entity.aliases if isinstance(entity.aliases, list) else None,
                # Phase 2: Entity Registry 2025 Attributes (Important)
                labels=entity.labels if isinstance(entity.labels, list) else None,
                options=entity.options if isinstance(entity.options, dict) else None,
                timestamp=entity.updated_at.isoformat() if entity.updated_at else (entity.created_at.isoformat() if entity.created_at else datetime.now().isoformat())
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting entity {entity_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve entity: {str(e)}") from e


# Relationship Query Endpoints

@router.get("/api/entities/by-device/{device_id}")
async def get_entities_by_device(
    device_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all entities for a device
    
    Args:
        device_id: Device ID
        
    Returns:
        List of EntityRegistryEntry instances
    """
    try:
        registry = EntityRegistry(db)
        entities = await registry.get_entities_by_device(device_id)
        return {
            "success": True,
            "device_id": device_id,
            "entities": [entry.to_dict() for entry in entities],
            "count": len(entities)
        }
    except Exception as e:
        logger.error(f"Error getting entities by device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get entities by device: {str(e)}"
        ) from e


@router.get("/api/entities/{entity_id}/siblings")
async def get_sibling_entities(
    entity_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get sibling entities (entities from same device)
    
    Args:
        entity_id: Entity ID
        
    Returns:
        List of EntityRegistryEntry instances (sibling entities)
    """
    try:
        registry = EntityRegistry(db)
        siblings = await registry.get_sibling_entities(entity_id)
        # Filter out the entity itself
        siblings = [s for s in siblings if s.entity_id != entity_id]
        return {
            "success": True,
            "entity_id": entity_id,
            "siblings": [entry.to_dict() for entry in siblings],
            "count": len(siblings)
        }
    except Exception as e:
        logger.error(f"Error getting sibling entities for {entity_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sibling entities: {str(e)}"
        ) from e


@router.get("/api/entities/{entity_id}/device")
async def get_device_for_entity(
    entity_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get device for an entity
    
    Args:
        entity_id: Entity ID
        
    Returns:
        Device information
    """
    try:
        registry = EntityRegistry(db)
        device = await registry.get_device_for_entity(entity_id)

        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device not found for entity {entity_id}"
            )

        return {
            "success": True,
            "entity_id": entity_id,
            "device": {
                "device_id": device.device_id,
                "name": device.name,
                "manufacturer": device.manufacturer,
                "model": device.model,
                "sw_version": device.sw_version,
                "area_id": device.area_id,
                "integration": device.integration,
                "config_entry_id": device.config_entry_id,
                "via_device": device.via_device
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device for entity {entity_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get device for entity: {str(e)}"
        ) from e


@router.get("/api/entities/by-area/{area_id}")
async def get_entities_in_area(
    area_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all entities in an area
    
    Args:
        area_id: Area ID
        
    Returns:
        List of EntityRegistryEntry instances
    """
    try:
        registry = EntityRegistry(db)
        entities = await registry.get_entities_in_area(area_id)
        return {
            "success": True,
            "area_id": area_id,
            "entities": [entry.to_dict() for entry in entities],
            "count": len(entities)
        }
    except Exception as e:
        logger.error(f"Error getting entities in area {area_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get entities in area: {str(e)}"
        ) from e


@router.get("/api/entities/by-config-entry/{config_entry_id}")
async def get_entities_by_config_entry(
    config_entry_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get entities by config entry ID
    
    Args:
        config_entry_id: Config entry ID
        
    Returns:
        List of EntityRegistryEntry instances
    """
    try:
        registry = EntityRegistry(db)
        entities = await registry.get_entities_by_config_entry(config_entry_id)
        return {
            "success": True,
            "config_entry_id": config_entry_id,
            "entities": [entry.to_dict() for entry in entities],
            "count": len(entities)
        }
    except Exception as e:
        logger.error(f"Error getting entities by config entry {config_entry_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get entities by config entry: {str(e)}"
        ) from e


@router.get("/api/devices/{device_id}/hierarchy")
async def get_device_hierarchy(
    device_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get device hierarchy (via_device relationships)
    
    Args:
        device_id: Device ID
        
    Returns:
        Dictionary with device hierarchy information
    """
    try:
        registry = EntityRegistry(db)
        hierarchy = await registry.get_device_hierarchy(device_id)
        return {
            "success": True,
            **hierarchy
        }
    except Exception as e:
        logger.error(f"Error getting device hierarchy for {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get device hierarchy: {str(e)}"
        ) from e


@router.get("/api/integrations/{platform}/performance")
async def get_integration_performance(
    platform: str,
    period: str = Query(default="1h", description="Time period for metrics (1h, 24h, 7d)")
):
    """
    Get performance metrics for a specific integration platform (Phase 3.3)
    
    Returns event rate, error rate, response time, and discovery status
    """
    try:
        from influxdb_client import InfluxDBClient

        # Get InfluxDB configuration
        influxdb_url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
        influxdb_token = os.getenv("INFLUXDB_TOKEN")
        influxdb_org = os.getenv("INFLUXDB_ORG", "homeassistant")
        influxdb_bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")

        # Create client
        client = InfluxDBClient(url=influxdb_url, token=influxdb_token, org=influxdb_org)
        query_api = client.query_api()

        # Calculate events per minute
        # Event rate query - OPTIMIZED (Context7 KB Pattern)
        # FIX: Add _field filter to count unique events, not field instances
        platform_sanitized = sanitize_flux_value(platform)
        period_sanitized = sanitize_flux_value(period)

        event_rate_query = f'''
        from(bucket: "{influxdb_bucket}")
          |> range(start: -{period_sanitized})
          |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
          |> filter(fn: (r) => r._field == "context_id")
          |> filter(fn: (r) => r["platform"] == "{platform_sanitized}")
          |> count()
        '''

        event_result = query_api.query(event_rate_query)
        total_events = 0
        for table in event_result:
            for record in table.records:
                total_events += record.get_value()

        # Calculate time period in minutes
        period_minutes = {
            "1h": 60,
            "24h": 1440,
            "7d": 10080
        }.get(period, 60)

        events_per_minute = round(total_events / period_minutes, 2) if period_minutes > 0 else 0

        # Estimate error rate (events with error field)
        # Error count query - OPTIMIZED (Context7 KB Pattern)
        # FIX: Add _field filter to count unique events with errors
        error_query = f'''
        from(bucket: "{influxdb_bucket}")
          |> range(start: -{period_sanitized})
          |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
          |> filter(fn: (r) => r._field == "context_id")
          |> filter(fn: (r) => r["platform"] == "{platform_sanitized}")
          |> filter(fn: (r) => exists r["error"])
          |> count()
        '''

        error_result = query_api.query(error_query)
        total_errors = 0
        for table in error_result:
            for record in table.records:
                total_errors += record.get_value()

        error_rate = round((total_errors / total_events) * 100, 2) if total_events > 0 else 0

        # Calculate average response time (if available)
        # Response time query - OPTIMIZED (Context7 KB Pattern)
        # FIX: Filter by response_time field specifically
        response_time_query = f'''
        from(bucket: "{influxdb_bucket}")
          |> range(start: -{period_sanitized})
          |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
          |> filter(fn: (r) => r._field == "response_time")
          |> filter(fn: (r) => r["platform"] == "{platform_sanitized}")
          |> mean()
        '''

        response_result = query_api.query(response_time_query)
        avg_response_time = 0
        for table in response_result:
            for record in table.records:
                avg_response_time = round(record.get_value(), 2)

        # Device discovery status (simplified - check if we have recent device updates)
        discovery_query = f'''
        from(bucket: "{influxdb_bucket}")
          |> range(start: -5m)
          |> filter(fn: (r) => r["_measurement"] == "devices")
          |> filter(fn: (r) => r["platform"] == "{platform_sanitized}")
          |> count()
        '''

        discovery_result = query_api.query(discovery_query)
        recent_discoveries = 0
        for table in discovery_result:
            for record in table.records:
                recent_discoveries += record.get_value()

        discovery_status = "active" if recent_discoveries > 0 else "paused"

        return {
            "platform": platform,
            "period": period,
            "events_per_minute": events_per_minute,
            "error_rate": error_rate,
            "avg_response_time": avg_response_time if avg_response_time > 0 else None,
            "device_discovery_status": discovery_status,
            "total_events": total_events,
            "total_errors": total_errors,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting performance metrics for {platform}: {e}")
        # Return default metrics on error
        return {
            "platform": platform,
            "period": period,
            "events_per_minute": 0,
            "error_rate": 0,
            "avg_response_time": None,
            "device_discovery_status": "unknown",
            "total_events": 0,
            "total_errors": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
    finally:
        if client:
            try:
                client.close()
            except Exception as close_err:
                logger.warning(f"Failed to close InfluxDB client: {close_err}")


@router.get("/api/integrations/{platform}/analytics")
async def get_integration_analytics(
    platform: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get analytics for a specific integration platform (Phase 2.3)
    
    Returns device count, entity count, and entity breakdown by domain
    """
    try:
        # Get device count for this platform
        device_query = select(func.count(func.distinct(Device.device_id)))\
            .select_from(Device)\
            .join(Entity, Device.device_id == Entity.device_id)\
            .where(Entity.platform == platform)

        device_result = await db.execute(device_query)
        device_count = device_result.scalar() or 0

        # Get entity count for this platform
        entity_query = select(func.count(Entity.entity_id))\
            .where(Entity.platform == platform)

        entity_result = await db.execute(entity_query)
        entity_count = entity_result.scalar() or 0

        # Get entity breakdown by domain
        domain_query = select(
            Entity.domain,
            func.count(Entity.entity_id).label('count')
        )\
            .where(Entity.platform == platform)\
            .group_by(Entity.domain)\
            .order_by(func.count(Entity.entity_id).desc())

        domain_result = await db.execute(domain_query)
        domain_breakdown = [
            {"domain": row.domain, "count": row.count}
            for row in domain_result
        ]

        return {
            "platform": platform,
            "device_count": device_count,
            "entity_count": entity_count,
            "entity_breakdown": domain_breakdown,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting integration analytics for {platform}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve integration analytics: {str(e)}"
        ) from e


@router.get("/api/integrations", response_model=IntegrationsListResponse)
async def list_integrations(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of integrations to return")
):
    """
    List all Home Assistant integrations (config entries)
    
    Returns all discovered integrations with their setup status.
    """
    try:
        # Query config entries from InfluxDB
        # Ensure client is connected
        if not influxdb_client.is_connected:
            await influxdb_client.connect()

        query = f'''
            from(bucket: "home_assistant_events")
                |> range(start: -90d)
                |> filter(fn: (r) => r["_measurement"] == "config_entries")
                |> last()
                |> limit(n: {limit})
        '''

        results = await influxdb_client._execute_query(query)

        # Convert results to response models
        integrations = []
        for record in results:
            # Convert timestamp to string if needed
            timestamp = record.get("_time", datetime.now())
            if not isinstance(timestamp, str):
                timestamp = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)

            integration = IntegrationResponse(
                entry_id=record.get("entry_id", ""),
                domain=record.get("domain", "unknown"),
                title=record.get("title", "Unknown"),
                state=record.get("state", "unknown"),
                version=int(record.get("version", 1)),
                timestamp=timestamp
            )
            integrations.append(integration)

        return IntegrationsListResponse(
            integrations=integrations,
            count=len(integrations)
        )

    except Exception as e:
        logger.error(f"Error listing integrations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve integrations: {str(e)}"
        ) from e


# Helper functions
def _build_devices_query(filters: dict[str, str], limit: int) -> str:
    """Build Flux query for devices with filters"""
    query = '''
        from(bucket: "home_assistant_events")
            |> range(start: -90d)
            |> filter(fn: (r) => r["_measurement"] == "devices")
    '''

    # Add filters
    if filters.get("manufacturer"):
        manufacturer = sanitize_flux_value(filters["manufacturer"])
        if manufacturer:
            query += f'\n    |> filter(fn: (r) => r["manufacturer"] == "{manufacturer}")'
    if filters.get("model"):
        model = sanitize_flux_value(filters["model"])
        if model:
            query += f'\n    |> filter(fn: (r) => r["model"] == "{model}")'
    if filters.get("area_id"):
        area_id = sanitize_flux_value(filters["area_id"])
        if area_id:
            query += f'\n    |> filter(fn: (r) => r["area_id"] == "{area_id}")'

    query += f'\n    |> last()\n    |> limit(n: {limit})'

    return query


def _build_entities_query(filters: dict[str, str], limit: int) -> str:
    """Build Flux query for entities with filters"""
    query = '''
        from(bucket: "home_assistant_events")
            |> range(start: -90d)
            |> filter(fn: (r) => r["_measurement"] == "entities")
    '''

    # Add filters
    if filters.get("domain"):
        domain = sanitize_flux_value(filters["domain"])
        if domain:
            query += f'\n    |> filter(fn: (r) => r["domain"] == "{domain}")'
    if filters.get("platform"):
        platform_value = sanitize_flux_value(filters["platform"])
        if platform_value:
            query += f'\n    |> filter(fn: (r) => r["platform"] == "{platform_value}")'
    if filters.get("device_id"):
        device_id = sanitize_flux_value(filters["device_id"])
        if device_id:
            query += f'\n    |> filter(fn: (r) => r["device_id"] == "{device_id}")'

    query += f'\n    |> last()\n    |> limit(n: {limit})'

    return query


# Internal bulk upsert endpoints (called by websocket-ingestion)
# Note: No authentication needed for home use - services run on internal Docker network
@router.post("/internal/devices/bulk_upsert")
async def bulk_upsert_devices(
    devices: list[dict[str, Any]],
    db: AsyncSession = Depends(get_db)
):
    """
    Internal endpoint for websocket-ingestion to bulk upsert devices from HA discovery

    Uses INSERT OR REPLACE for reliable upsert without SQLAlchemy metadata issues
    """
    try:
        upserted_count = 0

        for device_data in devices:
            # Extract device_id (HA uses 'id', we use 'device_id')
            device_id = device_data.get('id') or device_data.get('device_id')
            if not device_id:
                logger.warning(f"Skipping device without ID: {device_data.get('name', 'unknown')}")
                continue

            # Check if device exists first
            result = await db.execute(
                select(Device).where(Device.device_id == device_id)
            )
            existing_device = result.scalar_one_or_none()

            # Prepare device data
            device_values = {
                'device_id': device_id,
                'name': device_data.get('name_by_user') or device_data.get('name', 'Unknown'),
                'name_by_user': device_data.get('name_by_user'),
                'manufacturer': device_data.get('manufacturer'),
                'model': device_data.get('model'),
                'sw_version': device_data.get('sw_version'),
                'area_id': device_data.get('area_id'),
                'integration': device_data.get('integration'),
                'entry_type': device_data.get('entry_type'),
                'configuration_url': device_data.get('configuration_url'),
                'suggested_area': device_data.get('suggested_area'),
                # Phase 2-3: Device Registry 2025 Attributes
                'labels': device_data.get('labels') or [],
                'serial_number': device_data.get('serial_number'),
                'model_id': device_data.get('model_id'),
                # Source tracking
                'config_entry_id': device_data.get('config_entry_id'),
                'via_device': device_data.get('via_device_id'),  # HA uses 'via_device_id'
                'last_seen': datetime.now()
            }

            # Phase 3.1: Enrich with Device Database if available
            device_db_service = get_device_database_service()
            if device_values.get('manufacturer') and device_values.get('model'):
                try:
                    db_updates = await device_db_service.update_device_from_database(
                        existing_device if existing_device else type('Device', (), device_values)(),
                        device_info=None  # Will fetch from Device Database
                    )
                    # Merge Device Database updates
                    device_values.update(db_updates)
                    if db_updates:
                        device_values['last_capability_sync'] = datetime.now()
                except Exception as e:
                    logger.debug(f"Device Database enrichment failed for {device_id}: {e}")

            if existing_device:
                # Update existing device
                for key, value in device_values.items():
                    if key != 'device_id':  # Don't update primary key
                        setattr(existing_device, key, value)
            else:
                # Insert new device
                device_values['created_at'] = datetime.now()
                new_device = Device(**device_values)
                db.add(new_device)

            upserted_count += 1

        await db.commit()

        logger.info(f"Bulk upserted {upserted_count} devices from HA discovery")

        return {
            "success": True,
            "upserted": upserted_count,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Error bulk upserting devices: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk upsert devices: {str(e)}"
        ) from e


@router.post("/internal/entities/bulk_upsert")
async def bulk_upsert_entities(
    entities: list[dict[str, Any]],
    db: AsyncSession = Depends(get_db)
):
    """
    Internal endpoint for websocket-ingestion to bulk upsert entities from HA discovery

    Simple approach: Loop and merge (SQLAlchemy handles upsert logic)
    """
    try:
        upserted_count = 0

        for entity_data in entities:
            entity_id = entity_data.get('entity_id')
            if not entity_id:
                logger.warning("Skipping entity without entity_id")
                continue

            # Extract domain from entity_id (e.g., "light.kitchen" -> "light")
            domain = entity_id.split('.')[0] if '.' in entity_id else 'unknown'

            # Extract name fields from entity registry data
            name = entity_data.get('name')  # Primary name (what shows in HA UI)
            name_by_user = entity_data.get('name_by_user')  # User-customized name
            original_name = entity_data.get('original_name')  # Original name

            # Compute friendly_name (priority: name_by_user > name > original_name > entity_id)
            friendly_name = name_by_user or name or original_name
            if not friendly_name:
                # Fallback: derive from entity_id
                friendly_name = entity_id.split('.')[-1].replace('_', ' ').title()

            # Capabilities will be enriched separately from State API
            # For now, set to None - will be populated by entity_capability_enrichment service
            supported_features = None
            capabilities = None
            available_services = None

            # Create entity instance
            entity = Entity(
                entity_id=entity_id,
                device_id=entity_data.get('device_id'),
                domain=domain,
                platform=entity_data.get('platform', 'unknown'),
                unique_id=entity_data.get('unique_id'),
                area_id=entity_data.get('area_id'),
                disabled=entity_data.get('disabled_by') is not None,
                # Entity Registry name fields (2025 HA API)
                name=name,
                name_by_user=name_by_user,
                original_name=original_name,
                friendly_name=friendly_name,
                # Entity capabilities (will be enriched from state API)
                supported_features=supported_features,
                capabilities=capabilities,
                available_services=available_services,
                # Phase 1: Entity Registry 2025 Attributes (Critical)
                icon=entity_data.get('icon'),  # Current icon (may be user-customized)
                original_icon=entity_data.get('original_icon'),  # Original icon from integration
                aliases=entity_data.get('aliases') or [],
                # Phase 2: Entity Registry 2025 Attributes (Important)
                labels=entity_data.get('labels') or [],
                options=entity_data.get('options'),
                # Source tracking
                config_entry_id=entity_data.get('config_entry_id'),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

            # Merge (upsert)
            await db.merge(entity)
            upserted_count += 1

        await db.commit()

        logger.info(f"Bulk upserted {upserted_count} entities from HA discovery")
        
        # After entity sync, trigger classification for devices with newly linked entities
        # This ensures devices get classified when entities are synced
        try:
            classifier_service = get_classifier_service()
            # Get devices that have entities but are unclassified
            unclassified_devices_query = select(Device).join(Entity, Device.device_id == Entity.device_id).where(
                or_(
                    Device.device_type.is_(None),
                    Device.device_type == ''
                )
            ).distinct().limit(100)  # Limit to avoid long operations
            
            unclassified_result = await db.execute(unclassified_devices_query)
            unclassified_devices = unclassified_result.scalars().all()
            
            if unclassified_devices:
                logger.info(f"Triggering automatic classification for {len(unclassified_devices)} devices with newly synced entities")
                classified_count = 0
                
                for device in unclassified_devices:
                    try:
                        # Get entities for this device
                        entities_query = select(Entity).where(Entity.device_id == device.device_id)
                        entities_result = await db.execute(entities_query)
                        entities = entities_result.scalars().all()
                        
                        # Extract entity domains
                        entity_domains = [e.domain for e in entities if e.domain]
                        entity_ids = [e.entity_id for e in entities]
                        
                        # Classify device
                        if entity_domains:
                            classification = await classifier_service.classify_device_from_domains(
                                device.device_id,
                                entity_domains,
                                entity_ids
                            )
                        else:
                            # Fallback to metadata classification
                            classification = classifier_service.classify_device_by_metadata(
                                device.device_id,
                                device.name or "",
                                device.manufacturer,
                                device.model
                            )
                        
                        # Update device if classification succeeded
                        if classification.get("device_type"):
                            device.device_type = classification.get("device_type")
                            device.device_category = classification.get("device_category")
                            classified_count += 1
                            
                    except Exception as e:
                        logger.warning(f"Failed to auto-classify device {device.device_id}: {e}")
                        continue
                
                if classified_count > 0:
                    await db.commit()
                    logger.info(f"Auto-classified {classified_count} devices after entity sync")
        except Exception as e:
            # Don't fail entity sync if classification fails
            logger.warning(f"Automatic classification after entity sync failed: {e}")

        return {
            "success": True,
            "upserted": upserted_count,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Error bulk upserting entities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk upsert entities: {str(e)}"
        ) from e


@router.post("/internal/services/bulk_upsert")
async def bulk_upsert_services(
    services: dict[str, dict[str, Any]],
    db: AsyncSession = Depends(get_db)
):
    """
    Internal endpoint for websocket-ingestion to bulk upsert services from HA Services API
    
    Accepts services in format: {domain: {service_name: service_data}}
    Flattens to list of services with domain and service_name
    
    Epic 2025: Stores available services per domain for service validation
    """
    try:
        upserted_count = 0
        
        # Flatten services dict to list of service records
        for domain, domain_services in services.items():
            if not isinstance(domain_services, dict):
                logger.warning(f"Skipping invalid domain services format for domain: {domain}")
                continue
                
            for service_name, service_data in domain_services.items():
                if not isinstance(service_data, dict):
                    logger.warning(f"Skipping invalid service data for {domain}.{service_name}")
                    continue
                
                # Check if service exists
                result = await db.execute(
                    select(Service).where(
                        Service.domain == domain,
                        Service.service_name == service_name
                    )
                )
                existing_service = result.scalar_one_or_none()
                
                # Prepare service values
                service_values = {
                    'domain': domain,
                    'service_name': service_name,
                    'name': service_data.get('name'),
                    'description': service_data.get('description'),
                    'fields': service_data.get('fields'),
                    'target': service_data.get('target'),
                    'last_updated': datetime.now()
                }
                
                if existing_service:
                    # Update existing service
                    for key, value in service_values.items():
                        if key not in ('domain', 'service_name'):  # Don't update primary keys
                            setattr(existing_service, key, value)
                else:
                    # Insert new service
                    new_service = Service(**service_values)
                    db.add(new_service)
                
                upserted_count += 1
        
        await db.commit()
        
        logger.info(f"Bulk upserted {upserted_count} services from HA Services API")
        
        return {
            "success": True,
            "upserted": upserted_count,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Error bulk upserting services: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk upsert services: {str(e)}"
        ) from e


# Phase 1.2: Device Health Endpoints
@router.get("/api/devices/{device_id}/health")
async def get_device_health(
    device_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get health report for a device.
    
    Phase 1.2: Analyzes device health including response times, battery levels,
    last seen timestamps, and power consumption anomalies.
    """
    try:
        # Get device from database
        device = await db.get(Device, device_id)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        # Get entities for this device
        entities_query = select(Entity).where(Entity.device_id == device_id)
        entities_result = await db.execute(entities_query)
        entities = entities_result.scalars().all()
        entity_ids = [e.entity_id for e in entities]
        
        # Get health analysis
        health_service = get_health_service()
        health_report = await health_service.get_device_health(
            device_id=device.device_id,
            device_name=device.name,
            entity_ids=entity_ids,
            power_spec_w=device.power_consumption_active_w
        )
        
        return health_report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device health for {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get device health: {str(e)}") from e


@router.get("/api/devices/health-summary")
async def get_health_summary(
    db: AsyncSession = Depends(get_db)
):
    """
    Get overall health summary for all devices.
    
    Phase 1.2: Provides summary of device health across all devices.
    """
    try:
        # Get all devices
        devices_query = select(Device)
        devices_result = await db.execute(devices_query)
        devices = devices_result.scalars().all()
        
        total_devices = len(devices)
        healthy_devices = 0
        warning_devices = 0
        error_devices = 0
        
        health_service = get_health_service()
        
        # Analyze each device (limit to avoid timeout)
        for device in devices[:100]:  # Limit to first 100 devices
            entities_query = select(Entity).where(Entity.device_id == device.device_id)
            entities_result = await db.execute(entities_query)
            entities = entities_result.scalars().all()
            entity_ids = [e.entity_id for e in entities]
            
            health_report = await health_service.get_device_health(
                device_id=device.device_id,
                device_name=device.name,
                entity_ids=entity_ids,
                power_spec_w=device.power_consumption_active_w
            )
            
            status = health_report.get("overall_status", "unknown")
            if status == "healthy":
                healthy_devices += 1
            elif status == "warning":
                warning_devices += 1
            elif status == "error":
                error_devices += 1
        
        return {
            "total_devices": total_devices,
            "healthy_devices": healthy_devices,
            "warning_devices": warning_devices,
            "error_devices": error_devices,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting health summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get health summary: {str(e)}") from e


@router.get("/api/devices/maintenance-alerts")
async def get_maintenance_alerts(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of alerts")
):
    """
    Get maintenance alerts for devices needing attention.
    
    Phase 1.2: Returns list of devices with health issues requiring maintenance.
    """
    try:
        # Get all devices
        devices_query = select(Device).limit(limit * 2)  # Get more to filter
        devices_result = await db.execute(devices_query)
        devices = devices_result.scalars().all()
        
        alerts = []
        health_service = get_health_service()
        
        for device in devices:
            entities_query = select(Entity).where(Entity.device_id == device.device_id)
            entities_result = await db.execute(entities_query)
            entities = entities_result.scalars().all()
            entity_ids = [e.entity_id for e in entities]
            
            health_report = await health_service.get_device_health(
                device_id=device.device_id,
                device_name=device.name,
                entity_ids=entity_ids,
                power_spec_w=device.power_consumption_active_w
            )
            
            # Only include devices with issues
            issues = health_report.get("issues", [])
            if issues:
                for issue in issues:
                    alerts.append({
                        "device_id": device.device_id,
                        "device_name": device.name,
                        "issue_type": issue.get("type"),
                        "severity": issue.get("severity"),
                        "message": issue.get("message"),
                        "timestamp": datetime.now().isoformat()
                    })
            
            if len(alerts) >= limit:
                break
        
        return {
            "alerts": alerts[:limit],
            "count": len(alerts[:limit]),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting maintenance alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get maintenance alerts: {str(e)}") from e


# Phase 1.3: Power Consumption Intelligence Endpoints
@router.get("/api/devices/{device_id}/power-analysis")
async def get_device_power_analysis(
    device_id: str,
    days: int = Query(default=7, ge=1, le=30, description="Days of history"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get power consumption analysis for a device.
    
    Phase 1.3: Compares actual power usage vs. device specifications,
    detects power anomalies, and calculates efficiency scores.
    """
    try:
        # Get device from database
        device = await db.get(Device, device_id)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        # Get entities for this device
        entities_query = select(Entity).where(Entity.device_id == device_id)
        entities_result = await db.execute(entities_query)
        entities = entities_result.scalars().all()
        
        if not entities:
            return {
                "device_id": device_id,
                "device_name": device.name,
                "message": "No entities found for device",
                "analysis": {}
            }
        
        # Get power data from energy endpoints (simplified - would need actual energy correlator integration)
        # For now, return analysis based on device specs
        spec_power = device.power_consumption_active_w
        actual_power = None  # Would come from energy-correlator
        
        analysis = {
            "device_id": device_id,
            "device_name": device.name,
            "spec_power_w": spec_power,
            "actual_power_w": actual_power,
            "efficiency_pct": None,
            "anomaly_detected": False,
            "recommendations": []
        }
        
        if spec_power:
            analysis["spec_power_w"] = spec_power
            if actual_power:
                efficiency = (spec_power / actual_power * 100) if actual_power > 0 else None
                analysis["efficiency_pct"] = efficiency
                if actual_power > spec_power * 1.5:
                    analysis["anomaly_detected"] = True
                    analysis["recommendations"].append({
                        "type": "high_power_consumption",
                        "message": f"Device consuming {actual_power:.1f}W, expected {spec_power:.1f}W",
                        "priority": "medium"
                    })
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting power analysis for {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get power analysis: {str(e)}") from e


@router.get("/api/devices/{device_id}/efficiency")
async def get_device_efficiency(
    device_id: str,
    days: int = Query(default=7, ge=1, le=30, description="Days of history"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get efficiency report for a device.
    
    Phase 1.3: Calculates device efficiency score based on power consumption.
    """
    try:
        device = await db.get(Device, device_id)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        spec_power = device.power_consumption_active_w
        actual_power = None  # Would come from energy-correlator
        
        if not spec_power:
            return {
                "device_id": device_id,
                "device_name": device.name,
                "efficiency_score": None,
                "message": "No power specification available for device"
            }
        
        efficiency_score = None
        if actual_power and spec_power:
            # Efficiency is how close actual is to spec (100% = perfect match)
            efficiency_score = max(0, min(100, (spec_power / actual_power * 100))) if actual_power > 0 else None
        
        return {
            "device_id": device_id,
            "device_name": device.name,
            "spec_power_w": spec_power,
            "actual_power_w": actual_power,
            "efficiency_score": efficiency_score,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting efficiency for {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get efficiency: {str(e)}") from e


@router.get("/api/devices/power-anomalies")
async def get_power_anomalies(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of anomalies")
):
    """
    Get devices with power consumption anomalies.
    
    Phase 1.3: Returns devices consuming more power than expected.
    """
    try:
        # Get devices with power specs
        devices_query = select(Device).where(
            Device.power_consumption_active_w.isnot(None)
        ).limit(limit * 2)
        devices_result = await db.execute(devices_query)
        devices = devices_result.scalars().all()
        
        anomalies = []
        
        for device in devices:
            spec_power = device.power_consumption_active_w
            actual_power = None  # Would come from energy-correlator
            
            if spec_power and actual_power:
                if actual_power > spec_power * 1.5:
                    anomalies.append({
                        "device_id": device.device_id,
                        "device_name": device.name,
                        "spec_power_w": spec_power,
                        "actual_power_w": actual_power,
                        "excess_power_w": actual_power - spec_power,
                        "excess_percentage": ((actual_power / spec_power - 1) * 100),
                        "severity": "high" if actual_power > spec_power * 2 else "medium",
                        "timestamp": datetime.now().isoformat()
                    })
            
            if len(anomalies) >= limit:
                break
        
        return {
            "anomalies": anomalies[:limit],
            "count": len(anomalies[:limit]),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting power anomalies: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get power anomalies: {str(e)}") from e


# Phase 2.1: Device Classification Endpoint
@router.post("/api/devices/{device_id}/classify")
async def classify_device(
    device_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Classify a device based on its entities.
    
    Phase 2.1: Analyzes device entities to infer device type and category,
    then updates the Device model.
    """
    try:
        # Get device from database
        device = await db.get(Device, device_id)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        # Get entities for this device
        entities_query = select(Entity).where(Entity.device_id == device_id)
        entities_result = await db.execute(entities_query)
        entities = entities_result.scalars().all()
        
        # Extract entity domains directly from database
        entity_domains = [e.domain for e in entities if e.domain]
        entity_ids = [e.entity_id for e in entities]
        
        # Classify device - use domains if available, otherwise use metadata
        classifier_service = get_classifier_service()
        if entity_domains:
            classification = await classifier_service.classify_device_from_domains(
                device_id, 
                entity_domains, 
                entity_ids
            )
        else:
            # Fallback: Classify by device name/manufacturer/model (no entities needed)
            classification = classifier_service.classify_device_by_metadata(
                device_id,
                device.name or "",
                device.manufacturer,
                device.model
            )
        
        # Update device with classification
        if classification.get("device_type"):
            device.device_type = classification.get("device_type")
            device.device_category = classification.get("device_category")
            await db.commit()
        
        return {
            "device_id": device_id,
            "device_name": device.name,
            "device_type": device.device_type,
            "device_category": device.device_category,
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "device_id": device_id,
            "device_name": device.name,
            "device_type": device.device_type,
            "device_category": device.device_category,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error classifying device {device_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to classify device: {str(e)}"
        ) from e


@router.post("/api/devices/link-entities")
async def link_entities_to_devices(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=1000, ge=1, le=10000, description="Maximum number of entities to link")
):
    """
    Re-link entities to devices using Home Assistant API.
    
    Queries HA entity registry to get device_id for each entity, then updates the database.
    """
    try:
        import os
        import aiohttp
        
        ha_url = os.getenv("HA_URL") or os.getenv("HA_HTTP_URL")
        ha_token = os.getenv("HA_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN")
        
        if not ha_url or not ha_token:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Home Assistant URL or token not configured"
            )
        
        # Get all entities without device_id (NULL or empty)
        unlinked_query = select(Entity).where(
            or_(
                Entity.device_id.is_(None),
                Entity.device_id == ''
            )
        ).limit(limit)
        
        result = await db.execute(unlinked_query)
        entities = result.scalars().all()
        
        if not entities:
            return {
                "message": "All entities are already linked to devices",
                "linked": 0,
                "total": 0
            }
        
        linked_count = 0
        headers = {
            "Authorization": f"Bearer {ha_token}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession(headers=headers) as session:
            # Get entity registry from Home Assistant
            # HA REST API endpoint: /api/config/entity_registry/list (returns list of entities)
            registry_url = f"{ha_url.rstrip('/')}/api/config/entity_registry/list"
            async with session.get(registry_url) as response:
                if response.status == 404:
                    # HA REST API might not support this endpoint - use database matching instead
                    logger.warning("Entity registry API endpoint not available (404), using database matching")
                    ha_entities = {}
                elif response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Failed to fetch entity registry: {response.status} - {error_text}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Failed to fetch entity registry from Home Assistant: {response.status}"
                    )
                else:
                        registry_data = await response.json()
                        # HA returns list directly, not wrapped in {"entities": [...]}
                        ha_entities_list = registry_data if isinstance(registry_data, list) else registry_data.get("entities", [])
                        ha_entities = {e.get("entity_id"): e for e in ha_entities_list}
                        logger.info(f"Fetched {len(ha_entities)} entities from Home Assistant entity registry")
        
        # Link entities to devices
        if not ha_entities:
            # Fallback: Match by config_entry_id and area_id if HA API not available
            logger.info("Using fallback matching by config_entry_id and area_id")
            for entity in entities:
                try:
                    if not entity.config_entry_id:
                        continue
                    
                    # Find devices with same config_entry_id
                    device_query = select(Device).where(Device.config_entry_id == entity.config_entry_id)
                    device_result = await db.execute(device_query)
                    device = device_result.scalar_one_or_none()
                    
                    if device:
                        entity.device_id = device.device_id
                        linked_count += 1
                        logger.debug(f"Linked entity {entity.entity_id} to device {device.device_id} via config_entry_id")
                    
                except Exception as e:
                    logger.warning(f"Failed to link entity {entity.entity_id}: {e}")
                    continue
        else:
            # Primary: Use HA entity registry data
            for entity in entities:
                try:
                    ha_entity = ha_entities.get(entity.entity_id)
                    if ha_entity:
                        device_id = ha_entity.get("device_id")
                        if device_id:
                            # Verify device exists
                            device_check = await db.execute(
                                select(Device).where(Device.device_id == device_id)
                            )
                            device = device_check.scalar_one_or_none()
                            
                            if device:
                                entity.device_id = device_id
                                linked_count += 1
                            else:
                                logger.debug(f"Device {device_id} not found for entity {entity.entity_id}")
                    
                except Exception as e:
                    logger.warning(f"Failed to link entity {entity.entity_id}: {e}")
                    continue
        
        # Commit all changes
        await db.commit()
        
        # After linking entities, trigger classification for affected devices
        if linked_count > 0:
            try:
                logger.info(f"Triggering automatic classification for devices with newly linked entities")
                classifier_service = get_classifier_service()
                
                # Get devices that had entities linked
                device_ids_with_linked_entities = {entity.device_id for entity in entities if entity.device_id}
                
                classified_count = 0
                for device_id in device_ids_with_linked_entities:
                    try:
                        device = await db.get(Device, device_id)
                        if not device or (device.device_type and device.device_type != ''):
                            continue  # Skip if already classified
                        
                        # Get entities for this device
                        entities_query = select(Entity).where(Entity.device_id == device_id)
                        entities_result = await db.execute(entities_query)
                        device_entities = entities_result.scalars().all()
                        
                        # Extract entity domains
                        entity_domains = [e.domain for e in device_entities if e.domain]
                        entity_ids = [e.entity_id for e in device_entities]
                        
                        # Classify device using domains (now that entities are linked)
                        if entity_domains:
                            classification = await classifier_service.classify_device_from_domains(
                                device_id,
                                entity_domains,
                                entity_ids
                            )
                            
                            if classification.get("device_type"):
                                device.device_type = classification.get("device_type")
                                device.device_category = classification.get("device_category")
                                classified_count += 1
                                logger.debug(f"Classified device {device_id} ({device.name}) as {classification.get('device_type')} after entity linking")
                    except Exception as e:
                        logger.warning(f"Failed to classify device {device_id} after linking: {e}")
                        continue
                
                if classified_count > 0:
                    await db.commit()
                    logger.info(f"Auto-classified {classified_count} devices after entity linking")
            except Exception as e:
                # Don't fail entity linking if classification fails
                logger.warning(f"Automatic classification after entity linking failed: {e}")
        
        return {
            "message": f"Linked {linked_count} entities to devices",
            "linked": linked_count,
            "total": len(entities),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking entities to devices: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to link entities: {str(e)}"
        ) from e


@router.post("/api/devices/classify-all")
async def classify_all_devices(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=1000, ge=1, le=10000, description="Maximum number of devices to classify")
):
    """
    Classify all devices that don't have a device_type assigned.
    
    Uses domain-based classification from entity domains (no HA API calls needed).
    """
    try:
        # Get all devices without device_type (NULL or empty)
        unclassified_query = select(Device).where(
            or_(
                Device.device_type.is_(None),
                Device.device_type == ''
            )
        ).limit(limit)
        
        result = await db.execute(unclassified_query)
        devices = result.scalars().all()
        
        if not devices:
            return {
                "message": "All devices are already classified",
                "classified": 0,
                "total": 0
            }
        
        classifier_service = get_classifier_service()
        classified_count = 0
        
        for device in devices:
            try:
                # Get entities for this device
                entities_query = select(Entity).where(Entity.device_id == device.device_id)
                entities_result = await db.execute(entities_query)
                entities = entities_result.scalars().all()
                
                # Extract entity domains directly from database
                entity_domains = [e.domain for e in entities if e.domain]
                entity_ids = [e.entity_id for e in entities]
                
                # Classify device - use domains if available, otherwise use metadata
                if entity_domains:
                    classification = await classifier_service.classify_device_from_domains(
                        device.device_id, 
                        entity_domains, 
                        entity_ids
                    )
                else:
                    # Fallback: Classify by device name/manufacturer/model (no entities needed)
                    logger.debug(f"Classifying device {device.device_id} by metadata (no entities found)")
                    classification = classifier_service.classify_device_by_metadata(
                        device.device_id,
                        device.name or "",
                        device.manufacturer,
                        device.model
                    )
                
                # Update device
                if classification.get("device_type"):
                    device.device_type = classification.get("device_type")
                    device.device_category = classification.get("device_category")
                    classified_count += 1
                    logger.debug(f"Classified device {device.device_id} ({device.name}) as {classification.get('device_type')}")
                else:
                    logger.debug(f"Could not classify device {device.device_id} ({device.name})")
                    
            except Exception as e:
                logger.warning(f"Failed to classify device {device.device_id}: {e}", exc_info=True)
                continue
        
        # Commit all changes
        await db.commit()
        
        # Note: Cache will expire naturally (5 minute TTL)
        # Devices list queries will get fresh data after cache expires
        
        return {
            "message": f"Classified {classified_count} devices",
            "classified": classified_count,
            "total": len(devices),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error classifying all devices: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to classify devices: {str(e)}"
        ) from e
    except Exception as e:
        await db.rollback()
        logger.error(f"Error classifying device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to classify device: {str(e)}") from e


# Phase 2.3: Device Setup Assistant Endpoints
@router.get("/api/devices/{device_id}/setup-guide")
async def get_setup_guide(
    device_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get setup guide for a device.
    
    Phase 2.3: Returns step-by-step setup instructions for the device.
    """
    try:
        # Get device from database
        device = await db.get(Device, device_id)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        # Generate setup guide
        setup_assistant = get_setup_assistant()
        guide = setup_assistant.generate_setup_guide(
            device_id=device.device_id,
            device_name=device.name,
            device_type=device.device_type,
            integration=device.integration,
            setup_instructions_url=device.setup_instructions_url
        )
        
        return guide
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting setup guide for {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get setup guide: {str(e)}") from e


@router.get("/api/devices/{device_id}/setup-issues")
async def get_setup_issues(
    device_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detected setup issues for a device.
    
    Phase 2.3: Returns list of detected setup problems.
    """
    try:
        # Get device from database
        device = await db.get(Device, device_id)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        # Get entities for this device
        entities_query = select(Entity).where(Entity.device_id == device_id)
        entities_result = await db.execute(entities_query)
        entities = entities_result.scalars().all()
        entity_ids = [e.entity_id for e in entities]
        
        # Detect setup issues
        setup_assistant = get_setup_assistant()
        issues = await setup_assistant.detect_setup_issues(
            device_id=device.device_id,
            device_name=device.name,
            entity_ids=entity_ids
        )
        
        return {
            "device_id": device_id,
            "device_name": device.name,
            "issues": issues,
            "count": len(issues),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting setup issues for {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get setup issues: {str(e)}") from e


@router.post("/api/devices/{device_id}/setup-complete")
async def mark_setup_complete(
    device_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Mark device setup as complete.
    
    Phase 2.3: Marks device setup as complete (for tracking purposes).
    """
    try:
        # Get device from database
        device = await db.get(Device, device_id)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        # Could add a setup_complete field to Device model if needed
        # For now, just return success
        return {
            "device_id": device_id,
            "device_name": device.name,
            "setup_complete": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking setup complete for {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to mark setup complete: {str(e)}") from e


# Phase 3.2: Capability Discovery Endpoint
@router.post("/api/devices/{device_id}/discover-capabilities")
async def discover_device_capabilities(
    device_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Discover device capabilities from HA API.
    
    Phase 3.2: Analyzes device entities to infer capabilities and features,
    then updates the Device model with device_features_json.
    """
    try:
        # Get device from database
        device = await db.get(Device, device_id)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        # Get entities for this device
        entities_query = select(Entity).where(Entity.device_id == device_id)
        entities_result = await db.execute(entities_query)
        entities = entities_result.scalars().all()
        entity_ids = [e.entity_id for e in entities]
        
        if not entity_ids:
            return {
                "device_id": device_id,
                "message": "No entities found for device",
                "capabilities": [],
                "features": {}
            }
        
        # Discover capabilities
        capability_service = get_capability_service()
        capabilities_data = await capability_service.discover_device_capabilities(device_id, entity_ids)
        
        # Update device with capabilities
        device.device_features_json = capability_service.format_capabilities_for_storage(capabilities_data)
        device.last_capability_sync = datetime.now()
        await db.commit()
        
        return {
            "device_id": device_id,
            "device_name": device.name,
            "capabilities": capabilities_data.get("capabilities", []),
            "features": capabilities_data.get("features", {}),
            "device_classes": capabilities_data.get("device_classes", []),
            "state_classes": capabilities_data.get("state_classes", []),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error discovering capabilities for {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to discover capabilities: {str(e)}") from e


# Phase 3.3: Device Recommendation Endpoints
@router.get("/api/devices/recommendations")
async def get_device_recommendations(
    device_type: str = Query(..., description="Device type to recommend"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get device recommendations.
    
    Phase 3.3: Returns device recommendations based on device type and requirements.
    """
    try:
        # Get user's existing devices
        devices_query = select(Device)
        devices_result = await db.execute(devices_query)
        devices = devices_result.scalars().all()
        
        user_devices = [
            {
                "device_id": d.device_id,
                "name": d.name,
                "manufacturer": d.manufacturer,
                "model": d.model,
                "device_type": d.device_type,
                "device_category": d.device_category
            }
            for d in devices
        ]
        
        # Get recommendations
        recommender_service = get_recommender_service()
        recommendations = await recommender_service.recommend_devices(
            device_type=device_type,
            requirements=None,  # Could add query params for requirements
            user_devices=user_devices
        )
        
        return {
            "device_type": device_type,
            "recommendations": recommendations,
            "count": len(recommendations),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}") from e


@router.get("/api/devices/compare")
async def compare_devices(
    device_ids: str = Query(..., description="Comma-separated device IDs"),
    db: AsyncSession = Depends(get_db)
):
    """
    Compare devices.
    
    Phase 3.3: Returns side-by-side comparison of devices.
    """
    try:
        # Parse device IDs
        device_id_list = [d.strip() for d in device_ids.split(",")]
        
        if len(device_id_list) < 2:
            raise HTTPException(
                status_code=400,
                detail="Need at least 2 device IDs to compare"
            )
        
        # Get devices from database
        devices_query = select(Device).where(Device.device_id.in_(device_id_list))
        devices_result = await db.execute(devices_query)
        devices = devices_result.scalars().all()
        
        if len(devices) < 2:
            raise HTTPException(
                status_code=404,
                detail="Not all devices found"
            )
        
        # Convert to dicts
        device_dicts = [
            {
                "device_id": d.device_id,
                "name": d.name,
                "manufacturer": d.manufacturer,
                "model": d.model,
                "device_type": d.device_type,
                "device_category": d.device_category,
                "power_consumption_active_w": d.power_consumption_active_w,
                "community_rating": d.community_rating,
                "device_features_json": d.device_features_json
            }
            for d in devices
        ]
        
        # Compare devices
        recommender_service = get_recommender_service()
        comparison = recommender_service.compare_devices(device_id_list, device_dicts)
        
        return comparison
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing devices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to compare devices: {str(e)}") from e


@router.get("/api/devices/similar/{device_id}")
async def find_similar_devices(
    device_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Find similar devices.
    
    Phase 3.3: Returns devices similar to the specified device.
    """
    try:
        # Get reference device
        device = await db.get(Device, device_id)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        # Get all devices
        devices_query = select(Device)
        devices_result = await db.execute(devices_query)
        all_devices = devices_result.scalars().all()
        
        # Convert to dicts
        device_dicts = [
            {
                "device_id": d.device_id,
                "name": d.name,
                "manufacturer": d.manufacturer,
                "model": d.model,
                "device_type": d.device_type,
                "device_category": d.device_category
            }
            for d in all_devices
        ]
        
        # Find similar devices
        recommender_service = get_recommender_service()
        similar = recommender_service.find_similar_devices(device_id, device_dicts)
        
        return {
            "reference_device_id": device_id,
            "reference_device_name": device.name,
            "similar_devices": similar,
            "count": len(similar),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding similar devices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to find similar devices: {str(e)}") from e


@router.delete("/internal/devices/clear")
async def clear_all_devices(
    db: AsyncSession = Depends(get_db)
):
    """
    Delete all devices and entities from the database (for reload/reset)
    """
    try:
        from sqlalchemy import delete

        # Delete all entities first (due to foreign key constraint)
        entities_deleted = await db.execute(delete(Entity))
        entities_count = entities_deleted.rowcount

        # Delete all devices
        devices_deleted = await db.execute(delete(Device))
        devices_count = devices_deleted.rowcount

        await db.commit()

        logger.info(f"Cleared {devices_count} devices and {entities_count} entities from database")

        return {
            "success": True,
            "devices_deleted": devices_count,
            "entities_deleted": entities_count,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Error clearing devices and entities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear devices and entities: {str(e)}"
        ) from e
