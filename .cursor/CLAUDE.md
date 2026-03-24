# CLAUDE.md - HomeIQ AI Assistant Guide

**Last Updated:** March 2, 2026
**Version:** 5.1.0
**Purpose:** Comprehensive guide for AI assistants working on HomeIQ

---

## 🎯 Quick Reference

**What is HomeIQ?** AI-powered Home Assistant intelligence platform — **~58 containers** (`--profile production`) across **9 domain groups**; **62** Compose service definitions. Services live under `domains/<group>/`.
**Deployment:** Single NUC, Docker Compose domain scripts (`start-stack`, `domain.ps1` / `domain.sh`), local network. **`.env` at repository root** (copy from `infrastructure/env.example`).
**Architecture:** Hybrid DB (InfluxDB time-series + PostgreSQL 17 metadata), Epic 31 direct writes (no enrichment-pipeline).
**Languages:** Python 3.12+ (backend), TypeScript/React 18 (frontend)
**Home Assistant:** External (e.g. `192.168.1.86:8123`), WebSocket connection
**Documentation:** [docs/README.md](docs/README.md) — single index; use it for all doc paths.
**Epic Index:** [stories/OPEN-EPICS-INDEX.md](../stories/OPEN-EPICS-INDEX.md) — **single source of truth** for all epic/story tracking. Check before creating new work. Update after completing any epic/story.

---

## Epic & Story Tracking

All epics (completed and planned) are tracked in **[stories/OPEN-EPICS-INDEX.md](../stories/OPEN-EPICS-INDEX.md)**.

**Rules for agents:**
1. **Before creating new epics:** Check the index for duplicates, superseded work, or overlap.
2. **After completing any epic/story:** Update the index immediately (status, commit hash, date).
3. **Planning docs** in `docs/planning/` contain detailed story breakdowns. The index links to them.
4. **The "Open Work" section** lists all planned-but-unstarted epics in priority order.
5. **Epic numbers are sequential.** Next available: **61+**. Never reuse a number.

---

## Quality Pipeline (TAPPS)

This project uses TAPPS for automated code quality enforcement. TappsMCP runs locally via **uv stdio** from `C:\cursor\TappMCP` (v1.6.0). When TappsMCP is configured (see [MCP_SETUP_INSTRUCTIONS.md](MCP_SETUP_INSTRUCTIONS.md)):

- Call `tapps_session_start()` at the start of every session
- Call `tapps_quick_check(file_path)` after editing any Python file
- Call `tapps_checklist(task_type)` as the final step
- Call `tapps_lookup_docs(library)` before using external library APIs
- Call `tapps_consult_expert(question)` for domain-specific decisions
- Call `tapps_impact_analysis(file_path)` before refactoring or deleting files

See AGENTS.md for the full tool reference.

---

## 📁 Repository Structure

```
HomeIQ/
├── domains/               # 9 domain groups (~58 prod containers; 62 compose definitions)
│   ├── core-platform/     # data-api, admin-api, websocket-ingestion, health-dashboard, etc.
│   ├── data-collectors/   # weather, sports, carbon, air-quality, calendar, smart-meter, etc.
│   ├── ml-engine/         # OpenVINO, NER, OpenAI, RAG, device-intelligence, etc.
│   ├── automation-core/   # ai-automation-service, NL→YAML, validation, deployment
│   ├── blueprints/        # Blueprint index, ML recommendations
│   ├── energy-analytics/  # Correlator, forecasting, proactive agent
│   ├── device-management/ # Device health, setup, classification
│   ├── pattern-analysis/  # Behavioral patterns, synergy
│   └── frontends/         # AI Automation UI (:3001), observability, health-dashboard (:3000)
├── libs/                  # Shared libraries (homeiq-patterns, homeiq-resilience, etc.)
├── docs/                  # Documentation — index: docs/README.md
│   ├── api/               # API_REFERENCE.md
│   ├── architecture/       # Service groups, event flow, database schema
│   ├── deployment/        # Runbook, pipeline, nginx
│   ├── planning/          # Phase plans, rebuild guides
│   ├── current/           # Active reference (prefer this)
│   └── archive/           # Historical (ignore unless researching history)
├── implementation/       # Status reports, session notes, plans (not reference docs)
├── infrastructure/        # Docker, env configs
├── scripts/               # Deployment & verification scripts
├── tests/                 # E2E (Playwright), pytest
└── docker-compose.yml    # Full stack (domain compose files under domains/<group>/)
```

