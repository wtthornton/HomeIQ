# Epic DI-1: Device Intelligence Service Foundation

**Epic ID:** DI-1  
**Title:** Device Intelligence Service Foundation  
**Status:** Planning  
**Priority:** High  
**Complexity:** Medium  
**Timeline:** 2-3 weeks  
**Story Points:** 37  

---

## Epic Description

Create a new standalone Device Intelligence Service (Port 8019) that centralizes all device discovery, capability parsing, and intelligence processing for the Home Assistant Ingestor system. This service will replace scattered device discovery logic across multiple services with a unified, performant solution specifically engineered for single standalone Home Assistant local Docker deployments.

## Business Value

- **Single Source of Truth**: Centralized device intelligence eliminates data inconsistencies across services
- **Performance**: 5-10x faster device queries through optimized caching and storage architecture
- **Maintainability**: Clear service boundaries reduce complexity and improve system reliability
- **2025 Compliance**: Full Home Assistant API coverage with latest features and best practices
- **Docker Optimization**: Designed for single-node Docker deployments with resource efficiency

## Success Criteria

- Device Intelligence Service operational on Port 8019
- Multi-source device discovery (HA + Zigbee2MQTT) functional
- Unified device API serving all client services
- Performance targets: <10ms device queries, <100ms capability analysis
- Zero data loss during migration from existing services
- Docker container <200MB, startup time <10s, memory usage <50MB

## Technical Architecture

### Service Overview
```
┌─────────────────────────────────────────────────────────────┐
│                DEVICE INTELLIGENCE SERVICE                   │
│                        Port 8019                             │
├─────────────────────────────────────────────────────────────┤
│  📡 Multi-Source Discovery                                 │
│  ├─ Home Assistant WebSocket API                           │
│  │  ├─ Device Registry (config/device_registry/list)      │
│  │  ├─ Entity Registry (config/entity_registry/list)      │
│  │  ├─ Area Registry (config/area_registry/list)          │
│  │  └─ Integration Registry (config/config_entries/list)  │
│  ├─ Zigbee2MQTT Bridge                                     │
│  │  ├─ Device Capabilities (bridge/devices)               │
│  │  ├─ Groups (bridge/groups)                             │
│  │  └─ Network Map (bridge/networkmap)                    │
│  └─ Future Integrations (Z-Wave, ESPHome)                  │
├─────────────────────────────────────────────────────────────┤
│  🧠 Intelligence Processing                                │
│  ├─ Capability Parser (Universal)                         │
│  ├─ Feature Analyzer (Utilization)                         │
│  ├─ Device Matcher (HA ↔ Zigbee2MQTT)                     │
│  └─ Suggestion Generator (Unused Features)                │
├─────────────────────────────────────────────────────────────┤
│  💾 Unified Storage                                        │
│  ├─ SQLite: Device metadata, capabilities                  │
│  ├─ Redis: Real-time cache (TTL-based)                     │
│  └─ InfluxDB: Device analytics, usage patterns            │
├─────────────────────────────────────────────────────────────┤
│  🔌 API Endpoints                                          │
│  ├─ GET /api/devices - All devices with capabilities      │
│  ├─ GET /api/devices/{id}/capabilities - Detailed info    │
│  ├─ GET /api/devices/{id}/features - Feature analysis     │
│  ├─ GET /api/integrations - Integration status             │
│  └─ WebSocket /ws - Real-time device updates               │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack
- **Runtime**: Python 3.11, FastAPI, Uvicorn
- **Databases**: SQLite (metadata), Redis (cache), InfluxDB (analytics)
- **Discovery**: WebSocket (HA), MQTT (Zigbee2MQTT)
- **Containerization**: Docker multi-stage Alpine build
- **Performance**: <200MB image, <10s startup, <50MB memory

## Stories

### DI-1.1: Service Foundation & Infrastructure
- **Story Points**: 8
- **Priority**: P0
- **Description**: Create FastAPI service foundation with Docker containerization

### DI-1.2: Multi-Source Discovery Engine
- **Story Points**: 13
- **Priority**: P0
- **Description**: Implement comprehensive device discovery from HA and Zigbee2MQTT

### DI-1.3: Unified Device Storage
- **Story Points**: 8
- **Priority**: P0
- **Description**: Create optimized storage system with SQLite and Redis caching

### DI-1.4: Device Intelligence API
- **Story Points**: 8
- **Priority**: P0
- **Description**: Build REST API endpoints for device queries and capabilities

## Dependencies

- **External**: Home Assistant WebSocket API, Zigbee2MQTT bridge, MQTT broker
- **Internal**: Docker infrastructure, Redis service, InfluxDB service
- **Data**: Existing device data from websocket-ingestion, data-api, ai-automation-service

## Risks & Mitigation

### High Risk
- **Service Integration Complexity**: Mitigation through gradual migration and comprehensive testing
- **Performance Degradation**: Mitigation through performance monitoring and optimization

### Medium Risk
- **Data Loss During Migration**: Mitigation through comprehensive backup and validation procedures
- **Docker Resource Constraints**: Mitigation through resource optimization and monitoring

### Low Risk
- **API Compatibility**: Mitigation through thorough API testing and documentation

## Acceptance Criteria

- [ ] Device Intelligence Service deployed and operational
- [ ] All device discovery sources functional
- [ ] API endpoints serving device data
- [ ] Performance targets met
- [ ] Docker container optimized
- [ ] Integration tests passing
- [ ] Documentation complete

## Definition of Done

- [ ] All stories completed and tested
- [ ] Service deployed in Docker environment
- [ ] Performance benchmarks met
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Code review completed
- [ ] QA approval received

---

**Created**: January 24, 2025  
**Last Updated**: January 24, 2025  
**Author**: BMAD Product Manager  
**Reviewers**: System Architect, QA Lead
