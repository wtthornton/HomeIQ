# Quick Reference - HA Ingestor

**For AI Agents:** Fast lookup guide for common tasks

---

## 🚀 Critical Files

| What | Where | Why |
|------|-------|-----|
| **Docker Rules** | `docs/DOCKER_STRUCTURE_GUIDE.md` | Read BEFORE modifying Dockerfiles |
| **Shared Logging** | `shared/logging_config.py` | Use for ALL Python services |
| **Code Standards** | `docs/architecture/coding-standards.md` | Naming & patterns |
| **Agent Guide** | `.cursor/AGENT_DEVELOPMENT_GUIDE.md` | Complete reference |

---

## 📋 Service Quick Reference

| Service | Port | Tech | Entry Point |
|---------|------|------|-------------|
| **websocket-ingestion** | 8001 | Python/aiohttp | `src/main.py` |
| **enrichment-pipeline** | 8002 | Python/FastAPI | `src/main.py` |
| **admin-api** | 8003→8004 | Python/FastAPI | `src/main.py` |
| **sports-data** | 8005 | Python/FastAPI | `src/main.py` |
| **data-retention** | 8080 | Python/FastAPI | `src/main.py` |
| **health-dashboard** | 3000 | React/nginx | `src/main.tsx` |
| **log-aggregator** | 8015 | Python | `src/main.py` |
| **influxdb** | 8086 | InfluxDB 2.7 | N/A |

---

## 🎨 Frontend Structure

```
health-dashboard/src/
├── App.tsx                        # Entry point
├── components/
│   ├── Dashboard.tsx             # Main dashboard (12 tabs)
│   ├── tabs/                     # All tab components
│   │   ├── OverviewTab.tsx      # System overview
│   │   ├── SportsTab.tsx        # Sports tracking
│   │   ├── ServicesTab.tsx      # Service management
│   │   └── ...                  # 9 more tabs
│   ├── ServiceDependencyGraph.tsx # Interactive graph
│   └── sports/                   # Sports components
├── hooks/
│   ├── useRealtimeMetrics.ts    # WebSocket hook
│   └── useHealth.ts             # Health data
└── services/
    └── api.ts                    # API client
```

### Frontend Tech Stack
- React 18.2 + TypeScript 5.2
- Vite 5.0 (build tool)
- TailwindCSS 3.4 (styling)
- Chart.js 4.5 + recharts 3.2 (charts)
- Vitest 3.2 (testing)
- Playwright 1.56 (E2E)

---

## 🐍 Backend Patterns

### Standard Logging (ALWAYS USE THIS)

```python
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.logging_config import (
    setup_logging, log_with_context, generate_correlation_id, 
    set_correlation_id, log_error_with_context
)

logger = setup_logging("my-service")

# Always use correlation IDs
corr_id = generate_correlation_id()
set_correlation_id(corr_id)

# Structured logging
log_with_context(
    logger, "INFO", "Processing event",
    operation="event_processing",
    correlation_id=corr_id,
    entity_id="sensor.temp"
)
```

### Standard FastAPI Service

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="My Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "my-service"}
```

### InfluxDB Pattern

```python
from influxdb_client import InfluxDBClient, Point

INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "ha-ingestor-token")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "ha-ingestor")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

point = Point("measurement") \
    .tag("entity_id", "sensor.temp") \
    .field("value", 23.5)
    
write_api.write(bucket=INFLUXDB_BUCKET, record=point)
```

---

## 🧪 Testing Commands

### Frontend (health-dashboard)
```bash
npm run test              # Vitest unit tests
npm run test:e2e          # Playwright E2E
npm run test:coverage     # Coverage report
```

### Backend (any Python service)
```bash
pytest                    # Run tests
pytest -v                 # Verbose
pytest --cov=src          # With coverage
```

---

## 🐳 Docker Commands

### Essential
```bash
docker-compose up -d                  # Start all
docker-compose up -d admin-api        # Start one service
docker-compose logs -f admin-api      # View logs
docker-compose restart admin-api      # Restart
docker-compose down                   # Stop all
```

### Rebuild Service
```bash
docker-compose build admin-api
docker-compose up -d admin-api
```

### Clean Everything
```bash
docker-compose down -v    # Includes volumes
```

### ⚠️ PowerShell Users (Windows)

**NEVER use `docker-compose exec` with Python commands:**
```powershell
# ❌ WRONG - Does NOT work in PowerShell
docker-compose exec service python -c "import ..."
```

**Use API endpoints instead:**
```powershell
# ✅ CORRECT - Get system prompt
$response = Invoke-RestMethod -Uri "http://localhost:8030/api/v1/complete-prompt"
$response.system_prompt

# ✅ CORRECT - Health check
Invoke-RestMethod -Uri "http://localhost:8030/health"
```

**See `.cursor/rules/development-environment.mdc` for full PowerShell command reference.**

---

## 📝 Code Conventions

### Python
```python
# snake_case
def process_event(): pass
class EventProcessor: pass
MAX_RETRIES = 3

# Type hints required
def process(data: dict) -> bool: pass
```

### TypeScript/React
```typescript
// PascalCase for components, camelCase for functions/hooks
export const Dashboard: React.FC = () => {};
const fetchData = async () => {};
export const useHealth = () => {};
```

---

## 🔧 Common Tasks

### Add New Service
1. Create `services/my-service/` with Dockerfile
2. Add to `docker-compose.yml` with health check
3. Use shared logging (`shared/logging_config.py`)
4. Add health endpoint: `/health`
5. Document in `docs/SERVICES_OVERVIEW.md`

### Add Dashboard Tab
1. Create `services/health-dashboard/src/components/tabs/MyTab.tsx`
2. Add to `components/tabs/index.ts`
3. Register in `Dashboard.tsx` TAB_COMPONENTS
4. Add to TAB_CONFIG array

### Modify Dockerfile
1. **READ** `docs/DOCKER_STRUCTURE_GUIDE.md` **FIRST**
2. Make changes carefully
3. Test rebuild: `docker-compose build SERVICE`
4. Verify: `docker-compose up SERVICE`

---

## ⚠️ Common Pitfalls

1. **Import errors** → Add `sys.path.append('../../shared')`
2. **CORS errors** → Check `nginx.conf` proxy config
3. **Service can't connect** → Use Docker names: `http://admin-api:8004`
4. **InfluxDB fails** → Check token, org, bucket env vars
5. **Build fails** → Read `DOCKER_STRUCTURE_GUIDE.md`

---

## 🔍 Where to Find...

| Need | Check |
|------|-------|
| **API endpoints** | `docs/API_ENDPOINTS_REFERENCE.md` |
| **Service details** | `docs/SERVICES_OVERVIEW.md` |
| **Architecture** | `docs/architecture/` directory |
| **Deployment** | `docs/DEPLOYMENT_GUIDE.md` |
| **Troubleshooting** | `docs/TROUBLESHOOTING_GUIDE.md` |
| **Complete guide** | `.cursor/AGENT_DEVELOPMENT_GUIDE.md` |

---

## 📞 Health Check URLs

```bash
curl http://localhost:8001/health   # WebSocket Ingestion
curl http://localhost:8002/health   # Enrichment Pipeline
curl http://localhost:8003/health   # Admin API
curl http://localhost:8005/health   # Sports Data
curl http://localhost:8080/health   # Data Retention
curl http://localhost:8015/health   # Log Aggregator
open http://localhost:3000          # Dashboard
```

---

**Remember:** Test locally, follow conventions, document changes!