---

## 🏗️ System Architecture

### Production stack overview

**Note:** Full `start-stack` + `--profile production` runs **~58** application containers (see `docs/architecture/service-groups.md`). The breakdown below is a **logical map**, not an exhaustive container list.

**Web Layer (2 services):**
- Health Dashboard (React) - Port 3000
- AI Automation UI (React) - Port 3001

**Core API Layer (3 services):**
- WebSocket Ingestion - Port 8001 (infinite retry + circuit breaker)
- Admin API - Port 8003→8004
- Data API - Port 8006 (PostgreSQL + InfluxDB queries)

**AI Services Layer (8 services):**
- AI Automation Service - Port 8024→8018 (pattern detection)
- AI Core Service - Port 8018 (orchestrator)
- OpenVINO Service - Port 8026→8019 (embeddings, re-ranking)
- ML Service - Port 8025→8020 (clustering, anomaly detection)
- NER Service - Port 8031 (entity recognition)
- OpenAI Service - Port 8020 (GPT-4o-mini)
- Device Intelligence - Port 8028 (capability discovery)
- Automation Miner - Port 8029 (community mining)

**Data Layer:**
- InfluxDB 2.7 - Port 8086 (time-series: 365-day retention, ~150 fields)
- PostgreSQL 17 - Port 5432 (metadata: schema-per-domain):
  - core (devices, entities, metadata)
  - automation (automations, plans, deployments)
  - blueprints (community corpus, suggestions)
  - devices (device intelligence, 7 tables)
  - energy, patterns, agent, rag

**Data Enrichment Layer (5 active + 1 disabled - Epic 31 Direct Writes):**
- Weather API - Port 8009 → InfluxDB
- Carbon Intensity - Port 8010 → InfluxDB
- Electricity Pricing - Port 8011 → InfluxDB
- Air Quality - Port 8012 → InfluxDB
- ⏸️ Calendar Service - Port 8013 → InfluxDB (currently disabled in docker-compose)
- Smart Meter - Port 8014 → InfluxDB

**Processing & Infrastructure (4 services):**
- Data Retention - Port 8080
- Energy Correlator - Port 8017
- Log Aggregator - Port 8015
- HA Setup Service - Port 8027→8020

**Development/External Dependencies:**
- HA Simulator - Port 8123 (dev environment only, not in production docker-compose)
- External MQTT Broker - mqtt://192.168.1.86:1883 (Home Assistant's MQTT broker, not a HomeIQ service)
- Home Assistant - http://192.168.1.86:8123 (external, single NUC deployment)
- ❌ Enrichment Pipeline (DEPRECATED - Epic 31, removed October 2025)

---

## 🔑 Critical Performance Patterns

### 1. Hybrid Database Architecture (5-10x Speedup)

**WHY:** InfluxDB excels at time-series writes but has 50ms+ query latency. PostgreSQL provides <10ms metadata lookups with connection pooling.

```
InfluxDB (Time-Series)          PostgreSQL (Metadata)
├── state_changed events        ├── core: devices, entities
├── metrics & telemetry         ├── automation: plans, deployments
├── historical queries          ├── blueprints: community corpus
└── retention policies          └── devices, energy, patterns, agent, rag
```

**Performance Impact:** Device queries: 50ms → <10ms = **5x faster**

### 2. Batch Processing Pattern

```python
class BatchProcessor:
    def __init__(self, batch_size: int = 100, batch_timeout: float = 5.0):
        self.batch_size = batch_size      # Max events per batch
        self.batch_timeout = batch_timeout  # Max seconds to wait
```

**Two Flush Triggers:**
1. Size-based: Batch reaches 100 events → flush immediately
2. Time-based: 5 seconds elapsed → flush partial batch

**Performance Impact:** 1 batch write vs 100 individual writes = **10-100x faster**

### 3. PostgreSQL Optimization

```python
# Connection pooling via asyncpg
pool_size=10                     # Per-service connection pool
max_overflow=5                   # Extra connections under load
pool_pre_ping=True               # Detect stale connections
# Schema-per-domain isolation
SET search_path TO {schema}, public  # Each service uses its own schema
```

### 4. InfluxDB Optimization

