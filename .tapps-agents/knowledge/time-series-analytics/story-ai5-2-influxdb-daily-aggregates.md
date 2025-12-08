# Story AI5.2: InfluxDB Daily Aggregates Implementation

**Story ID:** AI5.2  
**Epic:** Epic-AI-5 (Incremental Pattern Processing Architecture)  
**Priority:** Critical  
**Effort:** 10-12 hours  
**Dependencies:** AI5.1 (Multi-Layer Storage Design)

---

## User Story

**As a** backend developer  
**I want** to implement InfluxDB daily aggregate storage and retrieval  
**So that** detectors can store daily pattern summaries and query historical data efficiently

---

## Context

This story implements the Layer 2 (Daily Aggregates) storage infrastructure designed in AI5.1. It creates the InfluxDB buckets, implements write/read clients, and provides helper functions for detectors to store and query daily aggregates.

---

## Acceptance Criteria

### Infrastructure
- [ ] InfluxDB bucket `pattern_aggregates_daily` created with 90-day retention
- [ ] Write client implemented for all detector types
- [ ] Read client implemented with query helpers
- [ ] Connection pooling and error handling implemented

### Data Storage
- [ ] Each detector type can write daily aggregates
- [ ] JSON fields properly serialized/deserialized
- [ ] Tags and fields match schema from AI5.1
- [ ] Batch write support for efficiency

### Data Retrieval
- [ ] Query by date range
- [ ] Query by detector type
- [ ] Query by entity_id/device_id
- [ ] Aggregation functions (sum, mean, count)

### Testing
- [ ] Unit tests for write operations
- [ ] Unit tests for read operations
- [ ] Integration tests with real InfluxDB
- [ ] Performance tests (write 1000 records < 1 second)

---

## Technical Design

### File Structure
```
services/ai-automation-service/src/
├── clients/
│   ├── influxdb_client.py (existing - update)
│   └── pattern_aggregate_client.py (NEW)
├── models/
│   └── pattern_aggregates.py (NEW - Pydantic models)
└── utils/
    └── influxdb_helpers.py (NEW - helper functions)
```

### Pattern Aggregate Client

