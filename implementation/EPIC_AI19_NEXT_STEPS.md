# Epic AI-19: Next Steps

**Date:** January 2025  
**Status:** Epic AI-19 Complete ✅  
**Next Phase:** OpenAI Integration & Tool Implementation

---

## Current Status

### ✅ Completed (Epic AI-19)

1. **Tier 1 Context Injection System**
   - Entity Inventory Summary Service
   - Areas/Rooms List Service
   - Available Services Summary Service
   - Device Capability Patterns Service
   - Helpers & Scenes Summary Service
   - Context Builder orchestration

2. **System Prompt**
   - Comprehensive system prompt defining agent role and behavior
   - Integration with context builder
   - API endpoints for prompt retrieval

3. **Infrastructure**
   - FastAPI service foundation
   - SQLite caching system
   - Docker setup
   - Health checks and API endpoints

---

## Next Steps: OpenAI Agent Implementation

### Phase 1: Testing & Validation (1-2 days)

**Priority:** High  
**Effort:** 4-6 hours

#### 1.1 Test Context Injection
- [ ] Verify all context components return valid data
- [ ] Test caching behavior (TTL expiration)
- [ ] Validate context format and token count
- [ ] Test error handling (service unavailable scenarios)

#### 1.2 Test System Prompt
- [ ] Review system prompt for clarity and completeness
- [ ] Test prompt token count (~500 tokens)
- [ ] Validate complete prompt (system + context) format
- [ ] Test API endpoints (`/api/v1/system-prompt`, `/api/v1/complete-prompt`)

#### 1.3 Integration Testing
- [ ] Test with real Home Assistant instance
- [ ] Verify data-api integration
- [ ] Verify device-intelligence-service integration
- [ ] Test with various Home Assistant configurations

---

### Phase 2: OpenAI Integration (3-5 days)

**Priority:** High  
**Effort:** 16-24 hours

#### 2.1 OpenAI Client Setup
- [ ] Add OpenAI Python SDK to requirements.txt
- [ ] Create OpenAI client wrapper
- [ ] Implement API key configuration
- [ ] Add retry logic and error handling
- [ ] Support for GPT-5.1 (or current model)

#### 2.2 Conversation Handler
- [ ] Create conversation management service
- [ ] Implement message history tracking
- [ ] Add context injection to each conversation
- [ ] Implement streaming responses (optional)
- [ ] Add conversation state management

#### 2.3 Prompt Assembly
- [ ] Integrate `build_complete_system_prompt()` into conversation flow
- [ ] Add user message formatting
- [ ] Implement context refresh logic (when to update context)
- [ ] Add token counting and budget management

**Files to Create:**
- `src/clients/openai_client.py` - OpenAI API client
- `src/services/conversation_service.py` - Conversation management
- `src/models/conversation.py` - Conversation data models

---

### Phase 3: Tool/Function Calling (5-7 days) ✅ **COMPLETE**

**Priority:** High  
**Effort:** 24-32 hours  
**Status:** ✅ **COMPLETE** (January 2025)

#### 3.1 Home Assistant Tools Definition ✅
- [x] Define OpenAI function schemas for HA operations:
  - [x] `get_entity_state` - Get current state of entity
  - [x] `call_service` - Call Home Assistant service (replaces set_entity_state)
  - [x] `get_entities` - List entities (with filtering)
  - [x] `create_automation` - Create new automation
  - [x] `update_automation` - Update existing automation
  - [x] `delete_automation` - Delete automation
  - [x] `get_automations` - List automations
  - [x] `test_automation_yaml` - Test automation YAML syntax

#### 3.2 Tool Implementation ✅
- [x] Implement each tool function
- [x] Add error handling and validation
- [x] Add entity ID validation (regex pattern matching)
- [x] Implement service parameter validation
- [x] Add automation YAML validation

#### 3.3 Tool Execution Handler ✅
- [x] Create tool execution service
- [x] Implement tool call routing
- [x] Add result formatting for OpenAI
- [x] Handle tool execution errors gracefully
- [x] Add logging for tool calls

#### 3.4 System Prompt Updates ✅
- [x] Update system prompt with explicit tool definitions
- [x] Add tool selection guidelines and decision tree
- [x] Document when to use each tool

#### 3.5 API Endpoints ✅
- [x] `GET /api/v1/tools` - Get available tool schemas
- [x] `POST /api/v1/tools/execute` - Execute tool call
- [x] `POST /api/v1/tools/execute-openai` - Execute tool call (OpenAI format)

**Files Created:**
- ✅ `src/services/tool_service.py` - Tool execution handler
- ✅ `src/tools/__init__.py` - Tools package
- ✅ `src/tools/ha_tools.py` - Home Assistant tool implementations
- ✅ `src/tools/tool_schemas.py` - OpenAI function schemas
- ✅ `tests/test_tool_service.py` - Tool service tests
- ✅ `tests/test_ha_tools.py` - Tool handler tests

