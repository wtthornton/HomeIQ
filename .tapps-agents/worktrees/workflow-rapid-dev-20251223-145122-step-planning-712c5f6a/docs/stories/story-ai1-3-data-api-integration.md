# Story AI1.3: Data API Integration and Historical Data Fetching

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.3  
**Priority:** Critical  
**Estimated Effort:** 8-10 hours  
**Dependencies:** Story AI1.2 (Backend foundation)

---

## User Story

**As a** pattern analyzer  
**I want** to query the Data API for historical event data  
**so that** I can detect patterns in device usage

---

## Business Value

- Enables access to 30 days of historical Home Assistant data
- Provides data foundation for all pattern detection
- Reuses existing Data API (no InfluxDB coupling)
- Supports incremental data fetching for efficiency

---

## Acceptance Criteria

1. ✅ Can fetch last 30 days of events from Data API
2. ✅ Can fetch device metadata (name, manufacturer, area)
3. ✅ Can fetch entity metadata (platform, state, attributes)
4. ✅ Data transformed to pandas DataFrame format
5. ✅ Handles Data API downtime gracefully (retries 3x with backoff)
6. ✅ Query response time <5 seconds for 30 days of data
7. ✅ Implements rate limiting (no more than 10 requests/minute)
8. ✅ Unit tests achieve 80%+ coverage

---

## Technical Implementation Notes

### Data API Client

**Create: src/data_api_client.py**

```python
import httpx
import pandas as pd
from typing import List, Dict
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class DataAPIClient:
    """Client for fetching historical data from Data API"""
    
    def __init__(self, base_url: str = "http://data-api:8006"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def fetch_events(self, start: str = "-30d", device_id: str = None) -> pd.DataFrame:
        """
        Fetch historical events from Data API.
        
        Args:
            start: Time range (e.g., "-30d" for last 30 days)
            device_id: Optional filter for specific device
        
        Returns:
            pandas DataFrame with columns: timestamp, device_id, entity_id, state, attributes
        """
        try:
            params = {"start": start}
            if device_id:
                params["device_id"] = device_id
            
            response = await self.client.get(
                f"{self.base_url}/api/events",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Convert to pandas DataFrame
            if not data:
                logger.warning(f"No events returned from Data API for start={start}")
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            
            # Parse timestamps
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            logger.info(f"Fetched {len(df)} events from Data API")
            return df
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch events from Data API: {e}")
            raise
    
    async def fetch_devices(self) -> List[Dict]:
        """Fetch all devices from Data API"""
        try:
            response = await self.client.get(f"{self.base_url}/api/devices")
            response.raise_for_status()
            devices = response.json()
            logger.info(f"Fetched {len(devices)} devices")
            return devices
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch devices: {e}")
            raise
    
    async def fetch_entities(self) -> List[Dict]:
        """Fetch all entities from Data API"""
        try:
            response = await self.client.get(f"{self.base_url}/api/entities")
            response.raise_for_status()
            entities = response.json()
            logger.info(f"Fetched {len(entities)} entities")
            return entities
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch entities: {e}")
            raise
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
```

### Configuration Management

**Create: src/config.py**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Data API
    data_api_url: str = "http://data-api:8006"
    
    # Home Assistant
    ha_url: str = "http://home-assistant:8123"
    ha_token: str
    
    # MQTT
    mqtt_broker: str = "mosquitto"
    mqtt_port: int = 1883
    
    # OpenAI
    openai_api_key: str
    
    # Scheduling
    analysis_schedule: str = "0 3 * * *"  # 3 AM daily
    
    # Database
    database_url: str = "sqlite+aiosqlite:///data/ai_automation.db"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### Database Models

```python
# See Story AI1.2 implementation guide in PRD Section 7.3
# Tables: patterns, suggestions, user_feedback
```

---

## Integration Verification

**IV1: Data fetching doesn't impact other services**
- Monitor Data API response times before/after
- Verify no performance degradation
- Check Data API logs for query patterns