```python
# services/ai-automation-service/src/clients/pattern_aggregate_client.py

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)


class PatternAggregateClient:
    """
    Client for writing and reading pattern aggregates to/from InfluxDB.
    
    Supports Layer 2 (Daily Aggregates) storage for all detector types.
    """
    
    def __init__(
        self,
        url: str,
        token: str,
        org: str,
        bucket: str = "pattern_aggregates_daily"
    ):
        """Initialize Pattern Aggregate client."""
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()
        
        logger.info(f"PatternAggregateClient initialized: bucket={bucket}")
    
    # ========================================================================
    # Write Operations
    # ========================================================================
    
    def write_time_based_daily(
        self,
        date: datetime,
        entity_id: str,
        domain: str,
        hourly_distribution: List[int],
        peak_hours: List[int],
        frequency: float,
        confidence: float,
        occurrences: int
    ) -> bool:
        """
        Write time-based pattern daily aggregate.
        
        Args:
            date: Date for this aggregate (time component ignored)
            entity_id: Entity ID (e.g., "light.living_room")
            domain: Domain (e.g., "light")
            hourly_distribution: Array of 24 integers (activity per hour)
            peak_hours: List of peak activity hours
            frequency: Pattern frequency (0.0-1.0)
            confidence: Pattern confidence (0.0-1.0)
            occurrences: Number of occurrences
            
        Returns:
            True if successful, False otherwise
        """
        try:
            point = (
                Point("time_based_daily")
                .tag("date", date.strftime("%Y-%m-%d"))
                .tag("entity_id", entity_id)
                .tag("domain", domain)
                .field("hourly_distribution", json.dumps(hourly_distribution))
                .field("peak_hours", json.dumps(peak_hours))
                .field("frequency", frequency)
                .field("confidence", confidence)
                .field("occurrences", occurrences)
                .time(date, WritePrecision.S)
            )
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.debug(f"Wrote time_based_daily for {entity_id} on {date.date()}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write time_based_daily: {e}")
            return False
    
    def write_co_occurrence_daily(
        self,
        date: datetime,
        device_pair: str,
        co_occurrence_count: int,
        time_window_seconds: int,
        confidence: float,
        typical_hours: List[int]
    ) -> bool:
        """Write co-occurrence pattern daily aggregate."""
        try:
            point = (
                Point("co_occurrence_daily")
                .tag("date", date.strftime("%Y-%m-%d"))
                .tag("device_pair", device_pair)
                .field("co_occurrence_count", co_occurrence_count)
                .field("time_window_seconds", time_window_seconds)
                .field("confidence", confidence)
                .field("typical_hours", json.dumps(typical_hours))
                .time(date, WritePrecision.S)
            )
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.debug(f"Wrote co_occurrence_daily for {device_pair} on {date.date()}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write co_occurrence_daily: {e}")
            return False
    
    def write_sequence_daily(
        self,
        date: datetime,
        sequence_id: str,
        sequence: List[str],
        frequency: int,
        avg_duration_seconds: float,
        confidence: float
    ) -> bool:
        """Write sequence pattern daily aggregate."""
        try:
            point = (
                Point("sequence_daily")
                .tag("date", date.strftime("%Y-%m-%d"))
                .tag("sequence_id", sequence_id)
                .field("sequence", json.dumps(sequence))
                .field("frequency", frequency)
                .field("avg_duration_seconds", avg_duration_seconds)
                .field("confidence", confidence)
                .time(date, WritePrecision.S)
            )
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.debug(f"Wrote sequence_daily {sequence_id} on {date.date()}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write sequence_daily: {e}")
            return False
    
    def write_room_based_daily(
        self,
        date: datetime,
        area_id: str,
        activity_level: float,
        device_usage: Dict[str, int],
        transition_patterns: List[Dict],
        peak_activity_hours: List[int]
    ) -> bool:
        """Write room-based pattern daily aggregate."""
        try:
            point = (
                Point("room_based_daily")
                .tag("date", date.strftime("%Y-%m-%d"))
                .tag("area_id", area_id)
                .field("activity_level", activity_level)
                .field("device_usage", json.dumps(device_usage))
                .field("transition_patterns", json.dumps(transition_patterns))
                .field("peak_activity_hours", json.dumps(peak_activity_hours))
                .time(date, WritePrecision.S)
            )
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.debug(f"Wrote room_based_daily for {area_id} on {date.date()}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write room_based_daily: {e}")
            return False
    
    def write_duration_daily(
        self,
        date: datetime,
        entity_id: str,
        avg_duration_seconds: float,
        min_duration_seconds: float,
        max_duration_seconds: float,
        duration_variance: float,
        efficiency_score: float
    ) -> bool:
        """Write duration pattern daily aggregate."""
        try:
            point = (
                Point("duration_daily")
                .tag("date", date.strftime("%Y-%m-%d"))
                .tag("entity_id", entity_id)
                .field("avg_duration_seconds", avg_duration_seconds)
                .field("min_duration_seconds", min_duration_seconds)
                .field("max_duration_seconds", max_duration_seconds)
                .field("duration_variance", duration_variance)
                .field("efficiency_score", efficiency_score)
                .time(date, WritePrecision.S)
            )
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.debug(f"Wrote duration_daily for {entity_id} on {date.date()}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write duration_daily: {e}")
            return False
    
    def write_anomaly_daily(
        self,
        date: datetime,
        entity_id: str,
        anomaly_type: str,
        anomaly_score: float,
        baseline_deviation: float,
        occurrences: int,
        severity: str
    ) -> bool:
        """Write anomaly pattern daily aggregate."""
        try:
            point = (
                Point("anomaly_daily")
                .tag("date", date.strftime("%Y-%m-%d"))
                .tag("entity_id", entity_id)
                .tag("anomaly_type", anomaly_type)
                .field("anomaly_score", anomaly_score)
                .field("baseline_deviation", baseline_deviation)
                .field("occurrences", occurrences)
                .field("severity", severity)
                .time(date, WritePrecision.S)
            )
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.debug(f"Wrote anomaly_daily for {entity_id} on {date.date()}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write anomaly_daily: {e}")
            return False
    
    # ========================================================================
    # Batch Write Operations
    # ========================================================================
    
    def write_batch(self, points: List[Point]) -> bool:
        """
        Write multiple points in a single batch.
        
        Args:
            points: List of InfluxDB Point objects
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.write_api.write(bucket=self.bucket, org=self.org, record=points)
            logger.info(f"Wrote {len(points)} points in batch")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write batch: {e}")
            return False
    
    # ========================================================================
    # Read Operations
    # ========================================================================
    
    def query_time_based_daily(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        entity_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Query time-based daily aggregates.
        
        Args:
            start_date: Start date for query
            end_date: End date for query (default: now)
            entity_id: Optional filter by entity_id
            
        Returns:
            List of aggregate dictionaries
        """
        if end_date is None:
            end_date = datetime.now()
        
        flux_query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: {start_date.isoformat()}, stop: {end_date.isoformat()})
              |> filter(fn: (r) => r._measurement == "time_based_daily")
        '''
        
        if entity_id:
            flux_query += f'''
              |> filter(fn: (r) => r.entity_id == "{entity_id}")
            '''
        
        return self._execute_query(flux_query)
    
    def query_co_occurrence_daily(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        device_pair: Optional[str] = None
    ) -> List[Dict]:
        """Query co-occurrence daily aggregates."""
        if end_date is None:
            end_date = datetime.now()
        
        flux_query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: {start_date.isoformat()}, stop: {end_date.isoformat()})
              |> filter(fn: (r) => r._measurement == "co_occurrence_daily")
        '''
        
        if device_pair:
            flux_query += f'''
              |> filter(fn: (r) => r.device_pair == "{device_pair}")
            '''
        
        return self._execute_query(flux_query)
    
    def _execute_query(self, flux_query: str) -> List[Dict]:
        """
        Execute Flux query and return results as list of dictionaries.
        
        Args:
            flux_query: Flux query string
            
        Returns:
            List of result dictionaries
        """
        try:
            tables = self.query_api.query(flux_query, org=self.org)
            
            results = []
            for table in tables:
                for record in table.records:
                    result = {
                        'time': record.get_time(),
                        'measurement': record.get_measurement(),
                    }
                    
                    # Add tags
                    for key, value in record.values.items():
                        if key.startswith('_') or key in ['result', 'table']:
                            continue
                        result[key] = value
                    
                    # Parse JSON fields
                    for key in ['hourly_distribution', 'peak_hours', 'sequence', 
                               'device_usage', 'transition_patterns', 'typical_hours']:
                        if key in result and isinstance(result[key], str):
                            try:
                                result[key] = json.loads(result[key])
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse JSON field {key}")
                    
                    results.append(result)
            
            logger.debug(f"Query returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []
    
    def close(self):
        """Close InfluxDB client connection."""
        if self.client:
            self.client.close()
            logger.info("PatternAggregateClient closed")
```

