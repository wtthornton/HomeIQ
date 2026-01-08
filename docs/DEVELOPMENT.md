# HomeIQ Development Guide

This guide covers local development setup, AI-assisted development workflows, testing, and detailed architecture information for contributors and developers.

---

## 📑 Table of Contents

- [Development Environment Setup](#-development-environment-setup)
- [AI-Assisted Development with TappsCodingAgents](#-ai-assisted-development-with-tappscodingagents)
- [Running Services Locally](#-running-services-locally)
- [Testing](#-testing)
- [Detailed Architecture](#-detailed-architecture)
- [Service Reference](#-service-reference)
- [Code Quality Standards](#-code-quality-standards)

---

## 🛠️ Development Environment Setup

### Prerequisites

- **Python 3.12+** — Backend services
- **Node.js 20+** — Frontend applications
- **Docker & Docker Compose v2.0+** — Container orchestration
- **Git** — Version control

### Single-NUC Deployment Context

**Important:** HomeIQ is designed for a **single-home Home Assistant deployment on an Intel NUC** (i3/i5, 8-16GB RAM). This is not a multi-home or enterprise solution. All services run in Docker containers on the same host.

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/wtthornton/HomeIQ.git
cd HomeIQ

# Backend (Python services) - Development mode
cd services/ai-automation-service
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8018

# Frontend (React apps) - Development mode
# Build and run with Docker (recommended for consistency)
docker compose -f docker-compose.dev.yml up -d health-dashboard

# Or build locally
cd services/health-dashboard
npm install
npm run dev  # Development server with hot reload
```

### Docker Compose Variants

| File | Purpose |
|------|---------|
| `docker-compose.yml` | **Production** — All services |
| `docker-compose.minimal.yml` | Core services only |
| `docker-compose.dev.yml` | Development with hot reload |
| `docker-compose.simple.yml` | Basic setup for testing |

---

## 🤖 AI-Assisted Development with TappsCodingAgents

**HomeIQ uses TappsCodingAgents for enhanced code quality, testing, and development workflows.** AI assistants working on this project should **ALWAYS** use tapps-agents and Simple Mode commands to ensure high-quality code, comprehensive testing, and proper documentation.

### Quick Start with Simple Mode

**Simple Mode** provides natural language commands that automatically orchestrate multiple specialized agents:

```bash
# In Cursor chat, use @simple-mode for all development tasks:
@simple-mode *build "Create a new microservice for device monitoring"
@simple-mode *review services/websocket-ingestion/src/main.py
@simple-mode *fix services/data-api/src/main.py "Fix the database connection error"
@simple-mode *test services/ai-automation-service-new/src/main.py
@simple-mode *full "Build a complete REST API for automation management"
```

### Available TappsCodingAgents Commands

#### Code Quality & Review

```bash
# Quick quality score (fast, no LLM)
python -m tapps_agents.cli reviewer score services/websocket-ingestion/src/main.py

# Full code review with detailed feedback
python -m tapps_agents.cli reviewer review services/data-api/src/main.py

# Generate quality reports (JSON, Markdown, HTML)
python -m tapps_agents.cli reviewer report . json markdown html
```

#### Test Generation

```bash
# Generate comprehensive tests
python -m tapps_agents.cli tester test services/ai-automation-service-new/src/main.py

# Generate integration tests
python -m tapps_agents.cli tester generate-tests services/data-api/src/main.py --integration
```

#### Code Improvement

```bash
# Refactor and improve code
python -m tapps_agents.cli improver improve services/websocket-ingestion/src/main.py "Add type hints and improve error handling"

# Optimize performance
python -m tapps_agents.cli improver optimize services/data-api/src/main.py "Improve database query performance"
```

#### Feature Development

```bash
# Plan new features
python -m tapps_agents.cli planner plan "Add device health monitoring dashboard"

# Design architecture
python -m tapps_agents.cli architect design "Microservice architecture for device intelligence"

# Enhance prompts before implementation
python -m tapps_agents.cli enhancer enhance "Create REST API for automation suggestions"
```

### Why Use TappsCodingAgents?

1. **Quality Assurance**: Automatic code scoring (complexity, security, maintainability, test coverage, performance)
2. **Comprehensive Testing**: Automated test generation with coverage analysis
3. **Code Review**: LLM-powered code review with detailed feedback
4. **Expert Consultation**: Automatic consultation with domain experts (security, performance, testing, etc.)
5. **Workflow Orchestration**: Structured workflows ensure proper planning → design → implementation → testing → review
6. **Documentation**: Automatic documentation generation for APIs and code

### AI Assistant Guidelines

When working on HomeIQ, AI assistants should:

1. ✅ **Always use Simple Mode** (`@simple-mode`) for feature development, bug fixes, and code reviews
2. ✅ **Run code reviews** before committing: `@simple-mode *review {file}` or `python -m tapps_agents.cli reviewer review {file}`
3. ✅ **Generate tests** for all new code: `@simple-mode *test {file}` or `python -m tapps_agents.cli tester test {file}`
4. ✅ **Use enhancer** for complex features: `python -m tapps_agents.cli enhancer enhance "{description}"`
5. ✅ **Check quality scores** before finalizing code: `python -m tapps_agents.cli reviewer score {file}`
6. ✅ **Follow workflow patterns**: Use `*build`, `*review`, `*fix`, `*test` commands instead of direct implementation

### Configuration

- TappsCodingAgents is configured in `.tapps-agents/config.yaml`
- Simple Mode is **enabled** and ready to use
- Quality thresholds: 70+ overall score, 80+ for critical services
- Test coverage threshold: 80% minimum

### Related Documentation

- [Simple Mode Guide](.cursor/rules/simple-mode.mdc) — Complete Simple Mode documentation
- [Agent Capabilities](.cursor/rules/agent-capabilities.mdc) — All 13 workflow agents
- [TappsCodingAgents Documentation](https://github.com/wtthornton/TappsCodingAgents) — Framework documentation

---

## 🏃 Running Services Locally

### Running a Single Service

```bash
# Navigate to the service directory
cd services/[service-name]/src

# Run the main script
python main.py

# Or with environment variables
python -m dotenv run python main.py
```

### Development with Hot Reload

```bash
# FastAPI services with auto-reload
cd services/data-api/src
uvicorn main:app --reload --port 8006

# React apps with Vite
cd services/health-dashboard
npm run dev
```

---

## 🧪 Testing

### Current Status

Automated regression coverage is currently being rebuilt to match the new LangChain and PDL pipelines.

- ✅ **Current status**: The legacy multi-language test tree has been removed; no automated suites are available right now.
- 🚧 **Roadmap**: Focused smoke tests and regression checks will ship alongside the new workflows.
- 🔍 **Manual verification**: Use the Health Dashboard (`http://localhost:3000`) and AI Automation UI (`http://localhost:3001`) to validate critical flows after changes.
- 🧪 **Prototyping**: If you add new tests, stage them under the relevant service and wire them into fresh tooling instead of reviving the legacy structure.

### Using TappsCodingAgents for Testing

```bash
# Generate tests for a service
python -m tapps_agents.cli tester test services/data-api/src/main.py

# Generate integration tests
python -m tapps_agents.cli tester generate-tests services/data-api/src/main.py --integration

# Run existing tests
python -m tapps_agents.cli tester run-tests tests/unit/
```

---

## 🏗️ Detailed Architecture

### System Overview (Epic 31 Architecture — 30 Active Microservices)

**Note:** Plus InfluxDB infrastructure = 31 total containers in production

```
┌─────────────────────────────────────────────────────────────┐
│                        HomeIQ Stack                          │
│                  30 Active Microservices                     │
│              (+ InfluxDB = 31 total containers)              │
├─────────────────────────────────────────────────────────────┤
│  Web Layer (2 services)                                      │
│  ├─ Health Dashboard (React)            :3000 → nginx       │
│  └─ AI Automation UI (React)            :3001 → nginx       │
├─────────────────────────────────────────────────────────────┤
│  Core API Layer (3 services)                                │
│  ├─ WebSocket Ingestion                 :8001               │
│  │   └─ Infinite retry + circuit breaker                    │
│  ├─ Admin API                           :8003→8004          │
│  └─ Data API (SQLite + InfluxDB)        :8006               │
├─────────────────────────────────────────────────────────────┤
│  AI Services Layer (10 services)                            │
│  ├─ AI Automation Service               :8024→8018          │
│  │   └─ Pattern detection + conversational flow             │
│  ├─ HA AI Agent Service                 :8030               │
│  │   └─ Conversational AI automation creation               │
│  ├─ AI Core Service                     :8018               │
│  ├─ OpenVINO Service                    :8026→8019          │
│  ├─ ML Service                          :8025→8020          │
│  ├─ NER Service                         :8031 (internal)    │
│  ├─ OpenAI Service                      :8020               │
│  ├─ Device Intelligence Service         :8028→8019          │
│  ├─ Automation Miner                    :8029→8019          │
│  └─ Proactive Agent Service             :8031               │
│      └─ Context-aware automation suggestions                │
├─────────────────────────────────────────────────────────────┤
│  Data Layer (Hybrid Architecture)                           │
│  ├─ InfluxDB (Time-series)              :8086               │
│  │   └─ 365-day retention, ~150 flattened fields            │
│  └─ SQLite (5 Databases)                Files               │
│      ├─ metadata.db (devices, entities)                     │
│      ├─ ai_automation.db (11 tables)                        │
│      ├─ automation_miner.db (community corpus)              │
│      ├─ device_intelligence.db (7 tables)                   │
│      └─ ha_ai_agent.db (conversations, context cache)       │
├─────────────────────────────────────────────────────────────┤
│  Data Enrichment (5 active + 1 conditional)                 │
│  ├─ Weather API              :8009 → InfluxDB               │
│  ├─ Carbon Intensity         :8010 → InfluxDB               │
│  ├─ Electricity Pricing      :8011 → InfluxDB               │
│  ├─ Air Quality              :8012 → InfluxDB               │
│  ├─ Calendar Service         :8013 → InfluxDB (production)  │
│  └─ Smart Meter              :8014 → InfluxDB               │
├─────────────────────────────────────────────────────────────┤
│  Processing & Infrastructure (4 services)                   │
│  ├─ Data Retention                      :8080               │
│  ├─ Energy Correlator                   :8017               │
│  ├─ Log Aggregator                      :8015               │
│  └─ HA Setup Service                    :8027→8020          │
├─────────────────────────────────────────────────────────────┤
│  Device Intelligence (5 services)                           │
│  ├─ Device Health Monitor               :8019               │
│  ├─ Device Context Classifier           :8032               │
│  ├─ Device Setup Assistant              :8021               │
│  ├─ Device Database Client              :8022               │
│  └─ Device Recommender                  :8023               │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
                   ┌────────┴────────┐
                   │ Home Assistant  │
                   │ 192.168.1.86    │
                   │  :8123 / :1883  │
                   │  WebSocket API  │
                   └─────────────────┘
```

### AI Services Layer

| AI Service | Purpose | External Port | Internal Port | Status |
|------------|---------|---------------|---------------|--------|
| **OpenVINO Service** | Embeddings, re-ranking, classification | 8026 | 8019 | ✅ Active |
| **ML Service** | K-Means clustering, anomaly detection | 8025 | 8020 | ✅ Active |
| **NER Service** | Named Entity Recognition | Internal 8031 | Internal only | ✅ Active |
| **OpenAI Service** | GPT-4o-mini API client | 8020 | 8020 | ✅ Active |
| **AI Core Service** | Multi-model orchestration | 8018 | 8018 | ✅ Active |
| **AI Automation Service** | Pattern detection & automation | 8024 | 8018 | ✅ Active |
| **Device Intelligence** | Device capability discovery | 8028 | 8019 | ✅ Active |
| **Automation Miner** | Community automation mining | 8029 | 8019 | ✅ Active |
| **HA Setup Service** | HA setup recommendations | 8027 | 8020 | ✅ Active |

### Observability & Distributed Tracing

HomeIQ includes comprehensive observability using OpenTelemetry and Jaeger:

- **Jaeger UI**: http://localhost:16686 — View distributed traces across all services
- **Distributed Tracing**: Automatic instrumentation of FastAPI endpoints, HTTP requests, and database queries
- **Trace Context Propagation**: Correlation IDs propagated across service boundaries
- **Performance Monitoring**: Identify bottlenecks and latency issues across microservices

**Configuration:**
- Set `OTLP_ENDPOINT=http://jaeger:4317` in service environment variables (already configured in docker-compose.yml)
- Services gracefully degrade if Jaeger is unavailable (console exporter fallback)

---

## 📋 Service Reference

### Key Services

| Service | Purpose | External Port | Internal Port | Tech Stack |
|---------|---------|---------------|---------------|------------|
| **Health Dashboard** | System monitoring & management | 3000 | 80 | React, TypeScript, Vite |
| **AI Automation UI** | Conversational automation | 3001 | 80 | React, TypeScript |
| **WebSocket Ingestion** | Real-time HA event capture | 8001 | 8001 | Python, aiohttp, WebSocket |
| **AI Automation Service** | Pattern detection & AI | 8024 | 8018 | Python, FastAPI, OpenAI |
| **HA AI Agent Service** | Conversational AI automation | 8030 | 8030 | Python, FastAPI, OpenAI GPT-4o-mini |
| **Proactive Agent Service** | Context-aware suggestions | 8031 | 8031 | Python, FastAPI, APScheduler |
| **Data API** | Historical data queries | 8006 | 8006 | Python, FastAPI |
| **Admin API** | System control & config | 8003 | 8004 | Python, FastAPI |
| **Device Intelligence** | Device capability discovery | 8028 | 8019 | Python, FastAPI, MQTT |
| **Weather API** | Standalone weather service | 8009 | 8009 | Python, FastAPI |
| **InfluxDB** | Time-series database | 8086 | 8086 | InfluxDB 2.7 |

### Deprecated Services

| Service | Status | Notes |
|---------|--------|-------|
| **Enrichment Pipeline** | ❌ Deprecated (Epic 31) | Direct InfluxDB writes now |

---

## 📝 Code Quality Standards

### Quality Gates

All code MUST pass these quality gates:

- ✅ Overall quality score ≥ 70 (80+ for critical services)
- ✅ Security score ≥ 7.0/10
- ✅ Maintainability score ≥ 7.0/10
- ✅ Test coverage ≥ 80%

### Quick Commands

```bash
# Quick quality check (fast, no LLM)
python -m tapps_agents.cli reviewer score {file}

# Full code review with detailed feedback
python -m tapps_agents.cli reviewer review {file}

# Generate comprehensive tests
python -m tapps_agents.cli tester test {file}

# Generate quality reports
python -m tapps_agents.cli reviewer report . json markdown html
```

### Python Standards

- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Write docstrings for all public functions and classes
- Handle exceptions explicitly
- Use async/await for I/O operations

### TypeScript Standards

- Use TypeScript for all new code (strict mode enabled)
- Follow ESLint and Prettier configurations
- Use interfaces for object shapes
- Implement proper error boundaries in React components

---

## 📖 Related Documentation

- [Architecture Overview](ARCHITECTURE_OVERVIEW.md)
- [API Reference](api/API_REFERENCE.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md)
- [Services Architecture Quick Reference](../services/README_ARCHITECTURE_QUICK_REF.md)

---

## 📝 Recent Updates

- **Epic AI-24: Device Mapping Library Architecture** (January 2025) ✅
- **Epic AI-21: Proactive Conversational Agent Service** (December 2025) ✅
- **Security Audit & Quality Improvements** (December 2025)
- **LangChain integrations and PDL workflows** (November 2025)
- **Legacy tests removed** — New targeted coverage TBD

See the main [README](../README.md) for the full changelog.
