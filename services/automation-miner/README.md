# Automation Miner

**Community Knowledge Crawler for Home Assistant Automations**

**Port:** 8029 (External) → 8019 (Internal)
**Technology:** Python 3.11+, FastAPI 0.121, SQLAlchemy 2.0, BeautifulSoup 4.14
**Container:** `homeiq-automation-miner`
**Database:** SQLite (automation_miner.db)
**Epic:** AI-4 (Community Knowledge Augmentation)

## Overview

The Automation Miner service crawls high-quality Home Assistant automations from community sources (Discourse, GitHub), normalizes them into structured metadata, and provides a query API for the AI Automation service. It powers **Epic AI-4** by building a searchable corpus of 2,000+ community automations.

### Key Features

- **Selective Crawling** - Only fetches high-quality automations (500+ votes)
- **Normalization** - Extracts structured metadata (devices, integrations, use cases)
- **Storage** - SQLite-based corpus with fast query API
- **Performance** - <100ms query response time
- **Quality** - 2,000+ automations, avg quality ≥0.7
- **Weekly Refresh** - Incremental corpus updates (Story AI4.4)
- **PII Removal** - Automatic privacy protection

## Quick Start

### Prerequisites

- Python 3.11+
- SQLite 3.x
- Internet connectivity (for crawling)

### Running Locally

```bash
cd services/automation-miner

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start service
uvicorn src.api.main:app --reload --port 8019
```

### Running with Docker

```bash
# Build and start
docker compose up -d automation-miner

# View logs
docker compose logs -f automation-miner

# Check health
curl http://localhost:8029/health
```

## API Endpoints

### Health & Status

#### `GET /health`
Service health check
```bash
curl http://localhost:8029/health
```

### Query API

#### `GET /api/automation-miner/corpus/search`
Search automations by criteria

```bash
# Search by device
curl "http://localhost:8029/api/automation-miner/corpus/search?device=motion_sensor&limit=10"

# Search by use case
curl "http://localhost:8029/api/automation-miner/corpus/search?use_case=security&min_quality=0.8"
```

**Query Parameters:**
- `device` - Filter by device type (e.g., "light", "motion_sensor")
- `integration` - Filter by integration (e.g., "mqtt", "zigbee2mqtt")
- `use_case` - Filter by use case ("energy", "comfort", "security", "convenience")
- `min_quality` - Minimum quality score (0.0-1.0, default 0.7)
- `limit` - Maximum results (default 50)

**Response:**
```json
{
  "automations": [
    {
      "id": 1,
      "title": "Motion-activated night lighting",
      "description": "Turn on lights when motion detected at night",
      "devices": ["motion_sensor", "light"],
      "integrations": ["mqtt", "zigbee2mqtt"],
      "use_case": "comfort",
      "complexity": "low",
      "quality_score": 0.89,
      "vote_count": 542
    }
  ],
  "count": 1
}
```

#### `GET /api/automation-miner/corpus/stats`
Corpus statistics

```bash
curl http://localhost:8029/api/automation-miner/corpus/stats
```

**Response:**
```json
{
  "total_automations": 2143,
  "avg_quality": 0.78,
  "unique_devices": 54,
  "unique_integrations": 32,
  "use_case_distribution": {
    "comfort": 842,
    "security": 531,
    "energy": 428,
    "convenience": 342
  }
}
```

#### `GET /api/automation-miner/corpus/{id}`
Get single automation by ID

```bash
curl http://localhost:8029/api/automation-miner/corpus/123
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_AUTOMATION_MINER` | `false` | Enable/disable service |
| `MINER_DB_PATH` | `data/automation_miner.db` | Database file path |
| `DISCOURSE_BASE_URL` | `https://community.home-assistant.io` | Discourse API URL |
| `GITHUB_TOKEN` | - | Optional GitHub API token (higher rate limits) |
| `CRAWL_SCHEDULE` | `0 3 * * 0` | Weekly crawl schedule (3 AM Sunday) |
| `LOG_LEVEL` | `INFO` | Logging level |

### Example `.env`

```bash
ENABLE_AUTOMATION_MINER=true
MINER_DB_PATH=data/automation_miner.db
DISCOURSE_BASE_URL=https://community.home-assistant.io
GITHUB_TOKEN=your_github_token_here
CRAWL_SCHEDULE=0 3 * * 0
LOG_LEVEL=INFO
```

## Architecture

### Data Flow