---

## Implementation Tasks

### Task 1: Create Pattern Aggregate Client (4-5h)
- Implement `PatternAggregateClient` class
- Add write methods for all 6 detector types
- Add batch write support
- Add query methods with filters
- Implement error handling and logging

### Task 2: Create Pydantic Models (2h)
- Define models for each detector aggregate type
- Add validation rules
- Add JSON serialization helpers
- Document model schemas

### Task 3: Create Helper Functions (2h)
- Implement date range helpers
- Implement aggregation helpers (sum, mean, count)
- Implement JSON serialization helpers
- Add utility functions for common operations

### Task 4: Update Existing InfluxDB Client (1h)
- Add bucket creation method
- Add retention policy management
- Ensure compatibility with existing code

### Task 5: Write Unit Tests (2-3h)
- Test write operations for all detector types
- Test read operations with filters
- Test batch operations
- Test error handling
- Mock InfluxDB for unit tests

### Task 6: Write Integration Tests (1-2h)
- Test with real InfluxDB instance
- Test end-to-end write/read cycle
- Test query performance
- Test concurrent operations

---

## Testing Strategy

### Unit Tests
```python
# tests/test_pattern_aggregate_client.py

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from services.ai_automation_service.src.clients.pattern_aggregate_client import PatternAggregateClient

@pytest.fixture
def mock_influxdb():
    with patch('influxdb_client.InfluxDBClient') as mock:
        yield mock

def test_write_time_based_daily(mock_influxdb):
    """Test writing time-based daily aggregate."""
    client = PatternAggregateClient(
        url="http://localhost:8086",
        token="test-token",
        org="test-org"
    )
    
    result = client.write_time_based_daily(
        date=datetime(2025, 1, 15),
        entity_id="light.living_room",
        domain="light",
        hourly_distribution=[0]*24,
        peak_hours=[19, 20, 21],
        frequency=0.85,
        confidence=0.92,
        occurrences=12
    )
    
    assert result is True
    assert client.write_api.write.called

def test_query_time_based_daily(mock_influxdb):
    """Test querying time-based daily aggregates."""
    client = PatternAggregateClient(
        url="http://localhost:8086",
        token="test-token",
        org="test-org"
    )
    
    # Mock query response
    client.query_api.query.return_value = []
    
    results = client.query_time_based_daily(
        start_date=datetime(2025, 1, 1),
        entity_id="light.living_room"
    )
    
    assert isinstance(results, list)
    assert client.query_api.query.called
```

