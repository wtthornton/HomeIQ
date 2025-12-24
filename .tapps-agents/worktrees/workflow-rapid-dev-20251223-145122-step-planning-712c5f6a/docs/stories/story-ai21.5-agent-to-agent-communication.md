# Story AI21.5: Agent-to-Agent Communication

**Epic:** AI-21 - Proactive Conversational Agent Service  
**Status:** 🚧 In Progress  
**Points:** 3  
**Effort:** 6-8 hours  
**Created:** December 2025

---

## User Story

**As a** developer,  
**I want** agent-to-agent communication,  
**so that** I can call the HA AI Agent Service with generated prompts.

---

## Business Value

- Enables proactive automation suggestions via agent communication
- Leverages existing HA AI Agent Service capabilities
- Foundation for automated automation creation
- Seamless integration between services

---

## Acceptance Criteria

1. ✅ HAAgentClient class (HTTP client for ha-ai-agent-service:8030)
2. ✅ Conversation initiation (`POST /api/v1/chat`)
3. ✅ Response handling and parsing
4. ✅ Error recovery (retry logic)
5. ✅ Timeout handling (30 seconds default)
6. ✅ Response validation
7. ✅ Logging for agent-to-agent calls
8. ✅ Unit tests for communication client

---

## Tasks

- [x] Create HAAgentClient class
- [x] Implement conversation initiation
- [x] Add response handling
- [x] Add retry logic and error recovery
- [x] Add timeout handling
- [x] Add response validation
- [x] Add comprehensive logging
- [x] Write unit tests

---

## File List

- `services/proactive-agent-service/src/clients/ha_agent_client.py` (NEW)
- `services/proactive-agent-service/tests/test_ha_agent_client.py` (NEW)

---

## Implementation Notes

- Uses httpx for async HTTP calls
- Retry logic with exponential backoff
- Graceful degradation on errors
- Follows existing client patterns from Story AI21.3

---

## QA Results

_To be completed after implementation_

