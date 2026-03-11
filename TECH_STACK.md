# HomeIQ Tech Stack

**Last Updated:** March 6, 2026
**Source of Truth:** Actual `requirements.txt`, `package.json`, and `Dockerfile` files in the codebase

---

## Languages

| Language | Version | Usage |
|----------|---------|-------|
| **Python** | 3.12 (primary), 3.11 (2 services) | Backend services (47 services) |
| **TypeScript** | 5.9.3 | Frontend (health-dashboard, ai-automation-ui) |
| **JavaScript** | ES2022+ | Frontend build tooling |

### Python 3.11 Services
- `automation-linter` — Streamlit UI dependency
- `observability-dashboard` — Streamlit dependency

---

## Backend Frameworks & Libraries

### Web Framework
| Library | Version Range | Notes |
|---------|--------------|-------|
| **FastAPI** | 0.115.0 – 0.124.0 | Primary API framework for all Python services |
| **Uvicorn** | 0.32.0 – 0.34.0 | ASGI server |
| **Starlette** | (via FastAPI) | Middleware, routing |

### Data Validation
| Library | Version Range | Notes |
|---------|--------------|-------|
| **Pydantic** | 2.5.0 – 2.12.4 | Data models, settings |
| **pydantic-settings** | 2.1.0 – 2.8.1 | Environment-based configuration |

### Database & Storage
| Library | Version Range | Notes |
|---------|--------------|-------|
| **SQLAlchemy** | 2.0.25 – 2.0.46 | ORM for PostgreSQL |
| **asyncpg** | 0.30.0+ | Async PostgreSQL driver |
| **psycopg** | 3.x | Sync PostgreSQL driver (Alembic) |
| **influxdb-client** | 1.38.0 – 1.48.0 | InfluxDB 2.x Python client |

### HTTP & Networking
| Library | Version Range | Notes |
|---------|--------------|-------|
| **httpx** | 0.27.0 – 0.28.1 | Async HTTP client (service-to-service) |
| **aiohttp** | 3.10.0 – 3.11.11 | WebSocket client (HA connection) |
| **websockets** | 12.0 – 14.2 | WebSocket protocol support |

### AI/ML
| Library | Version | Notes |
|---------|---------|-------|
| **sentence-transformers** | >=5.0.0,<6.0.0 | Embeddings (openvino-service, homeiq-memory) — **Epic 38 upgrade** |
| **transformers** | >=4.50.0,<5.0.0 | HuggingFace model loading — **Story 38.5 upgrade** |
| **torch** | >=2.5.0,<3.0.0 | PyTorch backend for ML models (CPU-only) |
| **scikit-learn** | 1.4.0 – 1.6.1 | Classical ML (clustering, anomaly detection) |
| **openai** | 1.30.0 – 1.61.0 | OpenAI GPT-4o-mini API client |
| **tiktoken** | 0.7.0 – 0.8.0 | Token counting for LLM calls |

> **Note:** OpenVINO was removed from `openvino-service` due to dependency conflicts. The service now uses sentence-transformers with PyTorch backend directly.

> **Note:** LangChain is NOT used anywhere in the codebase.

> **ML Pipeline Docs:** See [docs/architecture/ml-pipeline.md](docs/architecture/ml-pipeline.md) for version compatibility, rollback procedures, and upgrade history.

### Observability
| Library | Version Range | Notes |
|---------|--------------|-------|
| **opentelemetry-api** | 1.25.0 – 1.30.0 | Tracing API |
| **opentelemetry-sdk** | 1.25.0 – 1.30.0 | Tracing SDK |
| **opentelemetry-exporter-otlp** | 1.25.0 – 1.30.0 | OTLP export to Jaeger |
| **opentelemetry-instrumentation-fastapi** | (latest) | Auto-instrumentation |
| **structlog** | 24.1.0 – 24.4.0 | Structured logging |

### Other Key Libraries
| Library | Version Range | Notes |
|---------|--------------|-------|
| **tenacity** | 8.2.0 – 9.0.0 | Retry with backoff |
| **APScheduler** | 3.10.4 | Scheduled tasks |
| **beautifulsoup4** | 4.12.3 | HTML parsing (automation-miner) |
| **Jinja2** | 3.1.3 – 3.1.5 | YAML template rendering |
| **PyYAML** | 6.0.1 – 6.0.2 | YAML parsing/generation |
| **streamlit** | 1.38.0 – 1.42.0 | UI for automation-linter, observability-dashboard |

---

## Frontend

