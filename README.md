# 🏠 HomeIQ

<div align="center">

**AI-Powered Home Automation Intelligence Platform**

Transform your Home Assistant into an intelligent automation powerhouse with conversational AI, pattern detection, and advanced analytics.

[![Production Ready](https://img.shields.io/badge/Status-Production%20Ready-brightgreen?style=for-the-badge)](#)
[![License](https://img.shields.io/badge/License-ISC-blue?style=for-the-badge)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Compatible-41BDF5?style=for-the-badge&logo=home-assistant)](https://www.home-assistant.io/)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

[Features](#-key-features) • [Quick Start](#-quick-start) • [Screenshots](#-screenshots) • [Documentation](#-documentation) • [Support](#-support)

</div>

---

## 🎯 What is HomeIQ?

HomeIQ is an **AI-powered companion for Home Assistant** that makes home automation accessible to everyone. Instead of writing complex YAML configurations, simply tell HomeIQ what you want in plain English.

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

### Why HomeIQ?

| Feature | Benefit |
|---------|---------|
| 🤖 **Conversational AI** | Create automations by chatting, no coding required |
| 🔍 **Smart Pattern Detection** | AI discovers automation opportunities from your usage |
| 📊 **Advanced Analytics** | Deep insights into your home's behavior |
| 🔌 **Rich Integrations** | Weather, energy pricing, air quality, sports scores, and more |
| 🎨 **Beautiful Dashboards** | Real-time monitoring with interactive visualizations |
| 🏠 **Single-Home Optimized** | Designed for Intel NUC deployment, not cloud-dependent |

---

## ✨ Key Features

### 🤖 AI-Powered Automation
- **Natural Language**: Create automations by describing what you want
- **Pattern Mining**: AI analyzes your usage and suggests automations
- **Device Templates**: Pre-built templates for common devices (thermostats, lights, appliances)
- **Proactive Suggestions**: Context-aware recommendations based on weather, time, and events

### 🏠 Device Intelligence
- **Health Monitoring**: Battery levels, response times, and maintenance alerts
- **Smart Classification**: Automatic device type detection (fridge, car, light, sensor)
- **Setup Assistant**: Step-by-step guides for new devices
- **Power Analysis**: Compare actual vs. expected power usage

### 📊 Real-Time Analytics
- **Live Dashboard**: Monitor all your devices and automations
- **Historical Data**: Analyze patterns over days, weeks, or months
- **Event Correlation**: Understand how devices interact
- **Performance Metrics**: Track system health and response times

### 🌐 Rich Data Enrichment
- ☁️ **Weather** — Forecasts and conditions via OpenWeatherMap
- ⚡ **Energy Pricing** — Real-time electricity costs
- 🌬️ **Air Quality** — AQI monitoring and alerts
- 🏈 **Sports** — Live game tracking (NFL, NHL, and more)
- 🌍 **Carbon Intensity** — Grid carbon footprint awareness
- 📅 **Calendar** — Event-triggered automations

---

## 🚀 Quick Start

### Requirements

- **Home Assistant** running on your local network
- **Intel NUC** (or similar PC) with 8GB+ RAM, 20GB+ disk space
- **Docker** and **Docker Compose** v2.0+

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/wtthornton/HomeIQ.git
cd HomeIQ

# 2. Copy and configure environment
cp infrastructure/env.example infrastructure/.env

# 3. Edit infrastructure/.env with your settings:
#    - HA_HTTP_URL=http://YOUR_HA_IP:8123
#    - HA_WS_URL=ws://YOUR_HA_IP:8123/api/websocket
#    - HA_TOKEN=your-long-lived-access-token

# 4. Start all services
docker compose up -d

# 5. Verify deployment
./scripts/verify-deployment.sh

# Or deploy individual services using the deployment script:
.\scripts\deploy-service.ps1 -ServiceName "service-name" -WaitForHealthy
```

### First Steps

1. **Open Health Dashboard**: [http://localhost:3000](http://localhost:3000)
   - View system health and integrations
   - Explore the interactive dependency graph

2. **Try AI Automation**: [http://localhost:3001](http://localhost:3001)
   - Click the "Ask AI" tab
   - Type: "Turn on lights when I arrive home"
   - Review and deploy your automation

3. **Explore APIs**: [http://localhost:8003/docs](http://localhost:8003/docs)
   - Interactive API documentation
   - Test endpoints and view real-time data

---

## 🎨 Screenshots

### Health Dashboard
Beautiful interactive system monitoring with dependency visualization:

> 📷 *Screenshot: Visit [http://localhost:3000](http://localhost:3000) to see the Health Dashboard*

### AI Automation
Natural language automation creation:

> 📷 *Screenshot: Visit [http://localhost:3001](http://localhost:3001) to see the AI Automation UI*

### Live Demo

Once HomeIQ is running, explore these interfaces:
- **Health Dashboard**: [http://localhost:3000](http://localhost:3000) — System monitoring and dependency graphs
- **AI Automation UI**: [http://localhost:3001](http://localhost:3001) — Conversational automation interface
- **API Documentation**: [http://localhost:8003/docs](http://localhost:8003/docs) — Interactive Swagger UI

---

## 🏗️ Architecture Overview

HomeIQ runs as a collection of 30+ microservices in Docker containers, designed for single-home deployment on resource-constrained hardware like an Intel NUC.

```
┌──────────────────────────────────────────────────────────────┐
│                     HomeIQ Stack                              │
├──────────────────────────────────────────────────────────────┤
│  🖥️ Web Dashboards                                           │
│    • Health Dashboard (localhost:3000)                       │
│    • AI Automation UI (localhost:3001)                       │
├──────────────────────────────────────────────────────────────┤
│  🤖 AI Services                                               │
│    • Conversational AI • Pattern Detection • NER             │
│    • Device Intelligence • Automation Mining                 │
├──────────────────────────────────────────────────────────────┤
│  📊 Data Layer                                                │
│    • InfluxDB (time-series) • SQLite (metadata)              │
├──────────────────────────────────────────────────────────────┤
│  🌐 Enrichment Services                                       │
│    • Weather • Energy • Air Quality • Sports • Calendar      │
└──────────────────────────────────────────────────────────────┘
                           ▲
                           │
                  ┌────────┴────────┐
                  │  Home Assistant │
                  │   (Your Home)   │
                  └─────────────────┘
```

**Event Flow (Epic 31 Architecture):**
Home Assistant → websocket-ingestion → InfluxDB (direct writes)
- All normalization happens inline in websocket-ingestion
- External services write directly to InfluxDB
- Query via data-api endpoint

For detailed architecture documentation, see:
- [Event Flow Architecture](docs/architecture/event-flow-architecture.md) - Event processing and data flow
- [Development Guide](docs/DEVELOPMENT.md) - Complete system architecture
- [Services Architecture Quick Reference](services/README_ARCHITECTURE_QUICK_REF.md) - Service patterns

---

## 📖 Documentation

### Getting Started
- [Quick Start Guide](docs/QUICK_START.md) — Get up and running
- [User Manual](docs/USER_MANUAL.md) — Complete usage guide
- [Troubleshooting Guide](docs/TROUBLESHOOTING_GUIDE.md) — Common issues and solutions

### Configuration
- [Environment Variables](docs/DEPLOYMENT_GUIDE.md#environment-variables) — Configuration options
- [Docker Compose Options](docs/DEPLOYMENT_GUIDE.md#docker-compose-variants) — Deployment variants

### API Reference
- [API Documentation](docs/api/API_REFERENCE.md) — RESTful API reference
- [Interactive Docs](http://localhost:8003/docs) — Swagger UI (when running)

### For Developers
- [Development Setup](docs/DEVELOPMENT.md) — Local development environment
- [Contributing Guide](CONTRIBUTING.md) — How to contribute
- [Architecture Documentation](docs/architecture/) — Technical deep-dives

---

## 📊 Project Stats

| Metric | Value |
|--------|-------|
| **Active Services** | 30 microservices + InfluxDB |
| **Target Hardware** | Intel NUC (i3/i5, 8-16GB RAM) |
| **Optimized For** | Single home, 50-100 devices |
| **Backend** | Python 3.12+, FastAPI |
| **Frontend** | React 18, TypeScript, Vite |
| **AI/ML** | OpenVINO, OpenAI GPT-4o-mini, LangChain |

---

## 🗺️ Roadmap

### Current (v1.x)
- ✅ Conversational AI automation
- ✅ Pattern detection and suggestions
- ✅ Device health monitoring
- ✅ Multi-source data enrichment
- 🚧 Advanced ML models

### Future
- 📱 Mobile app integration
- 🔊 Voice assistant support
- 🌐 Multi-language support
- 📈 Predictive automation

---

## 🤝 Contributing

We welcome contributions! See our [Contributing Guide](CONTRIBUTING.md) for details.

```bash
# Fork the repo, then:
git checkout -b feature/amazing-feature
git commit -m 'Add amazing feature'
git push origin feature/amazing-feature
# Open a Pull Request
```

---

## 📞 Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/wtthornton/HomeIQ/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/wtthornton/HomeIQ/discussions)
- 📚 **Wiki**: [Project Wiki](https://github.com/wtthornton/HomeIQ/wiki)
- 📖 **Full Docs**: [Documentation](docs/)

---

## 📜 License

This project is licensed under the ISC License — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Home Assistant](https://www.home-assistant.io/) — The amazing home automation platform
- [OpenVINO](https://github.com/openvinotoolkit/openvino) — AI inference optimization
- [InfluxDB](https://www.influxdata.com/) — Time-series database
- [FastAPI](https://fastapi.tiangolo.com/) — Modern Python web framework
- [React](https://react.dev/) — UI library

---

<div align="center">

**Made with ❤️ for the Home Assistant Community**

⭐ Star this repo if you find it helpful!

[Report Bug](https://github.com/wtthornton/HomeIQ/issues) · [Request Feature](https://github.com/wtthornton/HomeIQ/issues) · [Documentation](docs/)

</div>