```python
batch_size = 1000                # Points per batch
batch_timeout = 5.0              # Seconds before force flush
max_retries = 3                  # Retry on network errors
```

**Best Practices:**
- Batch everything (never write single points)
- Use appropriate tags vs fields (tags for filtering, fields for values)
- Query optimization (specific time range + field selection)

---

## 🛠️ Development Workflows

### Environment Setup (Single NUC Deployment)

```bash
# 1. Clone and setup
git clone https://github.com/wtthornton/HomeIQ.git
cd HomeIQ

# 2. Configure environment (repo root)
cp infrastructure/env.example .env
# Edit .env with your HA details:
# - HA_HTTP_URL=http://192.168.1.86:8123  # Your Home Assistant IP
# - HA_WS_URL=ws://192.168.1.86:8123/api/websocket
# - HA_TOKEN=your-long-lived-access-token

# 3. Start services (ordered domains — do not use bare `docker compose up` for daily use)
./scripts/start-stack.sh          # Linux/Mac
# Windows: .\scripts\start-stack.ps1

# 4. Verify deployment (from repo root)
./scripts/verify-deployment.sh    # Linux/Mac
# Windows: .\scripts\verify-deployment.ps1
```

### Running Services Locally

**Python Service:**
```bash
cd services/[service-name]
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn src.main:app --reload --port [port]
```

**Frontend Service:**
```bash
# Build and run with Docker (recommended)
docker compose up -d [service-name]

# Or build locally
cd services/[service-name]
npm install
npm run build
```

### Testing

**Current Status:** Automated test framework being rebuilt (legacy suites removed November 2025)

**Manual Verification:**
- Health Dashboard: http://localhost:3000
- AI Automation UI: http://localhost:3001
- API Docs: http://localhost:8003/docs

**Future:** Focused smoke/regression tests coming soon

---

## 📝 Code Quality Standards

### Complexity Thresholds

**Python (Radon):**
- A (1-5): Simple - **preferred for all new code**
- B (6-10): Moderate - **acceptable**
- C (11-20): Complex - **document thoroughly, refactor when touched**
- D (21-50): Very complex - **refactor as high priority**
- F (51+): Extremely complex - **immediate refactoring required**

**Project Standards:**
- Warn: Complexity > 15
- Error: Complexity > 20
- Target: Average complexity ≤ 5
- Current: 0.64% duplication ✅

### Naming Conventions

| Element | Frontend | Backend | Example |
|---------|----------|---------|---------|
| Components | PascalCase | - | `HealthDashboard.tsx` |
| Hooks | camelCase with 'use' | - | `useHealthStatus.ts` |
| API Routes | - | kebab-case | `/api/health-status` |
| Database Tables | - | snake_case | `home_assistant_events` |
| Functions | camelCase | snake_case | `getStatus()` / `get_status()` |

### Python Best Practices

```python
"""Module docstring explaining purpose"""

from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

class ExampleService:
    """Class docstring"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize with type hints and docstrings"""
        self.config = config

    async def process_data(self, data: List[Dict]) -> Optional[Dict]:
        """
        Process data asynchronously

        Args:
            data: List of data dictionaries

        Returns:
            Processed results or None

        Raises:
            ProcessingError: If processing fails
        """
        try:
            result = await self._internal_process(data)
            return result
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            return None
```

**Key Points:**
- Use `async/await` throughout Python services
- Type hints for all parameters and return values
- Docstrings for all classes and functions
- Descriptive variable names
- Functions < 50 lines
- Handle errors gracefully
- Use logging, not print statements

### TypeScript/React Best Practices

```typescript
/**
 * Example component with TypeScript
 */
import React, { useState, useEffect } from 'react';

interface ExampleProps {
  /** Service name to display */
  serviceName: string;
  /** Optional callback */
  onStatusChange?: (status: string) => void;
}

export const ExampleComponent: React.FC<ExampleProps> = ({
  serviceName,
  onStatusChange
}) => {
  const [status, setStatus] = useState<string>('loading');

  useEffect(() => {
    fetchStatus();
  }, [serviceName]);

  const fetchStatus = async () => {
    try {
      const response = await fetch(`/api/status/${serviceName}`);
      const data = await response.json();
      setStatus(data.status);
      onStatusChange?.(data.status);
    } catch (error) {
      console.error('Failed to fetch status:', error);
      setStatus('error');
    }
  };

  return (
    <div className="example-component">
      <h2>{serviceName}</h2>
      <p>Status: {status}</p>
    </div>
  );
};
```

