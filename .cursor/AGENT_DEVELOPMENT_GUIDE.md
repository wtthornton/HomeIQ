# Agent Development Guide - HomeIQ

**Last Updated:** March 2, 2026  
**Project:** HomeIQ — AI-powered Home Assistant intelligence platform  
**Purpose:** Complete reference for AI agents working on this codebase

---

## 🎯 Quick Reference

### Project Type
- **Architecture:** 50 microservices in 9 domain groups (`domains/<group>/`)
- **Tech Stack:** Python 3.12+, React 18, FastAPI, TypeScript 5.x
- **Databases:** InfluxDB 2.7 (time-series), PostgreSQL 17 (metadata)
- **Deployment:** Docker Compose; domain-specific compose files under `domains/<group>/compose.yml`
- **Testing:** Playwright E2E, pytest, Vitest

### Critical Rules
1. **Documentation:** Use [docs/README.md](../docs/README.md) as the single doc index.
2. **Architecture:** Epic 31 — no enrichment-pipeline; events flow websocket-ingestion → InfluxDB (direct). See `.cursor/rules/epic-31-architecture.mdc`.
3. **Shared libs:** Use `libs/` (e.g. homeiq-observability for logging); follow patterns in existing services.
4. **NEVER commit secrets** — use `infrastructure/.env` (gitignored).
5. **FOLLOW conventions** in `docs/architecture/coding-standards.md` and `.cursor/rules/`.

---

## 📁 Project Structure

```
HomeIQ/
├── domains/                       # 9 domain groups, 50 services
│   ├── core-platform/             # data-api, admin-api, websocket-ingestion, health-dashboard
│   ├── data-collectors/           # weather, sports, carbon, air-quality, calendar, smart-meter
│   ├── ml-engine/                 # OpenVINO, NER, RAG, device-intelligence
│   ├── automation-core/           # ai-automation-service, NL→YAML, validation
│   ├── blueprints/                # Blueprint index, ML recommendations
│   ├── energy-analytics/          # Correlator, forecasting
│   ├── device-management/        # Device health, setup, classification
│   ├── pattern-analysis/          # Behavioral patterns, synergy
│   └── frontends/                 # AI Automation UI, observability
├── libs/                          # Shared libraries (homeiq-patterns, homeiq-resilience, etc.)
├── infrastructure/                # Docker, env configs (e.g. infrastructure/.env)
├── docs/                          # Index: docs/README.md
├── implementation/                # Status reports, session notes (not reference docs)
├── tests/                         # E2E (Playwright), pytest
├── scripts/                       # Deployment & verification
└── docker-compose.yml             # Full stack
```

---

## 🔧 Service Architecture (Complete)

### Core Data Flow
```
Home Assistant → WebSocket Ingestion (8001) 
                    ↓
            Enrichment Pipeline (8002)
                    ↓ (validates, enriches)
            InfluxDB (8086)
                    ↑
            Data Retention (8080) → S3/Glacier
```

### All Services with Actual Ports

| Service | Port | External | Technology | Purpose |
|---------|------|----------|------------|---------|
| **websocket-ingestion** | 8001 | ✅ | Python/aiohttp | HA WebSocket client |
| **enrichment-pipeline** | 8002 | ✅ | Python/FastAPI | Data validation & enrichment |
| **admin-api** | 8003→8004 | ✅ | Python/FastAPI | REST API gateway |
| **sports-data** | 8005 | ✅ | Python/FastAPI | ESPN sports data (FREE) |
| **data-retention** | 8080 | ✅ | Python/FastAPI | Data lifecycle |
| **health-dashboard** | 3000 | ✅ | React/nginx | Frontend UI |
| **log-aggregator** | 8015 | ✅ | Python | Log aggregation |
| **carbon-intensity** | 8010 | ❌ | Python/FastAPI | Carbon data |
| **electricity-pricing** | 8011 | ❌ | Python/FastAPI | Pricing data |
| **air-quality** | 8012 | ❌ | Python/FastAPI | Air quality |
| **calendar** | 8013 | ❌ | Python/FastAPI | Calendar integration |
| **smart-meter** | 8014 | ❌ | Python/FastAPI | Smart meter data |
| **weather-api** | Internal | ❌ | Python/FastAPI | Weather enrichment |
| **influxdb** | 8086 | ✅ | InfluxDB 2.7 | Time-series DB |

**Note:** Port 8003 is mapped to container port 8004 for admin-api

---

## 🎨 Frontend Architecture (React Dashboard)

### Dashboard Tabs (Actual Implementation)

The dashboard has **12 tabs** with comprehensive features:

