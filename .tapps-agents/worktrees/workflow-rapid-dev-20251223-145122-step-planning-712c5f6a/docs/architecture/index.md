# Home Assistant Ingestor - Architecture Documentation Index

## Overview

This directory contains the comprehensive architectural documentation for the Home Assistant Ingestor system. This is an **API-first data hub and ingestion platform** for single-home automation systems, providing RESTful APIs, event-driven webhooks, and time-series data storage for Home Assistant and external integrations.

## Quick Reference

**Technology Stack**: Python 3.12+, React 18.2, FastAPI, aiohttp, InfluxDB 2.7, SQLite 3.45+, Docker  
**Database**: Hybrid architecture (InfluxDB for time-series, SQLite for metadata - Epic 22)  
**Deployment**: Single-tenant Docker Compose with optimized Alpine images  
**Architecture Style**: Microservices with event-driven processing, API-first design, and external service integration

---

## 🏛️ **System Classification**

### **System Type**
- **Primary**: Data Ingestor + API Platform
- **Secondary**: Admin Monitoring Dashboard

### **Primary Users (API Consumers)**
1. **Home Assistant Automations**
   - Webhook triggers (game events, threshold alerts)
   - Fast status APIs (<50ms response for conditional logic)
   - Entity sensor integration
   - Event-driven scene triggers

2. **External Integration Systems**
   - Cloud analytics dashboards
   - Mobile applications (via REST APIs)
   - Voice assistants ("What's the score?")
   - Third-party home automation platforms

3. **Analytics & Reporting Platforms**
   - Historical data queries (season stats, trends)
   - Time-series analysis (energy patterns, weather correlations)
   - Custom reporting dashboards
   - Data export for machine learning

### **Secondary Users (Admin Interface)**
1. **Home Administrator**
   - System health monitoring (occasional viewing)
   - Configuration management (infrequent updates)
   - Service deployment and control
   - API usage tracking

**Usage Pattern**: Admin dashboard opened occasionally (not continuous viewing)

### **Deployment Scope**

**Single-Home, Self-Hosted Platform**
- Small homes: 50-200 HA entities, basic automation
- Medium homes: 200-500 HA entities, moderate integration
- Large homes: 500-1000 HA entities, advanced automation
- Extra-large homes: 1000+ HA entities, complex integrations

**Characteristics**:
- Single tenant per deployment
- No multi-user access control needed
- Self-hosted on local network
- Optional cloud API access via VPN/tunnel
- Not designed for public internet exposure

### **Key Design Principles**

1. **API-First Architecture**
   - Every data source exposed via REST APIs
   - Fast endpoints optimized for automation (<50ms SLA)
   - Historical query APIs for analytics
   - Webhook system for event-driven integrations
   - Admin dashboard is secondary interface (monitoring only)

