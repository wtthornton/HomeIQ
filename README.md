# 🏠 HomeIQ

<div align="center">

**AI-Powered Home Automation Intelligence Platform**

Transform your Home Assistant into an intelligent automation powerhouse with conversational AI, pattern detection, and advanced analytics.

[![Production Ready](https://img.shields.io/badge/Status-Production%20Ready-brightgreen?style=for-the-badge)](#)
[![License](https://img.shields.io/badge/License-ISC-blue?style=for-the-badge)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Compatible-41BDF5?style=for-the-badge&logo=home-assistant)](https://www.home-assistant.io/)

[Features](#-key-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Architecture](#-architecture) • [Contributing](#-contributing)

</div>

---

## 🎯 What is HomeIQ?

HomeIQ is an **enterprise-grade intelligence layer** for Home Assistant that adds:

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

### 📊 Enterprise Analytics

- **Hybrid Database**: InfluxDB (time-series) + SQLite (metadata)
- **5-10x Faster Queries**: Optimized data structures
- **Real-Time Metrics**: Live system health monitoring
- **Historical Analysis**: Deep dive into past events and patterns

### 🌐 Rich Data Enrichment

- ☁️ **Weather**: OpenWeatherMap integration with forecasts
- ⚡ **Energy Pricing**: Dynamic electricity cost tracking
- 🌬️ **Air Quality**: AQI monitoring and alerts
- 🏈 **Sports**: Live game tracking for team-based automations
- 🌍 **Carbon Intensity**: Grid carbon footprint awareness

### 🎨 Modern UI/UX

- **Health Dashboard** (localhost:3000): System monitoring with dependency graphs
- **AI Automation UI** (localhost:3001): Conversational automation interface
- **Interactive Visualizations**: Click-to-explore architecture diagrams
- **Dark Mode**: Beautiful, eye-friendly design

---

## 🚀 Quick Start

### Prerequisites

- **Home Assistant** instance (any version)
- **Docker** & **Docker Compose**
- **Node.js 20+** (for development)
- **Python 3.10+** (for development)

### Installation

```bash
# Clone the repository
git clone https://github.com/wtthornton/HomeIQ.git
cd HomeIQ

# Copy environment template
cp infrastructure/env.example infrastructure/.env

# Configure your Home Assistant connection
# Edit infrastructure/.env and add:
# - HA_HTTP_URL=http://your-ha-instance:8123
# - HA_TOKEN=your-long-lived-access-token

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

### System Overview (Epic 31 Architecture - 24 Active Microservices)

**Note:** Plus InfluxDB infrastructure = 25 total containers in production

```
┌─────────────────────────────────────────────────────────────┐
│                        HomeIQ Stack                          │
│                  24 Active Microservices                     │
│              (+ InfluxDB = 25 total containers)              │
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
│  AI Services Layer (8 services)                             │
│  ├─ AI Automation Service               :8024→8018          │
│  │   └─ Pattern detection + conversational flow             │
│  ├─ AI Core Service                     :8018               │
│  ├─ OpenVINO Service                    :8026→8019          │
│  ├─ ML Service                          :8025→8020          │
│  ├─ NER Service                         :8031               │
│  ├─ OpenAI Service                      :8020               │
│  ├─ Device Intelligence Service         :8028→8019          │
│  └─ Automation Miner                    :8029→8019          │
├─────────────────────────────────────────────────────────────┤
│  Data Layer (Hybrid Architecture)                           │
│  ├─ InfluxDB (Time-series)              :8086               │
│  │   └─ 365-day retention, ~150 flattened fields            │
│  └─ SQLite (5 Databases)                Files               │
│      ├─ metadata.db (devices, entities)                     │
│      ├─ ai_automation.db (11 tables)                        │
│      ├─ automation_miner.db (community corpus)              │
│      ├─ device_intelligence.db (7 tables)                   │
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
│  Dev/External (not HomeIQ services)                         │
│  ├─ HA Simulator (dev only)             :8123 (not deployed)│
│  ├─ MQTT Broker (external)     mqtt://192.168.1.86:1883     │
│  └─ ❌ Enrichment Pipeline (DEPRECATED)  :8002 (Epic 31)     │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
                   ┌────────┴────────┐
                   │ Home Assistant  │
                   │  :8123 / :1883  │
                   │  WebSocket API  │
                   └─────────────────┘
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
| **Device Intelligence** | Device capability discovery | 8028 | 8019 | MQTT-based | ✅ Active |
| **Automation Miner** | Community automation mining | 8029 | 8019 | Web scraping | ✅ Active |
| **HA Setup Service** | HA setup recommendations | 8027 | 8020 | N/A | ✅ Active |

### Key Components

| Service | Purpose | External Port | Internal Port | Tech Stack | Status |
|---------|---------|---------------|---------------|------------|--------|
| **Health Dashboard** | System monitoring & management | 3000 | 80 | React, TypeScript, Vite | ✅ Active |
| **AI Automation UI** | Conversational automation | 3001 | 80 | React, TypeScript | ✅ Active |
| **WebSocket Ingestion** | Real-time HA event capture | 8001 | 8001 | Python, aiohttp, WebSocket | ✅ Active |
| **AI Automation Service** | Pattern detection & AI | 8024 | 8018 | Python, FastAPI, OpenAI, Self-Correction | ✅ Active |
| **Data API** | Historical data queries | 8006 | 8006 | Python, FastAPI | ✅ Active |
| **Admin API** | System control & config | 8003 | 8004 | Python, FastAPI | ✅ Active |
| **Device Intelligence** | Device capability discovery | 8028 | 8019 | Python, FastAPI, MQTT | ✅ Active |
| **Weather API** | Standalone weather service | 8009 | 8009 | Python, FastAPI | ✅ Active |
| **Data Retention** | Data lifecycle management | 8080 | 8080 | Python, FastAPI | ✅ Active |
| **Carbon Intensity** | Grid carbon footprint | 8010 | 8010 | Python, FastAPI | ✅ Active |
| **Electricity Pricing** | Real-time pricing | 8011 | 8011 | Python, FastAPI | ✅ Active |
| **Air Quality** | AQI monitoring | 8012 | 8012 | Python, FastAPI | ✅ Active |
| **Calendar Service** | Event correlation | 8013 | 8013 | Python, FastAPI | ⏸️ Disabled |
| **Smart Meter** | Energy consumption | 8014 | 8014 | Python, FastAPI | ✅ Active |
| **Energy Correlator** | Energy analysis | 8017 | 8017 | Python, FastAPI | ✅ Active |
| **Log Aggregator** | Centralized logging | 8015 | 8015 | Python, FastAPI | ✅ Active |
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
# Home Assistant Connection
HA_HTTP_URL=http://192.168.1.86:8123
HA_WS_URL=ws://192.168.1.86:8123/api/websocket
HA_TOKEN=your-long-lived-token

# InfluxDB
INFLUXDB_ORG=homeiq
INFLUXDB_BUCKET=home_assistant_events
INFLUXDB_TOKEN=your-influxdb-token

# Optional Integrations
WEATHER_API_KEY=your-openweathermap-key
WATTTIME_USERNAME=your-watttime-username
WATTTIME_PASSWORD=your-watttime-password
```

### Docker Compose Variants

- `docker-compose.yml` - **Production** (all services)
- `docker-compose.minimal.yml` - Core services only
- `docker-compose.dev.yml` - Development with hot reload
- `docker-compose.simple.yml` - Basic setup for testing

---

## 🧪 Development

### Local Development Setup

```bash
# Backend (Python services)
cd services/ai-automation-service
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8018

# Frontend (React apps)
cd services/health-dashboard
npm install
npm run dev
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

### Recent Updates
- **Add comprehensive OpenVINO ML tests** (November 16, 2025)
- **Add comprehensive OpenVINO ML tests** (November 16, 2025)
- **Fix critical issues and improve reliability** (November 16, 2025)
- **Fix critical issues and improve reliability** (November 16, 2025)
- **Fix critical issues and improve reliability** (November 16, 2025)
- **Fix critical issues and improve reliability** (November 15, 2025)
- **Fix critical issues and improve reliability** (November 15, 2025)
- **Implement API key authentication and admin roles** (November 15, 2025)
- **Implement API key authentication and admin roles** (November 15, 2025)
- **Implement API key authentication and admin roles** (November 15, 2025)
- **Implement API key authentication and admin roles** (November 15, 2025)
- **Implement API key authentication and admin roles** (November 15, 2025)
- **feat(issues): add 12 critical issues in Open status to issues tracker** (November 15, 2025)
- **feat(issues): add 12 critical issues in Open status to issues tracker** (November 15, 2025)
- **feat(issues): add 12 critical issues in Open status to issues tracker** (November 15, 2025)
- **feat(issues): add 12 critical issues in Open status to issues tracker** (November 15, 2025)
- **feat(mcp): add AI Automation MCP endpoint for pattern detection** (November 15, 2025)
- **feat(health-dashboard): enhance UI with modern styling and configurable URLs** (November 15, 2025)
- **feat(ai-automation-ui): comprehensive production-ready updates** (November 15, 2025)
- **fix(gitignore): properly format Phase 3 test artifact entries** (November 15, 2025)
- **feat(mcp): implement MCP code execution pattern with LangChain integration** (November 15, 2025)
- **feat(mcp): implement MCP code execution pattern with LangChain integration** (November 15, 2025)
- **feat(mcp): implement MCP code execution pattern with LangChain integration** (November 15, 2025)
- **fix(ci): resolve GitHub Actions test failures** (November 15, 2025)
- **fix(ci): resolve GitHub Actions test failures** (November 15, 2025)
- **feat(data-api): comprehensive security and performance improvements** (November 14, 2025)
- **feat(team-tracker): Add comprehensive Team Tracker integration** (November 14, 2025)
- **Fix service health API mapping** (November 14, 2025)
- **Fix service health API mapping** (November 14, 2025)
- **feat(ai-automation): implement multi-source fusion and dynamic synergy discovery** (November 14, 2025)
- **feat(ai-automation): implement multi-source fusion and dynamic synergy discovery** (November 14, 2025)
- **feat(ai-automation): implement multi-source fusion and dynamic synergy discovery** (November 14, 2025)
- **feat(automation-miner): implement Blueprint YAML parsing** (November 14, 2025)
- **feat(ai-automation): modernize to HA 2025 YAML automation syntax** (November 14, 2025)
- **feat(ai-automation): modernize to HA 2025 YAML automation syntax** (November 14, 2025)
- **Automate README, CLAUDE.md, and docs/DOCUMENTATION_INDEX updates** (November 14, 2025)
- **Automate README, CLAUDE.md, and docs/DOCUMENTATION_INDEX updates** (November 11, 2025)
- **Automate README, CLAUDE.md, and docs/DOCUMENTATION_INDEX updates** (November 11, 2025)

- **LangChain integrations**: Feature flags allow piloting LCEL-driven Ask AI prompts and pattern-detector chains.
- **PDL workflows**: YAML-based procedures now orchestrate nightly analysis and synergy guardrails when enabled.
- **Admin API stubs**: Lightweight in-memory alerting/logging/metrics modules keep imports satisfied without the retired test harness.
- **Legacy tests removed**: The old multi-language testing tree was deleted as part of this modernization; a slimmer suite will follow.

## 📊 Project Stats

- **Services**: 24 active microservices (+ InfluxDB infrastructure = 25 containers)
- **Languages**: Python, TypeScript, JavaScript
- **Databases**: InfluxDB (time-series) + 5 SQLite databases (metadata)
- **APIs**: RESTful, WebSocket, MQTT (external)
- **UI Frameworks**: React 18, Vite, Tailwind CSS
- **AI/ML**: OpenVINO, OpenAI GPT-4o-mini, LangChain 0.2.x, Sentence-BERT, scikit-learn
- **Testing**: Legacy suites removed; new targeted coverage TBD
- **Lines of Code**: 50,000+ (reviewed November 2025)
- **Shared Libraries**: 3,947 lines across 11 core modules

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

- 🐛 Issues: [GitHub Issues](https://github.com/wtthornton/HomeIQ/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/wtthornton/HomeIQ/discussions)
- 📚 Wiki: [Project Wiki](https://github.com/wtthornton/HomeIQ/wiki)
- 📖 Documentation: [Full Documentation](docs/)

---

## 📝 Documentation Updates

**Latest Code Review:** November 16, 2025

See [CODE_REVIEW_COMPREHENSIVE_FINDINGS.md](docs/CODE_REVIEW_COMPREHENSIVE_FINDINGS.md) for detailed findings including:
- Complete service inventory (24 active microservices)
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

