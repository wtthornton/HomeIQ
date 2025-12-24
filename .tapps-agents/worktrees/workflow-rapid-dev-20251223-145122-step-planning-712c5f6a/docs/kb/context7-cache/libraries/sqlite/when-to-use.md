# SQLite - When to Use (Decision Guide)

**Source**: Web Research 2025-01-14 (Trust Score: High)
**Snippets**: 3 | **Tokens**: ~600
**Last Updated**: 2025-01-14 | **Cache Hits**: 0

---

## Decision Matrix: SQLite vs PostgreSQL

### Use SQLite When:

✅ **Application Characteristics:**
- Single-server deployment (no distributed architecture)
- < 100GB database size
- < 100 concurrent users
- Read-heavy workloads (90%+ reads)
- Write throughput < 1000/sec

✅ **Use Cases:**
- Device/entity registry (metadata)
- User preferences and settings
- Webhook subscriptions
- Configuration management
- Session storage
- Cache layer
- Development/testing databases
- Embedded applications

✅ **Operational Requirements:**
- Zero-config database
- Simple backups (file copy)
- No separate database server
- Minimal operational overhead
- Docker-friendly (single file)

### Use PostgreSQL When:

❌ **Need Advanced Features:**
- Multi-server write access
- Replication/high availability
- Connection pooling across servers
- Table partitioning
- Full-text search (advanced)
- JSON operators (advanced)

❌ **Scale Requirements:**
- > 100GB database
- > 1000 writes/sec sustained
- > 100 concurrent connections
- Multiple application servers writing

❌ **Compliance/Security:**
- Row-level security
- Advanced audit logging
- Encryption at rest (database level)

## Hybrid Architecture (Recommended for Small HA Apps)

```
┌─────────────────────────────────────┐
│  InfluxDB (Time-Series)             │
│  - Event streams                    │
│  - Sensor readings                  │
│  - Metrics over time                │
│  - Automatic retention              │
└─────────────────────────────────────┘
              │
              │ Hybrid Storage
              │
┌─────────────────────────────────────┐
│  SQLite (Metadata)                  │
│  - Device registry                  │
│  - User preferences                 │
│  - Configuration                    │
│  - Webhooks                         │
└─────────────────────────────────────┘
```

## Real-World Examples

### Perfect for SQLite:
1. **Home Assistant Ingestor** (This App!)
   - Device registry: ~100-1000 devices
   - User preferences: < 100 users
   - Webhook subscriptions: < 50 webhooks
   - Single-server deployment
   - Read-heavy metadata queries

2. **Small SaaS Applications**
   - < 10,000 users
   - Single region deployment
   - Moderate data volume

3. **Internal Tools**
   - Corporate dashboards
   - Admin interfaces
   - Configuration portals

### Need PostgreSQL:
1. **Multi-tenant SaaS**
   - Hundreds/thousands of tenants
   - Distributed deployment
   - High write concurrency

2. **E-commerce Platform**
   - Inventory across warehouses
   - High transaction volume
   - Need ACID at scale

3. **Social Network**
   - Millions of users
   - Complex relationships
   - Global distribution

## Performance Comparison

| Metric | SQLite | PostgreSQL |
|--------|--------|------------|
| Setup time | 0 seconds | 5-30 minutes |
| Memory overhead | ~1MB | ~50-500MB |
| Read latency | 0.01-1ms | 1-10ms |
| Write latency | 0.1-5ms | 1-20ms |
| Concurrent readers | Unlimited | High (1000+) |
| Concurrent writers | 1 (WAL mode) | High (1000+) |
| Max DB size | 140TB (practical: 1TB) | Unlimited |
| Backup complexity | File copy | pg_dump/replication |

## Migration Path

**Start with SQLite, migrate when needed:**

```
Phase 1: Start Simple (SQLite)
├── Device registry
├── User preferences  
└── Configuration

Phase 2: Add Complexity (Keep SQLite)
├── Webhook management
├── Alert rules
└── Team preferences

Phase 3: Scale Trigger (Consider PostgreSQL)
├── > 10,000 devices
├── Multi-server writes
└── > 1000 writes/sec
```

## Cost Comparison

| Aspect | SQLite | PostgreSQL |
|--------|--------|------------|
| Licensing | Free (Public Domain) | Free (Open Source) |
| Hosting | Included (file-based) | $10-100/month cloud |
| Maintenance | Minimal | Moderate |
| Expertise needed | Basic SQL | Advanced DBA skills |
| Monitoring tools | Built-in | Requires setup |

## Recommendation for Home Assistant Ingestor

**Use Hybrid Approach:**

```python
# InfluxDB for time-series
time_series_data = {
    "ha_events": "InfluxDB",
    "sports_scores": "InfluxDB",
    "weather_data": "InfluxDB",
    "system_metrics": "InfluxDB"
}

# SQLite for metadata
metadata = {
    "devices": "SQLite",
    "entities": "SQLite",
    "users": "SQLite",
    "webhooks": "SQLite",
    "team_preferences": "SQLite",
    "integrations": "SQLite"
}
```

**Benefits:**
- ✅ Keep InfluxDB's time-series strength
- ✅ Add SQLite's relational simplicity
- ✅ No operational overhead increase
- ✅ Clear data separation
- ✅ Easy to migrate later if needed

---

## Quick Decision Checklist

Ask yourself:
1. ☐ Will multiple servers write to DB? → PostgreSQL
2. ☐ Need > 1000 writes/sec? → PostgreSQL
3. ☐ Database > 100GB? → PostgreSQL
4. ☐ Need replication/HA? → PostgreSQL
5. ☐ Otherwise? → **SQLite is perfect!**

<!-- KB Metadata -->
<!-- Library: sqlite -->
<!-- Topic: when-to-use -->
<!-- Context7 ID: N/A (Web Research) -->
<!-- Trust Score: High -->
<!-- Snippet Count: 3 -->
<!-- Last Updated: 2025-01-14 -->
<!-- Cache Hits: 0 -->
<!-- Token Count: ~600 -->

