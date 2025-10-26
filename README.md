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

- **Ask AI Tab**: Natural language automation creation
- **Pattern Mining**: AI analyzes your usage and suggests automations
- **Device Validation**: Intelligent device compatibility checking
- **Smart Recommendations**: Context-aware automation suggestions

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
docker-compose up -d

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

3. **Explore APIs**: http://localhost:8003/docs
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

To run tests for a specific service:

```bash
# Navigate to the service directory
cd services/[service-name]/tests

# Run all tests in the directory
pytest .

# Or run a specific test file
pytest test_[module_name].py
```

---

## 🏗️ Architecture

### System Overview (Epic 31 Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│                        HomeIQ Stack                          │
├─────────────────────────────────────────────────────────────┤
│  Web Layer                                                   │
│  ├─ Health Dashboard (React)            :3000               │
│  └─ AI Automation UI (React)            :3001               │
├─────────────────────────────────────────────────────────────┤
│  API Layer                                                   │
│  ├─ WebSocket Ingestion                 :8001               │
│  ├─ Admin API                           :8003               │
│  ├─ Data API                            :8006               │
│  ├─ AI Automation Service               :8018               │
│  ├─ Device Intelligence Service         :8021               │
│  └─ HA Setup Service                    :8020               │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                  │
│  ├─ InfluxDB (Time-series)              :8086               │
│  └─ SQLite (Metadata)                    Files              │
├─────────────────────────────────────────────────────────────┤
│  Integration Layer (Epic 31 - Direct Writes)                │
│  ├─ Weather API              :8009 → InfluxDB               │
│  ├─ Carbon Intensity         :8010 → InfluxDB               │
│  ├─ Electricity Pricing      :8011 → InfluxDB               │
│  ├─ Air Quality              :8012 → InfluxDB               │
│  ├─ Calendar Service         :8013 → InfluxDB               │
│  ├─ Smart Meter              :8014 → InfluxDB               │
│  └─ Sports Data              :8005 → InfluxDB               │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
                   ┌────────┴────────┐
                   │ Home Assistant  │
                   │  :8123 / :1883  │
                   └─────────────────┘

❌ DEPRECATED: Enrichment Pipeline (port 8002) - Epic 31
```

### 🤖 Phase 1 AI Services (Containerized)

**New in Phase 1:** Distributed AI microservices architecture with containerized models:

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Services Layer                        │
├─────────────────────────────────────────────────────────────┤
│  AI Core Service (Orchestrator)           :8018             │
│  ├─ OpenVINO Service (Embeddings)         :8022             │
│  ├─ ML Service (Clustering)               :8021             │
│  ├─ NER Service (Entity Recognition)      :8019             │
│  └─ OpenAI Service (GPT-4o-mini)          :8020             │
└─────────────────────────────────────────────────────────────┘
```

| AI Service | Purpose | Port | Models | Status |
|------------|---------|------|--------|--------|
| **OpenVINO Service** | Embeddings, re-ranking, classification | 8022 | all-MiniLM-L6-v2, bge-reranker-base, flan-t5-small | ✅ Active |
| **ML Service** | K-Means clustering, anomaly detection | 8021 | scikit-learn algorithms | ✅ Active |
| **NER Service** | Named Entity Recognition | 8019 | dslim/bert-base-NER | ✅ Active |
| **OpenAI Service** | GPT-4o-mini API client | 8020 | GPT-4o-mini | ✅ Active |
| **AI Core Service** | Multi-model orchestration | 8018 | Service coordinator | ✅ Active |

### Key Components

| Service | Purpose | Port | Tech Stack | Status |
|---------|---------|------|------------|--------|
| **Health Dashboard** | System monitoring & management | 3000 | React, TypeScript, Vite | ✅ Active |
| **AI Automation UI** | Conversational automation | 3001 | React, TypeScript | ✅ Active |
| **WebSocket Ingestion** | Real-time HA event capture | 8001 | Python, aiohttp, WebSocket | ✅ Active |
| **AI Automation Service** | Pattern detection & AI | 8018 | Python, FastAPI, OpenAI | ✅ Active |
| **Data API** | Historical data queries | 8006 | Python, FastAPI | ✅ Active |
| **Admin API** | System control & config | 8003 | Python, FastAPI | ✅ Active |
| **Device Intelligence** | Device capability discovery | 8021 | Python, FastAPI, MQTT | ✅ Active |
| **Weather API** | Standalone weather service | 8009 | Python, FastAPI | ✅ Active |
| **Sports Data** | NFL/NHL game data | 8005 | Python, FastAPI | ✅ Active |
| **❌ Enrichment Pipeline** | **DEPRECATED** (Epic 31) | 8002 | Python, FastAPI | ❌ Deprecated |

---

## 📖 Documentation

### User Guides
- [Quick Start Guide](docs/QUICK_START.md)
- [User Manual](docs/USER_MANUAL.md)
- [API Documentation](docs/API_DOCUMENTATION.md)
- [Troubleshooting Guide](docs/TROUBLESHOOTING_GUIDE.md)

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

```bash
# Unit Tests (Recommended) - Runs all unit tests with coverage
python scripts/simple-unit-tests.py

# Using npm scripts
npm test                           # Run all unit tests
npm run test:unit:python          # Python tests only
npm run test:unit:typescript      # TypeScript tests only
npm run test:coverage             # Run tests and show coverage info

# Unit Tests with options
python scripts/simple-unit-tests.py --python-only
python scripts/simple-unit-tests.py --typescript-only

# Cross-platform scripts
./run-unit-tests.sh                    # Linux/Mac
.\run-unit-tests.ps1                    # Windows

# E2E Tests
npm run test:e2e

# Individual service tests
cd services/ai-automation-service
pytest tests/

# Deployment Validation
npm run validate
```

### Test Coverage

The unit testing framework provides comprehensive coverage reports:

- **Python Coverage**: `test-results/coverage/python/index.html`
- **TypeScript Coverage**: `test-results/coverage/typescript/index.html`
- **Summary Report**: `test-results/unit-test-report.html`

**Current Coverage**: 272+ unit tests across all services

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

- Follow [code quality standards](docs/CODE_QUALITY.md)
- Write tests for new features
- Update documentation
- Run linters before committing

---

## 📊 Project Stats

- **Services**: 20 microservices
- **Languages**: Python, TypeScript, JavaScript
- **Databases**: InfluxDB, SQLite
- **APIs**: RESTful, WebSocket, MQTT
- **UI Frameworks**: React, Vite
- **AI/ML**: OpenVINO, Transformers, Sentence-BERT
- **Testing**: 272+ unit tests with comprehensive coverage
- **Lines of Code**: 50,000+

---

## 🗺️ Roadmap

### Current Focus (Q4 2024 - Q1 2025)
- ✅ AI-powered pattern detection (Phase 1)
- ✅ Conversational automation UI
- ✅ Device validation system
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

- 📧 Email: support@homeiq.example.com
- 🐛 Issues: [GitHub Issues](https://github.com/wtthornton/HomeIQ/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/wtthornton/HomeIQ/discussions)
- 📚 Wiki: [Project Wiki](https://github.com/wtthornton/HomeIQ/wiki)

---

<div align="center">

**Made with ❤️ for the Home Assistant Community**

⭐ Star this repo if you find it helpful!

[Report Bug](https://github.com/wtthornton/HomeIQ/issues) · [Request Feature](https://github.com/wtthornton/HomeIQ/issues) · [Documentation](docs/)

</div>

