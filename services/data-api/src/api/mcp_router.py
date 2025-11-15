"""
MCP tool endpoints for Data API.
These endpoints are called by code executed in the ai-code-executor sandbox.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp/tools", tags=["mcp"])


class QueryDeviceHistoryRequest(BaseModel):
    """Request for device history query"""
    entity_id: str
    start_time: str
    end_time: str
    fields: Optional[List[str]] = None


@router.post("/query_device_history")
async def query_device_history(request: QueryDeviceHistoryRequest):
    """
    MCP Tool: Query historical state data for a device.

    This endpoint is called by AI-generated code like:
    ```python
    import data
    history = await data.query_device_history(
        entity_id="sensor.power",
        start_time="-7d",
        end_time="now"
    )
    ```
    """
    try:
        logger.info(
            f"MCP query_device_history: {request.entity_id} "
            f"from {request.start_time} to {request.end_time}"
        )

        # Import here to avoid circular dependencies
        from ..database.influx_client import InfluxDBQueryClient

        influx_client = InfluxDBQueryClient()

        # Query InfluxDB
        query = f'''
        from(bucket: "home_assistant_events")
            |> range(start: {request.start_time}, stop: {request.end_time})
            |> filter(fn: (r) => r.entity_id == "{request.entity_id}")
        '''

        if request.fields:
            fields_filter = ' or '.join(
                f'r._field == "{field}"' for field in request.fields
            )
            query += f'\n    |> filter(fn: (r) => {fields_filter})'

        results = await influx_client.query(query)

        return {
            "entity_id": request.entity_id,
            "start_time": request.start_time,
            "end_time": request.end_time,
            "data_points": len(results),
            "data": results[:1000]  # Limit to prevent huge responses
        }

    except Exception as e:
        logger.error(f"MCP tool error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get_devices")
async def get_devices():
    """
    MCP Tool: Get all registered devices.

    Example usage in AI code:
    ```python
    import data
    devices = await data.get_devices()
    print(f"Found {len(devices)} devices")
    ```
    """
    try:
        logger.info("MCP get_devices")

        # Import here to avoid circular dependencies
        from ..database.sqlite_client import SQLiteClient

        sqlite_client = SQLiteClient()

        # Query SQLite metadata
        query = "SELECT * FROM devices ORDER BY entity_id"
        devices = await sqlite_client.query(query)

        return {
            "count": len(devices),
            "devices": devices
        }

    except Exception as e:
        logger.error(f"MCP tool error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search_events")
async def search_events(
    entity_id: Optional[str] = None,
    event_type: Optional[str] = None,
    start_time: str = "-24h",
    end_time: str = "now",
    limit: int = 100
):
    """
    MCP Tool: Search events by criteria.

    Example usage:
    ```python
    import data
    events = await data.search_events(
        entity_id="light.living_room",
        start_time="-7d"
    )
    ```
    """
    try:
        logger.info(f"MCP search_events: entity_id={entity_id}")

        # Import here to avoid circular dependencies
        from ..database.influx_client import InfluxDBQueryClient

        influx_client = InfluxDBQueryClient()

        # Build query
        query = f'''
        from(bucket: "home_assistant_events")
            |> range(start: {start_time}, stop: {end_time})
        '''

        if entity_id:
            query += f'\n    |> filter(fn: (r) => r.entity_id == "{entity_id}")'

        if event_type:
            query += f'\n    |> filter(fn: (r) => r.event_type == "{event_type}")'

        query += f'\n    |> limit(n: {limit})'

        results = await influx_client.query(query)

        return {
            "count": len(results),
            "events": results
        }

    except Exception as e:
        logger.error(f"MCP tool error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