```
┌──────────────────────────────┐
│ Community Sources            │
│ - Discourse (HA Community)   │
│ - GitHub (Popular repos)     │
└───────────┬──────────────────┘
            │
            │ Weekly crawl (500+ votes)
            ↓
┌──────────────────────────────┐
│ Automation Miner             │
│ (Port 8029)                  │
│                              │
│ ┌────────────────────────┐  │
│ │ Crawler                │  │
│ │ - Rate limiting        │  │
│ │ - Deduplication        │  │
│ └────────────────────────┘  │
│                              │
│ ┌────────────────────────┐  │
│ │ Parser                 │  │
│ │ - PII removal          │  │
│ │ - Metadata extraction  │  │
│ └────────────────────────┘  │
└───────────┬──────────────────┘
            │
            ↓
┌──────────────────────────────┐
│ SQLite Database              │
│ automation_miner.db          │
│ - community_automations      │
└───────────┬──────────────────┘
            │
            ↓
┌──────────────────────────────┐
│ AI Automation Service        │
│ Pattern Enhancement (AI4.2)  │
└──────────────────────────────┘
```

### Component Architecture

```
src/
├── api/
│   └── main.py             # FastAPI application
├── crawler/
│   ├── discourse.py        # Discourse crawler
│   └── github.py           # GitHub crawler
├── parser/
│   ├── automation.py       # YAML automation parser
│   ├── pii_remover.py      # Privacy protection
│   └── metadata.py         # Metadata extraction
├── storage/
│   ├── database.py         # SQLAlchemy setup
│   └── models.py           # Database models
└── scheduler/
    └── jobs.py             # Weekly refresh (AI4.4)
```

## Database Schema

### Table: community_automations

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `source` | VARCHAR | 'discourse' or 'github' |
| `source_id` | VARCHAR | Unique post/repo ID |
| `title` | VARCHAR | Automation title |
| `description` | TEXT | Normalized description (PII removed) |
| `devices` | JSON | Device types array |
| `integrations` | JSON | Integration array |
| `triggers` | JSON | Trigger metadata |
| `conditions` | JSON | Condition metadata |
| `actions` | JSON | Action metadata |
| `use_case` | VARCHAR | 'energy', 'comfort', 'security', 'convenience' |
| `complexity` | VARCHAR | 'low', 'medium', 'high' |
| `quality_score` | FLOAT | 0.0-1.0 (votes, recency, completeness) |
| `vote_count` | INTEGER | Community votes |
| `created_at` | DATETIME | Original post date |
| `updated_at` | DATETIME | Last update date |
| `last_crawled` | DATETIME | Last crawl timestamp |
| `metadata` | JSON | Additional data |

**Indexes:**
- `source`, `source_id` (unique constraint)
- `quality_score` (descending)
- `use_case`
- `devices`, `integrations` (JSON indexes)

## Use Cases

### 1. Pattern Enhancement (AI4.2)
Find similar community automations during pattern detection:
```python
# User has motion sensor + light patterns
similar = await search_corpus(
    devices=["motion_sensor", "light"],
    use_case="comfort",
    min_quality=0.8
)
# Returns top community patterns for inspiration
```

### 2. Device Discovery (AI4.3)
Suggest automations for newly discovered devices:
```python
# New motion sensor added
recommendations = await search_corpus(
    devices=["motion_sensor"],
    min_quality=0.7,
    limit=10
)
# Returns popular motion sensor automations
```

### 3. Weekly Refresh (AI4.4)
Incremental corpus updates every Sunday at 3 AM:
- Fetch new automations since last crawl
- Update vote counts for existing automations
- Re-calculate quality scores
- Clean up deleted/archived content

## Performance

### Performance Targets

| Operation | Target | Acceptable | Investigation |
|-----------|--------|------------|---------------|
| Query API | <100ms | <200ms | >500ms |
| Initial crawl | <3 hours | <5 hours | >8 hours |
| Weekly refresh | <30 min | <60 min | >2 hours |
| Storage | <500MB | <1GB | >2GB |

### Resource Usage

- **Memory:** <200MB crawler peak
- **Disk:** <500MB database size
- **Network:** Rate-limited (Discourse: 2 req/sec)

### Quality Targets

- **Corpus Size:** 2,000+ automations
- **Avg Quality:** ≥0.7
- **Device Coverage:** 50+ unique device types
- **Integration Coverage:** 30+ integrations
- **Deduplication:** <5% duplicates

## Development

### Manual Crawl

