# SQLite - FastAPI Best Practices

**Source**: Web Research 2025-01-14 (Trust Score: High)
**Snippets**: 5 | **Tokens**: ~1200
**Last Updated**: 2025-01-14 | **Cache Hits**: 0

---

## Overview

SQLite is ideal for small-to-medium applications, especially when:
- Single-server deployment
- Read-heavy workloads with moderate writes (<1000/sec)
- Simple relational data models
- No need for distributed/replicated databases

## Best Practices for FastAPI + SQLite

### 1. Enable WAL Mode (Write-Ahead Logging)

**Critical for concurrent access:**
```python
from sqlalchemy import create_engine, event

# Enable WAL mode for better concurrency
engine = create_engine(
    "sqlite:///./data/app.db",
    connect_args={
        "check_same_thread": False,  # Allow multi-threaded access
        "timeout": 30.0  # 30 second timeout for locks
    },
    pool_pre_ping=True,  # Verify connections before using
    echo=False
)

# Enable WAL mode on connection
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")  # Faster, still safe
    cursor.execute("PRAGMA cache_size=-64000")   # 64MB cache
    cursor.execute("PRAGMA temp_store=MEMORY")   # Use RAM for temp tables
    cursor.execute("PRAGMA foreign_keys=ON")     # Enable foreign keys
    cursor.close()
```

### 2. Use Async SQLAlchemy 2.0

**Modern async pattern with FastAPI:**
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from contextlib import asynccontextmanager

# Create async engine
async_engine = create_async_engine(
    "sqlite+aiosqlite:///./data/app.db",
    echo=False,
    pool_pre_ping=True
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base model class
class Base(DeclarativeBase):
    pass

# Dependency for FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Example FastAPI endpoint
from fastapi import Depends
from sqlalchemy import select

@app.get("/devices")
async def list_devices(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Device))
    devices = result.scalars().all()
    return {"devices": devices}
```

### 3. Simple Table Design

**Keep it simple for small apps:**
```python
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

class Device(Base):
    __tablename__ = "devices"
    
    device_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    manufacturer = Column(String)
    model = Column(String)
    area_id = Column(String)
    integration = Column(String)
    last_seen = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    entities = relationship("Entity", back_populates="device")

class Entity(Base):
    __tablename__ = "entities"
    
    entity_id = Column(String, primary_key=True)
    device_id = Column(String, ForeignKey("devices.device_id"))
    domain = Column(String, nullable=False)
    platform = Column(String)
    disabled = Column(Boolean, default=False)
    
    # Relationship
    device = relationship("Device", back_populates="entities")
```

### 4. Docker Deployment

**Persistent volume configuration:**
```yaml
services:
  data-api:
    image: data-api:latest
    volumes:
      - sqlite-data:/app/data  # Persistent SQLite storage
    environment:
      - DATABASE_URL=sqlite:///./data/app.db

volumes:
  sqlite-data:
    driver: local
```

### 5. Backup Strategy

**Simple file-based backups:**
```python
import shutil
from datetime import datetime
from pathlib import Path

async def backup_database():
    """Backup SQLite database file"""
    source = Path("./data/app.db")
    backup_dir = Path("./backups")
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    destination = backup_dir / f"app_backup_{timestamp}.db"
    
    # SQLite backup is just a file copy (when no active connections)
    shutil.copy2(source, destination)
    
    # Also backup WAL file if exists
    wal_file = Path("./data/app.db-wal")
    if wal_file.exists():
        shutil.copy2(wal_file, backup_dir / f"app_backup_{timestamp}.db-wal")
```

## When NOT to Use SQLite

**Use PostgreSQL instead if:**
- ❌ Multiple servers need to write simultaneously
- ❌ Need connection pooling across servers
- ❌ Write throughput > 1000/sec sustained
- ❌ Database size > 100GB
- ❌ Need advanced features (partitioning, replication)
- ❌ High-concurrency write workloads

**SQLite is PERFECT for:**
- ✅ Single-server applications
- ✅ Read-heavy workloads
- ✅ Metadata/configuration storage
- ✅ Cache/session storage
- ✅ Embedded applications
- ✅ Development/testing

## Performance Characteristics

| Operation | SQLite Performance | Notes |
|-----------|-------------------|-------|
| Read throughput | Excellent (100k+ reads/sec) | Limited by disk I/O |
| Write throughput | Good (1000-5000 writes/sec) | WAL mode helps |
| Concurrent reads | Excellent | No blocking |
| Concurrent writes | Good with WAL | One writer at a time |
| Database size | Up to 140TB theoretical | Practical limit ~1TB |
| Startup time | Instant | No server process |

## Common Pitfalls

### ❌ Don't Do This:
```python
# BAD: Synchronous SQLite in async FastAPI
from sqlalchemy import create_engine
engine = create_engine("sqlite:///app.db")

@app.get("/devices")
def list_devices():  # Blocking!
    with Session(engine) as session:
        return session.query(Device).all()
```

### ✅ Do This Instead:
```python
# GOOD: Async SQLite in async FastAPI
from sqlalchemy.ext.asyncio import create_async_engine

async_engine = create_async_engine("sqlite+aiosqlite:///app.db")

@app.get("/devices")
async def list_devices(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Device))
    return result.scalars().all()
```

## Migration Management

**Use Alembic for schema changes:**
```bash
# Install Alembic
pip install alembic

# Initialize
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Add devices table"

# Apply migration
alembic upgrade head
```

---

## References
- SQLite Official Docs: https://www.sqlite.org/wal.html
- SQLAlchemy 2.0 Async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- FastAPI SQLAlchemy Tutorial: https://fastapi.tiangolo.com/tutorial/sql-databases/

<!-- KB Metadata -->
<!-- Library: sqlite -->
<!-- Topic: fastapi-best-practices -->
<!-- Context7 ID: N/A (Web Research) -->
<!-- Trust Score: High -->
<!-- Snippet Count: 5 -->
<!-- Last Updated: 2025-01-14 -->
<!-- Cache Hits: 0 -->
<!-- Token Count: ~1200 -->

