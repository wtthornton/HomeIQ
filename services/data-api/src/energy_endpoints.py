"""
Energy Correlation API Endpoints
Provides access to energy-event correlation data and smart meter readings
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel

from influxdb_client import InfluxDBClient

import os

logger = logging.getLogger(__name__)


# Pydantic Models
class EnergyCorrelation(BaseModel):
    """Energy correlation data model"""
    timestamp: datetime
    entity_id: str
    domain: str
    state: str
    previous_state: str
    power_before_w: float
    power_after_w: float
    power_delta_w: float
    power_delta_pct: float


class PowerReading(BaseModel):
    """Power reading from smart meter"""
    timestamp: datetime
    total_power_w: float
    daily_kwh: float


class CircuitPowerReading(BaseModel):
    """Circuit-level power reading"""
    timestamp: datetime
    circuit_name: str
    power_w: float
    percentage: float


class DeviceEnergyImpact(BaseModel):
    """Energy impact analysis for a device"""
    entity_id: str
    domain: str
    average_power_on_w: float
    average_power_off_w: float
    total_state_changes: int
    estimated_daily_kwh: float
    estimated_monthly_cost: float


class EnergyStatistics(BaseModel):
    """Overall energy statistics"""
    current_power_w: float
    daily_kwh: float
    peak_power_w: float
    peak_time: Optional[datetime]
    average_power_w: float
    total_correlations: int


# Router
router = APIRouter(prefix="/energy", tags=["energy"])


def get_influxdb_client():
    """Get InfluxDB client instance"""
    influxdb_url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
    influxdb_token = os.getenv("INFLUXDB_TOKEN", "homeiq-token")
    influxdb_org = os.getenv("INFLUXDB_ORG", "homeiq")
    
    return InfluxDBClient(
        url=influxdb_url,
        token=influxdb_token,
        org=influxdb_org
    )


@router.get("/correlations", response_model=List[EnergyCorrelation])
async def get_energy_correlations(
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    domain: Optional[str] = Query(None, description="Filter by domain (switch, light, climate, etc.)"),
    hours: int = Query(24, description="Hours of history to return", ge=1, le=168),
    min_delta: float = Query(50.0, description="Minimum power delta (watts)", ge=0),
    limit: int = Query(100, description="Maximum number of results", ge=1, le=1000)
):
    """
    Get event-energy correlations
    
    Shows which events caused significant power changes
    """
    
    try:
        client = get_influxdb_client()
        query_api = client.query_api()
        
        # Build Flux query
        start_time = datetime.utcnow() - timedelta(hours=hours)
        bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")
        
        # Build filters
        filters = []
        if entity_id:
            filters.append(f'r["entity_id"] == "{entity_id}"')
        if domain:
            filters.append(f'r["domain"] == "{domain}"')
        
        filter_clause = " and ".join(filters) if filters else "true"
        
        flux_query = f'''
        from(bucket: "{bucket}")
          |> range(start: {start_time.isoformat()}Z)
          |> filter(fn: (r) => r["_measurement"] == "event_energy_correlation")
          |> filter(fn: (r) => {filter_clause})
          |> filter(fn: (r) => r["_field"] == "power_delta_w" and (r["_value"] >= {min_delta} or r["_value"] <= -{min_delta}))
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: {limit})
        '''
        
        tables = query_api.query(flux_query, org=os.getenv("INFLUXDB_ORG", "homeiq"))
        
        correlations = []
        for table in tables:
            for record in table.records:
                correlations.append(EnergyCorrelation(
                    timestamp=record.get_time(),
                    entity_id=record.values.get("entity_id", ""),
                    domain=record.values.get("domain", ""),
                    state=record.values.get("state", ""),
                    previous_state=record.values.get("previous_state", ""),
                    power_before_w=record.values.get("power_before_w", 0),
                    power_after_w=record.values.get("power_after_w", 0),
                    power_delta_w=record.values.get("_value", 0),
                    power_delta_pct=record.values.get("power_delta_pct", 0)
                ))
        
        client.close()
        return correlations
        
    except Exception as e:
        logger.error(f"Error getting energy correlations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to query correlations: {str(e)}"
        )


@router.get("/current", response_model=PowerReading)
async def get_current_power():
    """Get current power consumption from smart meter"""
    
    try:
        client = get_influxdb_client()
        query_api = client.query_api()
        
        bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")
        
        flux_query = f'''
        from(bucket: "{bucket}")
          |> range(start: -5m)
          |> filter(fn: (r) => r["_measurement"] == "smart_meter")
          |> filter(fn: (r) => r["_field"] == "total_power_w" or r["_field"] == "daily_kwh")
          |> last()
        '''
        
        tables = query_api.query(flux_query, org=os.getenv("INFLUXDB_ORG", "homeiq"))
        
        power_w = 0.0
        daily_kwh = 0.0
        timestamp = datetime.utcnow()
        
        for table in tables:
            for record in table.records:
                field = record.get_field()
                value = record.get_value()
                timestamp = record.get_time()
                
                if field == "total_power_w":
                    power_w = float(value)
                elif field == "daily_kwh":
                    daily_kwh = float(value)
        
        client.close()
        
        return PowerReading(
            timestamp=timestamp,
            total_power_w=power_w,
            daily_kwh=daily_kwh
        )
        
    except Exception as e:
        logger.error(f"Error getting current power: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query power: {str(e)}"
        )


@router.get("/circuits", response_model=List[CircuitPowerReading])
async def get_circuit_power(
    hours: int = Query(1, description="Hours of history", ge=1, le=24)
):
    """Get circuit-level power readings"""
    
    try:
        client = get_influxdb_client()
        query_api = client.query_api()
        
        bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        flux_query = f'''
        from(bucket: "{bucket}")
          |> range(start: {start_time.isoformat()}Z)
          |> filter(fn: (r) => r["_measurement"] == "smart_meter_circuit")
          |> filter(fn: (r) => r["_field"] == "power_w")
          |> group(columns: ["circuit_name"])
          |> last()
        '''
        
        tables = query_api.query(flux_query, org=os.getenv("INFLUXDB_ORG", "homeiq"))
        
        circuits = []
        for table in tables:
            for record in table.records:
                circuits.append(CircuitPowerReading(
                    timestamp=record.get_time(),
                    circuit_name=record.values.get("circuit_name", ""),
                    power_w=float(record.get_value()),
                    percentage=record.values.get("percentage", 0.0)
                ))
        
        client.close()
        return circuits
        
    except Exception as e:
        logger.error(f"Error getting circuit power: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query circuits: {str(e)}"
        )


@router.get("/device-impact/{entity_id}", response_model=DeviceEnergyImpact)
async def get_device_energy_impact(
    entity_id: str,
    days: int = Query(7, description="Days of history", ge=1, le=30)
):
    """
    Get energy impact analysis for a specific device
    
    Returns:
    - Average power change when device turns on/off
    - Total energy attributed to device
    - Usage patterns and cost estimates
    """
    
    try:
        client = get_influxdb_client()
        query_api = client.query_api()
        
        bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")
        start_time = datetime.utcnow() - timedelta(days=days)
        
        # Query ON transitions
        flux_on = f'''
        from(bucket: "{bucket}")
          |> range(start: {start_time.isoformat()}Z)
          |> filter(fn: (r) => r["_measurement"] == "event_energy_correlation")
          |> filter(fn: (r) => r["entity_id"] == "{entity_id}")
          |> filter(fn: (r) => r["state"] == "on")
          |> filter(fn: (r) => r["_field"] == "power_delta_w")
          |> mean()
        '''
        
        # Query OFF transitions
        flux_off = f'''
        from(bucket: "{bucket}")
          |> range(start: {start_time.isoformat()}Z)
          |> filter(fn: (r) => r["_measurement"] == "event_energy_correlation")
          |> filter(fn: (r) => r["entity_id"] == "{entity_id}")
          |> filter(fn: (r) => r["state"] == "off")
          |> filter(fn: (r) => r["_field"] == "power_delta_w")
          |> mean()
        '''
        
        # Count total state changes
        flux_count = f'''
        from(bucket: "{bucket}")
          |> range(start: {start_time.isoformat()}Z)
          |> filter(fn: (r) => r["_measurement"] == "event_energy_correlation")
          |> filter(fn: (r) => r["entity_id"] == "{entity_id}")
          |> filter(fn: (r) => r["_field"] == "power_delta_w")
          |> count()
        '''
        
        # Execute queries
        on_tables = query_api.query(flux_on, org=os.getenv("INFLUXDB_ORG", "homeiq"))
        off_tables = query_api.query(flux_off, org=os.getenv("INFLUXDB_ORG", "homeiq"))
        count_tables = query_api.query(flux_count, org=os.getenv("INFLUXDB_ORG", "homeiq"))
        
        avg_power_on = 0.0
        avg_power_off = 0.0
        total_changes = 0
        domain = ""
        
        # Parse ON power
        for table in on_tables:
            for record in table.records:
                avg_power_on = float(record.get_value())
                domain = record.values.get("domain", "")
        
        # Parse OFF power
        for table in off_tables:
            for record in table.records:
                avg_power_off = float(record.get_value())
        
        # Parse count
        for table in count_tables:
            for record in table.records:
                total_changes = int(record.get_value())
        
        # Calculate daily usage (assuming average 8 hours on per day)
        hours_on_per_day = 8.0
        if avg_power_on > 0:
            daily_kwh = (avg_power_on * hours_on_per_day) / 1000.0
        else:
            daily_kwh = 0.0
        
        # Estimate monthly cost (assuming $0.12/kWh)
        monthly_cost = daily_kwh * 30 * 0.12
        
        client.close()
        
        return DeviceEnergyImpact(
            entity_id=entity_id,
            domain=domain,
            average_power_on_w=avg_power_on,
            average_power_off_w=avg_power_off,
            total_state_changes=total_changes,
            estimated_daily_kwh=daily_kwh,
            estimated_monthly_cost=monthly_cost
        )
        
    except Exception as e:
        logger.error(f"Error getting device impact for {entity_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query device impact: {str(e)}"
        )


@router.get("/statistics", response_model=EnergyStatistics)
async def get_energy_statistics(
    hours: int = Query(24, description="Hours for statistics", ge=1, le=168)
):
    """Get overall energy statistics"""
    
    try:
        client = get_influxdb_client()
        query_api = client.query_api()
        
        bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Current power
        flux_current = f'''
        from(bucket: "{bucket}")
          |> range(start: -5m)
          |> filter(fn: (r) => r["_measurement"] == "smart_meter")
          |> filter(fn: (r) => r["_field"] == "total_power_w" or r["_field"] == "daily_kwh")
          |> last()
        '''
        
        # Peak power in period
        flux_peak = f'''
        from(bucket: "{bucket}")
          |> range(start: {start_time.isoformat()}Z)
          |> filter(fn: (r) => r["_measurement"] == "smart_meter")
          |> filter(fn: (r) => r["_field"] == "total_power_w")
          |> max()
        '''
        
        # Average power
        flux_avg = f'''
        from(bucket: "{bucket}")
          |> range(start: {start_time.isoformat()}Z)
          |> filter(fn: (r) => r["_measurement"] == "smart_meter")
          |> filter(fn: (r) => r["_field"] == "total_power_w")
          |> mean()
        '''
        
        # Count correlations
        flux_correlations = f'''
        from(bucket: "{bucket}")
          |> range(start: {start_time.isoformat()}Z)
          |> filter(fn: (r) => r["_measurement"] == "event_energy_correlation")
          |> filter(fn: (r) => r["_field"] == "power_delta_w")
          |> count()
        '''
        
        # Execute queries
        current_tables = query_api.query(flux_current, org=os.getenv("INFLUXDB_ORG", "homeiq"))
        peak_tables = query_api.query(flux_peak, org=os.getenv("INFLUXDB_ORG", "homeiq"))
        avg_tables = query_api.query(flux_avg, org=os.getenv("INFLUXDB_ORG", "homeiq"))
        corr_tables = query_api.query(flux_correlations, org=os.getenv("INFLUXDB_ORG", "homeiq"))
        
        current_power = 0.0
        daily_kwh = 0.0
        peak_power = 0.0
        peak_time = None
        avg_power = 0.0
        total_correlations = 0
        
        # Parse current
        for table in current_tables:
            for record in table.records:
                field = record.get_field()
                if field == "total_power_w":
                    current_power = float(record.get_value())
                elif field == "daily_kwh":
                    daily_kwh = float(record.get_value())
        
        # Parse peak
        for table in peak_tables:
            for record in table.records:
                peak_power = float(record.get_value())
                peak_time = record.get_time()
        
        # Parse average
        for table in avg_tables:
            for record in table.records:
                avg_power = float(record.get_value())
        
        # Parse correlations count
        for table in corr_tables:
            for record in table.records:
                total_correlations = int(record.get_value())
        
        client.close()
        
        return EnergyStatistics(
            current_power_w=current_power,
            daily_kwh=daily_kwh,
            peak_power_w=peak_power,
            peak_time=peak_time,
            average_power_w=avg_power,
            total_correlations=total_correlations
        )
        
    except Exception as e:
        logger.error(f"Error getting energy statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query statistics: {str(e)}"
        )


@router.get("/top-consumers", response_model=List[DeviceEnergyImpact])
async def get_top_energy_consumers(
    days: int = Query(7, description="Days of history", ge=1, le=30),
    limit: int = Query(10, description="Number of devices to return", ge=1, le=50)
):
    """
    Get top energy consuming devices based on correlation data
    
    Returns devices sorted by estimated daily energy consumption
    """
    
    try:
        client = get_influxdb_client()
        query_api = client.query_api()
        
        bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")
        start_time = datetime.utcnow() - timedelta(days=days)
        
        # Get average power delta by entity (ON transitions only)
        flux_query = f'''
        from(bucket: "{bucket}")
          |> range(start: {start_time.isoformat()}Z)
          |> filter(fn: (r) => r["_measurement"] == "event_energy_correlation")
          |> filter(fn: (r) => r["state"] == "on")
          |> filter(fn: (r) => r["_field"] == "power_delta_w")
          |> group(columns: ["entity_id", "domain"])
          |> mean()
          |> sort(desc: true)
          |> limit(n: {limit})
        '''
        
        tables = query_api.query(flux_query, org=os.getenv("INFLUXDB_ORG", "homeiq"))
        
        devices = []
        for table in tables:
            for record in table.records:
                entity_id = record.values.get("entity_id", "")
                domain = record.values.get("domain", "")
                avg_power = float(record.get_value())
                
                # Estimate daily usage (8 hours on)
                daily_kwh = (avg_power * 8) / 1000.0
                monthly_cost = daily_kwh * 30 * 0.12
                
                devices.append(DeviceEnergyImpact(
                    entity_id=entity_id,
                    domain=domain,
                    average_power_on_w=avg_power,
                    average_power_off_w=0.0,
                    total_state_changes=0,
                    estimated_daily_kwh=daily_kwh,
                    estimated_monthly_cost=monthly_cost
                ))
        
        client.close()
        return devices
        
    except Exception as e:
        logger.error(f"Error getting top consumers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query top consumers: {str(e)}"
        )