**Implementation Notes:**
- All 8 tools implemented following 2025 best practices
- Comprehensive error handling and validation
- YAML validation for automations
- Entity ID format validation
- Tool execution logging
- OpenAI-compatible response formatting

---

### Phase 4: API Endpoints (2-3 days)

**Priority:** Medium  
**Effort:** 12-16 hours

#### 4.1 Conversation Endpoints
- [ ] `POST /api/v1/conversations` - Start new conversation
- [ ] `POST /api/v1/conversations/{id}/messages` - Send message
- [ ] `GET /api/v1/conversations/{id}` - Get conversation history
- [ ] `DELETE /api/v1/conversations/{id}` - Delete conversation

#### 4.2 Automation Endpoints
- [ ] `POST /api/v1/automations` - Create automation (via agent)
- [ ] `GET /api/v1/automations` - List automations
- [ ] `POST /api/v1/automations/{id}/test` - Test automation

#### 4.3 WebSocket Support (Optional)
- [ ] WebSocket endpoint for real-time conversations
- [ ] Streaming response support

**Files to Modify:**
- `src/main.py` - Add new endpoints
- `src/api/` - Create API router modules

---

### Phase 5: Database & Persistence (2-3 days)

**Priority:** Medium  
**Effort:** 12-16 hours

#### 5.1 Conversation Storage
- [ ] Add conversation table to SQLite
- [ ] Store message history
- [ ] Store conversation metadata
- [ ] Add conversation cleanup (TTL-based)

#### 5.2 Automation Tracking
- [ ] Track automations created by agent
- [ ] Store automation metadata
- [ ] Link automations to conversations

**Files to Modify:**
- `src/database.py` - Add new models
- `src/models/` - Add conversation and automation models

---

### Phase 6: Testing & Quality Assurance (3-4 days)

**Priority:** High  
**Effort:** 16-24 hours

#### 6.1 Unit Tests
- [ ] Test OpenAI client wrapper
- [ ] Test conversation service
- [ ] Test tool execution
- [ ] Test prompt assembly
- [ ] Test error handling

#### 6.2 Integration Tests
- [ ] Test full conversation flow
- [ ] Test automation creation via agent
- [ ] Test tool calling scenarios
- [ ] Test error scenarios

#### 6.3 End-to-End Tests
- [ ] Test complete user journey
- [ ] Test with real Home Assistant
- [ ] Test with various device configurations
- [ ] Performance testing

---

## Future Enhancements (Post-MVP)

### Tier 2 Context (Future Epic)
- Entity details (full entity information)
- Existing automations summary
- Device health scores
- Recent events/state changes

### Tier 3 Context (Future Epic)
- Historical patterns
- Blueprint library
- User preferences
- Automation templates

### Advanced Features
- Multi-turn conversation optimization
- Context compression
- Dynamic context injection (based on conversation)
- Voice assistant integration
- Multi-home support

---

## Recommended Implementation Order

1. **Phase 1** - Testing & Validation (validate current work)
2. **Phase 2** - OpenAI Integration (core functionality)
3. **Phase 3** - Tool/Function Calling (enable automation creation)
4. **Phase 4** - API Endpoints (expose functionality)
5. **Phase 5** - Database & Persistence (store conversations)
6. **Phase 6** - Testing & QA (ensure quality)

**Total Estimated Effort:** 84-112 hours (2-3 weeks)

---

## Key Dependencies

- ✅ Epic AI-19 (Tier 1 Context Injection) - Complete
- ✅ System Prompt - Complete
- ⏳ OpenAI API Key - Required for Phase 2
- ⏳ Home Assistant instance - Required for testing
- ⏳ Tool definitions - Required for Phase 3

---

## Success Criteria

### MVP (Minimum Viable Product)
- [ ] Agent can have basic conversations
- [ ] Agent can query entity states
- [ ] Agent can create simple automations
- [ ] Agent uses context injection effectively
- [ ] API endpoints functional

### Production Ready
- [ ] Full test coverage (>90%)
- [ ] Error handling comprehensive
- [ ] Performance acceptable (<2s response time)
- [ ] Documentation complete
- [ ] Security reviewed

---

## References

- Epic AI-19: HA AI Agent Service - Tier 1 Context Injection
- OpenAI Function Calling Documentation
- Home Assistant REST API Documentation
- `services/ai-automation-service` - Reference for patterns

---

## Questions to Resolve

1. **Model Selection**: GPT-5.1 or GPT-4o? (GPT-5.1 may not be available yet)
2. **Streaming**: Do we need streaming responses for better UX?
3. **Conversation History**: How long to retain conversations?
4. **Rate Limiting**: Do we need rate limiting on API endpoints?
5. **Authentication**: Do we need user authentication for conversations?

---

## Next Immediate Actions

1. **Test current implementation** - Verify context injection works
2. **Review system prompt** - Ensure it's comprehensive
3. **Set up OpenAI account** - Get API key for testing
4. **Create Phase 2 epic** - Plan OpenAI integration stories
5. **Start Phase 2 implementation** - Begin OpenAI client setup

