# InfluxDB Admin API Query Patterns for Time-Series Statistics

**Context7 KB Cache**

**Library:** InfluxDB Python Client  
**Topic:** Admin API querying patterns, time-series aggregation, read layer architecture  
**Retrieved:** October 12, 2025  
**Project:** HA Ingestor  
**Status:** Implementation pattern for Admin API refactoring

---

## Overview

This document describes the architectural pattern for implementing Admin API statistics endpoints that query InfluxDB for historical time-series data, rather than making direct HTTP calls to upstream services.

### Architectural Problem

**Incorrect Pattern:**
```
Enrichment Pipeline → InfluxDB (write)
Enrichment Pipeline → Admin API (direct HTTP)
Enrichment Pipeline → Dashboard (direct HTTP)
```

**Correct Pattern:**
```
Enrichment Pipeline → InfluxDB (write)
InfluxDB → Admin API (read/query)
Admin API → Dashboard (API responses)
```

---

## Core Principles

1. **InfluxDB as Source of Truth**: All time-series metrics should be stored in InfluxDB
2. **Admin API as Read Layer**: Admin API queries InfluxDB for historical and aggregated data
3. **Service Independence**: Individual services write to InfluxDB; Admin API reads from it
4. **Performance**: Use InfluxDB's aggregation capabilities rather than application-level processing

---

## Implementation Pattern for Admin API

### 1. InfluxDB Client Setup

```python
"""
Admin API InfluxDB Client Configuration
File: services/admin-api/src/influxdb_client.py
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
from influxdb_client.client.query_api import QueryApi

logger = logging.getLogger(__name__)


class AdminAPIInfluxDBClient:
    """InfluxDB client for Admin API statistics queries"""
    
    def __init__(self):
        self.url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
        self.token = os.getenv("INFLUXDB_TOKEN")
        self.org = os.getenv("INFLUXDB_ORG", "homeiq")
        self.bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")
        
        self.client: Optional[InfluxDBClient] = None
        self.query_api: Optional[QueryApi] = None
        
        # Performance tracking
        self.query_count = 0
        self.error_count = 0
        self.avg_query_time_ms = 0
    
    async def connect(self) -> bool:
        """Connect to InfluxDB"""
        try:
            self.client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org,
                timeout=30000  # 30 seconds
            )
            
            self.query_api = self.client.query_api()
            
            # Test connection
            await self._test_connection()
            
            logger.info(f"Admin API connected to InfluxDB at {self.url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            return False
    
    async def _test_connection(self):
        """Test InfluxDB connection"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.url}/health") as response:
                if response.status != 200:
                    raise Exception(f"InfluxDB health check failed: {response.status}")
    
    async def close(self):
        """Close InfluxDB connection"""
        if self.client:
            self.client.close()
            self.client = None
            self.query_api = None
```

### 2. Statistics Query Patterns

#### Event Rate Statistics

```python
async def get_event_statistics(self, period: str = "1h") -> Dict[str, Any]:
    """
    Get event processing statistics from InfluxDB
    
    Args:
        period: Time period (1h, 6h, 24h, 7d)
    
    Returns:
        Dictionary with event statistics
    """
    query = f'''
    from(bucket: "{self.bucket}")
        |> range(start: -{period})
        |> filter(fn: (r) => r._measurement == "home_assistant_events")
        |> group(columns: ["event_type"])
        |> count()
        |> group()
        |> sum()
    '''
    
    result = await self._execute_query(query)
    
    # Calculate events per minute
    time_seconds = self._period_to_seconds(period)
    total_events = sum(r["_value"] for r in result)
    events_per_minute = (total_events / time_seconds) * 60 if time_seconds > 0 else 0
    
    return {
        "total_events": total_events,
        "events_per_minute": round(events_per_minute, 2),
        "period": period
    }
```

#### Error Rate Calculation

