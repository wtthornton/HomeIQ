# Epic 22: SQLite Metadata Storage

## Overview

**Epic Goal**: Add SQLite database for storing metadata (devices, webhooks, user preferences) separately from time-series data in InfluxDB.

**Status**: ✅ COMPLETE + ENHANCED (October 2025)  
**Priority**: Medium  
**Complexity**: Low (Kept Simple!)  
**Actual Duration**: <1 day (Stories 22.1-22.3 implemented 2025-01-14)  
**Cancelled**: Story 22.4 (User Preferences - optional, not needed)  
**Enhancement**: Direct HA → SQLite storage (October 2025) - Fixed architecture gap  

## Problem Statement

Currently, we store all data in InfluxDB, including:
- Device registry (static metadata)
- Webhook subscriptions (JSON files - not concurrent-safe)
- User preferences (localStorage/env vars - not persistent)
- Sports team selections (environment variables)

**Issues:**
- ❌ InfluxDB queries complex for simple lookups ("get device by ID")
- ❌ Webhook JSON file has race condition risks
- ❌ No server-side user preference persistence
- ❌ Mixing time-series and metadata in same database

## Solution

**Implement hybrid storage architecture:**
```
InfluxDB (Time-Series)      SQLite (Metadata)
- HA events                 - Device registry
- Sports scores             - Entity registry
- Weather data              - Webhooks
- System metrics            - User preferences
                            - Team selections
```

## User Stories

### Story 22.1: SQLite Infrastructure Setup (1 day)
**As a** developer  
**I want** a properly configured SQLite database with async support  
**So that** I can store metadata efficiently

**Acceptance Criteria:**
- [ ] SQLite database created with WAL mode enabled
- [ ] SQLAlchemy 2.0 async engine configured
- [ ] Docker volume for persistent storage
- [ ] Database initialization in data-api service
- [ ] Health check endpoint includes SQLite status
- [ ] Alembic migrations configured

**Implementation:**
```python
# Shared SQLite configuration
DATABASE_URL=sqlite+aiosqlite:///./data/metadata.db

# Tables: devices, entities, webhooks, user_preferences
```

### Story 22.2: Device & Entity Registry Migration (1-2 days)
**As a** developer  
**I want** device and entity metadata in SQLite  
**So that** I can query devices efficiently with joins

**Acceptance Criteria:**
- [ ] `devices` table created (device_id, name, manufacturer, model, area_id)
- [ ] `entities` table created with foreign key to devices
- [ ] Migration script from InfluxDB tags to SQLite
- [ ] `/api/devices` endpoint uses SQLite
- [ ] `/api/entities` endpoint uses SQLite
- [ ] Performance improvement measured (target: <10ms queries)

**Tables:**
```sql
CREATE TABLE devices (
    device_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    manufacturer TEXT,
    model TEXT,
    area_id TEXT,
    integration TEXT,
    last_seen TIMESTAMP
);

CREATE TABLE entities (
    entity_id TEXT PRIMARY KEY,
    device_id TEXT REFERENCES devices(device_id),
    domain TEXT NOT NULL,
    platform TEXT,
    disabled BOOLEAN DEFAULT 0
);
```

### Story 22.3: Webhook Storage Migration (0.5 day)
**As a** developer  
**I want** webhooks stored in SQLite instead of JSON  
**So that** registrations are concurrent-safe and transactional

**Acceptance Criteria:**
- [ ] `webhooks` table created
- [ ] Migration from `data/webhooks.json` to SQLite
- [ ] Webhook CRUD operations use SQLite
- [ ] JSON file backup created before migration
- [ ] No downtime during migration

**Implementation:**
```sql
CREATE TABLE webhooks (
    webhook_id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    events TEXT NOT NULL,  -- JSON array
    secret TEXT NOT NULL,
    team TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Story 22.4: User Preferences (Optional - 1 day)
**As a** user  
**I want** my team selections persisted on the server  
**So that** preferences work across devices

**Acceptance Criteria:**
- [ ] `user_preferences` table created
- [ ] `/api/user/preferences` endpoints added
- [ ] Dashboard loads preferences from API
- [ ] Migration from localStorage to SQLite

**Simple Implementation:**
```sql
CREATE TABLE user_preferences (
    user_id TEXT PRIMARY KEY DEFAULT 'default',
    selected_teams TEXT,  -- JSON array
    notification_settings TEXT,  -- JSON
    updated_at TIMESTAMP
);
```

## Technical Specifications

### Architecture

```
┌─────────────────────────────────────┐
│  data-api (Port 8006)               │
│                                     │
│  ┌──────────┐      ┌──────────┐   │
│  │ InfluxDB │      │  SQLite  │   │
│  │ Client   │      │  Session │   │
│  └────┬─────┘      └────┬─────┘   │
│       │                 │          │
│       │ Time-Series     │ Metadata │
└───────┼─────────────────┼──────────┘
        │                 │
  ┌─────▼─────┐    ┌──────▼──────┐
  │  InfluxDB │    │   SQLite    │
  │  (Events) │    │ (Metadata)  │
  └───────────┘    └─────────────┘
```

### Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Database | SQLite | 3.45+ | Metadata storage |
| ORM | SQLAlchemy | 2.0+ | Async database access |
| Migrations | Alembic | 1.13+ | Schema migrations |
| Driver | aiosqlite | 0.20+ | Async SQLite support |

### Configuration

**Environment Variables:**
```bash
# SQLite Configuration
SQLITE_DATABASE_URL=sqlite+aiosqlite:///./data/metadata.db
SQLITE_TIMEOUT=30
SQLITE_CACHE_SIZE=-64000  # 64MB
```

**Docker Compose:**
```yaml
services:
  data-api:
    volumes:
      - influxdb-data:/var/lib/influxdb2
      - sqlite-data:/app/data  # NEW: SQLite storage
    environment:
      - SQLITE_DATABASE_URL=sqlite+aiosqlite:///./data/metadata.db

