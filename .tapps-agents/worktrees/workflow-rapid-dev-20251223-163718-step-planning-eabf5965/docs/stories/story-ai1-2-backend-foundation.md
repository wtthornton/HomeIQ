# Story AI1.2: AI Service Backend Foundation

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.2  
**Priority:** Critical  
**Estimated Effort:** 6-8 hours  
**Dependencies:** Story AI1.1 (MQTT connection configured)

---

## User Story

**As a** developer  
**I want** to create the AI automation service backend structure  
**so that** we have a foundation for pattern detection and LLM integration

---

## Business Value

- Establishes backend service foundation
- Provides FastAPI REST API for frontend
- Sets up database schema for patterns and suggestions
- Enables future pattern detection and LLM integration

---

## Acceptance Criteria

1. ✅ Service starts successfully in Docker container
2. ✅ FastAPI health endpoint returns 200 OK at `/health`
3. ✅ SQLite database initializes with schema (patterns, suggestions, user_feedback tables)
4. ✅ Alembic migrations run successfully
5. ✅ Service accessible on port 8011
6. ✅ Logging outputs to stdout in JSON format
7. ✅ Environment variables loaded correctly from .env
8. ✅ Service restarts automatically on failure
9. ✅ OpenAPI documentation accessible at `/docs`

---

## Technical Implementation Notes

### Service Directory Structure

**Create: services/ai-automation-service/**

```
ai-automation-service/
├── src/
│   ├── __init__.py
│   ├── main.py                      # FastAPI entry point
│   ├── config.py                    # Configuration management
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py                # SQLAlchemy models
│   │   └── crud.py                  # Database operations
│   └── api/
│       ├── __init__.py
│       └── health.py                # Health check endpoint
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
├── tests/
│   ├── __init__.py
│   ├── test_main.py
│   └── test_database.py
├── Dockerfile
├── requirements.txt
├── alembic.ini
└── README.md
```

### FastAPI Main Application

**Reference:** `services/admin-api/src/main.py`

```python
# src/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.logging_config import setup_logging
import logging

# Setup logging (use existing shared config)
logger = setup_logging("ai-automation-service")

app = FastAPI(
    title="AI Automation Service",
    description="AI-powered Home Assistant automation suggestion system",
    version="1.0.0"
)

# CORS for frontend (localhost:3002)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ai-automation-service",
        "version": "1.0.0"
    }

@app.on_event("startup")
async def startup_event():
    logger.info("AI Automation Service starting up")
    # Initialize database
    from .database.models import init_db
    await init_db()
    logger.info("Database initialized")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)
```

### Database Models

**Reference:** `services/data-api/src/models/device.py`

```python
# src/database/models.py
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime

Base = declarative_base()

class Pattern(Base):
    __tablename__ = 'patterns'
    
    id = Column(Integer, primary_key=True)
    pattern_type = Column(String, nullable=False)  # 'time_of_day', 'co_occurrence', 'anomaly'
    device_id = Column(String, nullable=False)
    metadata = Column(JSON)  # Pattern-specific data
    confidence = Column(Float, nullable=False)
    occurrences = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Suggestion(Base):
    __tablename__ = 'suggestions'
    
    id = Column(Integer, primary_key=True)
    pattern_id = Column(Integer, ForeignKey('patterns.id'))
    title = Column(String, nullable=False)
    description = Column(Text)
    automation_yaml = Column(Text, nullable=False)
    status = Column(String, default='pending')  # pending, approved, deployed, rejected
    confidence = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deployed_at = Column(DateTime, nullable=True)
    ha_automation_id = Column(String, nullable=True)

class UserFeedback(Base):
    __tablename__ = 'user_feedback'
    
    id = Column(Integer, primary_key=True)
    suggestion_id = Column(Integer, ForeignKey('suggestions.id'))
    action = Column(String, nullable=False)  # 'approved', 'rejected', 'modified'
    feedback_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# Database initialization
async def init_db():
    engine = create_async_engine('sqlite+aiosqlite:///data/ai_automation.db')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

### Dockerfile

**Reference:** `services/data-api/Dockerfile`

```dockerfile
FROM python:3.11-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache gcc musl-dev python3-dev

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-alpine

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Add shared logging
COPY ../../shared/logging_config.py ./shared/

# Make sure scripts are in PATH
ENV PATH=/root/.local/bin:$PATH

# Create data directory
RUN mkdir -p /app/data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8011/health || exit 1

# Run migrations and start service
CMD alembic upgrade head && python -m uvicorn src.main:app --host 0.0.0.0 --port 8011
```

### Requirements

**Create: requirements.txt**

```
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
sqlalchemy==2.0.25
aiosqlite==0.19.0
alembic==1.13.1
paho-mqtt==1.6.1
httpx==0.25.2
pandas==2.1.4
numpy==1.26.2
scikit-learn==1.3.2
openai==1.12.0
apscheduler==3.10.4
python-dotenv==1.0.0
```

---

## Integration Verification

**IV1: Service starts alongside existing services without errors**
- Run `docker-compose up -d`
- Check all services healthy: `docker ps`
- No error messages in logs: `docker logs ai-automation-service`

**IV2: Port 8011 is available and responds**
- Test health endpoint: `curl http://localhost:8011/health`
- Should return: `{"status": "healthy", "service": "ai-automation-service", "version": "1.0.0"}`

**IV3: Docker network allows service-to-service communication**
- Test from ai-automation-service to data-api: `docker exec ai-automation-service curl http://data-api:8006/health`
- Should succeed

**IV4: Shared logging infrastructure captures AI service logs**
- Check log aggregator receives logs
- Verify JSON format matches existing services
- Correlation IDs present

---

## Tasks Breakdown

1. **Create service directory structure** (30 min)
2. **Set up FastAPI application** (1 hour)
3. **Implement SQLAlchemy models** (1 hour)
4. **Create Alembic migrations** (1 hour)
5. **Set up logging integration** (30 min)
6. **Create Dockerfile** (1 hour)
7. **Add to docker-compose.yml** (30 min)
8. **Write tests** (1 hour)
9. **Documentation** (30 min)
10. **Integration testing** (1 hour)

**Total:** 6-8 hours

---

## Definition of Done

- [ ] Service directory created with proper structure
- [ ] FastAPI application responds to /health
- [ ] SQLite database created with all tables
- [ ] Alembic migrations functional
- [ ] Docker container builds successfully
- [ ] Service accessible on port 8011
- [ ] Logging outputs JSON to stdout
- [ ] Tests pass (unit + integration)
- [ ] Documentation complete
- [ ] Integration verification passed
- [ ] Code reviewed and approved

---

## Reference Files

**Copy patterns from:**
- `services/data-api/src/main.py` - FastAPI setup
- `services/data-api/src/models/device.py` - SQLAlchemy models
- `services/data-api/Dockerfile` - Multi-stage build
- `shared/logging_config.py` - Logging configuration

---

## Notes

- Keep it simple - this is foundation work
- Follow existing patterns religiously
- Don't add features not in acceptance criteria
- Use Alpine base image for small footprint
- Multi-stage build keeps image small

---

**Story Status:** Not Started  
**Assigned To:** TBD  
**Created:** 2025-10-15  
**Updated:** 2025-10-15


