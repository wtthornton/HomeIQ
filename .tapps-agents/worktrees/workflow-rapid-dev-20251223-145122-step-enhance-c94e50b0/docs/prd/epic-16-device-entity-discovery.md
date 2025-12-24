# Epic 16: Device & Entity Discovery

## Epic Overview
**Epic ID**: 16  
**Epic Title**: Home Assistant Device & Entity Discovery  
**Epic Goal**: Discover and maintain complete inventory of all devices, entities, and integrations connected to Home Assistant  
**Epic Status**: Approved  
**Epic Priority**: P1 - HIGH  
**Epic Effort**: Medium (4-6 weeks)  
**Epic Risk**: Low (uses stable HA APIs)

## Epic Description
**As a** system administrator,  
**I want** complete visibility into all devices, entities, and integrations connected to Home Assistant,  
**so that** I can monitor inventory, troubleshoot issues, and understand system topology.

## Business Justification
Currently we capture state change events but lack comprehensive inventory of what's connected to HA. This limits troubleshooting, monitoring, and understanding of the overall system. Complete device/entity discovery enables better operational visibility, device tracking, and foundation for advanced features.

**Research Completed**: Comprehensive research in `docs/research/` shows WebSocket API provides all needed capabilities with minimal overhead.

## Epic Acceptance Criteria
1. **AC1: Device Discovery** - System can query and store all HA devices with metadata
2. **AC2: Entity Discovery** - System can query and store all HA entities with configuration
3. **AC3: Real-Time Updates** - System detects when devices/entities are added/removed/changed
4. **AC4: API Access** - Admin API provides access to device/entity inventory
5. **AC5: Data Persistence** - Device/entity data stored in InfluxDB with 90-day retention

## Epic Stories

### Story 16.1: WebSocket Registry Commands
**Goal**: Implement WebSocket commands to query HA device/entity registries  
**Priority**: P1 - HIGH | **Effort**: 1 week

**Acceptance Criteria**:
- Send `config/device_registry/list` command and parse response
- Send `config/entity_registry/list` command and parse response
- Send `config_entries/list` command and parse response
- Handle errors and malformed responses
- Log discovery results (counts and samples)

### Story 16.2: Data Models & Storage
**Goal**: Create data models and InfluxDB storage for device/entity inventory  
**Priority**: P1 - HIGH | **Effort**: 1 week

**Acceptance Criteria**:
- Create Device, Entity, ConfigEntry data models
- Create InfluxDB buckets: `devices/`, `entities/`
- Implement storage functions (write, query)
- Set 90-day retention policy
- Validate data integrity on storage

### Story 16.3: Real-Time Registry Updates
**Goal**: Subscribe to HA registry events for real-time inventory updates  
**Priority**: P2 - MEDIUM | **Effort**: 1-2 weeks

**Acceptance Criteria**:
- Subscribe to `device_registry_updated` events
- Subscribe to `entity_registry_updated` events
- Process registry update events
- Update storage when devices/entities change
- Log all registry changes

### Story 16.4: Admin API Endpoints
**Goal**: Expose device/entity inventory via Admin API  
**Priority**: P2 - MEDIUM | **Effort**: 1 week

**Acceptance Criteria**:
- GET `/api/devices` - List all devices
- GET `/api/devices/{id}` - Get device details
- GET `/api/entities` - List all entities
- GET `/api/entities/{id}` - Get entity details
- GET `/api/integrations` - List config entries
- Support filtering and pagination

## Technical Requirements

### WebSocket Integration
- Reuse existing WebSocket connection
- Add 3 new command types (device/entity/config registries)
- Subscribe to 2 new event types (registry updates)

### Data Storage
- New InfluxDB buckets: `devices/`, `entities/`
- 90-day retention policy
- ~200MB storage for typical home (100 devices, 500 entities)

### Performance
- Initial discovery: ~4 seconds on startup
- Real-time updates: < 100ms latency
- System overhead: < 5% additional load

### Data Models (Simple)
```python
Device:
  - device_id: str
  - name: str
  - manufacturer: str
  - model: str
  - sw_version: str
  - area_id: str
  - entity_count: int

Entity:
  - entity_id: str
  - device_id: str
  - domain: str (light, sensor, switch)
  - platform: str
  - unique_id: str
  - area_id: str
```

## Dependencies
- **Existing**: WebSocket ingestion service (operational)
- **Existing**: InfluxDB storage (operational)
- **Existing**: Admin API service (operational)
- **Research**: Complete (docs/research/)

## Out of Scope (Future Enhancements)
- Periodic full sync (can add later if needed)
- Dashboard UI for device browser (separate epic)
- Device topology visualization (separate epic)
- Historical device tracking beyond 90 days

## Success Criteria
- All HA devices discoverable via API
- All HA entities discoverable via API
- Real-time detection of device/entity changes
- < 5% performance overhead
- < 2% storage increase

## Implementation Notes

### Keep It Simple
- Use existing WebSocket connection (don't create new one)
- Minimal data models (no over-engineering)
- Simple storage schema (flat, not complex relationships)
- Basic API endpoints (no advanced features initially)

### Existing Patterns to Follow
- WebSocket command handling: `websocket_client.py`
- Event processing: `event_processor.py`
- InfluxDB writes: `influxdb_wrapper.py`
- API endpoints: `admin-api/src/main.py`

## Timeline
**Week 1-2**: Story 16.1 & 16.2 (Foundation)  
**Week 3-4**: Story 16.3 (Real-time updates)  
**Week 5-6**: Story 16.4 (API endpoints)

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| HA API changes | Low | Using stable, documented APIs |
| Performance impact | Low | < 5% overhead measured |
| Storage growth | Low | 90-day retention, ~200MB |
| Integration complexity | Low | Reusing existing infrastructure |

**Overall Risk**: **LOW** - Proven APIs, existing infrastructure, comprehensive research

## Related Documentation
- **Research**: `docs/research/RESEARCH_SUMMARY.md`
- **Architecture**: `docs/architecture/tech-stack.md`
- **WebSocket Service**: `services/websocket-ingestion/`
- **Admin API**: `services/admin-api/`
- **Context7 KB**: `docs/kb/context7-cache/libraries/homeassistant/docs.md`

---

**Created**: October 12, 2025  
**Status**: Ready for Story Creation  
**Next Step**: Create detailed stories 16.1-16.4

