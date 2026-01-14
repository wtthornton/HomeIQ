# Enhanced Prompt: Create device API service for fetching devices from data-api. Service should support filtering by device_type, area_id, manufacturer, model, and search functionality. Must follow existing API patterns from blueprintSuggestionsApi.ts, use API_CONFIG.DATA for base URL, and include proper TypeScript interfaces for Device, DeviceResponse, and DevicesListResponse. Include error handling and authentication headers pattern. File location: services/ai-automation-ui/src/services/deviceApi.ts

[Context7: Detected 3 libraries. Documentation available for 3 libraries.]

## Metadata
- **Created**: 2026-01-14T10:19:14.904913

## Analysis
- **Intent**: bug-fix
- **Scope**: large
- **Workflow Type**: greenfield
- **Complexity**: high
- **Detected Domains**: security, database, api, ui, integration
- **Technologies**: TypeScript, Home Assistant, playwright, puppeteer, typescript

### Analysis Details
```
Analyze the following prompt and extract structured information.

Prompt:
Create device API service for fetching devices from data-api. Service should support filtering by device_type, area_id, manufacturer, model, and search functionality. Must follow existing API patterns from blueprintSuggestionsApi.ts, use API_CONFIG.DATA for base URL, and include proper TypeScript interfaces for Device, DeviceResponse, and DevicesListResponse. Include error handling and authentication headers pattern. File ...
```

## Requirements
### Functional Requirements
- *No functional requirements extracted yet. This will be populated during requirements gathering stage.*

### Non-Functional Requirements
- *No non-functional requirements extracted yet.*

## Architecture Guidance
*Architecture guidance will be generated during the architecture stage.*

## Codebase Context
## Codebase Context

### Related Files
- `services\admin-api\src\devices_endpoints.py`
- `services\data-api\src\models\device.py`
- `services\ha-ai-agent-service\src\services\context_builder.backup_20260102_103010.py`
- `services\ha-ai-agent-service\src\services\devices_summary_service.py`
- `services\ha-ai-agent-service\src\services\context_builder.py`
- `services\archive\2025-q4\ai-automation-service\src\api\suggestion_router.py`
- `services\archive\2025-q4\ai-automation-service\src\api\conversational_router.py`
- `services\data-api\src\devices_endpoints.py`
- `services\ha-ai-agent-service\src\services\device_state_context_service.py`
- `services\device-intelligence-service\scripts\recreate_database.py`

### Existing Patterns
- **Common Import Patterns** (architectural): Commonly imported modules: datetime, fastapi, pydantic, influxdb_client, sqlalchemy
- **Class Structure Patterns** (structure): Common class types: Service

### Cross-References
- No cross-references found

### Context Summary
Found 10 related files in the codebase. Extracted 2 patterns and 0 cross-references. Use these as reference when implementing new features.

### Related Files
- C:\cursor\HomeIQ\services\admin-api\src\devices_endpoints.py
- C:\cursor\HomeIQ\services\data-api\src\models\device.py
- C:\cursor\HomeIQ\services\ha-ai-agent-service\src\services\context_builder.backup_20260102_103010.py
- C:\cursor\HomeIQ\services\ha-ai-agent-service\src\services\devices_summary_service.py
- C:\cursor\HomeIQ\services\ha-ai-agent-service\src\services\context_builder.py
- C:\cursor\HomeIQ\services\archive\2025-q4\ai-automation-service\src\api\suggestion_router.py
- C:\cursor\HomeIQ\services\archive\2025-q4\ai-automation-service\src\api\conversational_router.py
- C:\cursor\HomeIQ\services\data-api\src\devices_endpoints.py
- C:\cursor\HomeIQ\services\ha-ai-agent-service\src\services\device_state_context_service.py
- C:\cursor\HomeIQ\services\device-intelligence-service\scripts\recreate_database.py

### Existing Patterns
- {'type': 'architectural', 'name': 'Common Import Patterns', 'description': 'Commonly imported modules: datetime, fastapi, pydantic, influxdb_client, sqlalchemy', 'examples': ['C:\\cursor\\HomeIQ\\services\\admin-api\\src\\devices_endpoints.py', 'C:\\cursor\\HomeIQ\\services\\data-api\\src\\models\\device.py', 'C:\\cursor\\HomeIQ\\services\\ha-ai-agent-service\\src\\services\\context_builder.backup_20260102_103010.py'], 'confidence': 1.0}
- {'type': 'structure', 'name': 'Class Structure Patterns', 'description': 'Common class types: Service', 'examples': ['C:\\cursor\\HomeIQ\\services\\admin-api\\src\\devices_endpoints.py', 'C:\\cursor\\HomeIQ\\services\\data-api\\src\\models\\device.py', 'C:\\cursor\\HomeIQ\\services\\ha-ai-agent-service\\src\\services\\context_builder.backup_20260102_103010.py'], 'confidence': 0.3333333333333333}

## Quality Standards
### Code Quality Thresholds
- **Overall Score Threshold**: 70.0

## Implementation Strategy
## Enhanced Prompt