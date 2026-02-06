# HomeIQ Technology Stack

**Last Updated:** February 6, 2026
**Version:** 2.0.0 (Post Phase 2 Library Upgrades)

---

## Overview

HomeIQ is built as a microservices architecture with 40+ Docker containers, designed for single-home deployment on resource-constrained hardware (Intel NUC).

---

## Core Technologies

### Runtime Environment

| Component | Version | Notes |
|-----------|---------|-------|
| **Python** | 3.12+ | Primary backend language |
| **Node.js** | 22.x LTS | Frontend builds |
| **Docker** | 24.x+ | Container runtime |
| **Docker Compose** | 2.x+ | Container orchestration |

### Web Frameworks

| Framework | Version | Usage |
|-----------|---------|-------|
| **FastAPI** | 0.128.x | Primary API framework (all Python services) |
| **Uvicorn** | 0.40.x | ASGI server with standard extras |
| **React** | 18.x | Frontend UI framework |
| **Vite** | 6.x | Frontend build tool |

### Data Validation & Serialization

| Library | Version | Notes |
|---------|---------|-------|
| **Pydantic** | 2.12.5 | Data validation and settings |
| **pydantic-settings** | 2.12.x | Configuration management |

### Databases

| Database | Version | Usage |
|----------|---------|-------|
| **InfluxDB** | 2.7+ | Time-series data (events, metrics) |
| **SQLite** | 3.x | Metadata storage (via SQLAlchemy) |

### Database Libraries

| Library | Version | Notes |
|---------|---------|-------|
| **SQLAlchemy** | 2.0.46 | SQL toolkit and async ORM |
| **aiosqlite** | 0.22.1 | Async SQLite driver |
| **Alembic** | 1.17.x | Database migrations |
| **influxdb3-python** | 0.17.0 | InfluxDB 3.0 client (Phase 2) |

---

## HTTP & Networking

### HTTP Clients

| Library | Version | Notes |
|---------|---------|-------|
| **httpx** | 0.28.1 | Async HTTP client (primary) |
| **aiohttp** | 3.13.3 | Async HTTP client/server |
| **tenacity** | 9.1.2 | Retry logic with exponential backoff |

### WebSocket & MQTT

| Library | Version | Notes |
|---------|---------|-------|
| **websockets** | 12.x | WebSocket client/server |
| **aiomqtt** | 2.4.0 | Async MQTT client (Phase 2 migration from asyncio-mqtt) |
| **paho-mqtt** | 1.6.x | Synchronous MQTT client |

### Proxy & Load Balancing

| Component | Version | Usage |
|-----------|---------|-------|
| **nginx** | 1.27.x | Reverse proxy for UI containers |

---

## AI & Machine Learning

### AI Frameworks

| Library | Version | Usage |
|---------|---------|-------|
| **OpenAI API** | Latest | GPT-4o-mini for NL automation |
| **LangChain** | 0.3.x | AI orchestration and chains |
| **OpenVINO** | 2024.x | Local ML inference optimization |

### ML Libraries

| Library | Version | Usage |
|---------|---------|-------|
| **scikit-learn** | 1.6.x | Pattern detection, classification |
| **numpy** | 2.x | Numerical computing |
| **polars** | 1.x | High-performance DataFrames |
| **darts** | 0.30.x | Time-series forecasting |

---

## Frontend Stack

### Core

| Technology | Version | Notes |
|------------|---------|-------|
| **React** | 18.x | UI framework |
| **TypeScript** | 5.x | Type-safe JavaScript |
| **Vite** | 6.x | Build tool and dev server |
| **TailwindCSS** | 4.x | Utility-first CSS |

### UI Components

| Library | Version | Usage |
|---------|---------|-------|
| **Recharts** | 2.x | Data visualization charts |
| **Lucide React** | Latest | Icon library |
| **React Router** | 6.x | Client-side routing |

---

## Testing

### Python Testing

| Library | Version | Notes |
|---------|---------|-------|
| **pytest** | 9.0.2 | Testing framework |
| **pytest-asyncio** | 1.3.0 | Async test support (Phase 2) |
| **pytest-cov** | 5.x | Coverage reporting |

### Frontend Testing

| Library | Version | Notes |
|---------|---------|-------|
| **Vitest** | 2.x | Unit testing |
| **Testing Library** | 14.x | React component testing |
| **MSW** | 2.x | API mocking |

---

## Observability

### OpenTelemetry Stack

| Component | Version | Usage |
|-----------|---------|-------|
| **opentelemetry-api** | 1.24.x | Telemetry API |
| **opentelemetry-sdk** | 1.24.x | SDK implementation |
| **opentelemetry-instrumentation-fastapi** | 0.45b | FastAPI auto-instrumentation |
| **opentelemetry-exporter-otlp** | 1.24.x | OTLP export |