**Key Points:**
- Use TypeScript for type safety
- JSDoc comments for interfaces
- Functional components with hooks
- Handle loading and error states
- useMemo for expensive calculations
- Selective subscriptions for state management

---

## 🔄 Git Workflow

### Branch Naming

```bash
# Feature branches
feature/amazing-feature
feature/ai-automation-improvements

# Bug fixes
fix/websocket-reconnection
fix/database-migration-error

# Documentation
docs/update-architecture
docs/api-reference-improvements
```

### Commit Message Conventions (Conventional Commits)

```bash
# Format: <type>(<scope>): <subject>

# Examples:
feat(ai-automation): add multi-hop synergy detection
fix(websocket): resolve infinite retry loop
docs(readme): update installation instructions
refactor(data-api): optimize query performance
test(ai-automation): add unit tests for pattern detection
chore(deps): update dependencies
perf(influxdb): improve batch write performance
ci(github): update deployment workflow
```

**Types:** feat, fix, docs, style, refactor, test, chore, perf, ci

**Scopes:** Service or component name (ai-automation, websocket, health-dashboard, etc.)

### Creating Pull Requests

```bash
# 1. Update your branch
git checkout main
git pull upstream main

# 2. Create feature branch
git checkout -b feature/amazing-feature

# 3. Make changes and commit
git add .
git commit -m "feat(service): add amazing feature"

# 4. Push to your fork
git push origin feature/amazing-feature

# 5. Create PR on GitHub with description
```

**PR Title Format:** `<type>(<scope>): <short summary>`

**PR Checklist:**
- [ ] Code follows project style guidelines
- [ ] All manual tests pass (automated tests being rebuilt)
- [ ] Documentation updated (if applicable)
- [ ] No console errors or warnings
- [ ] Commit messages follow conventions

---

## 📚 Documentation Structure

### Single Sources of Truth

**API Documentation:**
- **USE:** [docs/api/API_REFERENCE.md](docs/api/API_REFERENCE.md) - All 65 endpoints
- **IGNORE:** All other API_*.md files (marked with redirect notices)

**Architecture:**
- **USE:** [docs/architecture/](docs/architecture/) - 27 current docs
- **KEY FILES:**
  - coding-standards.md
  - database-schema.md
  - performance-patterns.md
  - deployment-architecture.md

**Current vs Archive:**
- **USE:** [docs/current/](docs/current/) - Active reference documentation
- **IGNORE:** [docs/archive/](docs/archive/) - Historical docs (51 files)

### Finding Documentation

| Need | Location |
|------|----------|
| **Doc index (use first)** | [docs/README.md](docs/README.md) |
| API endpoints | docs/api/API_REFERENCE.md |
| Architecture | docs/architecture/ |
| Deployment | docs/deployment/DEPLOYMENT_RUNBOOK.md |
| Quick start | README.md#quick-start, deployment runbook |
| Contributing | README.md#contributing, CONTRIBUTING.md |
| Troubleshooting | tools/cli/docs/TROUBLESHOOTING.md |

---

## 🔍 Key Service Patterns

### AI Automation Service (Port 8024→8018)

**Location:** `domains/automation-core/ai-automation-service-new/`

**Key Features:**
- Pattern detection (time-of-day, co-occurrence, anomaly)
- Natural language automation generation
- Conversational refinement flow
- Device intelligence integration
- Multi-hop synergy detection
- LangChain integration (feature flags)
- PDL workflows (YAML-based procedures)

**Database:** ai_automation.db (11 tables)

**Critical Modules:**
- `nl_automation_generator.py` - Natural language to YAML
- `safety_validator.py` - 6-rule safety engine
- `pattern_detection/` - Pattern analysis
- `synergy_detection/` - Device relationship discovery
- `langchain_integration/` - LangChain LCEL chains
- `pdl/` - PDL workflow orchestration

### WebSocket Ingestion (Port 8001)

**Location:** `domains/core-platform/websocket-ingestion/`

**Key Features:**
- Real-time HA event capture
- Infinite retry with circuit breaker
- Batch processing (100 events / 5 seconds)
- Direct InfluxDB writes
- PostgreSQL metadata caching

**Critical Patterns:**
- Always use async/await
- Batch database operations
- Handle WebSocket disconnections gracefully
- Circuit breaker prevents cascading failures

