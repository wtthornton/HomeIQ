"""
Devices and Entities Endpoints for Data API
Migrated from admin-api as part of Epic 13 Story 13.2
Story 22.2: Updated to use SQLite storage
"""

import logging
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from fastapi import APIRouter, HTTPException, status, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from shared.influxdb_query_client import InfluxDBQueryClient

# Story 22.2: SQLite models and database
from .database import get_db
from .models import Device, Entity

logger = logging.getLogger(__name__)


# Response Models
class DeviceResponse(BaseModel):
    """Device response model"""
    device_id: str = Field(description="Unique device identifier")
    name: str = Field(description="Device name")
    manufacturer: str = Field(description="Device manufacturer")
    model: str = Field(description="Device model")
    sw_version: Optional[str] = Field(default=None, description="Software/firmware version")
    area_id: Optional[str] = Field(default=None, description="Area/room ID")
    entity_count: int = Field(default=0, description="Number of entities")
    timestamp: str = Field(description="Last update timestamp")


class EntityResponse(BaseModel):
    """Entity response model"""
    entity_id: str = Field(description="Unique entity identifier")
    device_id: Optional[str] = Field(default=None, description="Associated device ID")
    domain: str = Field(description="Entity domain (light, sensor, etc)")
    platform: str = Field(description="Integration platform")
    unique_id: Optional[str] = Field(default=None, description="Unique ID within platform")
    area_id: Optional[str] = Field(default=None, description="Area/room ID")
    disabled: bool = Field(default=False, description="Whether entity is disabled")
    timestamp: str = Field(description="Last update timestamp")


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
    devices: List[DeviceResponse]
    count: int
    limit: int


class EntitiesListResponse(BaseModel):
    """Entities list response"""
    entities: List[EntityResponse]
    count: int
    limit: int


class IntegrationsListResponse(BaseModel):
    """Integrations list response"""
    integrations: List[IntegrationResponse]
    count: int


# Create router
router = APIRouter(tags=["Devices & Entities"])


# InfluxDB client (initialized on first use to avoid circular imports)
influxdb_client = InfluxDBQueryClient()


