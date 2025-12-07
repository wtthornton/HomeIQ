# 🏠 HomeIQ

<div align="center">

**AI-Powered Home Automation Intelligence Platform**

Transform your Home Assistant into an intelligent automation powerhouse with conversational AI, pattern detection, and advanced analytics.

[![Production Ready](https://img.shields.io/badge/Status-Production%20Ready-brightgreen?style=for-the-badge)](#)
[![License](https://img.shields.io/badge/License-ISC-blue?style=for-the-badge)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Compatible-41BDF5?style=for-the-badge&logo=home-assistant)](https://www.home-assistant.io/)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

[Features](#-key-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Architecture](#-architecture) • [Contributing](#-contributing)

</div>

---

## 📑 Table of Contents

- [What is HomeIQ?](#-what-is-homeiq)
- [Key Features](#-key-features)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Documentation](#-documentation)
- [Configuration](#-configuration)
- [Development](#-development)
- [Screenshots](#-screenshots)
- [Project Stats](#-project-stats)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)
- [Support](#-support)

---

## 🎯 What is HomeIQ?

**HomeIQ is a single-home Home Assistant intelligence application running on an Intel NUC.** Designed specifically for a single-home deployment on resource-constrained NUC hardware (i3/i5, 8-16GB RAM), it adds:

- 🤖 **Conversational AI Automation** - Create automations by chatting, no YAML required
- 🔍 **Smart Pattern Detection** - AI discovers automation opportunities from your usage patterns
- 📊 **Advanced Analytics** - Deep insights with hybrid database architecture (5-10x faster queries)
- 🔌 **Multi-Source Enrichment** - Combines weather, energy pricing, air quality, sports, and more
- 🎨 **Beautiful Dashboards** - Real-time system health and interactive dependency visualization
- 🚀 **RESTful APIs** - Comprehensive API access to all data and AI capabilities
- 🐳 **Containerized AI Services** - Distributed AI models with microservices architecture

### Why HomeIQ?

**Traditional Home Assistant:**
```yaml
# Complex YAML configuration
alias: "Evening Routine"
trigger:
  - platform: sun
    event: sunset
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
```

**With HomeIQ:**
```
You: "Turn on living room lights at sunset"
HomeIQ: ✓ Created automation. Want to add conditions or additional actions?
```

---

## ✨ Key Features

### 🤖 AI-Powered Automation

- **Ask AI Tab**: Natural language automation creation, now with optional LangChain prompt templating
- **Pattern Mining**: AI analyzes your usage and suggests automations
- **Synergy Detection**: Multi-type synergy detection (device pairs, weather, energy, events) with optional PDL-governed guardrails
- **Device Validation**: Intelligent device compatibility checking with post-refinement sanitization
- **Device Selection & Mapping**: Check/uncheck devices and customize entity mappings with visual interface
- **Smart Recommendations**: Context-aware automation suggestions with priority scoring
- **Self-Healing YAML**: Automatic entity ID correction during refinement
- **Configurable Fallbacks**: Tune guardrail models and soft prompt thresholds directly from the Settings UI (persisted server-side)
- **Device-Specific Templates**: Pre-built automation templates for common device types (fridge, car, 3D printer, thermostat)
- **Proactive Agent Service**: Context-aware automation suggestions based on weather, sports, energy, and historical patterns

### 🏠 Device Intelligence & Database

- **Device Health Monitoring**: Real-time health analysis with battery levels, response times, and maintenance alerts
- **Device Classification**: Automatic device type inference (fridge, car, light, sensor, etc.) from entity patterns
- **Power Consumption Intelligence**: Compare actual vs. expected power usage with anomaly detection
- **Device Setup Assistant**: Step-by-step setup guides and issue detection for new devices
- **Capability Discovery**: Infer device capabilities from Home Assistant API (HA API-only, no direct protocol access)
- **Device Recommendations**: Get device recommendations based on requirements and compare similar devices
- **Device Database Integration**: Optional integration with external Device Database for enriched metadata
- **Device Mapping Library (Epic AI-24)**: Plugin-based architecture for device-specific intelligence
  - Automatic device type detection (Hue Room groups, WLED master/segments)
  - Device relationship mapping (segments to masters, groups to members)
  - Hot-reloadable handlers without service restart
  - Add new device handlers in < 1 hour without core code changes

### 📊 Single-Home Analytics

- **Hybrid Database**: InfluxDB (time-series) + SQLite (metadata)
- **5-10x Faster Queries**: Optimized for single-home scale (~50-100 devices)
- **Real-Time Metrics**: Live system health monitoring
- **Historical Analysis**: Deep dive into past events and patterns
- **NUC-Optimized**: Lightweight, resource-efficient for Intel NUC deployment

### 🌐 Rich Data Enrichment

- ☁️ **Weather**: OpenWeatherMap API integration with forecasts (standalone service)
- ⚡ **Energy Pricing**: Awattar API for dynamic electricity cost tracking
- 🌬️ **Air Quality**: AirNow API for AQI monitoring and alerts
- 🏈 **Sports**: ESPN API for NFL/NHL live game tracking
- 🌍 **Carbon Intensity**: WattTime API for grid carbon footprint awareness
- 📅 **Calendar**: Home Assistant calendar integration (optional, currently disabled)
- ⚡ **Smart Meter**: SMETS2/P1 protocol support for energy consumption data

### 🎨 Modern UI/UX

- **Health Dashboard** (localhost:3000): System monitoring with dependency graphs
- **AI Automation UI** (localhost:3001): Conversational automation interface
- **Interactive Visualizations**: Click-to-explore architecture diagrams
- **Dark Mode**: Beautiful, eye-friendly design
- **Responsive Design**: Mobile-friendly with touch gestures

---

## 🚀 Quick Start

### Prerequisites

**⚠️ Deployment Context: Single-Home Home Assistant on Intel NUC**

**HomeIQ is designed exclusively for a single-home Home Assistant deployment running on an Intel NUC.** This is not a multi-home or enterprise solution.

**Required:**
- **Home Assistant** instance running on local network (e.g., `192.168.1.86:8123`)
  - Single-home deployment (~50-100 devices)
  - Running on the same NUC or accessible via local network
- **Intel NUC** (recommended: i3/i5, 8-16GB RAM) or similar small form factor PC
  - **8GB RAM minimum** (16GB recommended for full stack)
  - **20GB+ free disk space** (for InfluxDB data retention)
  - **Single-home deployment** - optimized for one home, not multi-home
- **Docker** & **Docker Compose** (Docker Compose v2.0+)
- **Network access** to Home Assistant instance
- **Node.js 20+** (for development only)
- **Python 3.12+** (for development only)

**Important:** This application is optimized for a single-home Home Assistant deployment on resource-constrained NUC hardware. It is **not designed for multi-home or enterprise-scale deployments**. All services run on a single NUC, and the architecture is optimized for this use case.

### Installation

```bash
# Clone the repository
git clone https://github.com/wtthornton/HomeIQ.git
cd HomeIQ

# Copy environment template
cp infrastructure/env.example infrastructure/.env

# Configure your Home Assistant connection
# Edit infrastructure/.env and add:
# - HA_HTTP_URL=http://192.168.1.86:8123  # Your HA instance IP
# - HA_WS_URL=ws://192.168.1.86:8123/api/websocket  # WebSocket URL
# - HA_TOKEN=your-long-lived-access-token  # From HA Profile → Long-Lived Access Tokens

# Start all services
docker compose up -d

# Verify deployment
./scripts/verify-deployment.sh
```

### First Steps

1. **Open Health Dashboard**: http://localhost:3000
   - View system health
   - Check all integrations
   - Explore dependency graph

2. **Try AI Automation**: http://localhost:3001
   - Click "Ask AI" tab
   - Type: "Turn on lights when I arrive home"
   - Review and deploy the automation

3. **Configure AI Settings**: http://localhost:3001/settings
   - Enable/disable guardrails and soft prompt fallback
   - Point to your local model directory and tweak thresholds
   - Save changes directly to the backend (no redeploy required)

4. **Launch Training Runs (Optional)**: http://localhost:3001/admin
   - Start a soft prompt fine-tuning job with one click
   - Track status, sample counts, and loss in the training history table

5. **Explore APIs**: http://localhost:8003/docs
   - Interactive API documentation
   - Test endpoints
   - View real-time data

### How to Run

To run a specific service's `main.py` script:

```bash
# Navigate to the service directory
cd services/[service-name]/src

# Run the main script
python main.py

# Or with environment variables
python -m dotenv run python main.py
```

### How to Test

Automated regression coverage is currently being rebuilt to match the new LangChain and PDL pipelines.

- ✅ **Current status**: The legacy multi-language test tree has been removed; no automated suites are available right now.
- 🚧 **Roadmap**: Focused smoke tests and regression checks will ship alongside the new workflows.
- 🔍 **Manual verification**: Use the Health Dashboard (`http://localhost:3000`) and AI Automation UI (`http://localhost:3001`) to validate critical flows after changes.
- 🧪 **Prototyping**: If you add new tests, stage them under the relevant service and wire them into fresh tooling instead of reviving the legacy structure.

---

## 🏗️ Architecture

### System Overview (Epic 31 Architecture - 30 Active Microservices)

**Note:** Plus InfluxDB infrastructure = 31 total containers in production

**New Services:**
- **Proactive Agent Service** (Port 8031) - Context-aware automation suggestions (Epic AI-21) ✅
- Device Health Monitor (Port 8019)
- Device Context Classifier (Port 8032)
- Device Setup Assistant (Port 8021)
- Device Database Client (Port 8022)
- Device Recommender (Port 8023)

```
┌─────────────────────────────────────────────────────────────┐
│                        HomeIQ Stack                          │
│                  31 Active Microservices                     │
│              (+ InfluxDB = 32 total containers)              │
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
│  │   └─ Conversational AI automation creation (Epic AI-20)   │
│  ├─ AI Core Service                     :8018               │
│  ├─ OpenVINO Service                    :8026→8019          │
│  ├─ ML Service                          :8025→8020          │
│  ├─ NER Service                         :8031               │
│  ├─ OpenAI Service                      :8020               │
│  ├─ Device Intelligence Service         :8028→8019          │
│  ├─ Automation Miner                    :8029→8019          │
│  └─ Proactive Agent Service             :8031               │
│      └─ Context-aware automation suggestions (Epic AI-21)   │
├─────────────────────────────────────────────────────────────┤
│  Data Layer (Hybrid Architecture)                           │
│  ├─ InfluxDB (Time-series)              :8086               │
│  │   └─ 365-day retention, ~150 flattened fields            │
│  └─ SQLite (5 Databases)                Files               │
│      ├─ metadata.db (devices, entities)                     │
│      ├─ ai_automation.db (11 tables)                        │
│      ├─ automation_miner.db (community corpus)              │
│      ├─ device_intelligence.db (7 tables)                   │
│      ├─ ha_ai_agent.db (conversations, context cache)       │
│      └─ webhooks.db                                         │
├─────────────────────────────────────────────────────────────┤
│  Data Enrichment (5 active + 1 disabled - Epic 31 Direct)   │
│  ├─ Weather API              :8009 → InfluxDB               │
│  ├─ Carbon Intensity         :8010 → InfluxDB               │
│  ├─ Electricity Pricing      :8011 → InfluxDB               │
│  ├─ Air Quality              :8012 → InfluxDB               │
│  ├─ Calendar Service ⏸️      :8013 → InfluxDB (disabled)    │
│  └─ Smart Meter              :8014 → InfluxDB               │
├─────────────────────────────────────────────────────────────┤
│  Processing & Infrastructure (4 services)                   │
│  ├─ Data Retention                      :8080               │
│  ├─ Energy Correlator                   :8017               │
│  ├─ Log Aggregator                      :8015               │
│  └─ HA Setup Service                    :8027→8020          │
├─────────────────────────────────────────────────────────────┤
│  Device Intelligence (5 services - NEW)                     │
│  ├─ Device Health Monitor               :8019               │
│  ├─ Device Context Classifier           :8032               │
│  ├─ Device Setup Assistant              :8021               │
│  ├─ Device Database Client              :8022               │
│  └─ Device Recommender                  :8023               │
├─────────────────────────────────────────────────────────────┤
│  Dev/External (not HomeIQ services)                         │
│  ├─ HA Simulator (dev only)             :8123 (not deployed)│
│  ├─ MQTT Broker (external)     mqtt://192.168.1.86:1883     │
│  └─ ❌ Enrichment Pipeline (DEPRECATED)  :8002 (Epic 31)     │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
                   ┌────────┴────────┐
                   │ Home Assistant  │
                   │ 192.168.1.86    │
                   │  :8123 / :1883  │
                   │  WebSocket API  │
                   │  (External)     │
                   └─────────────────┘
        Single-Home Home Assistant on Intel NUC
        (i3/i5, 8-16GB RAM, ~50-100 devices)
```

### 🤖 Phase 1 AI Services (Containerized)

**New in Phase 1:** Distributed AI microservices architecture with containerized models:

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Services Layer                        │
├─────────────────────────────────────────────────────────────┤
│  AI Core Service (Orchestrator)           :8018             │
│  ├─ OpenVINO Service (Embeddings)         :8026 (ext→8019)  │
│  ├─ ML Service (Clustering)               :8025 (ext→8020)  │
│  ├─ NER Service (Entity Recognition)      :8031             │
│  ├─ OpenAI Service (GPT-4o-mini)          :8020             │
│  ├─ AI Automation Service                 :8024 (ext→8018)  │
│  ├─ Device Intelligence Service           :8028 (ext→8019)  │
│  └─ Automation Miner                      :8029 (ext→8019)  │
└─────────────────────────────────────────────────────────────┘
```

| AI Service | Purpose | External Port | Internal Port | Models | Status |
|------------|---------|---------------|---------------|--------|--------|
| **OpenVINO Service** | Embeddings, re-ranking, classification | 8026 | 8019 | all-MiniLM-L6-v2, bge-reranker-base, flan-t5-small | ✅ Active |
| **ML Service** | K-Means clustering, anomaly detection | 8025 | 8020 | scikit-learn algorithms | ✅ Active |
| **NER Service** | Named Entity Recognition | 8031 | 8031 | dslim/bert-base-NER | ✅ Active |
| **OpenAI Service** | GPT-4o-mini API client | 8020 | 8020 | GPT-4o-mini | ✅ Active |
| **AI Core Service** | Multi-model orchestration | 8018 | 8018 | Service coordinator | ✅ Active |
| **AI Automation Service** | Pattern detection & automation | 8024 | 8018 | Orchestrator | ✅ Active |
| **Device Intelligence** | Device capability discovery + Device Mapping Library | 8028 | 8019 | MQTT-based | ✅ Active |
| **Automation Miner** | Community automation mining | 8029 | 8019 | Web scraping | ✅ Active |
| **HA Setup Service** | HA setup recommendations | 8027 | 8020 | N/A | ✅ Active |

### Key Components

| Service | Purpose | External Port | Internal Port | Tech Stack | Status |
|---------|---------|---------------|---------------|------------|--------|
| **Health Dashboard** | System monitoring & management | 3000 | 80 | React, TypeScript, Vite | ✅ Active |
| **AI Automation UI** | Conversational automation | 3001 | 80 | React, TypeScript | ✅ Active |
| **WebSocket Ingestion** | Real-time HA event capture | 8001 | 8001 | Python, aiohttp, WebSocket | ✅ Active |
| **AI Automation Service** | Pattern detection & AI | 8024 | 8018 | Python, FastAPI, OpenAI, Self-Correction | ✅ Active |
| **HA AI Agent Service** | Conversational AI automation creation | 8030 | 8030 | Python, FastAPI, OpenAI GPT-4o-mini | ✅ Active |
| **Proactive Agent Service** | Context-aware suggestions | 8031 | 8031 | Python, FastAPI, APScheduler | ✅ Active |
| **Data API** | Historical data queries | 8006 | 8006 | Python, FastAPI | ✅ Active |
| **Admin API** | System control & config | 8003 | 8004 | Python, FastAPI | ✅ Active |
| **Device Intelligence** | Device capability discovery + Device Mapping Library | 8028 | 8019 | Python, FastAPI, MQTT | ✅ Active |
| **Weather API** | Standalone weather service | 8009 | 8009 | Python, FastAPI | ✅ Active |
| **Data Retention** | Data lifecycle management | 8080 | 8080 | Python, FastAPI | ✅ Active |
| **Carbon Intensity** | Grid carbon footprint | 8010 | 8010 | Python, FastAPI | ✅ Active |
| **Electricity Pricing** | Real-time pricing | 8011 | 8011 | Python, FastAPI | ✅ Active |
| **Air Quality** | AQI monitoring | 8012 | 8012 | Python, FastAPI | ✅ Active |
| **Calendar Service** | Event correlation | 8013 | 8013 | Python, FastAPI | ⏸️ Disabled |
| **Smart Meter** | Energy consumption | 8014 | 8014 | Python, FastAPI | ✅ Active |
| **Energy Correlator** | Energy analysis | 8017 | 8017 | Python, FastAPI | ✅ Active |
| **Log Aggregator** | Centralized logging | 8015 | 8015 | Python, FastAPI | ✅ Active |
| **Device Health Monitor** | Device health & maintenance | 8019 | 8019 | Python, FastAPI | ✅ Active |
| **Device Context Classifier** | Device type classification | 8032 | 8020 | Python, FastAPI | ✅ Active |
| **Device Setup Assistant** | Setup guides & issue detection | 8021 | 8021 | Python, FastAPI | ✅ Active |
| **Device Database Client** | External Device Database integration | 8022 | 8022 | Python, FastAPI | ✅ Active |
| **Device Recommender** | Device recommendations & comparisons | 8023 | 8023 | Python, FastAPI | ✅ Active |
| **InfluxDB** | Time-series database | 8086 | 8086 | InfluxDB 2.7 | ✅ Active |
| **HA Simulator** | Dev environment HA instance | 8123 | 8123 | Python, FastAPI | 🚧 Dev only |
| **External MQTT Broker** | MQTT messaging (not HomeIQ) | 1883 | 1883 | Eclipse Mosquitto | ℹ️ External |
| **❌ Enrichment Pipeline** | **DEPRECATED** (Epic 31) | 8002 | - | Python, FastAPI | ❌ Deprecated |

---

## 📖 Documentation

### User Guides
- [Quick Start Guide](docs/QUICK_START.md)
- [User Manual](docs/USER_MANUAL.md)
- [API Reference](docs/api/API_REFERENCE.md)
- [Device Database Enhancements](docs/DEVICE_DATABASE_ENHANCEMENTS.md)
- [Troubleshooting Guide](docs/TROUBLESHOOTING_GUIDE.md)
- [Soft Prompt Training Guide](docs/current/operations/soft-prompt-training.md)

### Developer Guides
- [Development Environment Setup](docs/development-environment-setup.md)
- [Architecture Documentation](docs/architecture/)
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [Docker Optimization](docs/DOCKER_OPTIMIZATION_PLAN.md)
- [Unit Testing Framework](docs/UNIT_TESTING_FRAMEWORK.md)
- [Unit Testing Quick Start](docs/UNIT_TESTING_QUICK_START.md)

### Implementation Notes
- [AI Pattern Detection Plan](implementation/AI_PATTERN_DETECTION_IMPLEMENTATION_PLAN.md)
- [System Health Fix](implementation/SYSTEM_HEALTH_FIX_PLAN.md)
- [Epic AI4 Complete](implementation/EPIC_AI4_COMPLETE.md)

---

## 🔧 Configuration

### Environment Variables

Key configuration options in `infrastructure/.env`:

```bash
# Home Assistant Connection (Single NUC Deployment)
HA_HTTP_URL=http://192.168.1.86:8123  # Your Home Assistant IP address
HA_WS_URL=ws://192.168.1.86:8123/api/websocket  # WebSocket endpoint
HA_TOKEN=your-long-lived-access-token  # From HA Profile → Long-Lived Access Tokens

# InfluxDB (Local instance, runs in Docker)
INFLUXDB_ORG=homeiq
INFLUXDB_BUCKET=home_assistant_events
INFLUXDB_TOKEN=your-influxdb-token  # Auto-generated on first run

# Optional External API Integrations
WEATHER_API_KEY=your-openweathermap-key  # OpenWeatherMap API key
WATTTIME_USERNAME=your-watttime-username  # WattTime API credentials
WATTTIME_PASSWORD=your-watttime-password
AIRNOW_API_KEY=your-airnow-key  # AirNow API key (optional)
```

### Docker Compose Variants

- `docker-compose.yml` - **Production** (all services)
- `docker-compose.minimal.yml` - Core services only
- `docker-compose.dev.yml` - Development with hot reload
- `docker-compose.simple.yml` - Basic setup for testing

---

## 🧪 Development

### Local Development Setup (Single NUC)

**Note:** This project is designed for **single-home Home Assistant deployment on an Intel NUC**. All services run in Docker containers on the same NUC host. This is a single-home application, not a multi-home or enterprise solution.

```bash
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

### Running Tests

Automated test commands are intentionally absent while the new smoke/regression harness is under construction. Refer to the "[How to Test](#how-to-test)" section above for the current manual verification approach and watch the repo for updates as soon as scripted coverage returns.

### Test Coverage

Coverage reports are temporarily disabled. Historical artifacts (`test-results/coverage/*` and friends) were removed together with the legacy suites and will reappear once the new smoke/regression harness lands.

---

## 🎨 Screenshots

### Health Dashboard - Dependencies Tab
Beautiful interactive dependency graph showing system architecture:

![Dependencies](docs/images/health-dashboard-dependencies.png)

### AI Automation - Ask AI Tab
Natural language automation creation:

![Ask AI](docs/images/ask-ai-tab.png)

### System Health Overview
Real-time monitoring of all services:

![System Health](docs/images/system-health.png)

---

## 📊 Project Stats

- **Services**: 30 active microservices (+ InfluxDB infrastructure = 31 containers)
- **Deployment**: Single-home Home Assistant on Intel NUC (i3/i5, 8-16GB RAM)
- **Scale**: Optimized for ~50-100 devices (single-home, not multi-home)
- **Hardware**: Intel NUC i3/i5, 8-16GB RAM, 20GB+ disk space
- **Languages**: Python 3.12+ (backend), TypeScript/React 18 (frontend)
- **Databases**: InfluxDB 2.7 (time-series) + 5 SQLite databases (metadata)
- **APIs**: RESTful (FastAPI), WebSocket (Home Assistant), MQTT (external broker)
- **UI Frameworks**: React 18, Vite, Tailwind CSS
- **AI/ML**: OpenVINO, OpenAI GPT-4o-mini, LangChain 0.2.x, Sentence-BERT, scikit-learn
- **External Integrations**: OpenWeatherMap, WattTime, Awattar, AirNow, ESPN
- **Testing**: Legacy suites removed (November 2025); new targeted coverage TBD
- **Lines of Code**: 50,000+ (reviewed November 2025)
- **Shared Libraries**: 3,947 lines across 11 core modules
- **Resource Constraints**: Optimized for NUC hardware, CPU-only (no GPU required)

---

## 🗺️ Roadmap

### Current Focus (Q4 2024 - Q1 2025)
- ✅ AI-powered pattern detection (Phase 1)
- ✅ Conversational automation UI
- ✅ Device validation system
- ✅ Post-refinement entity sanitization (Nov 2025)
- 🚧 Advanced ML models (Phase 2)
- 🚧 Multi-hop automation chains

### Future Plans
- 📱 Mobile app integration
- 🔊 Voice assistant support
- 🌐 Multi-language support
- 🔐 Enhanced security features
- 📈 Predictive automation

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md).

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Quality

- Follow [code quality standards](docs/CODE_QUALITY.md) ([coding standards](docs/architecture/coding-standards.md))
- Write tests for new features
- Update documentation
- Run linters before committing

---

## 📝 Recent Updates

- **Epic AI-24: Device Mapping Library Architecture** (January 2025) ✅
  - Plugin-based device mapping library with auto-discovery
  - Base DeviceHandler interface and registry system
  - YAML configuration support with hot-reload capability
  - Device Intelligence Service API integration (5 endpoints)
  - Entity Inventory Service integration (replaces hardcoded detection)
  - System prompt updated with device-specific guidelines
  - Two device handlers implemented (Hue, WLED) as proof of concept
  - Add new device handlers in < 1 hour without core code changes
  - Comprehensive unit tests (>90% coverage)
- **Add simulation framework enhancements, training improvements, and implementation documentation** (December 03, 2025)

- **Epic AI-21: Proactive Conversational Agent Service** (December 2025) ✅
  - New microservice for context-aware automation suggestions
  - Analyzes weather, sports, energy, and historical patterns
  - Generates proactive suggestions via agent-to-agent communication
  - Scheduled daily batch jobs (3 AM) for automated suggestions
  - Complete REST API for suggestion management
  - Production ready with comprehensive testing and code review
- **Security Audit & Quality Improvements** (December 03, 2025)
  - Enhanced Flux query sanitization with length validation
  - Created comprehensive security test suites
  - Fixed hardcoded default tokens
  - Added production readiness monitoring
  - Improved test infrastructure with smoke tests
- **Create Epics AI-11 through AI-16 with comprehensive review and 2025 patterns** (December 03, 2025)
- **Epic AI-6 - Blueprint-Enhanced Suggestion Intelligence** (December 2025)
  - Blueprint opportunity discovery from device inventory
  - Pattern validation against community blueprints with confidence boosting
  - User preference system (max suggestions, creativity level, blueprint preference)
  - Preference-aware ranking for more relevant suggestions
  - Preference API endpoints (`GET/PUT /api/v1/preferences`)
  - Settings UI for easy preference configuration
- **Epic 40 - Dual Deployment Configuration (Test & Production)** (December 02, 2025)
- **Home Type Categorization System** (November 25, 2025)
  - ML-based home type classification using RandomForest classifier
  - Synthetic data generation for training (100-120 homes)
  - Production profiling and classification API endpoints
  - Event categorization based on home type (security, climate, lighting, appliance, monitoring, general)
  - Integration with suggestion ranking (10% weight boost for home type preferences)
- **Automation Template Enhancements** (November 25, 2025)
  - Device-specific automation templates for common device types
  - Quick wins improvements for automation creation
- **Implement Quick Wins for Ask AI: Fix 54% failure rate** (November 24, 2025)
- **Device Database Enhancements** (January 20, 2025)
  - Device health monitoring with battery levels and response time analysis
  - Automatic device classification (fridge, car, light, etc.) from entity patterns
  - Device-specific automation templates for common device types
  - Setup assistant with step-by-step guides and issue detection
  - Device recommendations and comparison features
- **Fix entities endpoint database schema issue** (November 18, 2025)
  - Fixed 500 error on `/api/entities` endpoint caused by missing database columns
  - Added migration 004 documentation and troubleshooting steps
  - Entities now display correctly in dashboard
- **Fix websocket ingestion, dashboard, and AI automation improvements** (November 17, 2025)
  - Fixed websocket-ingestion service crash loop (import path fixes, Dockerfile correction)
  - Fixed health dashboard OverviewTab to properly show system status
  - Added area filtering to AI automation Ask AI interface
- **Story AI1.26: Persistent clarification session storage** (November 18, 2025)
  - Database-backed clarification flow with query ID linkage
  - Smart suggestion retrieval supporting both direct and clarification query IDs
  - HOME_ASSISTANT_TOKEN standardization (removed LOCAL_HA_TOKEN/LOCAL_HA_URL)
  - YAML 2025 standards enforcement
- **feat(data-api): comprehensive security and performance improvements** (November 14, 2025)
- **feat(ai-automation): modernize to HA 2025 YAML automation syntax** (November 14, 2025)

- **LangChain integrations**: Feature flags allow piloting LCEL-driven Ask AI prompts and pattern-detector chains.
- **PDL workflows**: YAML-based procedures now orchestrate nightly analysis and synergy guardrails when enabled.
- **Admin API stubs**: Lightweight in-memory alerting/logging/metrics modules keep imports satisfied without the retired test harness.
- **Legacy tests removed**: The old multi-language testing tree was deleted as part of this modernization; a slimmer suite will follow.

---

## 📜 License

This project is licensed under the ISC License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Home Assistant](https://www.home-assistant.io/) - Amazing home automation platform
- [OpenVINO](https://github.com/openvinotoolkit/openvino) - AI inference optimization
- [HuggingFace](https://huggingface.co/) - ML models and transformers
- [InfluxDB](https://www.influxdata.com/) - Time-series database
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://react.dev/) - UI library

---

## 📞 Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/wtthornton/HomeIQ/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/wtthornton/HomeIQ/discussions)
- 📚 **Wiki**: [Project Wiki](https://github.com/wtthornton/HomeIQ/wiki)
- 📖 **Documentation**: [Full Documentation](docs/)

---

## 📝 Documentation Updates

**Latest Code Review:** December 07, 2025

See [CODE_REVIEW_COMPREHENSIVE_FINDINGS.md](docs/CODE_REVIEW_COMPREHENSIVE_FINDINGS.md) for detailed findings including:
- Complete service inventory (30 active microservices)
- Database architecture analysis (5 SQLite + InfluxDB)
- Shared libraries documentation (3,947 lines, 11 modules)
- Infrastructure and deployment patterns
- Performance characteristics and optimizations
- Security measures and best practices

---

<div align="center">

**Made with ❤️ for the Home Assistant Community**

⭐ Star this repo if you find it helpful!

[Report Bug](https://github.com/wtthornton/HomeIQ/issues) · [Request Feature](https://github.com/wtthornton/HomeIQ/issues) · [Documentation](docs/)

</div>
