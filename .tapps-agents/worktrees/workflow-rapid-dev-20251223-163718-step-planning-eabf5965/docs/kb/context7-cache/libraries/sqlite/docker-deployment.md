# SQLite - Docker Deployment Best Practices

**Source**: Web Research 2025-01-14 (Trust Score: High)
**Snippets**: 4 | **Tokens**: ~800
**Last Updated**: 2025-01-14 | **Cache Hits**: 0

---

## Docker Volume Configuration

### Basic Setup

```yaml
version: '3.8'

services:
  data-api:
    image: data-api:latest
    volumes:
      - sqlite-data:/app/data
    environment:
      - DATABASE_URL=sqlite:///./data/app.db
      - SQLITE_WAL_MODE=1
    
volumes:
  sqlite-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ./volumes/sqlite-data
```

### Production Configuration

```yaml
version: '3.8'

services:
  data-api:
    image: data-api:latest
    volumes:
      # Data volume
      - sqlite-data:/app/data
      # Backup volume (read-only)
      - sqlite-backups:/app/backups:ro
    environment:
      - DATABASE_URL=sqlite:///./data/app.db
      - SQLITE_WAL_MODE=1
      - SQLITE_TIMEOUT=30000
      - SQLITE_CACHE_SIZE=64000
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import sqlite3; sqlite3.connect('/app/data/app.db').cursor().execute('SELECT 1')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  sqlite-data:
    driver: local
  sqlite-backups:
    driver: local
```

## File Permissions

### Dockerfile Configuration

```dockerfile
FROM python:3.11-alpine

# Create app user (non-root)
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

# Create data directory
RUN mkdir -p /app/data && \
    chown -R appuser:appuser /app

# Switch to app user
USER appuser

WORKDIR /app

COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser src/ ./src/

# Ensure data directory is writable
RUN chmod 755 /app/data

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8006"]
```

## WAL Mode in Docker

### Application Initialization

```python
# src/database.py
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import create_async_engine
import os

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")

# Async engine with WAL mode
async_engine = create_async_engine(
    DATABASE_URL.replace("sqlite:", "sqlite+aiosqlite:"),
    echo=False,
    pool_pre_ping=True,
    connect_args={
        "timeout": int(os.getenv("SQLITE_TIMEOUT", "30"))
    }
)

# Enable WAL mode on connection
@event.listens_for(async_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    
    # WAL mode for concurrent access
    cursor.execute("PRAGMA journal_mode=WAL")
    
    # Synchronous mode (NORMAL is faster, still safe)
    cursor.execute("PRAGMA synchronous=NORMAL")
    
    # Cache size (negative = KB, positive = pages)
    cache_size = int(os.getenv("SQLITE_CACHE_SIZE", "-64000"))
    cursor.execute(f"PRAGMA cache_size={cache_size}")
    
    # Use memory for temp tables
    cursor.execute("PRAGMA temp_store=MEMORY")
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys=ON")
    
    # Busy timeout (milliseconds)
    timeout_ms = int(os.getenv("SQLITE_TIMEOUT", "30")) * 1000
    cursor.execute(f"PRAGMA busy_timeout={timeout_ms}")
    
    cursor.close()
```

## Backup Strategy

### Automated Backups in Docker

```yaml
# docker-compose.yml
services:
  sqlite-backup:
    image: alpine:latest
    volumes:
      - sqlite-data:/data:ro
      - sqlite-backups:/backups
    environment:
      - BACKUP_INTERVAL=3600  # Hourly backups
    command: >
      sh -c '
      while true; do
        timestamp=$$(date +%Y%m%d_%H%M%S)
        cp /data/app.db /backups/backup_$$timestamp.db
        echo "Backup created: backup_$$timestamp.db"
        sleep $$BACKUP_INTERVAL
      done
      '
    restart: unless-stopped

volumes:
  sqlite-data:
  sqlite-backups:
```

### Manual Backup Script

```bash
#!/bin/bash
# scripts/backup-sqlite.sh

set -e

CONTAINER_NAME="data-api"
BACKUP_DIR="./backups/sqlite"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Copy database from container
docker cp "$CONTAINER_NAME:/app/data/app.db" "$BACKUP_DIR/backup_$TIMESTAMP.db"

# Compress backup
gzip "$BACKUP_DIR/backup_$TIMESTAMP.db"

# Keep only last 30 backups
cd "$BACKUP_DIR"
ls -t backup_*.db.gz | tail -n +31 | xargs -r rm

echo "Backup completed: backup_$TIMESTAMP.db.gz"
```

## Health Checks

### Database Health Check

```python
# src/health.py
from sqlalchemy import select
from sqlalchemy.sql import text

async def check_database_health(db: AsyncSession) -> dict:
    """Check SQLite database health"""
    try:
        # Test connection
        await db.execute(text("SELECT 1"))
        
        # Check WAL mode
        result = await db.execute(text("PRAGMA journal_mode"))
        journal_mode = result.scalar()
        
        # Check database size
        result = await db.execute(text("PRAGMA page_count"))
        page_count = result.scalar()
        
        result = await db.execute(text("PRAGMA page_size"))
        page_size = result.scalar()
        
        db_size_mb = (page_count * page_size) / (1024 * 1024)
        
        return {
            "status": "healthy",
            "journal_mode": journal_mode,
            "database_size_mb": round(db_size_mb, 2),
            "wal_enabled": journal_mode == "wal"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
```

## Volume Management

### Best Practices

```yaml
# Use named volumes for production
volumes:
  sqlite-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /var/lib/docker-volumes/sqlite-data

# Use tmpfs for testing (ephemeral)
services:
  test-api:
    volumes:
      - type: tmpfs
        target: /app/data
```

### Volume Backup

```bash
# Backup volume
docker run --rm \
  -v sqlite-data:/source:ro \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/sqlite-data-$(date +%Y%m%d).tar.gz -C /source .

# Restore volume
docker run --rm \
  -v sqlite-data:/target \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/sqlite-data-20250114.tar.gz -C /target
```

## Common Issues

### Issue: "Database is locked"

**Solution:**
```python
# Increase timeout
connect_args={"timeout": 30.0}

# Enable WAL mode
cursor.execute("PRAGMA journal_mode=WAL")
```

### Issue: "No such file or directory"

**Solution:**
```dockerfile
# Ensure data directory exists
RUN mkdir -p /app/data && chmod 755 /app/data
```

### Issue: "Permission denied"

**Solution:**
```dockerfile
# Set correct ownership
RUN chown -R appuser:appuser /app/data

# Run as non-root user
USER appuser
```

---

<!-- KB Metadata -->
<!-- Library: sqlite -->
<!-- Topic: docker-deployment -->
<!-- Context7 ID: N/A (Web Research) -->
<!-- Trust Score: High -->
<!-- Snippet Count: 4 -->
<!-- Last Updated: 2025-01-14 -->
<!-- Cache Hits: 0 -->
<!-- Token Count: ~800 -->