| Technology | Version | Notes |
|------------|---------|-------|
| **React** | 18.3.1 | UI library |
| **Vite** | 6.4.1 | Build tool and dev server |
| **TypeScript** | 5.9.3 | Type-safe development |
| **TailwindCSS** | 3.4.18 | Utility-first CSS framework |
| **Recharts** | 2.x | Charting library |
| **Lucide React** | (latest) | Icon library |

### Frontend Services
- **health-dashboard** (Port 3000) — React + Vite, served by Node
- **ai-automation-ui** (Port 3001) — React + Vite, served by nginx:alpine

---

## Infrastructure

### Container Runtime
| Technology | Version | Notes |
|------------|---------|-------|
| **Docker** | 27.x | Container engine |
| **Docker Compose** | v2.x | Multi-container orchestration |
| **Docker Buildx** | (bundled) | Parallel builds via `docker-bake.hcl` |

### Base Images
| Image | Usage |
|-------|-------|
| `python:3.12-alpine` | Primary backend (28+ services) |
| `python:3.12-slim` | Services needing glibc (13 services) |
| `python:3.11-slim` | Streamlit services (2 services) |
| `node:20.20.0-alpine` | Frontend build stage |
| `nginx:alpine` | Frontend production (ai-automation-ui) |

### Databases
| Database | Version | Purpose |
|----------|---------|---------|
| **InfluxDB** | 2.8.0 | Time-series data (events, metrics, sensor data) |
| **PostgreSQL** | 17 | Metadata (devices, entities, config) — single instance, schema-per-domain |

### Observability
| Tool | Version | Purpose |
|------|---------|---------|
| **Jaeger** | 2.15.0 | Distributed tracing UI |
| **OpenTelemetry** | (see libraries) | Trace collection and export |

---

## Shared Libraries (under `libs/`)

Five installable Python packages shared across services:

| Package | Purpose | Key Exports |
|---------|---------|-------------|
| **homeiq-patterns** | Reusable architecture patterns | `RAGContextService`, `UnifiedValidationRouter`, `PostActionVerifier` |
| **homeiq-resilience** | Cross-group fault tolerance | `CircuitBreaker`, `CrossGroupClient`, `GroupHealthCheck`, `wait_for_dependency` |
| **homeiq-observability** | Structured logging and tracing | `setup_logging`, `monitoring`, `metrics`, `tracing` |
| **homeiq-data** | Data access layer | InfluxDB client, database pool, caching, auth |
| **homeiq-ha** | Home Assistant integration | HA connection manager, automation lint engine |

### Installation Pattern (Dockerfiles)
```dockerfile
COPY libs/ /tmp/libs/
RUN pip install /tmp/libs/homeiq-*/
COPY requirements.txt .
RUN pip install -r requirements.txt
```

---

## CI/CD

| Tool | Purpose |
|------|---------|
| **GitHub Actions** | CI pipeline (build, test, lint) |
| **docker-bake.hcl** | Parallel Docker builds |
| **ruff** | Python linting and formatting |
| **pytest** | Python test framework |
| **pytest-asyncio** | Async test support |
| **Playwright** | E2E browser testing |

---

## Testing

| Framework | Version Range | Purpose |
|-----------|--------------|---------|
| **pytest** | 8.1.0 – 8.3.4 | Unit and integration tests |
| **pytest-asyncio** | 0.24.0 – 0.25.3 | Async test support |
| **pytest-cov** | 5.0.0 – 6.0.0 | Coverage reporting |
| **httpx** | (see above) | API testing via `AsyncClient` |
| **Playwright** | (latest) | E2E browser testing |

---

## Service Count

**50 deployable services** across 9 domain groups:

| # | Domain | Count | Notes |
|---|--------|-------|-------|
| 1 | core-platform | 6 | Includes InfluxDB |
| 2 | data-collectors | 8 | Stateless external API fetchers |
| 3 | ml-engine | 9 | Includes ner-service and openai-service (built from archive) |
| 4 | automation-core | 7 | Core automation engine |
| 5 | blueprints | 4 | Blueprint discovery and suggestions |
| 6 | energy-analytics | 3 | Energy intelligence |
| 7 | device-management | 8 | Device lifecycle |
| 8 | pattern-analysis | 2 | Behavioral pattern detection |
| 9 | frontends | 3 | UIs (ai-automation-ui, observability-dashboard, health-dashboard) |
| — | infrastructure | — | Jaeger (in frontends compose), InfluxDB (in core-platform compose) |

> **Note:** `ha-simulator` is available under the `development` Docker Compose profile. `nlp-fine-tuning` and `model-prep` are offline/one-shot training tools, not deployed services.