### Integration Tests
```python
# tests/integration/test_pattern_aggregate_integration.py

import pytest
from datetime import datetime, timedelta
from services.ai_automation_service.src.clients.pattern_aggregate_client import PatternAggregateClient

@pytest.fixture
def influxdb_client():
    """Real InfluxDB client for integration tests."""
    client = PatternAggregateClient(
        url="http://localhost:8086",
        token="test-token",
        org="test-org",
        bucket="test_pattern_aggregates"
    )
    yield client
    client.close()

def test_write_and_read_cycle(influxdb_client):
    """Test complete write/read cycle."""
    date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Write
    success = influxdb_client.write_time_based_daily(
        date=date,
        entity_id="light.test",
        domain="light",
        hourly_distribution=[1, 2, 3] + [0]*21,
        peak_hours=[0, 1, 2],
        frequency=0.75,
        confidence=0.85,
        occurrences=10
    )
    assert success is True
    
    # Read
    results = influxdb_client.query_time_based_daily(
        start_date=date - timedelta(days=1),
        entity_id="light.test"
    )
    
    assert len(results) > 0
    assert results[0]['entity_id'] == "light.test"
    assert results[0]['frequency'] == 0.75
```

---

## Performance Requirements

### Write Performance
- Single write: < 10ms
- Batch write (100 records): < 100ms
- Batch write (1000 records): < 1 second

### Read Performance
- Query 7 days of data: < 100ms
- Query 30 days of data: < 500ms
- Query 90 days of data: < 1 second

### Resource Usage
- Memory: < 50MB for client
- CPU: < 5% during normal operations
- Network: < 1MB/s typical

---

## Definition of Done

- [ ] `PatternAggregateClient` class implemented
- [ ] Write methods for all 6 detector types working
- [ ] Read methods with filtering working
- [ ] Batch write support implemented
- [ ] Pydantic models created and validated
- [ ] Helper functions implemented
- [ ] Unit tests written and passing (>90% coverage)
- [ ] Integration tests written and passing
- [ ] Performance tests meet requirements
- [ ] Error handling comprehensive
- [ ] Logging implemented
- [ ] Code reviewed and approved
- [ ] Documentation updated

---

## Notes

### Single-Home Optimizations
- No need for complex sharding or partitioning
- Simple connection pooling sufficient
- Focus on reliability over extreme performance
- Keep implementation simple and maintainable

### Error Handling
- Retry failed writes (3 attempts with exponential backoff)
- Log all errors with context
- Return False on failure, don't raise exceptions
- Graceful degradation if InfluxDB unavailable

### JSON Field Considerations
- Keep JSON fields small (<1KB typical)
- Validate JSON before writing
- Handle parse errors gracefully on read
- Consider flattening if performance issues

---

**Story Points:** 8  
**Sprint:** Epic AI-5 Sprint 1  
**Status:** Ready for Development  
**Blocked By:** AI5.1 (schema design must be complete)