### Monitoring

| Tool | Usage |
|------|-------|
| **Streamlit** | Observability dashboard |
| **Custom Health Endpoints** | Per-service health checks |

---

## Configuration & Security

### Configuration

| Library | Version | Notes |
|---------|---------|-------|
| **python-dotenv** | 1.2.1 | Environment variable loading |
| **pydantic-settings** | 2.12.x | Settings management |

### Security

| Feature | Implementation |
|---------|----------------|
| **API Authentication** | Bearer token (API_KEY) |
| **CSRF Protection** | Token + cookie validation |
| **Security Headers** | X-Frame-Options, CSP, etc. |
| **Rate Limiting** | Per-IP rate limits |

---

## DevOps & Infrastructure

### Container Build

| Tool | Version | Usage |
|------|---------|-------|
| **Docker BuildKit** | Latest | Multi-stage builds |
| **Python base images** | 3.12-slim | Minimal container footprint |

### CI/CD

| Tool | Usage |
|------|-------|
| **GitHub Actions** | CI/CD pipelines |
| **Docker Compose** | Local orchestration |

---

## Service Port Mapping

### Frontend Services

| Service | External Port | Internal Port |
|---------|---------------|---------------|
| health-dashboard | 3000 | 80 |
| ai-automation-ui | 3001 | 80 |
| observability-dashboard | 8501 | 8501 |

### Core Backend Services

| Service | External Port | Internal Port |
|---------|---------------|---------------|
| admin-api | 8004 | 8004 |
| data-api | 8006 | 8006 |
| websocket-ingestion | 8001 | 8001 |
| ai-automation-service-new | 8036 | 8025 |

### Data Services

| Service | External Port | Internal Port |
|---------|---------------|---------------|
| weather-api | 8009 | 8009 |
| sports-api | 8010 | 8010 |
| calendar-service | 8011 | 8011 |
| air-quality-service | 8012 | 8012 |
| carbon-intensity-service | 8013 | 8013 |
| electricity-pricing-service | 8014 | 8014 |
| smart-meter-service | 8016 | 8016 |

### AI Services

| Service | External Port | Internal Port |
|---------|---------------|---------------|
| ai-core-service | 8017 | 8017 |
| openvino-service | 8019 | 8019 |
| rag-service | 8027 | 8027 |
| ai-pattern-service | 8028 | 8028 |

### Infrastructure

| Service | External Port | Internal Port |
|---------|---------------|---------------|
| InfluxDB | 8086 | 8086 |
| InfluxDB (gRPC) | 8087 | 8087 |

---

## Memory Allocation (Docker)

| Tier | Memory Limit | Services |
|------|--------------|----------|
| **High** | 768M | openvino-service |
| **Medium-High** | 512M | ner-service |
| **Medium** | 384M | InfluxDB, ha-test-container |
| **Standard** | 256M | data-api, ML services (7 services) |
| **Light** | 192M | AI orchestrators (6 services) |
| **Minimal** | 128M | Most microservices (33 services) |
| **UI** | 64M | Frontend containers (2 services) |

**Total Estimated Memory:** ~8-10 GB for full stack

---

## Phase 2 Library Upgrades (February 2026)

### Breaking Changes Migrated

| Library | Old Version | New Version | Breaking Change |
|---------|-------------|-------------|-----------------|
| pytest-asyncio | 0.x | 1.3.0 | `loop_scope` parameter required |
| tenacity | 8.x | 9.1.2 | `retry_if_exception_cause_type()` API |
| asyncio-mqtt | 0.x | aiomqtt 2.4.0 | Package renamed, API changes |
| influxdb-client | 1.x | influxdb3-python 0.17.0 | New client class, SQL queries |
| python-dotenv | 1.0.x | 1.2.1 | Minor API updates |

### Migration Status

- **31/31 Python services** migrated (100% success rate)
- **41/41 Docker images** rebuilt
- **Memory optimized** ~5-6 GB savings

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-06 | 2.0.0 | Phase 2 library upgrades complete, Pydantic 2.12 compatibility fixes |
| 2026-02-05 | 1.9.0 | Phase 2 breaking changes migration |
| 2026-02-04 | 1.8.0 | Phase 1 critical compatibility fixes |
| 2026-01-xx | 1.7.0 | Initial Phase 1 library upgrades |

---

## References

- [Phase 2 Final Summary](docs/planning/phase2-final-summary.md)
- [Library Upgrade Plan](docs/planning/library-upgrade-plan.md)
- [API Reference](docs/api/API_REFERENCE.md)
- [Development Guide](docs/DEVELOPMENT.md)