2. **Event-Driven Over Polling**
   - Webhooks push events to consumers (don't make them poll)
   - Background event detection (sports scores, threshold alerts) ✅ Epic 12
   - HMAC-signed secure webhook delivery ✅ Epic 12
   - Reliable retry logic with exponential backoff (1s, 2s, 4s) ✅ Epic 12

3. **Single-Tenant Optimization**
   - No multi-user scaling concerns
   - Simplified security model (local network trust)
   - Direct database access (no query isolation needed)
   - Resource allocation for single home workload

4. **Data Persistence First**
   - InfluxDB as source of truth for all time-series data
   - Historical queries more important than real-time dashboard
   - API performance > dashboard UX
   - Long-term retention for analytics

5. **External Service Integration (NEW - October 2025)**
   - InfluxDB as central data hub
   - External services consume data from InfluxDB
   - Clean microservices pattern (no monolithic enrichment)
   - Weather, energy, and other data via dedicated services

### **What This System Is NOT**

- ❌ User-facing sports tracking app (it's a data hub for automations)
- ❌ Multi-tenant SaaS platform (single home per deployment)
- ❌ Public web application (admin tool on local network)
- ❌ High-frequency trading system (home automation scale)
- ❌ Mission-critical infrastructure (home comfort, not life-safety)  

## 📚 Architecture Documentation

### Getting Started

- **[Introduction](introduction.md)** - Project overview, goals, and high-level architecture
- **[Key Concepts](key-concepts.md)** - Core architectural concepts and design patterns
- **[Tech Stack](tech-stack.md)** - Complete technology stack with rationale and versions

### System Architecture

- **[Core Workflows](core-workflows.md)** - Primary system workflows and data flow diagrams
- **[AI Automation System](ai-automation-system.md)** - AI-powered automation generation with safety validation ✨ NEW
- **[Epic 39 Microservices Architecture](epic-39-microservices-architecture.md)** - Modularized AI Automation microservices architecture ✨ NEW (January 2025)
- **[Home Type Categorization](home-type-categorization.md)** - ML-based home classification system for context-aware suggestions ✨ NEW (November 2025)
- **[HA Connection Management](ha-connection-management.md)** - Enhanced HA connection manager with circuit breaker and fallback support ✨ NEW
- **[Deployment Architecture](deployment-architecture.md)** - Deployment patterns and infrastructure setup
- **[Source Tree](source-tree.md)** - Project structure and file organization
- **[Data Models](data-models.md)** - Data structures and type definitions

### Development & Operations

- **[Development Workflow](development-workflow.md)** - Developer setup and contribution guide
- **[Coding Standards](coding-standards.md)** - Code quality standards and best practices
- **[Frontend Specification](frontend-specification.md)** - UI/UX design system, component patterns, and accessibility standards
- **[AI Automation UI Standards](ai-automation-ui-standards.md)** - Streamlined UI standards and patterns for AI automation dashboard ✨ NEW
- **[Configuration Management](configuration-management.md)** - Environment and configuration guidelines
- **[API Guidelines](api-guidelines.md)** - REST API design standards and conventions

### Quality & Testing

- **[Testing Strategy](testing-strategy.md)** - Comprehensive testing approach (unit, integration, E2E)
- **[Error Handling Strategy](error-handling-strategy.md)** - Error handling patterns and recovery
- **[Monitoring and Observability](monitoring-and-observability.md)** - Logging, metrics, and alerting
- **[Performance Standards](performance-standards.md)** - Performance targets and optimization

### Security & Compliance

- **[Security Standards](security-standards.md)** - Security best practices and authentication
- **[Security and Performance](security-and-performance.md)** - Combined security and performance considerations
- **[Compliance Standard Framework](compliance-standard-framework.md)** - Compliance and regulatory standards

### Database

- **[Database Schema](database-schema.md)** - InfluxDB schema design and data organization

## 🏗️ System Architecture Overview

### Services

#### Core Services

| Service | Technology | Port | Purpose |
|---------|-----------|------|---------|
| **websocket-ingestion** | Python/aiohttp | 8001 | Home Assistant WebSocket client |
| ❌ **enrichment-pipeline** | Python/FastAPI | 8002 | **DEPRECATED** (Epic 31 - Direct writes to InfluxDB) |
| **admin-api** | Python/FastAPI | 8003→8004 | System monitoring, health checks, Docker management |
| **data-api** | Python/FastAPI | 8006 | **Feature data hub** (events, devices, sports, analytics, alerts) |
| **data-retention** | Python/FastAPI | 8080 | Data lifecycle and cleanup management |
| **health-dashboard** | React/TypeScript | 3000 | Web-based monitoring interface (13 tabs) |
| **sports-data** | Python/FastAPI | 8005 | ESPN sports API integration (NFL/NHL) |
| **ai-automation-service** | Python/FastAPI | 8024 (external), 8018 (internal) | **AI automation suggestions** (NL generation, pattern detection, safety validation) ✨ |
| **influxdb** | InfluxDB 2.7 | 8086 | Time-series data storage |

#### External Data Services

| Service | Technology | Port | Purpose |
|---------|-----------|------|---------|
| **carbon-intensity** | Python/FastAPI | 8010 | Carbon intensity data |
| **electricity-pricing** | Python/FastAPI | 8011 | Electricity pricing data |
| **air-quality** | Python/FastAPI | 8012 | Air quality monitoring |
| **calendar** | Python/FastAPI | 8013 | Calendar integration |
| **smart-meter** | Python/FastAPI | 8014 | Smart meter data |
| **weather-api** | Python/FastAPI | Internal | Weather data integration |
| **log-aggregator** | Python/FastAPI | 8015 | Centralized log collection |

**Note:** As of Epic 13, the API layer was separated into two services:
- **admin-api (8003)**: System monitoring, health checks, Docker container management
- **data-api (8006)**: Feature data queries (events, devices, sports, analytics, alerts)

### Data Flow

```
Home Assistant → WebSocket Ingestion → InfluxDB (Direct - Epic 31)
                                           ↑
                                    Weather API + External Data Services

Dashboard → nginx → admin-api (system monitoring)
                 └→ data-api (feature queries) → InfluxDB
```

### Key Architectural Patterns

- **Microservices Architecture**: Independent, containerized services
- **Event-Driven Processing**: Real-time WebSocket event streaming
- **API Gateway Pattern**: FastAPI as unified REST interface
- **Service Isolation**: Docker containerization with health checks
- **Optimized Deployment**: Multi-stage Docker builds with Alpine Linux (71% size reduction)

## 📊 Technology Decisions

### Frontend Stack
- **React 18.2** + **TypeScript 5.2** - Type-safe UI development
- **TailwindCSS 3.4** - Utility-first styling
- **Vite 5.0** - Fast build tooling
- **Vitest 3.2** - Component testing

### Backend Stack
- **Python 3.11** - Async/await support
- **FastAPI 0.104** - High-performance REST APIs
- **aiohttp 3.9** - WebSocket client
- **pytest 7.4** - Backend testing

### Data & Infrastructure
- **InfluxDB 2.7** - Time-series database
- **Docker Compose 2.20+** - Service orchestration
- **Playwright 1.56** - E2E testing
- **GitHub Actions** - CI/CD pipeline

## 🔒 Security Architecture

- **Authentication**: Long-lived access tokens for Home Assistant
- **API Security**: API key authentication for admin endpoints
- **Container Security**: Non-root users, read-only filesystems
- **Network Security**: Internal service communication, minimal external ports

## 📈 Performance Characteristics

- **Event Processing**: 10,000+ events/day
- **Response Time**: <100ms API calls
- **Reliability**: 99.9% uptime with auto-reconnection
- **Container Size**: 71% reduction with Alpine images (40-80MB per service)

## 🧪 Testing Strategy

- **Unit Tests**: 600+ tests across services (pytest, Vitest)
- **Integration Tests**: End-to-end workflow testing
- **E2E Tests**: Playwright browser testing
- **Coverage Target**: 95%+ for critical services

## 🔍 Monitoring & Observability

- **Structured Logging**: JSON format with correlation IDs
- **Health Checks**: All services expose `/health` endpoints
- **Metrics Collection**: Real-time system and application metrics
- **Alerting**: Configurable thresholds for critical metrics

## 📖 Additional Documentation

### Project Documentation
- **[PRD](../prd.md)** - Product Requirements Document
- **[Stories](../stories/)** - User stories and epic documentation
- **[QA Gates](../qa/gates/)** - Quality assurance checkpoints

### Operational Documentation
- **[Deployment Guide](../DEPLOYMENT_GUIDE.md)** - Complete deployment instructions
- **[Production Deployment](../PRODUCTION_DEPLOYMENT.md)** - Production setup guide
- **[Security Configuration](../SECURITY_CONFIGURATION.md)** - Security best practices
- **[Troubleshooting Guide](../TROUBLESHOOTING_GUIDE.md)** - Common issues and solutions

### Developer Documentation
- **[API Documentation](../api/API_REFERENCE.md)** - Complete API reference (consolidated Oct 2025) ✨ UPDATED
- **[CLI Reference](../CLI_REFERENCE.md)** - Command-line tools
- **[User Manual](../USER_MANUAL.md)** - End-user documentation
- **[Documentation Index](../DOCUMENTATION_INDEX.md)** - Master navigation guide ✨ NEW

### Integration Documentation
- **[Context7 Integration](../CONTEXT7_INTEGRATION.md)** - Context7 MCP integration guide
- **[Context7 KB Status](../kb/CONTEXT7_KB_STATUS_REPORT.md)** - Knowledge base status

## 🚀 Getting Started

1. **Read the [Introduction](introduction.md)** to understand the system
2. **Review the [Tech Stack](tech-stack.md)** for technology details
3. **Follow the [Development Workflow](development-workflow.md)** to set up your environment
4. **Check [Coding Standards](coding-standards.md)** before contributing

## 📝 Conventions

- All documentation uses Markdown format
- Code examples include language tags
- Architecture diagrams use Mermaid format where possible
- Links use relative paths from document location

## 🔄 Keeping Documentation Updated

This architecture documentation should be updated whenever:
- New services are added or removed
- Technology choices change
- Architectural patterns are introduced
- Performance characteristics change significantly

---

**Last Updated**: November 26, 2025  
**Version**: 5.2 (Documentation updates - Epic 31 architecture, service count standardization)  
**Status**: Production Ready  
**Maintained By**: HA Ingestor Team