```bash
# Trigger initial crawl
python -m src.cli crawl --initial

# Dry run (no database changes)
python -m src.cli crawl --dry-run

# Incremental update
python -m src.cli crawl --incremental
```

### Testing

```bash
# Run all tests
pytest tests/

# Unit tests
pytest tests/unit -v

# Integration tests
pytest tests/integration -v

# Coverage
pytest --cov=src --cov-report=html
```

## Monitoring

### Structured Logging

Logs include:
- Crawl progress (pages, automations found)
- Rate limiting status
- Parsing errors
- Quality distribution
- Database writes

### Metrics

- Total automations in corpus
- Average quality score
- Device/integration coverage
- Crawl success rate
- Query performance

## Dependencies

### Core

```
fastapi>=0.121.0          # Web framework
uvicorn[standard]>=0.38.0 # ASGI server
pydantic>=2.8.2           # Data validation
pydantic-settings>=2.4.0  # Settings management
```

### HTTP & Parsing

```
httpx>=0.28.1             # Async HTTP client
beautifulsoup4>=4.14.2    # HTML parsing
lxml>=6.0.2               # XML/HTML parser
```

### Database

```
sqlalchemy[asyncio]>=2.0.0  # Async ORM
aiosqlite>=0.20.0          # Async SQLite
alembic>=1.13.0            # Migrations
```

### Utilities

```
apscheduler>=3.10.0       # Job scheduling
pyyaml>=6.0               # YAML parsing
rapidfuzz>=3.14.3         # Deduplication
python-json-logger>=2.0.0 # Structured logging
```

### Testing

```
pytest>=8.3.3             # Testing framework
pytest-asyncio>=0.23.0    # Async tests
pytest-cov>=4.1.0         # Coverage
pytest-httpx>=0.30.0      # HTTP mocking
```

## Troubleshooting

### Health Check Failing

**Check service status:**
```bash
curl http://localhost:8029/health
```

**Check logs:**
```bash
docker logs automation-miner
```

**Verify database:**
```bash
sqlite3 data/automation_miner.db "SELECT COUNT(*) FROM community_automations;"
```

### Crawl Failing

**Symptoms:**
- No new automations added
- HTTP errors in logs
- Rate limit errors

**Solutions:**
- Check rate limits (Discourse: 2 req/sec)
- Verify network connectivity
- Check API endpoint availability
- Review logs for HTTP errors
- Add GitHub token for higher rate limits

### Low Quality Scores

**Symptoms:**
- Average quality < 0.7

**Solutions:**
- Increase minimum vote threshold
- Check vote_count distribution
- Verify recency calculation
- Review quality score formula

### Database Growth

**Symptoms:**
- Database > 1GB

**Solutions:**
- Run vacuum: `sqlite3 data/automation_miner.db "VACUUM;"`
- Archive old/low-quality automations
- Review deduplication logic

## Integration

The Automation Miner integrates with:
- **Story AI4.2:** Pattern Enhancement (queries corpus during pattern detection)
- **Story AI4.3:** Device Discovery (provides device recommendations)
- **Story AI4.4:** Weekly Refresh (incremental corpus updates)

## Related Documentation

- [AI Automation Service](../ai-automation-service/README.md) - Consumer of corpus
- [Epic AI-4 PRD](../../docs/prd/epic-ai4-community-knowledge-augmentation.md)
- [API Reference](../../docs/api/API_REFERENCE.md)
- [CLAUDE.md](../../CLAUDE.md)

## Support

- **Issues:** https://github.com/wtthornton/HomeIQ/issues
- **Documentation:** `/docs` directory
- **Health Check:** http://localhost:8029/health
- **API Docs:** http://localhost:8029/docs

## Version History

### 2.1 (November 15, 2025)
- Updated documentation to 2025 standards
- Corrected port (8029 external, 8019 internal)
- Enhanced dependency documentation
- Added comprehensive API endpoint documentation
- Improved troubleshooting section
- Added Epic AI-4 context

### 2.0 (October 2025)
- Weekly refresh scheduler (AI4.4)
- Enhanced quality scoring
- Improved deduplication

### 1.0 (Initial Release - Story AI4.1)
- Discourse and GitHub crawling
- Basic corpus storage
- Query API

---

**Last Updated:** November 15, 2025
**Version:** 2.1
**Status:** Production Ready ✅
**Port:** 8029 (External) → 8019 (Internal)
**Epic:** AI-4 (Community Knowledge Augmentation)