```python
async def get_error_rate(self, period: str = "1h") -> Dict[str, Any]:
    """
    Calculate error rate from InfluxDB metrics
    
    Returns:
        Dictionary with error statistics
    """
    # Query for total writes
    total_query = f'''
    from(bucket: "{self.bucket}")
        |> range(start: -{period})
        |> filter(fn: (r) => r._measurement == "service_metrics")
        |> filter(fn: (r) => r._field == "write_attempts")
        |> sum()
    '''
    
    # Query for errors
    error_query = f'''
    from(bucket: "{self.bucket}")
        |> range(start: -{period})
        |> filter(fn: (r) => r._measurement == "service_metrics")
        |> filter(fn: (r) => r._field == "write_errors")
        |> sum()
    '''
    
    total_result = await self._execute_query(total_query)
    error_result = await self._execute_query(error_query)
    
    total = total_result[0]["_value"] if total_result else 0
    errors = error_result[0]["_value"] if error_result else 0
    
    error_rate = (errors / total * 100) if total > 0 else 0
    
    return {
        "total_writes": total,
        "write_errors": errors,
        "error_rate_percent": round(error_rate, 2),
        "period": period
    }
```

#### Service-Specific Metrics

```python
async def get_service_metrics(self, service_name: str, period: str = "1h") -> Dict[str, Any]:
    """
    Get metrics for a specific service from InfluxDB
    
    Args:
        service_name: Name of the service (websocket-ingestion, enrichment-pipeline, etc.)
        period: Time period
    
    Returns:
        Service metrics dictionary
    """
    query = f'''
    from(bucket: "{self.bucket}")
        |> range(start: -{period})
        |> filter(fn: (r) => r._measurement == "service_metrics")
        |> filter(fn: (r) => r.service == "{service_name}")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> last()
    '''
    
    result = await self._execute_query(query)
    
    if not result:
        return {"error": f"No data found for service {service_name}"}
    
    metrics = result[0]
    
    return {
        "service": service_name,
        "events_processed": metrics.get("events_processed", 0),
        "processing_time_ms": metrics.get("processing_time_ms", 0),
        "success_rate": metrics.get("success_rate", 100),
        "last_update": metrics.get("_time"),
        "period": period
    }
```

#### Aggregated Statistics Across Services

```python
async def get_all_service_statistics(self, period: str = "1h") -> Dict[str, Any]:
    """
    Get aggregated statistics across all services
    
    Returns:
        Dictionary with aggregated metrics
    """
    # Query for all service metrics
    query = f'''
    from(bucket: "{self.bucket}")
        |> range(start: -{period})
        |> filter(fn: (r) => r._measurement == "service_metrics")
        |> group(columns: ["service"])
        |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
        |> yield(name: "mean")
    '''
    
    result = await self._execute_query(query)
    
    # Group by service
    services = {}
    for record in result:
        service = record.get("service", "unknown")
        if service not in services:
            services[service] = {
                "events_processed": 0,
                "avg_processing_time": 0,
                "success_rate": 100
            }
        
        field = record.get("_field")
        value = record.get("_value", 0)
        
        if field == "events_processed":
            services[service]["events_processed"] += value
        elif field == "processing_time_ms":
            services[service]["avg_processing_time"] = value
        elif field == "success_rate":
            services[service]["success_rate"] = value
    
    return {
        "services": services,
        "period": period,
        "timestamp": datetime.now().isoformat()
    }
```

### 3. Time-Series Trends

```python
async def get_event_trends(self, period: str = "24h", window: str = "1h") -> Dict[str, Any]:
    """
    Get event processing trends over time
    
    Args:
        period: Overall time period
        window: Aggregation window (1m, 5m, 1h)
    
    Returns:
        Time-series trend data
    """
    query = f'''
    from(bucket: "{self.bucket}")
        |> range(start: -{period})
        |> filter(fn: (r) => r._measurement == "home_assistant_events")
        |> aggregateWindow(every: {window}, fn: count, createEmpty: false)
        |> yield(name: "count")
    '''
    
    result = await self._execute_query(query)
    
    trends = []
    for record in result:
        trends.append({
            "time": record.get("_time").isoformat(),
            "count": record.get("_value", 0)
        })
    
    return {
        "trends": trends,
        "period": period,
        "window": window
    }
```

