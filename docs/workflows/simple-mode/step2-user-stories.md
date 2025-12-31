# Step 2: User Stories

**Date:** December 31, 2025  
**Workflow:** Entity Validation Fix for ai-automation-service-new  
**Step:** 2 of 7

## User Stories

### Story 1: Entity Context Fetching (R1)
**As a** developer using ai-automation-service-new  
**I want** the service to fetch real entities from Data API before generating YAML  
**So that** the LLM has access to actual entity IDs

**Acceptance Criteria:**
- Service fetches entities before YAML generation
- Entities are cached for request duration
- Fetch failures are handled gracefully

**Story Points:** 3  
**Priority:** P0

### Story 2: Entity Context in LLM Prompts (R2)
**As a** developer using ai-automation-service-new  
**I want** entity context included in LLM prompts  
**So that** the LLM generates YAML with real entity IDs only

**Acceptance Criteria:**
- All OpenAI client methods receive entity context
- System prompts instruct LLM to use only provided entities
- Entity context is formatted optimally

**Story Points:** 5  
**Priority:** P0

### Story 3: Mandatory Entity Validation (R3)
**As a** developer using ai-automation-service-new  
**I want** entity validation to be mandatory and fail on invalid entities  
**So that** no YAML with fictional entities is generated

**Acceptance Criteria:**
- Validation runs after YAML generation
- Generation fails if invalid entities found
- Error messages include invalid entity list

**Story Points:** 3  
**Priority:** P0

### Story 4: Enhanced Entity Extraction (R5)
**As a** developer using ai-automation-service-new  
**I want** entity extraction to handle all YAML patterns  
**So that** all entities are validated regardless of where they appear

**Acceptance Criteria:**
- Extracts from template expressions
- Extracts from area targets
- Extracts from scene snapshots
- Extracts from all nested structures

**Story Points:** 5  
**Priority:** P1