### Data API (Port 8006)

**Location:** `domains/core-platform/data-api/`

**Key Features:**
- Hybrid query router (PostgreSQL + InfluxDB)
- Device/entity metadata queries (<10ms)
- Historical event queries (<100ms)
- RESTful API with FastAPI

**Performance Targets:**
- Health checks: <10ms
- Device queries: <10ms (PostgreSQL)
- Event queries: <100ms (InfluxDB)

### Shared Libraries

**Location:** `shared/`

**Key Modules:**
- `ha_connection_manager.py` - HA WebSocket/HTTP client with retry logic
- `metrics_collector.py` - Telemetry and metrics collection
- `logging_config.py` - Centralized logging configuration
- `correlation_middleware.py` - Request correlation IDs
- `influxdb_query_client.py` - InfluxDB query wrapper

**Usage Pattern:**
```python
from shared.ha_connection_manager import get_ha_connection
from shared.metrics_collector import get_metrics_collector
from shared.logging_config import setup_logging

# Setup logging
logger = setup_logging("service-name")

# Get HA connection
ha = get_ha_connection()

# Collect metrics
metrics = get_metrics_collector("service-name")
metrics.increment_counter("requests_total", tags={"endpoint": "/health"})
```

---

## 🚀 Common Development Tasks

### Adding a New API Endpoint

```python
# services/[service]/src/api/example.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class ExampleRequest(BaseModel):
    """Request model with validation"""
    entity_id: str
    start_time: Optional[str] = None

class ExampleResponse(BaseModel):
    """Response model"""
    entity_id: str
    data: List[dict]

@router.post("/api/example", response_model=ExampleResponse)
async def example_endpoint(request: ExampleRequest):
    """
    Example endpoint with proper error handling

    Args:
        request: Example request payload

    Returns:
        ExampleResponse with processed data

    Raises:
        HTTPException: If processing fails
    """
    try:
        # Process request
        data = await process_data(request.entity_id)

        return ExampleResponse(
            entity_id=request.entity_id,
            data=data
        )
    except Exception as e:
        logger.error(f"Failed to process request: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### Adding Database Migrations

```bash
# For services with Alembic (PostgreSQL)
cd services/[service]
alembic revision --autogenerate -m "Add new table"
alembic upgrade head
```

### Adding Frontend Components

```typescript
// services/[ui-service]/src/components/Example.tsx

import React, { useState, useEffect } from 'react';

interface ExampleProps {
  title: string;
}

export const Example: React.FC<ExampleProps> = ({ title }) => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/example');
      const result = await response.json();
      setData(result.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="example-component">
      <h2>{title}</h2>
      {data.map((item, index) => (
        <div key={index}>{JSON.stringify(item)}</div>
      ))}
    </div>
  );
};
```

---

## ⚡ Performance Targets

| Endpoint Type | Target | Acceptable | Investigation |
|---------------|--------|------------|---------------|
| Health checks | <10ms | <50ms | >100ms |
| Device queries | <10ms | <50ms | >100ms |
| Event queries | <100ms | <200ms | >500ms |
| Dashboard load | <2s | <5s | >10s |
| AI operations | <5s | <10s | >30s |

## 🔧 Common Commands

```bash
# Monitor performance
docker stats
docker compose logs -f websocket-ingestion | grep -E "duration_ms|error"

# Service health
curl http://localhost:8003/health
curl http://localhost:8006/health
curl http://localhost:8024/health

# Database queries (PostgreSQL)
docker exec homeiq-postgres psql -U homeiq -d homeiq -c "SELECT * FROM core.devices LIMIT 5;"

# Restart specific service
docker compose restart ai-automation-service

# View logs
docker compose logs -f ai-automation-service

