# BMAD Simple Migration Plan - Alpha System

## Executive Summary

**Objective**: Transform the current monolithic websocket ingestion service into proper microservices architecture with a simple, straightforward migration approach suitable for an alpha system.

**Approach**: Direct replacement with minimal complexity, focusing on getting the architecture right rather than zero-downtime operations.

---

## Current State Analysis

### Current Architecture Issues
```
Home Assistant → WebSocket Ingestion (Monolithic) → InfluxDB
                                    ↓
                            Enrichment Pipeline (Unused)
```

**Problems**:
- WebSocket service does everything (connection, processing, enrichment, storage)
- Enrichment pipeline is completely unused
- No proper service separation
- Single point of failure

---

## Simple Migration Strategy

### Phase 1: Prepare New Services (1-2 days)

#### 1.1 Create New Service Structure
```bash
# Create new service directories
mkdir -p services/websocket-ingestion-v2/src
mkdir -p services/enrichment-pipeline-v2/src
mkdir -p services/data-storage/src

# Copy and modify existing code
cp -r services/websocket-ingestion/* services/websocket-ingestion-v2/
cp -r services/enrichment-pipeline/* services/enrichment-pipeline-v2/
```

#### 1.2 Update Docker Configuration
```yaml
# docker-compose.simple.yml
version: '3.8'
services:
  websocket-ingestion-v2:
    build: ./services/websocket-ingestion-v2
    ports:
      - "8001:8001"
    environment:
      - ENRICHMENT_PIPELINE_URL=http://enrichment-pipeline-v2:8002
    depends_on:
      - enrichment-pipeline-v2

  enrichment-pipeline-v2:
    build: ./services/enrichment-pipeline-v2
    ports:
      - "8002:8002"
    environment:
      - DATA_STORAGE_URL=http://data-storage:8004
    depends_on:
      - data-storage

  data-storage:
    build: ./services/data-storage
    ports:
      - "8004:8004"
    depends_on:
      - influxdb
```

### Phase 2: Implement Service Communication (2-3 days)

#### 2.1 WebSocket Service - Event Forwarding Only
```python
# services/websocket-ingestion-v2/src/main.py
class WebSocketIngestionService:
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.event_forwarder = EventForwarder()
        # REMOVE: All internal processing components
    
    async def _on_event(self, processed_event):
        """Forward events to enrichment pipeline"""
        try:
            # Simple HTTP POST to enrichment pipeline
            success = await self.event_forwarder.send_event(processed_event)
            if success:
                logger.info(f"Event forwarded successfully: {processed_event.get('entity_id')}")
            else:
                logger.error(f"Failed to forward event: {processed_event.get('entity_id')}")
        except Exception as e:
            logger.error(f"Error forwarding event: {e}")

# services/websocket-ingestion-v2/src/event_forwarder.py
class EventForwarder:
    def __init__(self, enrichment_url: str):
        self.enrichment_url = enrichment_url
        self.session = aiohttp.ClientSession()
    
    async def send_event(self, event_data: dict) -> bool:
        """Send event to enrichment pipeline"""
        try:
            async with self.session.post(
                f"{self.enrichment_url}/api/v1/events",
                json=event_data,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Failed to send event: {e}")
            return False
```

#### 2.2 Enrichment Pipeline - HTTP Event Reception
```python
# services/enrichment-pipeline-v2/src/api_server.py
from fastapi import FastAPI, HTTPException
import uvicorn

app = FastAPI(title="Enrichment Pipeline API")

@app.post("/api/v1/events")
async def receive_event(event_data: dict):
    """Receive events from websocket service"""
    try:
        # Process the event
        processed_event = await event_processor.process(event_data)
        
        # Send to data storage
        success = await storage_client.store_event(processed_event)
        
        if success:
            return {"success": True, "message": "Event processed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to store event")
            
    except Exception as e:
        logger.error(f"Event processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
```

#### 2.3 Data Storage Service - Simple HTTP API
```python
# services/data-storage/src/api_server.py
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Data Storage API")

@app.post("/api/v1/events")
async def store_event(event_data: dict):
    """Store event in InfluxDB"""
    try:
        # Simple InfluxDB write
        await influxdb_client.write_event(event_data)
        return {"success": True, "message": "Event stored successfully"}
    except Exception as e:
        logger.error(f"Failed to store event: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/v1/events")
async def query_events(limit: int = 100):
    """Query recent events"""
    try:
        events = await influxdb_client.query_recent_events(limit)
        return {"events": events}
    except Exception as e:
        logger.error(f"Failed to query events: {e}")
        return {"events": [], "error": str(e)}
```

### Phase 3: Simple Migration Execution (1 day)

#### 3.1 Stop Current System
```bash
# Stop current services
docker-compose down

# Backup current data (optional)
docker exec homeiq-influxdb influx backup /backup/$(date +%Y%m%d_%H%M%S)
```