---

## Port Reference (Source of Truth: `docker compose config`)

| Port | Service | Domain |
|------|---------|--------|
| 3000 | health-dashboard | core-platform |
| 3001 | ai-automation-ui | frontends |
| 4317 | jaeger (OTLP gRPC) | frontends |
| 4318 | jaeger (OTLP HTTP) | frontends |
| 8001 | websocket-ingestion | core-platform |
| 8004 | admin-api | core-platform |
| 8005 | sports-api | data-collectors |
| 8006 | data-api | core-platform |
| 8009 | weather-api | data-collectors |
| 8010 | carbon-intensity-service | data-collectors |
| 8011 | electricity-pricing-service | data-collectors |
| 8012 | air-quality-service | data-collectors |
| 8013 | calendar-service | data-collectors |
| 8014 | smart-meter-service | data-collectors |
| 8015 | log-aggregator | data-collectors |
| 8016 | automation-linter | automation-core |
| 8017 | energy-correlator | energy-analytics |
| 8018 | ai-core-service | ml-engine |
| 8019 | device-health-monitor | device-management |
| 8020 | openai-service | ml-engine |
| 8021 | device-setup-assistant | device-management |
| 8022 | device-database-client | device-management |
| 8023 | device-recommender | device-management |
| 8024 | ha-setup-service | device-management |
| 8025 | ml-service | ml-engine |
| 8026 | openvino-service | ml-engine |
| 8027 | rag-service | ml-engine |
| 8028 | device-intelligence-service | ml-engine |
| 8029 | automation-miner | blueprints |
| 8030 | ha-ai-agent-service | automation-core |
| 8031 | proactive-agent-service | energy-analytics |
| 8032 | device-context-classifier | device-management |
| 8033 | ai-training-service | ml-engine |
| 8034 | ai-pattern-service | pattern-analysis |
| 8035 | ai-query-service | automation-core |
| 8036 | ai-automation-service-new | automation-core |
| 8037 | yaml-validation-service | automation-core |
| 8038 | blueprint-index | blueprints |
| 8039 | blueprint-suggestion-service | blueprints |
| 8040 | rule-recommendation-ml | blueprints |
| 8041 | api-automation-edge | pattern-analysis |
| 8042 | energy-forecasting | energy-analytics |
| 8043 | activity-recognition | device-management |
| 8044 | automation-trace-service | automation-core |
| 8045 | activity-writer | device-management |
| 8046 | ha-device-control | automation-core |
| 8047 | voice-gateway | frontends |
| 8080 | data-retention | core-platform |
| 8086 | InfluxDB | core-platform |
| 8501 | observability-dashboard | frontends |
| 16686 | jaeger (UI) | frontends |

Internal-only services (no published host port): `ner-service`, `ai-code-executor`

---

## Tech stack by service (simple)

