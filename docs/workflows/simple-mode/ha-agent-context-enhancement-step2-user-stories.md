# Step 2: User Stories - HA AI Agent Context Enhancement

## Story 1: Device State Context Service
**As a** user of HA AI Agent  
**I want** the system to include current device states when generating automations  
**So that** the LLM can make smarter decisions about automation logic

**Acceptance Criteria:**
- Service extracts entity IDs from user prompt
- Fetches current states via Data API or HA Client
- Formats states for context inclusion
- Implements caching (30-60 second TTL)
- Gracefully degrades if dependencies unavailable
- Integrates with ContextBuilder

**Story Points:** 5  
**Priority:** High

---

## Story 2: Recent Automation Patterns Service
**As a** user of HA AI Agent  
**I want** the system to learn from my recent automation patterns  
**So that** it can suggest similar automations or follow my preferences

**Acceptance Criteria:**
- Service queries HA for last 5-10 automations
- Extracts patterns (triggers, actions, modes)
- Formats patterns for context inclusion
- Implements caching (5-10 minute TTL)
- Gracefully degrades if HA unavailable

**Story Points:** 8  
**Priority:** High

---

## Story 3: Conflict Detection Service
**As a** user of HA AI Agent  
**I want** the system to detect potential conflicts with existing automations  
**So that** I can avoid creating overlapping or conflicting automations

**Acceptance Criteria:**
- Service analyzes user prompt for conflict indicators
- Queries existing automations from HA
- Detects potential conflicts (same entities, overlapping times)
- Generates warnings included in preview
- Does not block automation creation (warning only)

**Story Points:** 8  
**Priority:** Medium

---

## Story 4: Enhancement Preferences Tracking
**As a** user of HA AI Agent  
**I want** the system to remember my enhancement preferences  
**So that** future enhancement suggestions are more relevant

**Acceptance Criteria:**
- ConversationService tracks enhancement selections
- Preferences stored per conversation
- Enhancement tool includes preferences
- Preferences influence suggestion generation

**Story Points:** 5  
**Priority:** Medium
