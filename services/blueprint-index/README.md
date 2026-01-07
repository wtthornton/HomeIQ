# Blueprint Index Service

A microservice for indexing and searching Home Assistant community blueprints.

## Overview

The Blueprint Index Service crawls GitHub repositories and Home Assistant Community forums to build a searchable index of 5,000+ Home Assistant blueprints. This enables HomeIQ to:

- **Discover blueprint opportunities** based on user device inventory
- **Match detected patterns** to community-validated blueprints
- **Deploy automations via blueprints** for safer, version-compatible deployments

## Features

- **Multi-source indexing**: GitHub repositories and Discourse forums
- **Rich metadata extraction**: Device requirements, use cases, quality scores
- **Pattern-based search**: Find blueprints by trigger/action patterns
- **Community metrics**: Stars, downloads, ratings
- **Async architecture**: High-performance async HTTP and database operations

## API Endpoints

### Search

```bash
# Search by device requirements
GET /api/blueprints/search?domains=binary_sensor,light&device_classes=motion

# Search by use case
GET /api/blueprints/search?use_case=security&min_quality_score=0.7

# Text search
GET /api/blueprints/search?query=motion%20light
```

### Pattern Matching

```bash
# Find blueprints for a trigger-action pattern
GET /api/blueprints/by-pattern?trigger_domain=binary_sensor&action_domain=light
```

### Indexing

```bash
# Trigger full re-indexing
POST /api/blueprints/index/refresh
{"job_type": "full"}

# Check indexing status
GET /api/blueprints/status
```

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite+aiosqlite:///data/blueprint_index.db` |
| `GITHUB_TOKEN` | GitHub API token (optional, for higher rate limits) | None |
| `LOG_LEVEL` | Logging level | `INFO` |
| `SERVICE_PORT` | Service port | `8031` |

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python -m uvicorn src.main:app --host 0.0.0.0 --port 8031 --reload
```

## Docker

```bash
# Build image
docker build -t blueprint-index .

# Run container
docker run -p 8031:8031 -v ./data:/app/data blueprint-index
```

## Data Model

### IndexedBlueprint

- `id`: Unique identifier
- `source_url`: Source URL (GitHub/Discourse)
- `name`: Blueprint name
- `description`: Blueprint description
- `required_domains`: Required entity domains (e.g., `["binary_sensor", "light"]`)
- `required_device_classes`: Required device classes (e.g., `["motion"]`)
- `inputs`: Blueprint input definitions
- `use_case`: Classification (energy, comfort, security, convenience)
- `quality_score`: Quality score (0.0-1.0)
- `community_rating`: Community rating (0.0-1.0)
- `stars`: GitHub stars or Discourse likes

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Blueprint Index Service                 │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   GitHub    │  │  Discourse  │  │   Search    │     │
│  │   Indexer   │  │   Indexer   │  │   Engine    │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
│         │                │                │             │
│         └────────────────┼────────────────┘             │
│                          │                              │
│                   ┌──────▼──────┐                       │
│                   │  Blueprint  │                       │
│                   │   Parser    │                       │
│                   └──────┬──────┘                       │
│                          │                              │
│                   ┌──────▼──────┐                       │
│                   │  SQLite DB  │                       │
│                   └─────────────┘                       │
└─────────────────────────────────────────────────────────┘
```

## Integration with HomeIQ

The Blueprint Index Service integrates with:

- **ai-pattern-service**: Provides blueprint data for synergy detection
- **Blueprint Opportunity Engine**: Matches devices to blueprints
- **Blueprint Deployer**: Provides YAML for deployment

## Development

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Lint
ruff check src/
mypy src/
```

## License

MIT License - see LICENSE file for details.