volumes:
  sqlite-data:  # NEW
    driver: local
```

### Database Configuration

**Pragmas (Auto-Applied):**
```sql
PRAGMA journal_mode=WAL;        -- Concurrent reads
PRAGMA synchronous=NORMAL;      -- Fast, still safe
PRAGMA cache_size=-64000;       -- 64MB cache
PRAGMA temp_store=MEMORY;       -- RAM temp tables
PRAGMA foreign_keys=ON;         -- Enforce FK
PRAGMA busy_timeout=30000;      -- 30s timeout
```

## Dependencies

**Python Packages:**
```
sqlalchemy==2.0.25
aiosqlite==0.20.0
alembic==1.13.1
```

## Success Criteria

- ✅ SQLite database operational with WAL mode
- ✅ Device/entity queries < 10ms (vs ~50ms with InfluxDB)
- ✅ Webhooks stored in SQLite (no JSON files)
- ✅ Zero downtime migration
- ✅ All existing APIs work unchanged
- ✅ Docker volumes properly configured
- ✅ Backup strategy documented

## Testing Strategy

**Unit Tests:**
- SQLite connection and configuration
- Device/Entity CRUD operations
- Webhook registration and lookup
- User preference storage

**Integration Tests:**
- Device migration from InfluxDB
- API endpoints with SQLite backend
- Concurrent webhook operations
- Health check with both databases

**Performance Tests:**
- Device lookup latency (target: <10ms)
- Concurrent webhook writes (target: 100/sec)
- Database file size monitoring

## Migration Plan

### Phase 1: Setup (Day 1)
1. Add SQLite dependencies to `requirements.txt`
2. Create database initialization code
3. Configure Alembic migrations
4. Add Docker volume
5. Test database health checks

### Phase 2: Device Registry (Day 2-3)
1. Create device/entity tables
2. Write migration script (InfluxDB → SQLite)
3. Run migration on test data
4. Update `/api/devices` endpoints
5. Performance testing

### Phase 3: Webhooks (Day 3)
1. Create webhooks table
2. Migrate from JSON to SQLite
3. Update webhook manager
4. Test concurrent operations
5. Backup old JSON file

### Phase 4: User Preferences (Optional - Day 4)
1. Create user_preferences table
2. Add API endpoints
3. Update dashboard
4. Test cross-device sync

### Phase 5: Testing & Deployment (Day 5)
1. Full integration testing
2. Performance validation
3. Documentation updates
4. Deploy to production

## Rollback Plan

**If issues occur:**
1. Keep InfluxDB queries as fallback
2. Restore JSON file for webhooks
3. Revert Docker volume changes
4. Document issues for retry

## Future Enhancements (Out of Scope)

- PostgreSQL migration if scale increases
- Multi-user authentication
- Backup automation
- Replication/HA setup

## Non-Goals

- ❌ Replace InfluxDB for time-series data
- ❌ Add complex relational queries
- ❌ Multi-server deployment
- ❌ Advanced security features

## References

- Context7 KB: `docs/kb/context7-cache/libraries/sqlite/`
- SQLAlchemy 2.0 Docs: https://docs.sqlalchemy.org/en/20/
- SQLite WAL Mode: https://www.sqlite.org/wal.html
- FastAPI + SQLAlchemy: https://fastapi.tiangolo.com/tutorial/sql-databases/

---

**Keep It Simple Philosophy:**
- Single SQLite file for all metadata
- Async patterns matching existing FastAPI code
- Minimal operational overhead
- Easy rollback if needed
- No complex migrations

**Estimated Effort**: 24-40 hours over 5 days (with optional Story 22.4)

---

## October 2025 Enhancement: Direct HA → SQLite Storage

### Problem Identified

The original Epic 22 implementation left an architectural gap:
- ✅ SQLite database created
- ✅ Data-API endpoints serve from SQLite
- ❌ Discovery service still wrote to InfluxDB only
- ❌ No automated sync from InfluxDB → SQLite
- **Result**: Stale mock data in SQLite, real data orphaned in InfluxDB

### Solution Implemented

**Direct Storage Architecture**:
```
Home Assistant WebSocket
         ↓ Discovery Service
    HTTP POST /internal/devices/bulk_upsert
         ↓ Data-API
    SQLite (PRIMARY) ✅
```

**Changes Made**:
1. Added `POST /internal/devices/bulk_upsert` endpoint (data-api)
2. Added `POST /internal/entities/bulk_upsert` endpoint (data-api)
3. Updated `discovery_service.py` to POST to data-api
4. Triggered discovery in `main._on_connect()`
5. Made InfluxDB device storage optional (disabled by default)

**Results**:
- ✅ 99 real devices from Home Assistant
- ✅ 100+ real entities from Home Assistant
- ✅ Automatic on every WebSocket connection
- ✅ No manual sync scripts needed
- ✅ Real-time updates

**Files Modified**:
- `services/data-api/src/devices_endpoints.py` - Bulk upsert endpoints
- `services/websocket-ingestion/src/discovery_service.py` - Direct SQLite storage
- `services/websocket-ingestion/src/main.py` - Discovery trigger
- `docker-compose.yml` - Added DATA_API_URL env var

**Deprecated Scripts** (no longer needed):
- `sync_devices.py`
- `populate_sqlite.py`
- `simple_populate_sqlite.py`

**Documentation**: See `implementation/ARCHITECTURE_FIX_COMPLETE.md` for full details.