#### 3.2 Deploy New System
```bash
# Deploy new architecture
docker-compose -f docker-compose.simple.yml up -d

# Wait for services to start
sleep 30

# Check service health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8004/health
```

#### 3.3 Validate Migration
```bash
# Run simple validation
python tests/validate_migration.py

# Check event processing
curl http://localhost:8004/api/v1/events?limit=10
```

### Phase 4: Cleanup and Optimization (1 day)

#### 4.1 Remove Old Code
```bash
# Remove old service directories
rm -rf services/websocket-ingestion
rm -rf services/enrichment-pipeline

# Rename new services
mv services/websocket-ingestion-v2 services/websocket-ingestion
mv services/enrichment-pipeline-v2 services/enrichment-pipeline

# Update docker-compose.yml
cp docker-compose.simple.yml docker-compose.yml
```

#### 4.2 Update Configuration
```bash
# Update environment variables
# Update service URLs
# Update health check endpoints
# Update monitoring configurations
```

---

## Implementation Checklist

### Pre-Migration
- [ ] Create new service directories
- [ ] Implement HTTP communication
- [ ] Test new services individually
- [ ] Create simple validation script

### Migration Execution
- [ ] Stop current system
- [ ] Deploy new system
- [ ] Validate service health
- [ ] Test event processing
- [ ] Verify data flow

### Post-Migration
- [ ] Remove old code
- [ ] Update configurations
- [ ] Test end-to-end functionality
- [ ] Update documentation

---

## Simple Validation Script

```python
# tests/validate_migration.py
import asyncio
import aiohttp
import json

async def validate_migration():
    """Simple migration validation"""
    print("🔍 Validating migration...")
    
    # Test service health
    services = [
        "http://localhost:8001/health",
        "http://localhost:8002/health", 
        "http://localhost:8004/health"
    ]
    
    async with aiohttp.ClientSession() as session:
        for service_url in services:
            try:
                async with session.get(service_url) as response:
                    if response.status == 200:
                        print(f"✅ {service_url} - Healthy")
                    else:
                        print(f"❌ {service_url} - Unhealthy ({response.status})")
            except Exception as e:
                print(f"❌ {service_url} - Error: {e}")
    
    # Test event processing
    test_event = {
        "event_type": "state_changed",
        "entity_id": "sensor.test",
        "state": "test_value",
        "timestamp": "2025-01-06T14:30:00Z"
    }
    
    try:
        async with session.post("http://localhost:8001/api/v1/events/forward", json=test_event) as response:
            if response.status == 200:
                print("✅ Event forwarding - Working")
            else:
                print(f"❌ Event forwarding - Failed ({response.status})")
    except Exception as e:
        print(f"❌ Event forwarding - Error: {e}")
    
    # Test data retrieval
    try:
        async with session.get("http://localhost:8004/api/v1/events?limit=5") as response:
            if response.status == 200:
                data = await response.json()
                if len(data.get("events", [])) > 0:
                    print("✅ Data retrieval - Working")
                else:
                    print("⚠️  Data retrieval - No events found")
            else:
                print(f"❌ Data retrieval - Failed ({response.status})")
    except Exception as e:
        print(f"❌ Data retrieval - Error: {e}")
    
    print("🎉 Migration validation complete!")

if __name__ == "__main__":
    asyncio.run(validate_migration())
```

---

## Rollback Plan (Simple)

### If Migration Fails
```bash
# Stop new system
docker-compose -f docker-compose.simple.yml down

# Restore old system
docker-compose up -d

# Validate old system
curl http://localhost:8001/health
```

### If Data Issues
```bash
# Restore from backup
docker exec homeiq-influxdb influx restore /backup/backup_name

# Restart services
docker-compose restart
```

---

## Success Criteria

### Simple Validation
- [ ] All services start successfully
- [ ] Health checks pass
- [ ] Events flow from HA → WebSocket → Enrichment → Storage
- [ ] Data is stored in InfluxDB
- [ ] Admin API can retrieve events

### Performance Validation
- [ ] System processes events at baseline rate (17 events/min)
- [ ] No significant performance degradation
- [ ] Error rates remain low

### Architecture Validation
- [ ] Clear service separation
- [ ] HTTP communication between services
- [ ] No direct database access from multiple services
- [ ] Proper error handling

---

## Timeline

| Day | Task | Effort |
|-----|------|--------|
| 1 | Create new service structure | 4 hours |
| 2 | Implement HTTP communication | 6 hours |
| 3 | Test new services | 4 hours |
| 4 | Execute migration | 2 hours |
| 5 | Validate and cleanup | 2 hours |

**Total**: ~18 hours over 5 days

---

## Benefits of Simple Approach

1. **Faster Implementation**: No complex parallel processing
2. **Easier Debugging**: Straightforward service communication
3. **Lower Risk**: Simple rollback if issues occur
4. **Appropriate for Alpha**: Matches current development stage
5. **Focus on Architecture**: Get the design right first

This simple migration plan is much more appropriate for an alpha system and will get you to the proper microservices architecture quickly and reliably.