@router.get("/api/devices", response_model=DevicesListResponse)
async def list_devices(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of devices to return"),
    manufacturer: Optional[str] = Query(default=None, description="Filter by manufacturer"),
    model: Optional[str] = Query(default=None, description="Filter by model"),
    area_id: Optional[str] = Query(default=None, description="Filter by area/room"),
    platform: Optional[str] = Query(default=None, description="Filter by integration platform"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all discovered devices from Home Assistant (SQLite storage)
    
    Story 22.2: Simple, fast SQLite queries with JOIN for entity counts
    Enhanced: Platform filtering support for Top Integrations feature
    """
    try:
        # Build query with entity count
        if platform:
            # Join with entities to filter by platform
            query = select(Device, func.count(Entity.entity_id).label('entity_count'))\
                .join(Entity, Device.device_id == Entity.device_id)\
                .where(Entity.platform == platform)\
                .group_by(Device.device_id)
        else:
            # Standard query without platform filter
            query = select(Device, func.count(Entity.entity_id).label('entity_count'))\
                .outerjoin(Entity, Device.device_id == Entity.device_id)\
                .group_by(Device.device_id)
        
        # Apply additional filters (simple WHERE clauses)
        if manufacturer:
            query = query.where(Device.manufacturer == manufacturer)
        if model:
            query = query.where(Device.model == model)
        if area_id:
            query = query.where(Device.area_id == area_id)
        
        # Apply limit
        query = query.limit(limit)
        
        # Execute
        result = await db.execute(query)
        rows = result.all()
        
        # Convert to response
        device_responses = [
            DeviceResponse(
                device_id=device.device_id,
                name=device.name,
                manufacturer=device.manufacturer or "Unknown",
                model=device.model or "Unknown",
                sw_version=device.sw_version,
                area_id=device.area_id,
                entity_count=entity_count,
                timestamp=device.last_seen.isoformat() if device.last_seen else datetime.now().isoformat()
            )
            for device, entity_count in rows
        ]
        
        return DevicesListResponse(
            devices=device_responses,
            count=len(device_responses),
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Error listing devices from SQLite: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve devices: {str(e)}"
        )


@router.get("/api/devices/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: str, db: AsyncSession = Depends(get_db)):
    """Get device by ID (SQLite) - Story 22.2"""
    try:
        # Simple SELECT with entity count (only select columns that exist in current schema)
        query = select(
            Device.device_id,
            Device.name,
            Device.manufacturer,
            Device.model,
            Device.sw_version,
            Device.area_id,
            Device.integration,
            Device.last_seen,
            func.count(Entity.entity_id).label('entity_count')
        )\
            .outerjoin(Entity, Device.device_id == Entity.device_id)\
            .where(Device.device_id == device_id)\
            .group_by(Device.device_id)
        
        result = await db.execute(query)
        row = result.first()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        # Unpack row tuple (simplified - only columns that exist)
        (device_id_col, name, manufacturer, model, sw_version, area_id, 
         integration, last_seen, entity_count) = row
        
        return DeviceResponse(
            device_id=device_id_col,
            name=name,
            manufacturer=manufacturer or "Unknown",
            model=model or "Unknown",
            sw_version=sw_version,
            area_id=area_id,
            entity_count=entity_count,
            timestamp=last_seen.isoformat() if last_seen else datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve device: {str(e)}"        )


# Epic 23.5: Device Reliability Endpoint
@router.get("/api/devices/reliability", response_model=Dict[str, Any])
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
        
        # Build query based on group_by parameter
        field_name = "manufacturer" if group_by == "manufacturer" else "model"
        
        query = f'''
        from(bucket: "{influxdb_bucket}")
          |> range(start: -{period})
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
          |> range(start: -{period})
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
        
        client.close()
        
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
        )


@router.get("/api/entities", response_model=EntitiesListResponse)
async def list_entities(
    limit: int = Query(default=100, ge=1, le=10000, description="Maximum number of entities to return"),
    domain: Optional[str] = Query(default=None, description="Filter by domain (light, sensor, etc)"),
    platform: Optional[str] = Query(default=None, description="Filter by platform"),
    device_id: Optional[str] = Query(default=None, description="Filter by device ID"),
    db: AsyncSession = Depends(get_db)
):
    """List entities (SQLite) - Story 22.2"""
    try:
        # Build query
        query = select(Entity)
        
        # Apply filters
        if domain:
            query = query.where(Entity.domain == domain)
        if platform:
            query = query.where(Entity.platform == platform)
        if device_id:
            query = query.where(Entity.device_id == device_id)
        
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
                timestamp=entity.created_at.isoformat() if entity.created_at else datetime.now().isoformat()
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
        raise HTTPException(status_code=500, detail=f"Failed to retrieve entities: {str(e)}")


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
            timestamp=entity.created_at.isoformat() if entity.created_at else datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting entity {entity_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve entity: {str(e)}")


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
        event_rate_query = f'''
        from(bucket: "{influxdb_bucket}")
          |> range(start: -{period})
          |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
          |> filter(fn: (r) => r._field == "context_id")
          |> filter(fn: (r) => r["platform"] == "{platform}")
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
          |> range(start: -{period})
          |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
          |> filter(fn: (r) => r._field == "context_id")
          |> filter(fn: (r) => r["platform"] == "{platform}")
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
          |> range(start: -{period})
          |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
          |> filter(fn: (r) => r._field == "response_time")
          |> filter(fn: (r) => r["platform"] == "{platform}")
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
          |> filter(fn: (r) => r["platform"] == "{platform}")
          |> count()
        '''
        
        discovery_result = query_api.query(discovery_query)
        recent_discoveries = 0
        for table in discovery_result:
            for record in table.records:
                recent_discoveries += record.get_value()
        
        discovery_status = "active" if recent_discoveries > 0 else "paused"
        
        client.close()
        
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
        )


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
        )


# Helper functions
def _build_devices_query(filters: Dict[str, str], limit: int) -> str:
    """Build Flux query for devices with filters"""
    query = f'''
        from(bucket: "home_assistant_events")
            |> range(start: -90d)
            |> filter(fn: (r) => r["_measurement"] == "devices")
    '''
    
    # Add filters
    if filters.get("manufacturer"):
        query += f'\n    |> filter(fn: (r) => r["manufacturer"] == "{filters["manufacturer"]}")'
    if filters.get("model"):
        query += f'\n    |> filter(fn: (r) => r["model"] == "{filters["model"]}")'
    if filters.get("area_id"):
        query += f'\n    |> filter(fn: (r) => r["area_id"] == "{filters["area_id"]}")'
    
    query += f'\n    |> last()\n    |> limit(n: {limit})'
    
    return query


def _build_entities_query(filters: Dict[str, str], limit: int) -> str:
    """Build Flux query for entities with filters"""
    query = f'''
        from(bucket: "home_assistant_events")
            |> range(start: -90d)
            |> filter(fn: (r) => r["_measurement"] == "entities")
    '''
    
    # Add filters
    if filters.get("domain"):
        query += f'\n    |> filter(fn: (r) => r["domain"] == "{filters["domain"]}")'
    if filters.get("platform"):
        query += f'\n    |> filter(fn: (r) => r["platform"] == "{filters["platform"]}")'
    if filters.get("device_id"):
        query += f'\n    |> filter(fn: (r) => r["device_id"] == "{filters["device_id"]}")'
    
    query += f'\n    |> last()\n    |> limit(n: {limit})'
    
    return query


# Internal bulk upsert endpoints (called by websocket-ingestion)
@router.post("/internal/devices/bulk_upsert")
async def bulk_upsert_devices(
    devices: List[Dict[str, Any]],
    db: AsyncSession = Depends(get_db)
):
    """
    Internal endpoint for websocket-ingestion to bulk upsert devices from HA discovery
    
    Simple approach: Loop and merge (SQLAlchemy handles upsert logic)
    """
    try:
        upserted_count = 0
        
        for device_data in devices:
            # Extract device_id (HA uses 'id', we use 'device_id')
            device_id = device_data.get('id') or device_data.get('device_id')
            if not device_id:
                logger.warning(f"Skipping device without ID: {device_data.get('name', 'unknown')}")
                continue
            
            # Create device instance
            device = Device(
                device_id=device_id,
                name=device_data.get('name_by_user') or device_data.get('name'),
                name_by_user=device_data.get('name_by_user'),
                manufacturer=device_data.get('manufacturer'),
                model=device_data.get('model'),
                sw_version=device_data.get('sw_version'),
                area_id=device_data.get('area_id'),
                integration=device_data.get('integration'),  # Fix: Include integration field
                entry_type=device_data.get('entry_type'),
                configuration_url=device_data.get('configuration_url'),
                suggested_area=device_data.get('suggested_area'),
                last_seen=datetime.now()
            )
            
            # Merge (upsert) - updates if exists, inserts if new
            await db.merge(device)
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk upsert devices: {str(e)}"
        )


@router.post("/internal/entities/bulk_upsert")
async def bulk_upsert_entities(
    entities: List[Dict[str, Any]],
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
            
            # Create entity instance
            entity = Entity(
                entity_id=entity_id,
                device_id=entity_data.get('device_id'),
                domain=domain,
                platform=entity_data.get('platform', 'unknown'),
                unique_id=entity_data.get('unique_id'),
                area_id=entity_data.get('area_id'),
                disabled=entity_data.get('disabled_by') is not None,
                created_at=datetime.now()
            )
            
            # Merge (upsert)
            await db.merge(entity)
            upserted_count += 1
        
        await db.commit()
        
        logger.info(f"Bulk upserted {upserted_count} entities from HA discovery")
        
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
        )


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
        )