### 4. Helper Methods

```python
async def _execute_query(self, query: str) -> List[Dict[str, Any]]:
    """
    Execute InfluxDB query and return results
    
    Args:
        query: Flux query string
    
    Returns:
        List of result dictionaries
    """
    if not self.query_api:
        raise Exception("InfluxDB client not connected")
    
    try:
        start_time = datetime.now()
        
        # Execute query
        result = self.query_api.query(query=query, org=self.org)
        
        # Track performance
        query_time = (datetime.now() - start_time).total_seconds() * 1000
        self.query_count += 1
        self.avg_query_time_ms = (self.avg_query_time_ms * (self.query_count - 1) + query_time) / self.query_count
        
        # Convert to list of dictionaries
        data = []
        for table in result:
            for record in table.records:
                data.append(record.values)
        
        logger.debug(f"Query returned {len(data)} records in {query_time:.2f}ms")
        return data
        
    except Exception as e:
        self.error_count += 1
        logger.error(f"Error executing query: {e}")
        raise

def _period_to_seconds(self, period: str) -> int:
    """Convert period string to seconds"""
    conversions = {
        "15m": 15 * 60,
        "1h": 60 * 60,
        "6h": 6 * 60 * 60,
        "24h": 24 * 60 * 60,
        "7d": 7 * 24 * 60 * 60
    }
    return conversions.get(period, 3600)
```

---

## Integration with Stats Endpoints

### Refactored stats_endpoints.py Pattern

```python
"""
Refactored Statistics Endpoints using InfluxDB
File: services/admin-api/src/stats_endpoints.py
"""

from fastapi import APIRouter, HTTPException, Query
from .influxdb_client import AdminAPIInfluxDBClient

class StatsEndpoints:
    """Statistics endpoints that query InfluxDB"""
    
    def __init__(self):
        self.router = APIRouter()
        self.influxdb_client = AdminAPIInfluxDBClient()
        self._add_routes()
    
    async def initialize(self):
        """Initialize InfluxDB connection"""
        await self.influxdb_client.connect()
    
    def _add_routes(self):
        
        @self.router.get("/stats")
        async def get_statistics(period: str = Query("1h")):
            """Get comprehensive statistics from InfluxDB"""
            try:
                # Query InfluxDB directly instead of calling services
                event_stats = await self.influxdb_client.get_event_statistics(period)
                error_stats = await self.influxdb_client.get_error_rate(period)
                service_stats = await self.influxdb_client.get_all_service_statistics(period)
                trends = await self.influxdb_client.get_event_trends(period)
                
                return {
                    "timestamp": datetime.now().isoformat(),
                    "period": period,
                    "metrics": {
                        **event_stats,
                        **error_stats,
                        "services": service_stats["services"]
                    },
                    "trends": trends["trends"],
                    "source": "influxdb"  # Indicates data source
                }
                
            except Exception as e:
                logger.error(f"Error getting statistics: {e}")
                raise HTTPException(status_code=500, detail=str(e))
```

---

## Fallback Strategy

### Hybrid Approach (InfluxDB + Direct Service Queries)

```python
async def get_statistics_with_fallback(self, period: str) -> Dict[str, Any]:
    """
    Get statistics with fallback to direct service calls
    
    This provides resilience when InfluxDB is unavailable
    """
    try:
        # Primary: Query InfluxDB
        stats = await self.influxdb_client.get_all_service_statistics(period)
        stats["source"] = "influxdb"
        return stats
        
    except Exception as influx_error:
        logger.warning(f"InfluxDB query failed: {influx_error}, falling back to service calls")
        
        try:
            # Fallback: Direct service HTTP calls
            stats = await self._get_stats_from_services(period)
            stats["source"] = "services"
            stats["warning"] = "Using fallback data source"
            return stats
            
        except Exception as service_error:
            logger.error(f"Both InfluxDB and service queries failed")
            raise HTTPException(
                status_code=503,
                detail="Statistics unavailable"
            )
```

