# Hybrid Database Architecture - Quick Reference

**Epic 22 - SQLite Metadata Storage**  
**Implemented**: January 14, 2025  
**Status**: Production Ready

---

## 🎯 Overview

The HA Ingestor uses a **hybrid database architecture** optimizing different data types:

```
┌─────────────────────────────────────┐
│  InfluxDB 2.7 (Time-Series)         │
│  - HA events (state_changed)        │
│  - Sports scores                     │
│  - Weather data                      │
│  - System metrics                    │
│  - Retention policies                │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  SQLite 3.45+ (Metadata) ✅         │
│  - Device registry (99 devices)     │
│  - Entity registry (100+ entities)  │
│  - Webhook subscriptions             │
│  - WAL mode (concurrent-safe)        │
│  - Direct from HA (no sync needed)  │
└─────────────────────────────────────┘
```

### Data Population (Updated October 2025)

**Devices & Entities** → Direct from Home Assistant ✅
```
HA WebSocket → Discovery Service → POST → Data-API → SQLite
```
- Automatic on WebSocket connection
- Real-time updates
- No manual sync required

**Events** → InfluxDB ✅
```
HA WebSocket → Event Stream → Enrichment → InfluxDB
```
- Real-time state changes
- Time-series storage

---

## 📊 Performance Improvements

| Query Type | Before (InfluxDB) | After (SQLite) | Improvement |
|------------|-------------------|----------------|-------------|
| Get device by ID | ~50ms | <10ms | **5x faster** |
| List devices filtered | ~100ms | <15ms | **6-7x faster** |
| List entities by domain | ~40ms | <5ms | **8x faster** |
| Device + entity count (JOIN) | ~120ms | <10ms | **12x faster** |

---

## 🗂️ Database Files

### data-api Service
**Location**: `services/data-api/data/metadata.db`

**Tables:**
- `devices` - HA device registry
- `entities` - HA entity registry (FK to devices)

**Configuration:**
```bash
DATABASE_URL=sqlite+aiosqlite:///./data/metadata.db
SQLITE_TIMEOUT=30
SQLITE_CACHE_SIZE=-64000  # 64MB
```

### sports-data Service
**Location**: `services/sports-data/data/webhooks.db`

**Tables:**
- `webhooks` - Webhook subscriptions for game events

**Features:**
- Concurrent-safe operations
- ACID transactions
- No race conditions

---

## 🔧 Configuration

### Docker Volumes

```yaml
volumes:
  sqlite-data:  # Persistent SQLite storage
    driver: local
```

### Service Mounts

**data-api:**
```yaml
volumes:
  - sqlite-data:/app/data
```

### Environment Variables

```bash
# SQLite Configuration
DATABASE_URL=sqlite+aiosqlite:///./data/metadata.db
SQLITE_TIMEOUT=30           # Connection timeout (seconds)
SQLITE_CACHE_SIZE=-64000    # 64MB cache (negative = KB)
```

---

## 🏥 Health Checks

**Check SQLite Status:**
```bash
curl http://localhost:8006/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "dependencies": {
    "influxdb": { ... },
    "sqlite": {
      "status": "healthy",
      "journal_mode": "wal",
      "database_size_mb": 0.05,
      "wal_enabled": true
    }
  }
}
```

---

## 💾 Backup & Restore

### Backup (Simple File Copy)

```bash
# Create backup directory
mkdir -p backups/sqlite

# Backup SQLite databases (safe with WAL mode)
docker cp homeiq-data-api:/app/data/metadata.db backups/sqlite/
docker cp homeiq-sports-data:/app/data/webhooks.db backups/sqlite/

# Optional: Add timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker cp homeiq-data-api:/app/data/metadata.db backups/sqlite/metadata_$TIMESTAMP.db
```

### Restore

```bash
# Stop services
docker-compose stop data-api sports-data

# Restore databases
docker cp backups/sqlite/metadata.db homeiq-data-api:/app/data/
docker cp backups/sqlite/webhooks.db homeiq-sports-data:/app/data/

# Restart services
docker-compose start data-api sports-data
```

---

## 🧪 Testing

### Verify SQLite Working

```bash
# Test health endpoint
curl http://localhost:8006/health | jq '.dependencies.sqlite'

# Test device endpoints
curl http://localhost:8006/api/devices
curl http://localhost:8006/api/entities

# Test webhook endpoints
curl http://localhost:8005/api/v1/webhooks/list
```

### Database Migrations

```bash
# Check current migration
cd services/data-api
alembic current

# Upgrade to latest
alembic upgrade head

# Rollback one version
alembic downgrade -1
```

---

## 📖 API Endpoints

### Device & Entity Endpoints (data-api)

**All now using SQLite:**

```bash
# List devices
GET /api/devices?manufacturer=Philips&area_id=living_room

# Get specific device
GET /api/devices/{device_id}

# List entities
GET /api/entities?domain=light&device_id={device_id}

# Get specific entity
GET /api/entities/{entity_id}
```

### Webhook Endpoints (sports-data)

**All now using SQLite:**

```bash
# Register webhook
POST /api/v1/webhooks/register
{
  "url": "https://example.com/hook",
  "events": ["game_started", "score_changed"],
  "secret": "secret_key_16+_chars",
  "team": "sf"
}

# List webhooks
GET /api/v1/webhooks/list

# Delete webhook
DELETE /api/v1/webhooks/{webhook_id}
```

---

## 🔍 Troubleshooting

### Database Locked Error

**Symptom**: `database is locked`

**Solution:**
- WAL mode should prevent this
- Check `PRAGMA journal_mode` returns "wal"
- Increase `SQLITE_TIMEOUT` if needed

### File Not Found

**Symptom**: `no such file or directory: ./data/metadata.db`

**Solution:**
- Ensure `/app/data` directory exists
- Check Docker volume mounted correctly
- Verify permissions (appuser owns directory)

### Migration Errors

**Symptom**: Alembic migration fails

**Solution:**
```bash
# Check current state
alembic current

# Stamp database to current
alembic stamp head

# Recreate database if corrupted
rm services/data-api/data/metadata.db
docker-compose restart data-api
```

---

## 📚 Related Documentation

- **Tech Stack**: [docs/architecture/tech-stack.md](../architecture/tech-stack.md)
- **Database Schema**: [docs/architecture/database-schema.md](../architecture/database-schema.md)
- **Source Tree**: [docs/architecture/source-tree.md](../architecture/source-tree.md)
- **Epic 22**: [docs/prd/epic-22-sqlite-metadata-storage.md](../prd/epic-22-sqlite-metadata-storage.md)
- **Context7 KB**: [docs/kb/context7-cache/libraries/sqlite/](../kb/context7-cache/libraries/sqlite/)

---

## 🚀 Quick Start

### First Time Setup

```bash
# Pull latest code
git pull

# Rebuild services with SQLite
docker-compose up --build -d data-api sports-data

# Verify SQLite working
curl http://localhost:8006/health | jq '.dependencies.sqlite'

# Check that WAL mode is enabled
# Should see: "journal_mode": "wal", "wal_enabled": true
```

### Add Test Data

```python
# Add a test device (optional)
import requests

requests.post('http://localhost:8006/api/devices', json={
    "device_id": "test_123",
    "name": "Test Device",
    "manufacturer": "Test Co",
    "area_id": "living_room"
})
```

---

## Summary

**Epic 22 delivered:**
- ✅ Hybrid database architecture
- ✅ 5-10x faster metadata queries
- ✅ Concurrent-safe webhook storage
- ✅ Simple, production-ready implementation
- ✅ Comprehensive documentation

**No over-engineering. Just clean, fast, reliable database architecture.**

