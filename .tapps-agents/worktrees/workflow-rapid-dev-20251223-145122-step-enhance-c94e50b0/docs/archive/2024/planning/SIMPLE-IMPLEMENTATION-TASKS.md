# Simple Implementation Tasks
## HA Ingestor Service Separation

### Overview
**Total Effort**: 2-3 hours  
**Complexity**: Low  
**Risk**: Minimal  

---

## Task 1: WebSocket Service Refactor (1 hour)

### 1.1 Create Simple HTTP Client
**File**: `services/websocket-ingestion/src/http_client.py`  
**Effort**: 20 minutes

```python
import aiohttp
import asyncio
import logging
from typing import Dict, Any

class SimpleHTTPClient:
    """Simple HTTP client for sending events to enrichment service"""
    
    def __init__(self, enrichment_url: str):
        self.enrichment_url = enrichment_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def send_event(self, event_data: Dict[str, Any]) -> bool:
        """Send event to enrichment service with simple retry logic"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                async with self.session.post(
                    f"{self.enrichment_url}/events",
                    json=event_data,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        logging.info(f"Event sent successfully on attempt {attempt + 1}")
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

**Acceptance Criteria:**
- [ ] HTTP client with basic retry logic (3 attempts)
- [ ] Simple exponential backoff (0.5s, 1s, 1.5s)
- [ ] Proper error handling and logging
- [ ] 5-second timeout for requests

### 1.2 Remove InfluxDB Dependencies
**File**: `services/websocket-ingestion/src/main.py`  
**Effort**: 15 minutes

**Changes to make:**
```python
# REMOVE these imports and code:
# from influxdb_client import InfluxDBClient
# from influxdb_client.client.write_api import SYNCHRONOUS

# REMOVE InfluxDB client initialization
# self.influx_client = InfluxDBClient(...)

# REMOVE direct InfluxDB writes
# await self.write_to_influxdb(processed_event)
```

**Acceptance Criteria:**
- [ ] Remove all InfluxDB imports
- [ ] Remove InfluxDB client initialization
- [ ] Remove direct database write calls
- [ ] Clean up unused variables

### 1.3 Update Event Handler
**File**: `services/websocket-ingestion/src/main.py`  
**Effort**: 25 minutes

**Replace existing event handler:**
```python
async def on_event(self, event_data: dict):
    """Handle incoming HA event - send to enrichment service"""
    try:
        # Send event to enrichment service
        success = await self.http_client.send_event(event_data)
        
        if success:
            # Record for monitoring
            self.event_rate_monitor.record_event(event_data)
            logging.info(f"Event processed successfully: {event_data.get('event_type', 'unknown')}")
        else:
            logging.error("Failed to send event to enrichment service")
            
    except Exception as e:
        logging.error(f"Error processing event: {e}")
```

**Update main function:**
```python
async def main():
    # Initialize HTTP client
    enrichment_url = os.getenv("ENRICHMENT_SERVICE_URL", "http://enrichment-pipeline:8002")
    
    async with SimpleHTTPClient(enrichment_url) as http_client:
        # Initialize websocket service with HTTP client
        service = WebSocketIngestionService(http_client=http_client)
        await service.start()
```

**Acceptance Criteria:**
- [ ] Event handler sends to enrichment service via HTTP
- [ ] Proper error handling and logging
- [ ] HTTP client properly initialized and managed
- [ ] Event monitoring still works

---

## Task 2: Enrichment Service Enhancement (1 hour)

### 2.1 Add FastAPI HTTP Endpoint
**File**: `services/enrichment-pipeline/src/main.py`  
**Effort**: 30 minutes

**Add FastAPI endpoint:**
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import uvicorn

app = FastAPI()

class EventData(BaseModel):
    event_type: str
    data: Dict[str, Any]
    time_fired: str
    origin: str
    context: Dict[str, Any] = {}

@app.post("/events")
async def receive_event(event: EventData):
    """Receive event from websocket service"""
    try:
        logging.info(f"Received event: {event.event_type}")
        
        # Process the event (use existing logic)
        processed_event = await process_event(event.dict())
        
        if processed_event:
            # Write to InfluxDB (use existing logic)
            await write_to_influxdb(processed_event)
            logging.info(f"Event processed and stored: {event.event_type}")
            return {"status": "success", "event_id": processed_event.get("id")}
        else:
            logging.warning(f"Event processing returned None: {event.event_type}")
            return {"status": "skipped", "reason": "processing_returned_none"}
            
    except Exception as e:
        logging.error(f"Error processing event: {e}")
        raise HTTPException(status_code=500, detail=f"Event processing failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "enrichment-pipeline"}
```

**Acceptance Criteria:**
- [ ] FastAPI endpoint receives events via HTTP POST
- [ ] Uses existing event processing logic
- [ ] Uses existing InfluxDB writing logic
- [ ] Proper error handling and HTTP status codes
- [ ] Health check endpoint

### 2.2 Update Main Function
**File**: `services/enrichment-pipeline/src/main.py`  
**Effort**: 20 minutes

