# Automation Miner - Deployment Guide

**Service:** automation-miner  
**Port:** 8019  
**Epic:** AI-4, Story AI4.1  
**Status:** ✅ Deployed

---

## Quick Start

### 1. Start Service

**Using Docker Compose (Recommended):**
```bash
# From project root
docker-compose up automation-miner -d

# Verify health
curl http://localhost:8019/health
```

**Standalone:**
```bash
cd domains/blueprints/automation-miner
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8019
```

### 2. Initialize Database

```bash
cd domains/blueprints/automation-miner
python -c "from src.miner.database import Database; import asyncio; asyncio.run(Database().create_tables())"
```

### 3. Run Initial Crawl

```bash
# Test crawl (100 posts, dry-run)
python -m src.cli crawl --limit 100 --dry-run

# Full crawl (2,000-3,000 posts)
python -m src.cli crawl

# Monitor progress (check stats)
python -m src.cli stats
```

---

## API Endpoints

### Health Check
```bash
GET http://localhost:8019/health

Response:
{
  "status": "healthy",
  "service": "automation-miner",
  "version": "0.1.0",
  "corpus": {
    "total_automations": 0,
    "avg_quality": 0.0,
    "last_crawl": null
  },
  "enabled": false
}
```

### Search Corpus
```bash
GET /api/automation-miner/corpus/search?device=motion_sensor&min_quality=0.8&limit=10

Response:
{
  "automations": [...],
  "count": 10,
  "filters": {...}
}
```

### Get Statistics
```bash
GET /api/automation-miner/corpus/stats

Response:
{
  "total": 2543,
  "avg_quality": 0.76,
  "device_count": 52,
  "integration_count": 35,
  "by_use_case": {...},
  "by_complexity": {...}
}
```

---

## Configuration

### Environment Variables

```bash
# Feature Flags
ENABLE_AUTOMATION_MINER=false  # Set to true after testing

# Database
MINER_DB_PATH=data/automation_miner.db

# Discourse API
DISCOURSE_BASE_URL=https://community.home-assistant.io
DISCOURSE_MIN_LIKES=500  # Quality threshold

# GitHub API (optional)
GITHUB_TOKEN=your_token_here  # For higher rate limits

# Logging
LOG_LEVEL=INFO
```

### Docker Compose

Service is configured in main `docker-compose.yml`:
```yaml
automation-miner:
  build: ./domains/blueprints/automation-miner
  ports:
    - "8019:8019"
  volumes:
    - automation_miner_data:/app/data
  environment:
    - ENABLE_AUTOMATION_MINER=false
```

---

## Troubleshooting

### Service Won't Start

**Check logs:**
```bash
docker logs automation-miner
```

**Common issues:**
- Port 8019 already in use → Change port in docker-compose.yml
- Database permission error → Check volume permissions
- Missing dependencies → Rebuild: `docker-compose build automation-miner`

### API Returns Empty Results

**Normal if corpus not crawled yet:**
```bash
# Run initial crawl
cd domains/blueprints/automation-miner
python -m src.cli crawl --limit 100

# Check stats
python -m src.cli stats
```

### Health Check Failing

**Check service status:**
```bash
curl http://localhost:8019/health
```

**If unhealthy:**
- Check database file exists: `ls data/automation_miner.db`
- Check logs for errors: `docker logs automation-miner`
- Restart service: `docker-compose restart automation-miner`

---

## Performance Tuning

### Query Performance

**Expected:**
- Query API: <100ms p95
- Search by device: ~10-50ms (indexed)
- Stats endpoint: ~5-10ms (aggregations)

**If slow:**
- Check corpus size (should be <500MB)
- Verify indexes exist (run migration)
- Consider adding Redis cache (optional)

### Crawler Performance

**Expected:**
- Initial crawl: 2-3 hours for 2,000-3,000 posts
- Rate limit: 2 requests/second (Discourse API)
- Memory: <200MB peak

**If slow:**
- Reduce batch size: `CRAWLER_BATCH_SIZE=25`
- Increase rate limit (if API allows): `DISCOURSE_RATE_LIMIT_PER_SEC=3.0`
- Check network latency

---

## Maintenance

### Weekly Refresh (Story AI4.4)

**Automated** (when AI4.4 deployed):
- Runs every Sunday at 2 AM
- Incremental crawl (15-30 minutes)
- Automatic cache invalidation

**Manual:**
```bash
python -m src.cli crawl --since 2025-10-11
```

### Corpus Cleanup

**Auto-pruning** (Story AI4.4):
- Removes quality_score < 0.4
- Removes stale (>2 years old, <100 votes)

**Manual:**
```bash
# View corpus stats
python -m src.cli stats

# Run crawl with --dry-run to see what would change
python -m src.cli crawl --dry-run
```

---

## Integration with AI Automation Service

### Story AI4.2: Pattern Enhancement

**When enabled:**
```bash
# In infrastructure/env.ai-automation
ENABLE_PATTERN_ENHANCEMENT=true
MINER_BASE_URL=http://automation-miner:8019
MINER_QUERY_TIMEOUT_MS=100
```

**Effect:**
- Daily analysis queries Miner during Phase 3
- Suggestions include community best practices
- 80/20 weighting (personal patterns = primary)

### Story AI4.3: Device Discovery

**New endpoints** (when deployed):
- `/api/automation-miner/devices/{type}/possibilities`
- `/api/automation-miner/recommendations/devices`

**UI:** Discovery Tab at http://localhost:3001/discovery

---

## Security Considerations

### API Access
- Currently: No authentication (internal service)
- Production: Add API key if exposed externally
- CORS: Configured for internal use only

### Data Privacy
- PII removal: Entity IDs, IP addresses filtered
- No user-specific data stored
- Community data only (public domain)

### Rate Limiting
- Discourse API: 2 requests/second (respects their limits)
- Query API: No rate limit (internal service)
- Consider adding if exposed externally

---

## Success Checklist

### Deployment
- [x] Service running on port 8019
- [x] Health check passing
- [x] All API endpoints responding
- [x] Database created
- [x] Docker Compose integrated
- [ ] Initial crawl executed
- [ ] Corpus quality verified

### Integration
- [x] MinerClient created (Story AI4.2)
- [x] EnhancementExtractor created (Story AI4.2)
- [ ] Daily analysis integration (Story AI4.2)
- [ ] Discovery UI (Story AI4.3)
- [ ] Weekly refresh (Story AI4.4)

---

## Support

**Issues:** Check logs at `docker logs automation-miner`  
**API Docs:** http://localhost:8019/docs  
**Health Check:** http://localhost:8019/health  

**Created:** October 18, 2025  
**Status:** ✅ Deployed and Verified