**IV2: InfluxDB query patterns don't change**
- Data API continues to serve Health Dashboard
- No new InfluxDB connection created
- All queries go through Data API

**IV3: Rate limiting prevents API overload**
- Maximum 10 requests/minute enforced
- Batching used where possible
- Exponential backoff on retries

**IV4: Data transformation is efficient**
- DataFrame creation <1 second for 10k events
- Memory usage proportional to data size
- No data leaks or duplicates

---

## Tasks Breakdown

1. **Create DataAPIClient class** (2 hours)
2. **Implement fetch_events with retries** (1.5 hours)
3. **Implement fetch_devices and fetch_entities** (1 hour)
4. **Add DataFrame transformation** (1 hour)
5. **Implement rate limiting** (1 hour)
6. **Error handling and logging** (1 hour)
7. **Unit tests** (1.5 hours)
8. **Integration testing with real Data API** (1 hour)

**Total:** 8-10 hours

---

## Testing Strategy

### Unit Tests

```python
# tests/test_data_api_client.py
import pytest
from src.data_api_client import DataAPIClient
import httpx
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_fetch_events_success():
    """Test successful event fetching"""
    client = DataAPIClient()
    
    with patch.object(client.client, 'get') as mock_get:
        mock_get.return_value.json.return_value = [
            {"timestamp": "2025-10-15T12:00:00Z", "device_id": "light.bedroom", "state": "on"}
        ]
        mock_get.return_value.raise_for_status = lambda: None
        
        df = await client.fetch_events(start="-7d")
        
        assert len(df) == 1
        assert df.iloc[0]['device_id'] == 'light.bedroom'
        assert 'timestamp' in df.columns

@pytest.mark.asyncio
async def test_fetch_events_retry_on_failure():
    """Test retry logic"""
    client = DataAPIClient()
    
    with patch.object(client.client, 'get') as mock_get:
        # Fail twice, then succeed
        mock_get.side_effect = [
            httpx.HTTPError("Connection error"),
            httpx.HTTPError("Connection error"),
            AsyncMock(json=lambda: [], raise_for_status=lambda: None)
        ]
        
        df = await client.fetch_events()
        
        assert mock_get.call_count == 3  # Retried 3 times
```

### Integration Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_data_api_connection():
    """Test with real Data API (requires Docker Compose up)"""
    client = DataAPIClient(base_url="http://localhost:8006")
    
    devices = await client.fetch_devices()
    assert len(devices) > 0
    assert 'device_id' in devices[0]
    
    events = await client.fetch_events(start="-7d")
    assert isinstance(events, pd.DataFrame)
    assert len(events) > 0
```

---

## Definition of Done

- [ ] DataAPIClient class implemented
- [ ] All fetch methods working (events, devices, entities)
- [ ] DataFrame transformation implemented
- [ ] Retry logic with exponential backoff
- [ ] Rate limiting implemented
- [ ] Error handling comprehensive
- [ ] Logging for all operations
- [ ] Unit tests pass (80%+ coverage)
- [ ] Integration tests pass with real Data API
- [ ] Documentation updated
- [ ] Code reviewed and approved

---

## Reference Files

**Copy patterns from:**
- Data API existing endpoints documentation
- `shared/logging_config.py` for logging
- Existing httpx usage in other services

**Documentation:**
- httpx: https://www.python-httpx.org/
- pandas: https://pandas.pydata.org/
- tenacity (retries): https://tenacity.readthedocs.io/

---

## Notes

- Use existing Data API - don't query InfluxDB directly
- DataFrame format required for scikit-learn (Story 1.4+)
- Retry logic critical for reliability
- Rate limiting prevents overwhelming Data API
- Keep it simple - just fetch and transform, no analysis yet

---

**Story Status:** Not Started  
**Assigned To:** TBD  
**Created:** 2025-10-15  
**Updated:** 2025-10-15