# Run database migrations
cd domains/automation-core/ai-automation-service-new
alembic upgrade head
```

---

## 🚨 Common Anti-Patterns to Avoid

1. **Blocking the Event Loop** - Use `aiohttp`, not `requests`
2. **N+1 Database Queries** - Use eager loading
3. **Unbounded Queries** - Always use LIMIT clauses
4. **Not Using Connection Pooling** - Reuse HTTP sessions
5. **Inefficient Frontend Re-renders** - Use useMemo, selective subscriptions
6. **Logging Too Much** - Batch log statements
7. **Not Setting Timeouts** - Always configure timeouts
8. **Direct process.env Access** - Use config objects
9. **Mutating State Directly** - Use proper state management
10. **Creating Duplicate Docs** - Update existing documentation

---

## 📊 Feature Flags & Configuration

### LangChain Integration

**Feature Flags** (AI Automation Service):
- `USE_LANGCHAIN_ASK_AI` - Enable LangChain for Ask AI prompts
- `USE_LANGCHAIN_PATTERNS` - Enable LangChain for pattern detection

**Configuration:**
- Location: `domains/automation-core/ai-automation-service-new/src/config.py`
- Settings UI: http://localhost:3001/settings

### PDL Workflows

**YAML-based Procedures:**
- Location: `domains/automation-core/ai-automation-service-new/src/pdl/`
- Nightly analysis orchestration
- Synergy guardrails (when enabled)

---

## 🔐 Security & Safety

### API Authentication

- HA Long-Lived Access Token (configured in repository root `.env`)
- Internal service-to-service calls (no auth)
- External API keys (OpenAI, Weather, etc.)

### Safety Validation (6-Rule Engine)

**Implemented in:** `domains/automation-core/ai-automation-service-new/src/safety_validator.py`

1. No destructive actions without confirmation
2. No entity ID mismatches
3. No excessive automation frequency
4. No unsafe device combinations
5. No privacy-violating data collection
6. No unrealistic time ranges

---

## 🎯 Quick Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose logs [service-name]

# Check environment variables
cat .env   # repository root

# Verify dependencies
docker compose ps
```

### Database Connection Issues

```bash
# Check InfluxDB
curl http://localhost:8086/health

# Check PostgreSQL connectivity
docker exec homeiq-postgres pg_isready -U homeiq

# Verify configuration
echo $INFLUXDB_TOKEN
```

### WebSocket Connection Failures

```bash
# Check HA connectivity
curl $HA_HTTP_URL/api/

# Verify WebSocket endpoint
wscat -c $HA_WS_URL

# Check ingestion service
docker compose logs websocket-ingestion
```

---

## 📖 Additional Resources

**Essential Documentation:**
- [Docs Index](docs/README.md)
- [API Reference](docs/api/API_REFERENCE.md)
- [Architecture](docs/architecture/) — service groups, database schema, event flow
- [Deployment Runbook](docs/deployment/DEPLOYMENT_RUNBOOK.md)
- [Contributing](README.md#contributing), [CONTRIBUTING.md](CONTRIBUTING.md)

**External Resources:**
- [Home Assistant API](https://developers.home-assistant.io/docs/api/rest/)
- [InfluxDB Best Practices](https://docs.influxdata.com/influxdb/v2.7/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)

**External API Integrations:**
- **OpenWeatherMap** - Weather data (API key required)
- **WattTime** - Carbon intensity data (username/password required)
- **Awattar** - Electricity pricing (no auth required, Germany/Austria)
- **AirNow** - Air quality data (API key optional)
- **ESPN** - Sports data (no auth required, free API)

---

## 🎓 Remember

1. **Performance First** - Profile before optimizing, batch everything
2. **Async Everything** - Use async/await throughout Python services
3. **Document Thoroughly** - Update docs with code changes
4. **Test Manually** - Automated tests being rebuilt, verify manually
5. **Follow Conventions** - Consistent naming, commit messages, code style
6. **Use Single Sources of Truth** - Don't create duplicate documentation
7. **Handle Errors Gracefully** - Proper logging, retries, circuit breakers
8. **Think Microservices** - Each service has a single responsibility
9. **Optimize Databases** - Right tool for right job (PostgreSQL for metadata, InfluxDB for time-series)
10. **Communicate Clearly** - Commit messages, PR descriptions, code comments

---

**Document Metadata:**
- **Created:** October 23, 2025
- **Last Updated:** March 2, 2026
- **Version:** 5.1.0
- **Next Review:** Quarterly or after major architectural changes
- **Maintainer:** HomeIQ Development Team

**Change Log v5.1.0:**
- Documentation index: use docs/README.md (removed reference to nonexistent DOCUMENTATION_INDEX / PORT_MAPPING_REFERENCE)
- Repository structure updated to domains/ layout (9 groups; ~58 prod containers / 62 compose definitions)
- Finding Documentation table aligned with docs/README.md and deployment runbook paths
