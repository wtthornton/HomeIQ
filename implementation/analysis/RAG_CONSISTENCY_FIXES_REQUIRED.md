# RAG Knowledge Base Consistency Fixes Required

**Date:** January 11, 2026  
**Status:** Analysis Complete - Fixes Required  
**Issues Found:** 13 files with contradictions or outdated references

## Critical Issues (Contradict Epic 31 Architecture)

### 1. Files Showing Active enrichment-pipeline Usage (CRITICAL)

These files show HTTP POST to enrichment-pipeline which contradicts Epic 31:

1. **home-assistant/HA_WEBSOCKET_CALL_TREE.md**
   - Shows: `HTTP POST {enrichment_url}/events [INTERNAL API CALL]`
   - Location: Line 170
   - **Fix Required:** Update call tree to show direct InfluxDB writes

2. **iot-home-automation/HA_WEBSOCKET_CALL_TREE.md**
   - Shows: `HTTP POST {enrichment_url}/events [INTERNAL API CALL]`
   - Location: Line 170
   - **Fix Required:** Update call tree to show direct InfluxDB writes

3. **microservices-architecture/event-flow-architecture.md**
   - Shows: "WebSocket Service flattens Home Assistant events before sending to Enrichment Pipeline"
   - Location: Line 379
   - **Fix Required:** Update to reflect direct InfluxDB writes

### 2. Files Mentioning enrichment-pipeline Without Deprecation Context

These files mention enrichment-pipeline but don't clearly mark it as deprecated:

4. **home-assistant/HOME_ASSISTANT_API_KB_UPDATE_2025-10-12.md**
   - **Fix Required:** Add Epic 31 deprecation note

5. **home-assistant/HOME_ASSISTANT_QUICK_REF.md**
   - **Fix Required:** Add Epic 31 deprecation note

6. **microservices-architecture/api-guidelines.md**
   - **Fix Required:** Add Epic 31 deprecation note

7. **microservices-architecture/compliance-standard-framework.md**
   - **Fix Required:** Add Epic 31 deprecation note

8. **microservices-architecture/DOCKER_COMPOSE_SERVICES_REFERENCE.md**
   - **Fix Required:** Mark enrichment-pipeline as deprecated/removed

9. **time-series-analytics/3.2.influxdb-schema-design-storage.md**
   - **Fix Required:** Add Epic 31 deprecation note

### 3. Files With Old Year References (2024/2023)

10. **home-assistant/docs.md**
    - Contains: "2024-04-22", "2024-10-12" (example dates)
    - **Fix Required:** Update to 2025/2026 dates or mark as examples

11. **microservices-architecture/api-guidelines.md**
    - Contains: 2024 references
    - **Fix Required:** Update dates

12. **microservices-architecture/database-schema.md**
    - Contains: 2024 references
    - **Fix Required:** Update dates

13. **microservices-architecture/introduction.md**
    - Contains: 2024 references
    - **Fix Required:** Update dates

14. **microservices-architecture/source-tree.md**
    - Contains: 2024 references
    - **Fix Required:** Update dates

15. **time-series-analytics/3.2-influxdb-schema-design-storage-risk-20241219.md**
    - Contains: 2024 references (filename also has date)
    - **Fix Required:** Update dates or mark as historical

16. **time-series-analytics/3.2.influxdb-schema-design-storage.md**
    - Contains: 2024 references
    - **Fix Required:** Update dates

## Fix Strategy

### Phase 1: Critical Architecture Contradictions (Priority 1)
Fix files that show active enrichment-pipeline usage:
1. Update call tree diagrams to show direct InfluxDB writes
2. Update event-flow-architecture.md decision text
3. Add clear Epic 31 deprecation notes

### Phase 2: Missing Deprecation Context (Priority 2)
Add Epic 31 deprecation notes to files mentioning enrichment-pipeline

### Phase 3: Date Updates (Priority 3)
Update year references to 2025/2026 or mark as historical examples

## Expected Outcomes

After fixes:
- ✅ No contradictions with Epic 31 architecture
- ✅ All enrichment-pipeline references include deprecation context
- ✅ All dates updated to 2025/2026 or marked as examples
- ✅ Consistent architecture patterns across all files
- ✅ Clear distinction between current (Epic 31) and historical patterns