1. **📊 Overview** - System health, metrics cards, real-time stats
2. **🎨 Custom** - Customizable widget dashboard (drag & drop)
3. **🔧 Services** - Service control, health monitoring, logs
4. **🔗 Dependencies** - Animated dependency graph with click-to-highlight
5. **📱 Devices** - Device & entity browser (Epic 19/20)
6. **📡 Events** - Real-time event stream with filtering
7. **📜 Logs** - Live log tail viewer with search
8. **🏈 Sports** - NFL/NHL game tracker with team selection
9. **🌐 Data Sources** - External data source status
10. **📈 Analytics** - Performance metrics and charts
11. **🚨 Alerts** - Alert management and history
12. **⚙️ Configuration** - Service configuration UI

### Key React Components

Located in `domains/core-platform/health-dashboard/src/components/`:

```typescript
// Main entry point
Dashboard.tsx                     // Main dashboard with tab routing

// Tabs (in components/tabs/)
OverviewTab.tsx                  // System overview
CustomTab.tsx                    // Customizable dashboard
ServicesTab.tsx                  // Service management
DependenciesTab.tsx              // Dependency visualization
DevicesTab.tsx                   // Device browser
EventsTab.tsx                    // Event stream
LogsTab.tsx                      // Log viewer
SportsTab.tsx                    // Sports tracking
DataSourcesTab.tsx               // Data sources
AnalyticsTab.tsx                 // Analytics
AlertsTab.tsx                    // Alerts
ConfigurationTab.tsx             // Configuration UI

// Shared Components
ServiceDependencyGraph.tsx       // ⭐ Interactive dependency graph
ConnectionStatusIndicator.tsx    // WebSocket connection status
MetricsChart.tsx                 // Chart.js integration
AlertBanner.tsx                  // Alert notifications

// Sports Components (in components/sports/)
LiveGameCard.tsx                 // Live game display
TeamSelector.tsx                 // Team selection UI
SetupWizard.tsx                  // First-run setup
```

### State Management Pattern

```typescript
// Uses React Context + Hooks (no Redux)
import { useRealtimeMetrics } from '../hooks/useRealtimeMetrics';
import { useHealth } from '../hooks/useHealth';

// API calls through service layer
import { apiService } from '../services/api';
```

### API Integration

```typescript
// Environment variables (set at build time)
VITE_API_BASE_URL=http://localhost:8003/api/v1
VITE_WS_URL=ws://localhost:8001/ws
VITE_ENVIRONMENT=production

// nginx.conf proxies /api to admin-api service
location /api {
    proxy_pass http://admin-api:8004;  # Internal Docker network
}
```

---

## 🐍 Backend Architecture Patterns

### Logging Pattern (CRITICAL - Use This!)

```python
# Import shared logging
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.logging_config import (
    setup_logging, log_with_context, log_error_with_context,
    performance_monitor, generate_correlation_id, set_correlation_id
)

# Setup logging for service
logger = setup_logging("my-service")

# Always use correlation IDs
corr_id = generate_correlation_id()
set_correlation_id(corr_id)

# Structured logging
log_with_context(
    logger, "INFO", "Processing event",
    operation="event_processing",
    correlation_id=corr_id,
    event_type="state_changed",
    entity_id="sensor.temperature"
)

# Error logging with context
try:
    process_event()
except Exception as e:
    log_error_with_context(
        logger, "Failed to process event", e,
        operation="event_processing",
        correlation_id=corr_id
    )

# Performance monitoring
@performance_monitor("database_query")
async def fetch_data():
    pass
```

### FastAPI Service Pattern

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from aiohttp import web  # For services using aiohttp

# Standard FastAPI structure
app = FastAPI(
    title="My Service",
    version="1.0.0",
    description="Service description"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoint (REQUIRED)
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "my-service",
        "timestamp": datetime.now().isoformat()
    }

# Startup/shutdown events
@app.on_event("startup")
async def on_startup():
    logger.info("Service starting...")
    
@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Service stopping...")
```

### InfluxDB Integration Pattern

```python
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Configuration from environment
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "ha-ingestor-token")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "ha-ingestor")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")

# Create client
client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

# Write data
point = Point("measurement_name") \
    .tag("entity_id", "sensor.temp") \
    .field("value", 23.5) \
    .time(datetime.utcnow())
    
write_api.write(bucket=INFLUXDB_BUCKET, record=point)
```

---

## 🧪 Testing Infrastructure

### Frontend Testing (Vitest)

```bash
cd domains/core-platform/health-dashboard

# Run unit tests
npm run test

# Run with UI
npm run test:ui

