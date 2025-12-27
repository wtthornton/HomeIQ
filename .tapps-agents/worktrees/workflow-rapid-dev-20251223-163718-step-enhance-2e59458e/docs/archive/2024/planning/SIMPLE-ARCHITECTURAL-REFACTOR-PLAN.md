# Simple Architectural Refactor Plan
## Proper Service Separation for HA Ingestor

### Executive Summary

**Problem**: Current websocket ingestion service violates microservices principles by handling all processing internally, bypassing the enrichment pipeline and creating a monolithic service.

**Solution**: Simple refactor to separate concerns with basic HTTP communication between services.

**Scope**: 2-3 hour refactor for a system processing 17 events/minute (not enterprise-scale).

---

## Current State Analysis

### ❌ Current Architecture Issues

```
Home Assistant → WebSocket Ingestion (MONOLITHIC) → InfluxDB
                                    ↓
                            Enrichment Pipeline (UNUSED)
```

**Issues:**
1. **Monolithic Service**: Websocket ingestion does everything
2. **Unused Services**: Enrichment pipeline is completely bypassed
3. **No Service Communication**: Services don't communicate
4. **Direct Database Access**: Multiple services writing directly to InfluxDB

---

## Target Architecture Design

### ✅ Simple Microservices Architecture

```
Home Assistant → WebSocket Ingestion → HTTP POST → Enrichment Pipeline → InfluxDB
     (Event Capture Only)                    (Processing & Storage)
```

### Service Responsibilities

| Service | Current | Target | Communication |
|---------|---------|--------|---------------|
| **WebSocket Ingestion** | Everything | Event capture only | HTTP POST → Enrichment |
| **Enrichment Pipeline** | Unused | Processing & storage | Direct InfluxDB write |

---

## Simple Implementation Plan

### Phase 1: WebSocket Service Refactor (1 hour)

#### 1.1 Remove Direct InfluxDB Access
**Files to modify:**
- `services/websocket-ingestion/src/main.py`

**Changes:**
- Remove InfluxDB client initialization
- Remove direct database writes
- Add simple HTTP client for enrichment service

#### 1.2 Add HTTP Client
**Implementation:**
```python
# services/websocket-ingestion/src/http_client.py
import aiohttp
import logging

class SimpleHTTPClient:
    def __init__(self, enrichment_url: str):
        self.enrichment_url = enrichment_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def send_event(self, event_data: dict) -> bool:
        """Send event to enrichment service with simple retry"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                async with self.session.post(
                    f"{self.enrichment_url}/events",
                    json=event_data,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        return True
                    else:
                        logging.warning(f"HTTP {response.status} on attempt {attempt + 1}")
                        
            except Exception as e:
                logging.warning(f"Attempt {attempt + 1} failed: {e}")
                
            if attempt < max_retries - 1:
                await asyncio.sleep(0.5 * (attempt + 1))  # Simple backoff
        
        logging.error(f"Failed to send event after {max_retries} attempts")
        return False
```

#### 1.3 Update Event Handler
**Changes to main.py:**
```python
# Replace direct InfluxDB write with HTTP call
async def on_event(self, event_data: dict):
    """Handle incoming HA event"""
    try:
        success = await self.http_client.send_event(event_data)
        if success:
            self.event_rate_monitor.record_event(event_data)
        else:
            logging.error("Failed to send event to enrichment service")
    except Exception as e:
        logging.error(f"Error processing event: {e}")
```

### Phase 2: Enrichment Service Enhancement (1 hour)

#### 2.1 Add HTTP Endpoint
**Files to modify:**
- `services/enrichment-pipeline/src/main.py`

**Add FastAPI endpoint:**
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

app = FastAPI()

class EventData(BaseModel):
    event_type: str
    data: Dict[str, Any]
    time_fired: str
    origin: str

@app.post("/events")
async def receive_event(event: EventData):
    """Receive event from websocket service"""
    try:
        # Process the event (existing logic)
        processed_event = await process_event(event.dict())
        
        # Write to InfluxDB (existing logic)
        await write_to_influxdb(processed_event)
        
        return {"status": "success", "event_id": processed_event.get("id")}
        
    except Exception as e:
        logging.error(f"Error processing event: {e}")
        raise HTTPException(status_code=500, detail="Event processing failed")
```

#### 2.2 Update Main Function
**Changes:**
- Remove unused WebSocket connection logic
- Keep existing event processing and InfluxDB writing
- Add FastAPI server startup

### Phase 3: Configuration Updates (30 minutes)

#### 3.1 Environment Variables
**Add to docker-compose files:**
```yaml
services:
  websocket-ingestion:
    environment:
      - ENRICHMENT_SERVICE_URL=http://enrichment-pipeline:8002
      
  enrichment-pipeline:
    environment:
      - INFLUXDB_URL=http://influxdb:8086
      - INFLUXDB_TOKEN=${INFLUXDB_TOKEN}
```

#### 3.2 Port Configuration
**Update enrichment service:**
- Expose port 8002 for HTTP API
- Remove unused WebSocket port

---

## Simple Migration Strategy

### Step 1: Prepare New Code (30 minutes)
1. Implement HTTP client in websocket service
2. Add HTTP endpoint to enrichment service
3. Update configuration files

### Step 2: Deploy Changes (15 minutes)
```bash
# Stop services
docker-compose down

# Deploy new code
docker-compose up -d

# Verify services are running
docker-compose ps
```

### Step 3: Validate Functionality (15 minutes)
1. Check service health endpoints
2. Monitor logs for event flow
3. Verify InfluxDB data ingestion
4. Compare event rates (should maintain ~17 events/minute)

---

## Success Criteria

### ✅ Functional Requirements
- [ ] WebSocket service only captures events
- [ ] Enrichment service processes all events
- [ ] Events flow: HA → WebSocket → HTTP → Enrichment → InfluxDB
- [ ] No data loss during migration
- [ ] Maintain baseline performance (17 events/minute)

### ✅ Technical Requirements
- [ ] Simple HTTP communication between services
- [ ] Basic retry logic (3 attempts)
- [ ] Proper error handling and logging
- [ ] Clean service separation
- [ ] No over-engineering

### ✅ Operational Requirements
- [ ] Services start successfully
- [ ] Health checks pass
- [ ] Logs show proper event flow
- [ ] Easy rollback if needed

---

## Rollback Plan

If issues occur:
1. Stop services: `docker-compose down`
2. Revert to previous code version
3. Restart: `docker-compose up -d`

**Rollback time: < 5 minutes**

---

## Benefits of This Approach

### ✅ Appropriate for Scale
- Simple HTTP communication for 17 events/minute
- No complex patterns needed
- Easy to understand and maintain

### ✅ Proper Separation
- WebSocket service: Event capture only
- Enrichment service: Processing and storage
- Clear service boundaries

### ✅ Maintainable
- Simple code changes
- Easy to debug
- No complex infrastructure

### ✅ Cost Effective
- 2-3 hours total effort
- No additional infrastructure
- Minimal risk

---

## Next Steps

1. **Review this plan** - Ensure it meets requirements
2. **Implement Phase 1** - WebSocket service refactor
3. **Implement Phase 2** - Enrichment service enhancement
4. **Deploy and validate** - Simple migration
5. **Monitor and optimize** - Fine-tune as needed

This approach achieves proper microservices architecture without over-engineering for a simple, low-volume system.
