# 🏠 HomeIQ Documentation

[![Production Ready](https://img.shields.io/badge/Status-Production%20Ready-brightgreen?style=for-the-badge)](#)
[![License](https://img.shields.io/badge/License-ISC-blue?style=for-the-badge)](../LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Compatible-41BDF5?style=for-the-badge&logo=home-assistant)](https://www.home-assistant.io/)

**AI-Powered Home Automation Intelligence Platform**

Comprehensive documentation for HomeIQ - an enterprise-grade intelligence layer for Home Assistant with conversational AI, pattern detection, and advanced analytics.

## 🎯 **What is HomeIQ?**

HomeIQ is an enterprise-grade intelligence layer for Home Assistant that provides:
- 🤖 **Conversational AI Automation** - Create automations by chatting, no YAML required
- 🔍 **Smart Pattern Detection** - AI discovers automation opportunities from your usage patterns
- 📊 **Advanced Analytics** - Deep insights with hybrid database architecture (5-10x faster queries)
- 🔌 **Multi-Source Enrichment** - Combines weather, energy pricing, air quality, sports, and more
- 🎨 **Beautiful Dashboards** - Real-time system health and interactive dependency visualization
- 🚀 **RESTful APIs** - Comprehensive API access to all data and AI capabilities

## ✨ **Key Features**

### 🔄 **Real-time Data Pipeline**
- Direct WebSocket connection to Home Assistant
- Event normalization and validation
- Multi-source data enrichment (weather, carbon, pricing, air quality)
- Sports data integration (NFL/NHL)
- Smart meter integration
- High-performance batch processing (5-10x faster)

### 🤖 **AI & Machine Learning**
- Containerized AI services (OpenVINO, NER, ML models)
- Pattern detection and automation mining
- Device intelligence and recommendations
- Conversational automation creation
- Natural language processing
- Real-time model inference

### 📊 **Advanced Analytics**
- Time-series data storage in InfluxDB with tiered retention
- Materialized views for fast query performance
- Historical data analysis and trends
- Custom data queries and filtering
- Multiple export formats (CSV, JSON, PDF, Excel)
- Storage analytics and optimization

### 🖥️ **Modern Web Interface**
- Real-time monitoring dashboard
- Mobile-responsive design
- Touch gesture support
- Dark/light theme support

### 🔍 **Production Monitoring**
- Comprehensive health monitoring
- Configurable alerting system
- Performance metrics tracking
- Log aggregation and analysis

### 🛡️ **Enterprise Features**
- Tiered data retention (hot/warm/cold storage)
- S3/Glacier archival support
- Automated backup and restore
- Security and authentication
- Scalable microservices architecture
- Comprehensive monitoring and alerting

## ✅ **Recent Updates (October 2025)**

### 🤖 **AI Containerization (Phase 1)**
- Distributed AI microservices architecture
- OpenVINO service for embeddings and re-ranking
- Named Entity Recognition (NER) service
- ML clustering and anomaly detection service
- Improved AI response times (2-3x faster)

### 🧪 **Comprehensive Testing Framework**
- 272+ unit tests across all services
- E2E testing with Playwright
- Automated test coverage reports
- Python and TypeScript testing integration

### 🏗️ **Architecture Improvements (Epic 31)**
- Direct InfluxDB writes from integration services
- Hybrid database architecture (InfluxDB + SQLite)
- 5-10x faster metadata queries
- Improved system reliability and performance

## 🚀 **Quick Start**

### **Prerequisites**
- Docker 20.10+ and Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended)
- 20GB storage minimum (50GB recommended)

### **Deployment**
```bash
# Clone repository
git clone <repository-url>
cd homeiq

# Configure environment
cp infrastructure/env.example .env
nano .env  # Edit with your configuration

# Start the system
docker-compose up -d

# Verify deployment
docker-compose ps
```

### **Access Points**
- **Health Dashboard**: http://localhost:3000 (includes Configuration Management ⭐)
- **Admin API**: http://localhost:8003
- **API Documentation**: http://localhost:8003/docs
- **System Health**: http://localhost:8003/api/v1/health
- **Integration Management**: http://localhost:8003/api/v1/integrations ⭐
- **Data Retention API**: http://localhost:8080

## 📋 **System Architecture**

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
│  └─ Device Intelligence Service         :8028               │
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
│  ├─ Smart Meter              :8014 → InfluxDB               │
│  └─ Sports Data              :8005 → InfluxDB               │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
                   ┌────────┴────────┐
                   │ Home Assistant  │
                   │  :8123 / :1883  │
                   └─────────────────┘
```

## 🏗️ **Services**

### Core Services

| Service | Purpose | External Port | Internal Port | Tech Stack | Status |
|---------|---------|---------------|---------------|------------|--------|
| **Health Dashboard** | System monitoring & management | 3000 | 80 | React, TypeScript, Vite | ✅ Active |
| **AI Automation UI** | Conversational automation | 3001 | 80 | React, TypeScript | ✅ Active |
| **WebSocket Ingestion** | Real-time HA event capture | 8001 | 8001 | Python, aiohttp, WebSocket | ✅ Active |
| **AI Automation Service** | Pattern detection & AI orchestration | 8024 | 8018 | Python, FastAPI, OpenAI | ✅ Active |
| **Data API** | Historical data queries | 8006 | 8006 | Python, FastAPI | ✅ Active |
| **Admin API** | System control & config | 8003 | 8004 | Python, FastAPI | ✅ Active |
| **Device Intelligence** | Device capability discovery | 8028 | 8019 | Python, FastAPI, MQTT | ✅ Active |
| **InfluxDB** | Time-series database | 8086 | 8086 | InfluxDB 2.7 | ✅ Active |

### AI Services (Phase 1)

| AI Service | Purpose | External Port | Internal Port | Models | Status |
|------------|---------|---------------|---------------|--------|--------|
| **OpenVINO Service** | Embeddings, re-ranking, classification | 8026 | 8019 | all-MiniLM-L6-v2, bge-reranker-base | ✅ Active |
| **ML Service** | K-Means clustering, anomaly detection | 8025 | 8020 | scikit-learn algorithms | ✅ Active |
| **NER Service** | Named Entity Recognition | 8031 | 8031 | dslim/bert-base-NER | ✅ Active |
| **OpenAI Service** | GPT-4o-mini API client | 8020 | 8020 | GPT-4o-mini | ✅ Active |
| **AI Core Service** | Multi-model orchestration | 8018 | 8018 | Service coordinator | ✅ Active |

### Integration Services

| Service | Description | Port | Status |
|---------|-------------|------|--------|
| **Weather API** | Standalone weather service | 8009 | ✅ Active |
| **Carbon Intensity** | Grid carbon footprint data | 8010 | ✅ Active |
| **Electricity Pricing** | Real-time electricity costs | 8011 | ✅ Active |
| **Air Quality** | AQI monitoring and alerts | 8012 | ✅ Active |
| **Smart Meter** | Smart meter data integration | 8014 | ✅ Active |
### Deprecated Services

| Service | Reason | Deprecated | Migration Path |
|---------|--------|------------|----------------|
| **enrichment-pipeline** | Epic 31 - Direct writes to InfluxDB | Oct 2025 | Integration services write directly |
| **calendar-service** | Low usage, complexity | Oct 2025 | Disabled (commented out in docker-compose.yml) |
| **sports-api** | Replaced by HA sensors | Oct 2025 | Team Tracker + NHL HACS integrations |
| **sports-data** | Replaced by HA sensors | Oct 2025 | Team Tracker + NHL HACS integrations |

## 📊 **Project Status**

### **✅ Complete - All 5 Epics (100%)**

- **✅ Epic 1: Foundation & Core Infrastructure** - 10/10 stories completed
- **✅ Epic 2: Data Capture & Normalization** - 3/3 stories completed  
- **✅ Epic 3: Data Enrichment & Storage** - 3/3 stories completed
- **✅ Epic 4: Production Readiness & Monitoring** - 3/3 stories completed
- **✅ Epic 5: Admin Interface & Frontend** - 6/6 stories completed

**Total: 25/25 stories completed (100%)**

### **🧪 Test Coverage**
- **Status**: Test infrastructure being rebuilt (November 2025)
- **Legacy Tests**: Removed to accommodate LangChain/PDL refactor
- **Current Testing**: Manual validation via Health Dashboard (http://localhost:3000) and AI Automation UI (http://localhost:3001)
- **Roadmap**: New focused smoke/regression harness under development
- **See**: [Testing section in main README](../README.md#how-to-test) for current approach

## 📚 **Documentation**

### **📖 User Guides**
- **[Quick Start Guide](QUICK_START.md)** - Get up and running quickly
- **[User Manual](USER_MANUAL.md)** - Comprehensive user guide
- **[Deployment Guide](DEPLOYMENT_GUIDE.md)** - Complete deployment instructions
- **[Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md)** - Common issues and solutions

### **🔧 Technical Documentation**
- **[API Documentation](API_DOCUMENTATION.md)** - Complete API reference
- **[Services Overview](SERVICES_OVERVIEW.md)** - All services and their roles
- **[Architecture Documentation](architecture/)** - System architecture details
- **[Development Environment Setup](development-environment-setup.md)** - Development guide
- **[Unit Testing Framework](UNIT_TESTING_FRAMEWORK.md)** - Testing guide

### **🏗️ Architecture**
- **[Architecture Overview](architecture/)** - System design and patterns
- **[Performance Patterns](../CLAUDE.md)** - Performance best practices
- **[Hybrid Database Architecture](HYBRID_DATABASE_ARCHITECTURE.md)** - InfluxDB + SQLite design

## 🔧 **Configuration**

### **Required Environment Variables**
```bash
# Home Assistant Configuration
HA_URL=ws://your-ha-instance:8123/api/websocket
HA_ACCESS_TOKEN=your_long_lived_access_token

# Weather API Configuration
WEATHER_API_KEY=your_openweathermap_api_key
WEATHER_LOCATION=your_city,country_code

# InfluxDB Configuration
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=your_influxdb_token
INFLUXDB_ORG=your_organization
INFLUXDB_BUCKET=home_assistant

# API Configuration
API_KEY=your_secure_api_key
ENABLE_AUTH=true
```

## 🚀 **Features Overview**

### **🔄 Real-time Processing**
- WebSocket connection to Home Assistant
- Event normalization and validation
- Weather data enrichment
- High-performance data pipeline

### **📊 Data Management**
- Time-series data storage
- Data retention policies
- Automated backup and restore
- Data export in multiple formats

### **🖥️ User Interface**
- Modern React-based dashboard
- Mobile-responsive design
- Real-time monitoring
- **Web-based configuration management** ⭐ NEW

### **🔧 Configuration Management** ⭐ NEW
- Manage service credentials through web UI
- Edit API keys and tokens securely
- Real-time configuration validation
- Masked sensitive values
- One-click save functionality
- Service status monitoring

### **🔍 Monitoring & Alerting**
- System health monitoring
- Configurable alerts
- Performance metrics
- Log aggregation

### **🛡️ Security & Production**
- Authentication and authorization
- SSL/TLS support
- Docker containerization
- Production-ready deployment

## 🧪 **Testing**

### **Test Coverage**
```bash
# Run all tests
docker-compose exec admin-api python -m pytest tests/
docker-compose exec enrichment-pipeline python -m pytest tests/
docker-compose exec data-retention python -m pytest tests/

# Run frontend tests
cd services/health-dashboard
npm test
npm run test:coverage
```

### **Test Results**
- **Data Retention Service**: 104/105 tests passing (99%)
- **Enrichment Pipeline Service**: 40/40 tests passing (100%)
- **Admin API Service**: 36/45 tests passing (85%)
- **Health Dashboard Service**: 400+/427 tests passing (95%+)

## 🔄 **Development**

### **Local Development**
```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# Run tests
npm test
python -m pytest tests/

# Build for production
docker-compose build
```

### **Contributing**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📈 **Performance**

### **System Requirements**
- **CPU**: 2 cores minimum, 4 cores recommended
- **Memory**: 4GB minimum, 8GB recommended
- **Storage**: 20GB minimum, 50GB recommended
- **Network**: Stable internet connection

### **Performance Metrics**
- **Event Processing**: 1000+ events per minute
- **Response Time**: <100ms for API calls
- **Data Storage**: Efficient time-series storage
- **Memory Usage**: Optimized for production

## 🔒 **Security**

### **Security Features**
- API key authentication
- Secure WebSocket connections
- Encrypted data storage
- Regular security updates

### **Best Practices**
- Use strong API keys
- Enable HTTPS in production
- Regular security audits
- Monitor access logs

## 📞 **Support**

### **Getting Help**
- **Documentation**: Check the comprehensive documentation
- **Issues**: Report issues on GitHub
- **Discussions**: Join community discussions
- **Support**: Contact support for enterprise needs

### **Resources**
- **API Documentation**: http://localhost:8080/docs
- **Health Dashboard**: http://localhost:3000
- **Monitoring**: http://localhost:8080/api/v1/monitoring

## 📄 **License**

This project is licensed under the ISC License - see the [LICENSE](../LICENSE) file for details.

## 🙏 **Acknowledgments**

- [Home Assistant](https://www.home-assistant.io/) - Amazing home automation platform
- [OpenVINO](https://github.com/openvinotoolkit/openvino) - AI inference optimization
- [HuggingFace](https://huggingface.co/) - ML models and transformers
- [InfluxDB](https://www.influxdata.com/) - Time-series database
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://react.dev/) - UI library

---

## 🎉 **Ready for Production!**

**HomeIQ is an enterprise-grade intelligence layer for Home Assistant, providing AI-powered automation, pattern detection, and advanced analytics. With distributed AI services, comprehensive testing, and beautiful dashboards, it transforms your home automation experience.**

**🚀 Deploy today and unlock the full potential of your smart home!**

---

**⭐ Star this repo if you find it helpful!**

[Report Bug](https://github.com/wtthornton/HomeIQ/issues) · [Request Feature](https://github.com/wtthornton/HomeIQ/issues) · [Documentation](./)

---

**Last Updated:** October 25, 2025
**For the main project README, see:** [../README.md](../README.md)