# Run with coverage
npm run test:coverage
```

**Test Files:** `src/components/__tests__/*.test.tsx`

### Backend Testing (pytest)

```bash
cd domains/core-platform/admin-api  # or any Python service

# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/test_health.py -v
```

### E2E Testing (Playwright)

```bash
cd domains/core-platform/health-dashboard

# Run E2E tests
npm run test:e2e

# Run with UI
npm run test:e2e:ui

# Run in headed mode (see browser)
npm run test:e2e:headed

# Debug mode
npm run test:e2e:debug
```

**Test Files:** `tests/*.spec.ts`

---

## 🐳 Docker Development

### Docker Compose Files

- `docker-compose.yml` - **Production** (use this by default)
- `docker-compose.dev.yml` - Development with hot reload
- `docker-compose.minimal.yml` - Core services only
- `docker-compose.simple.yml` - Simplified config

### Key Docker Commands

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d admin-api

# View logs
docker-compose logs -f admin-api

# Restart service
docker-compose restart admin-api

# Rebuild service
docker-compose build admin-api
docker-compose up -d admin-api

# Stop all
docker-compose down

# Clean everything
docker-compose down -v  # Remove volumes too
```

### Dockerfile Patterns

**Python Services** (Alpine-based):
```dockerfile
FROM python:3.11-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "-m", "src.main"]
```

**Frontend** (Multi-stage build):
```dockerfile
# Build stage
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

---

## 📝 Code Conventions

### Python Standards

```python
# File naming: snake_case.py
# main.py, health_check.py, influxdb_client.py

# Function naming: snake_case
def process_event():
    pass

# Class naming: PascalCase
class EventProcessor:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3

# Type hints required
def process_event(event_data: dict) -> bool:
    pass

# Docstrings (Google style)
def process_event(event_data: dict) -> bool:
    """
    Process a Home Assistant event.
    
    Args:
        event_data: Event data dictionary
        
    Returns:
        True if processing successful, False otherwise
    """
    pass
```

### TypeScript/React Standards

```typescript
// File naming: PascalCase.tsx for components, camelCase.ts for utilities
// Dashboard.tsx, useHealth.ts

// Component naming: PascalCase
export const Dashboard: React.FC = () => {
    return <div>Dashboard</div>;
};

// Hook naming: camelCase with 'use' prefix
export const useHealth = () => {
    const [health, setHealth] = useState<HealthStatus | null>(null);
    return { health };
};

// Function naming: camelCase
const fetchHealthData = async () => {
    // ...
};

// Constants: UPPER_SNAKE_CASE
const API_BASE_URL = 'http://localhost:8003/api/v1';

// Type naming: PascalCase
interface HealthStatus {
    status: string;
    timestamp: string;
}

type ServiceStatus = 'healthy' | 'degraded' | 'unhealthy';
```

### Import Order

**Python:**
```python
# 1. Standard library
import os
import sys
from datetime import datetime

# 2. Third-party
from fastapi import FastAPI
from pydantic import BaseModel

# 3. Local/shared
from shared.logging_config import setup_logging

# 4. Relative imports
from .health_check import HealthChecker
```

**TypeScript:**
```typescript
// 1. React/external libraries
import React, { useState, useEffect } from 'react';

// 2. Internal utilities
import { apiService } from '../services/api';

// 3. Components
import { Dashboard } from './components/Dashboard';

// 4. Types
import type { HealthStatus } from '../types';

// 5. Styles (if applicable)
import './App.css';
```

---

## 🔍 Common Patterns & Best Practices

### Environment Variables

```python
# Always provide defaults for non-critical vars
PORT = int(os.getenv('PORT', '8000'))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Never provide defaults for secrets
API_KEY = os.getenv('API_KEY')  # Will be None if not set
if not API_KEY:
    raise ValueError("API_KEY environment variable is required")
```

### Error Handling

```python
# Specific exceptions > generic
try:
    result = await fetch_data()
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
except TimeoutError as e:
    logger.error(f"Request timeout: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
```

### Async/Await Pattern

```python
# Python: Use async/await consistently
async def process_event(event_data: dict) -> bool:
    try:
        # Await all async calls
        result = await http_client.post('/events', json=event_data)
        return result.status == 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

# TypeScript: Use async/await for API calls
const fetchHealth = async (): Promise<HealthStatus> => {
    try {
        const response = await fetch('/api/v1/health');
        return await response.json();
    } catch (error) {
        console.error('Error fetching health:', error);
        throw error;
    }
};
```

---

## 🚨 Common Pitfalls & Solutions

### 1. Import Path Issues (Python)

**Problem:** Can't import from `shared/`

**Solution:**
```python
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.logging_config import setup_logging
```

### 2. CORS Errors (Frontend)

**Problem:** API calls blocked by CORS

**Solution:** Check `nginx.conf` in health-dashboard:
```nginx
location /api {
    proxy_pass http://admin-api:8004;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### 3. Container Can't Connect to Another Service

**Problem:** Service can't reach another service

**Solution:** Use Docker internal network names:
```python
# ✅ Correct
ENRICHMENT_URL = "http://enrichment-pipeline:8002"

# ❌ Wrong
ENRICHMENT_URL = "http://localhost:8002"
```

### 4. InfluxDB Connection Fails

**Problem:** Can't connect to InfluxDB

**Solution:**
```python
# Check these environment variables
INFLUXDB_URL = "http://influxdb:8086"  # Use internal Docker name
INFLUXDB_TOKEN = "ha-ingestor-token"    # Default token
INFLUXDB_ORG = "ha-ingestor"            # Default org
INFLUXDB_BUCKET = "home_assistant_events"  # Default bucket
```

### 5. Dockerfile Build Fails

**Problem:** Dockerfile won't build

**Solution:**
1. Check `docs/DOCKER_STRUCTURE_GUIDE.md` first
2. Verify all COPY paths exist
3. Check requirements.txt/package.json syntax
4. Use `docker-compose build --no-cache admin-api` to force rebuild

---

## 📚 Key Documentation Files

### Must-Read Before Modifying

1. **`docs/DOCKER_STRUCTURE_GUIDE.md`** - Docker configuration rules (CRITICAL)
2. **`docs/architecture/coding-standards.md`** - Code conventions
3. **`docs/architecture/tech-stack.md`** - Technology decisions
4. **`docs/architecture/source-tree.md`** - Project structure
5. **`README.md`** - Quick start and overview

### API References

1. **`docs/API_ENDPOINTS_REFERENCE.md`** - All API endpoints
2. **`docs/SERVICES_OVERVIEW.md`** - Service descriptions
3. **`docs/API_DOCUMENTATION.md`** - Complete API docs

### Deployment

1. **`docs/DEPLOYMENT_GUIDE.md`** - Production deployment
2. **`docs/DEPLOYMENT_WIZARD_GUIDE.md`** - Interactive setup
3. **`docs/SECURITY_CONFIGURATION.md`** - Security setup

---

## 🎯 Development Workflow

### Adding a New Feature

1. **Read relevant documentation** (architecture, coding standards)
2. **Identify affected services** (usually 1-3 services)
3. **Write tests first** (TDD approach preferred)
4. **Implement feature** following code conventions
5. **Update types** if needed (shared/types/ or frontend types)
6. **Test locally** with docker-compose
7. **Update documentation** (this is CRITICAL)
8. **Run full test suite** before committing

### Modifying Existing Code

1. **Understand current implementation** (read the code)
2. **Check for tests** (tests/ directory)
3. **Make changes** incrementally
4. **Update tests** to match changes
5. **Verify no regressions** (run test suite)
6. **Update documentation** if behavior changes

### Debugging

1. **Check logs** first: `docker-compose logs -f SERVICE_NAME`
2. **Check health endpoints**: `curl http://localhost:PORT/health`
3. **Verify environment variables**: Check `.env` files in `infrastructure/`
4. **Test service isolation**: Start only the failing service
5. **Check Docker network**: `docker network inspect ha-ingestor-network`

---

## 🔧 Agent-Specific Notes

### When Working on Frontend

- Always test in both light and dark mode
- Test mobile responsiveness (dashboard is mobile-first)
- Use existing components from `components/` before creating new ones
- Follow TailwindCSS conventions for styling
- Update Dashboard.tsx if adding new tabs

### When Working on Backend

- Always use shared logging with correlation IDs
- Include health check endpoint in every service
- Use FastAPI for new services (consistency)
- Add service to docker-compose.yml with health check
- Document new endpoints in API_ENDPOINTS_REFERENCE.md

### When Working on Data Flow

- Understand the flow: WebSocket → Enrichment → InfluxDB
- Test with ha-simulator service for HA events
- Validate data structure at each stage
- Add quality metrics (enrichment-pipeline has built-in framework)

### When Working on DevOps

- Read DOCKER_STRUCTURE_GUIDE.md FIRST
- Test with all docker-compose variants
- Verify Alpine compatibility (all images are Alpine-based)
- Check resource limits (defined in docker-compose.yml)
- Update infrastructure/ env files if adding new config

---

## 📞 Quick Help

**Can't find something?**
1. Check `docs/DOCUMENTATION_INDEX.md`
2. Search in `docs/` directory
3. Check service-specific README: `services/SERVICE_NAME/README.md`

**Service not working?**
1. Check logs: `docker-compose logs -f SERVICE_NAME`
2. Check health: `curl http://localhost:PORT/health`
3. Check troubleshooting: `docs/TROUBLESHOOTING_GUIDE.md`

**Need examples?**
1. Check `services/` for similar implementations
2. Check `tests/` for usage examples
3. Check `docs/stories/` for feature specifications

---

**Remember:** This is a production-ready system. Test thoroughly, document changes, and follow conventions!