| Domain | Service | Language | Runtime / framework | Key stack |
|--------|---------|----------|--------------------|-----------|
| **core-platform** | influxdb | — | Container | InfluxDB 2.8 |
| | postgres | — | Container | PostgreSQL 17 |
| | data-api | Python 3.12 | FastAPI + Uvicorn | InfluxDB client, SQLAlchemy, asyncpg, Pydantic |
| | websocket-ingestion | Python 3.12 | FastAPI + Uvicorn | aiohttp, websockets, InfluxDB client |
| | admin-api | Python 3.12 | FastAPI + Uvicorn | Docker API, JWT, InfluxDB |
| | health-dashboard | TypeScript 5.9 | React 19 + Vite 7 | Tailwind 4, Radix UI, Chart.js, Recharts |
| | data-retention | Python 3.12 | FastAPI + Uvicorn | InfluxDB client |
| | ha-simulator | Python 3.12 | (dev profile) | HA WebSocket simulator |
| | prometheus / grafana / postgres-exporter | — | Container | Prometheus, Grafana 11, postgres-exporter |
| **frontends** | jaeger | — | Container | Jaeger 2.15 |
| | observability-dashboard | Python 3.11 | Streamlit | Pandas, Plotly, httpx |
| | ai-automation-ui | TypeScript 5.9 | React 19 + Vite 7 | Tailwind 4, TanStack Query, Zustand, Framer Motion |
| | voice-gateway | Python 3.12 | FastAPI + Uvicorn | faster-whisper (STT), kokoro (TTS), websockets |
| **data-collectors** | weather-api | Python 3.12 | FastAPI + Uvicorn | InfluxDB client |
| | smart-meter | Python 3.12 | FastAPI + Uvicorn | HA client, InfluxDB client |
| | sports-api | Python 3.12 | FastAPI + Uvicorn | HA client, InfluxDB client |
| | air-quality | Python 3.12 | FastAPI + Uvicorn | OpenWeatherMap, InfluxDB client |
| | carbon-intensity | Python 3.12 | FastAPI + Uvicorn | WattTime, InfluxDB client |
| | electricity-pricing | Python 3.12 | FastAPI + Uvicorn | aWattar, InfluxDB client |
| | calendar | Python 3.12 | FastAPI + Uvicorn | HA client, InfluxDB client |
| | log-aggregator | Python 3.12 | FastAPI + Uvicorn | Docker API, log aggregation |
| **automation-core** | ha-ai-agent-service | Python 3.12 | FastAPI + Uvicorn | OpenAI, SQLAlchemy, asyncpg, data-api |
| | ai-automation-service-new | Python 3.12 | FastAPI + Uvicorn | OpenAI, SQLAlchemy, asyncpg, PyYAML |
| | ai-query-service | Python 3.12 | FastAPI + Uvicorn | OpenAI, SQLAlchemy, asyncpg, data-api |
| | yaml-validation-service | Python 3.12 | FastAPI + Uvicorn | data-api, HA client |
| | automation-linter | Python 3.11 | FastAPI + Uvicorn | Streamlit UI, homeiq-ha lint |
| | ai-code-executor | Python 3.12 | FastAPI + Uvicorn | Sandboxed execution |
| | automation-trace-service | Python 3.12 | FastAPI + Uvicorn | HA WebSocket, InfluxDB, data-api |
| | ha-device-control | Python 3.12 | FastAPI + Uvicorn | HA REST API |
| **ml-engine** | openvino-service | Python 3.12 | FastAPI + Uvicorn | sentence-transformers, PyTorch |
| | ml-service | Python 3.12 | FastAPI + Uvicorn | ML inference |
| | ner-service | Python 3.12 | FastAPI + Uvicorn | NER models |
| | openai-service | Python 3.12 | FastAPI + Uvicorn | OpenAI API proxy |
| | rag-service | Python 3.12 | FastAPI + Uvicorn | Embeddings, vector search |
| | ai-core-service | Python 3.12 | FastAPI + Uvicorn | httpx, tenacity |
| | ai-training-service | Python 3.12 | FastAPI + Uvicorn | Training pipeline |
| | device-intelligence-service | Python 3.12 | FastAPI + Uvicorn | Device ML |
| | model-prep / nlp-fine-tuning | Python 3.12 | CLI / batch | Offline model prep |
| **blueprints** | blueprint-index | Python 3.12 | FastAPI + Uvicorn | PostgreSQL, asyncpg, GitHub |
| | blueprint-suggestion-service | Python 3.12 | FastAPI + Uvicorn | PostgreSQL, data-api, pattern service |
| | rule-recommendation-ml | Python 3.12 | FastAPI + Uvicorn | ML recommendations |
| | automation-miner | Python 3.12 | FastAPI + Uvicorn | BeautifulSoup, blueprint mining |
| **pattern-analysis** | ai-pattern-service | Python 3.12 | FastAPI + Uvicorn | PostgreSQL, data-api, device-intelligence |
| | api-automation-edge | Python 3.12 | FastAPI + Uvicorn | Huey (task queue), PostgreSQL, InfluxDB, WebSockets |
| **energy-analytics** | energy-correlator | Python 3.12 | FastAPI + Uvicorn | InfluxDB client |
| | energy-forecasting | Python 3.12 | FastAPI + Uvicorn | InfluxDB, data-api, ML models |
| | proactive-agent-service | Python 3.12 | FastAPI + Uvicorn | Energy analytics, agents |
| **device-management** | device-health-monitor | Python 3.12 | FastAPI + Uvicorn | HA client |
| | device-context-classifier | Python 3.12 | FastAPI + Uvicorn | HA client, classification |
| | device-setup-assistant | Python 3.12 | FastAPI + Uvicorn | HA, device onboarding |
| | device-database-client | Python 3.12 | FastAPI + Uvicorn | PostgreSQL, device metadata |
| | device-recommender | Python 3.12 | FastAPI + Uvicorn | Recommendations |
| | ha-setup-service | Python 3.12 | FastAPI + Uvicorn | HA setup |
| | activity-recognition | Python 3.12 | FastAPI + Uvicorn | Activity ML |
| | activity-writer | Python 3.12 | FastAPI + Uvicorn | InfluxDB writer |