**Replace main function:**
```python
async def main():
    """Start enrichment service as HTTP API"""
    import uvicorn
    
    # Initialize InfluxDB client (keep existing logic)
    influx_client = initialize_influxdb()
    
    # Start FastAPI server
    config = uvicorn.Config(
        app, 
        host="0.0.0.0", 
        port=8002,
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    logging.info("Starting enrichment service on port 8002")
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
```

**Acceptance Criteria:**
- [ ] FastAPI server starts on port 8002
- [ ] InfluxDB client properly initialized
- [ ] Proper logging and error handling
- [ ] Service runs as HTTP API (not WebSocket)

### 2.3 Remove Unused WebSocket Code
**File**: `services/enrichment-pipeline/src/main.py`  
**Effort**: 10 minutes

**Remove unused code:**
```python
# REMOVE WebSocket connection logic
# REMOVE WebSocket event handlers
# REMOVE WebSocket-specific imports
```

**Acceptance Criteria:**
- [ ] Remove all WebSocket-related code
- [ ] Remove unused imports
- [ ] Clean up unused functions
- [ ] Keep only HTTP API and InfluxDB logic

---

## Task 3: Configuration Updates (30 minutes)

### 3.1 Update Docker Compose
**Files**: All `docker-compose*.yml` files  
**Effort**: 15 minutes

**Add environment variables:**
```yaml
services:
  websocket-ingestion:
    environment:
      - ENRICHMENT_SERVICE_URL=http://enrichment-pipeline:8002
      - HA_WEBSOCKET_URL=${HA_WEBSOCKET_URL}
      - HA_ACCESS_TOKEN=${HA_ACCESS_TOKEN}
      
  enrichment-pipeline:
    environment:
      - INFLUXDB_URL=http://influxdb:8086
      - INFLUXDB_TOKEN=${INFLUXDB_TOKEN}
      - INFLUXDB_ORG=${INFLUXDB_ORG}
      - INFLUXDB_BUCKET=${INFLUXDB_BUCKET}
    ports:
      - "8002:8002"  # Expose HTTP API port
```

**Acceptance Criteria:**
- [ ] Environment variables for service communication
- [ ] Port 8002 exposed for enrichment service
- [ ] All necessary HA and InfluxDB variables

### 3.2 Update Requirements
**Files**: `services/*/requirements.txt`  
**Effort**: 10 minutes

**Add to websocket-ingestion requirements:**
```
aiohttp>=3.8.0
```

**Add to enrichment-pipeline requirements:**
```
fastapi>=0.100.0
uvicorn[standard]>=0.20.0
```

**Acceptance Criteria:**
- [ ] aiohttp added to websocket service
- [ ] FastAPI and uvicorn added to enrichment service
- [ ] Version constraints specified

### 3.3 Update Dockerfiles
**Files**: `services/*/Dockerfile*`  
**Effort**: 5 minutes

**Ensure proper port exposure:**
```dockerfile
# In enrichment-pipeline Dockerfile
EXPOSE 8002
```

**Acceptance Criteria:**
- [ ] Port 8002 exposed in enrichment service
- [ ] No unnecessary port exposures
- [ ] Proper service configuration

---

## Task 4: Testing and Validation (30 minutes)

### 4.1 Local Testing
**Effort**: 15 minutes

**Test steps:**
1. Build and start services
2. Check service health endpoints
3. Monitor logs for event flow
4. Verify InfluxDB data ingestion

**Commands:**
```bash
# Build and start
docker-compose up -d

# Check health
curl http://localhost:8002/health

# Monitor logs
docker-compose logs -f websocket-ingestion
docker-compose logs -f enrichment-pipeline
```

**Acceptance Criteria:**
- [ ] All services start successfully
- [ ] Health checks return 200 OK
- [ ] Events flow through HTTP communication
- [ ] Data appears in InfluxDB

### 4.2 Performance Validation
**Effort**: 15 minutes

**Validation steps:**
1. Monitor event processing rate
2. Check for data loss
3. Verify error handling
4. Test service restart

**Acceptance Criteria:**
- [ ] Maintain ~17 events/minute baseline
- [ ] No data loss during normal operation
- [ ] Proper error handling and logging
- [ ] Services recover gracefully from restarts

---

## Success Criteria

### ✅ Functional Requirements
- [ ] WebSocket service only captures events
- [ ] Enrichment service processes all events
- [ ] Events flow: HA → WebSocket → HTTP → Enrichment → InfluxDB
- [ ] No data loss during migration
- [ ] Maintain baseline performance

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

If issues occur during implementation:

1. **Stop services**: `docker-compose down`
2. **Revert code changes**: `git checkout HEAD~1`
3. **Restart services**: `docker-compose up -d`
4. **Verify functionality**: Check event flow and InfluxDB data

**Rollback time: < 5 minutes**

---

## Implementation Order

1. **Task 1**: WebSocket service refactor (1 hour)
2. **Task 2**: Enrichment service enhancement (1 hour)
3. **Task 3**: Configuration updates (30 minutes)
4. **Task 4**: Testing and validation (30 minutes)

**Total time: 3 hours**

This approach provides proper microservices architecture without over-engineering for a simple, low-volume system.