---

## Performance Best Practices

### 1. Query Optimization

```python
# BAD: Queries entire dataset
query = '''
from(bucket: "events")
    |> range(start: -30d)
    |> filter(fn: (r) => r._measurement == "events")
'''

# GOOD: Uses appropriate time ranges and aggregation
query = '''
from(bucket: "events")
    |> range(start: -1h)
    |> filter(fn: (r) => r._measurement == "events")
    |> aggregateWindow(every: 1m, fn: count)
'''
```

### 2. Caching Layer

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedStatsClient:
    """InfluxDB client with caching"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 60  # seconds
    
    async def get_statistics(self, period: str) -> Dict[str, Any]:
        """Get statistics with cache"""
        cache_key = f"stats_{period}"
        
        # Check cache
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if datetime.now() - cached_time < timedelta(seconds=self.cache_ttl):
                logger.debug(f"Cache hit for {cache_key}")
                return cached_data
        
        # Query InfluxDB
        data = await self.influxdb_client.get_all_service_statistics(period)
        
        # Update cache
        self.cache[cache_key] = (data, datetime.now())
        
        return data
```

### 3. Batch Queries

```python
async def get_dashboard_data(self, period: str) -> Dict[str, Any]:
    """Get all dashboard data in optimized queries"""
    
    # Single query with multiple calculations
    query = f'''
    events = from(bucket: "{self.bucket}")
        |> range(start: -{period})
        |> filter(fn: (r) => r._measurement == "home_assistant_events")
    
    event_count = events |> count() |> yield(name: "event_count")
    event_rate = events |> aggregateWindow(every: 1m, fn: count) |> yield(name: "event_rate")
    errors = events |> filter(fn: (r) => r.error == "true") |> count() |> yield(name: "errors")
    '''
    
    results = await self._execute_multi_query(query)
    
    return {
        "event_count": results["event_count"],
        "event_rate": results["event_rate"],
        "errors": results["errors"]
    }
```

---

## Testing Patterns

### Unit Tests

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_get_event_statistics():
    """Test event statistics query"""
    
    # Mock InfluxDB client
    mock_client = AsyncMock()
    mock_client.query_api.query = MagicMock(return_value=[
        MagicMock(records=[
            MagicMock(values={"_value": 1000, "_time": datetime.now()})
        ])
    ])
    
    client = AdminAPIInfluxDBClient()
    client.client = mock_client
    client.query_api = mock_client.query_api
    
    stats = await client.get_event_statistics("1h")
    
    assert stats["total_events"] == 1000
    assert "events_per_minute" in stats
```

---

## Migration Strategy

### Phase 1: Parallel Implementation
- Keep existing service HTTP calls
- Add InfluxDB queries in parallel
- Log and compare results

### Phase 2: Feature Flag
- Use feature flag to switch between sources
- Monitor performance and accuracy
- Gather metrics

### Phase 3: Full Migration
- Remove direct service HTTP calls
- Use InfluxDB as primary source
- Keep fallback for resilience

---

**Implementation Status:** Ready for deployment  
**Performance Target:** < 200ms per query  
**Cache Strategy:** 60-second TTL for dashboard queries  
**Fallback:** Direct service calls if InfluxDB unavailable  

**Related Files:**
- `services/admin-api/src/stats_endpoints.py` - Statistics endpoints
- `services/admin-api/src/health_endpoints.py` - Health monitoring
- `services/enrichment-pipeline/src/influxdb_wrapper.py` - Write patterns
- `services/websocket-ingestion/src/influxdb_wrapper.py` - Write patterns

**Source:** HA Ingestor architectural analysis  
**Cached:** 2025-10-12

