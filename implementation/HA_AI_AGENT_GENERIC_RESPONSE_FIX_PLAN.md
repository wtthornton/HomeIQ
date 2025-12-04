# HA AI Agent Generic Response Fix Plan

**Issue Identified:** January 2025  
**Status:** 📋 Planning  
**Priority:** High  
**Service:** `ha-ai-agent-service` (Port 8030)

---

## Problem Summary

The HA AI Agent is responding with generic welcome messages instead of processing user requests. When users send specific automation requests (e.g., "Make the office lights blink red every 15 mins and then return back to the state they where"), the agent responds with generic messages like "How can I assist you with your Home Assistant automations today?" instead of:

1. Understanding the user's request
2. Using available tools to gather information
3. Creating the requested automation
4. Providing a helpful response

### Root Cause Analysis

Based on code review and testing, the issue appears to be:

1. **Conversation History Confusion**: Old conversations may contain welcome messages that confuse the model
2. **System Prompt Clarity**: The system prompt may not be explicit enough about processing user requests immediately
3. **Message Assembly**: The way messages are assembled might not emphasize the user's current request
4. **Tool Call Behavior**: The model might not be properly instructed to use tools for automation creation

---

## Fix Strategy

### Phase 1: System Prompt Enhancement (High Priority)

**Goal:** Make the system prompt more explicit about processing user requests immediately.

**Changes:**
1. Add explicit instruction at the start of system prompt:
   - "When a user sends a message, immediately process their request. Do not respond with generic welcome messages."
   - "If the user asks for an automation, use the available tools to create it."
   - "Only provide welcome messages if the conversation is truly empty (no user messages)."

2. Enhance the "Response Format" section:
   - Add: "When a user asks for an automation, immediately use `get_entities` to find relevant devices, then use `test_automation_yaml` and `create_automation` to create it."
   - Remove ambiguity about when to use tools vs. when to just chat

3. Add explicit examples in system prompt:
   ```
   Example interaction:
   User: "Make the office lights blink red every 15 mins"
   Assistant: [Should immediately use get_entities to find office lights, then create_automation]
   ```

**Files to Modify:**
- `services/ha-ai-agent-service/src/prompts/system_prompt.py`

**Estimated Effort:** 1-2 hours

---

### Phase 2: Conversation History Cleanup (Medium Priority)

**Goal:** Ensure conversation history doesn't contain confusing welcome messages.

**Changes:**
1. Add validation in `prompt_assembly_service.py`:
   - Check if conversation history contains generic welcome messages
   - If detected, remove them before sending to OpenAI
   - Log when welcome messages are detected and removed

2. Add helper function to detect generic responses:
   ```python
   def is_generic_welcome_message(content: str) -> bool:
       """Detect if message is a generic welcome message"""
       generic_patterns = [
           "How can I assist you",
           "What can I help you with",
           "I'm here to help",
           # Add more patterns
       ]
       return any(pattern.lower() in content.lower() for pattern in generic_patterns)
   ```

3. Filter conversation history:
   - Remove assistant messages that are generic welcome messages
   - Keep only substantive assistant responses

**Files to Modify:**
- `services/ha-ai-agent-service/src/services/prompt_assembly_service.py`
- `services/ha-ai-agent-service/src/services/conversation_service.py` (add helper)

**Estimated Effort:** 2-3 hours

---

### Phase 3: Message Assembly Enhancement (Medium Priority)

**Goal:** Ensure the user's current request is emphasized in the message assembly.

**Changes:**
1. Modify `assemble_messages()` to:
   - Add a clear instruction before the user's message: "USER REQUEST: [message]"
   - Ensure the user's message is always the last message (already done, but verify)
   - Add explicit instruction: "Process the USER REQUEST above. Do not provide generic responses."

2. Add user message emphasis:
   ```python
   # In assemble_messages, before adding user message:
   emphasized_user_message = f"""USER REQUEST (process this immediately):
   {user_message}

   Instructions: Process this request now. Use tools if needed. Do not respond with generic welcome messages."""
   ```

**Files to Modify:**
- `services/ha-ai-agent-service/src/services/prompt_assembly_service.py`

**Estimated Effort:** 1-2 hours

---

### Phase 4: Tool Call Instruction Enhancement (High Priority)

**Goal:** Make tool usage more explicit and mandatory for automation requests.

**Changes:**
1. Enhance system prompt tool section:
   - Add: "When a user requests an automation, you MUST use tools. Do not just describe what you would do - actually create the automation."
   - Add: "If you don't know which entities to use, use `get_entities` to search. Do not guess."

2. Add explicit tool call examples:
   ```
   User: "Make office lights blink red every 15 minutes"
   Required actions:
   1. Call get_entities(domain="light", area_id="office") to find office lights
   2. Call test_automation_yaml() to validate the automation YAML
   3. Call create_automation() to create the automation
   4. Respond with confirmation
   ```

**Files to Modify:**
- `services/ha-ai-agent-service/src/prompts/system_prompt.py`

**Estimated Effort:** 1 hour

---

### Phase 5: Response Validation (Low Priority)

**Goal:** Detect and prevent generic responses before returning to user.

**Changes:**
1. Add response validation in `chat_endpoints.py`:
   - After getting response from OpenAI, check if it's a generic welcome message
   - If detected, log warning and optionally retry with more explicit instruction
   - Or add a follow-up message to force tool usage

2. Add validation function:
   ```python
   def is_generic_response(content: str, user_message: str) -> bool:
       """Check if response is generic and doesn't address user's request"""
       if is_generic_welcome_message(content):
           return True
       # Check if response doesn't mention key terms from user message
       # (simple heuristic - can be improved)
       return False
   ```

**Files to Modify:**
- `services/ha-ai-agent-service/src/api/chat_endpoints.py`

**Estimated Effort:** 2-3 hours

---

## Implementation Order

1. **Phase 1** (System Prompt Enhancement) - **Start here** - Highest impact, lowest risk
2. **Phase 4** (Tool Call Instruction Enhancement) - High impact, complements Phase 1
3. **Phase 3** (Message Assembly Enhancement) - Medium impact, supports Phase 1
4. **Phase 2** (Conversation History Cleanup) - Medium impact, prevents future issues
5. **Phase 5** (Response Validation) - Low priority, nice to have

---

## Testing Strategy

### Manual Testing
1. Test with new conversation:
   - Send: "Make the office lights blink red every 15 mins and then return back to the state they where"
   - Verify: Agent uses tools to find entities and create automation
   - Verify: Response addresses the specific request, not generic welcome

2. Test with existing conversation:
   - Load conversation with previous messages
   - Send new automation request
   - Verify: Agent processes new request, not confused by history

3. Test edge cases:
   - Empty conversation (should still process request, not just welcome)
   - Ambiguous requests (should ask clarifying questions, not generic response)
   - Multiple requests in one message (should handle all)

### Automated Testing
1. Add unit test for `is_generic_welcome_message()` function
2. Add integration test for chat endpoint:
   - Send automation request
   - Verify response contains automation creation (tool calls)
   - Verify response is not generic welcome message

3. Add test for conversation history cleanup:
   - Create conversation with generic welcome message
   - Send new request
   - Verify generic message is filtered out

**Test Files:**
- `services/ha-ai-agent-service/tests/test_chat_endpoints.py`
- `services/ha-ai-agent-service/tests/test_prompt_assembly_service.py`
- `services/ha-ai-agent-service/tests/integration/test_chat_flow_e2e.py`

---

## Success Criteria

✅ **Primary:**
- Agent processes user requests immediately (no generic welcome messages)
- Agent uses tools appropriately for automation requests
- Agent creates automations when requested (not just describes them)

✅ **Secondary:**
- Conversation history doesn't confuse the model
- Response quality improves (more specific, actionable responses)
- Tool call rate increases for automation requests

✅ **Metrics:**
- Generic response rate: < 5% (currently appears to be ~50%+)
- Tool call rate for automation requests: > 80% (currently unknown)
- User satisfaction: Improved (qualitative)

---

## Risk Assessment

**Low Risk:**
- Phase 1 (System Prompt Enhancement) - Only changes prompt text
- Phase 4 (Tool Call Instruction Enhancement) - Only changes prompt text

**Medium Risk:**
- Phase 3 (Message Assembly Enhancement) - Changes message format, could affect token counts
- Phase 2 (Conversation History Cleanup) - Changes conversation history, could affect context

**Mitigation:**
- Test thoroughly before deploying
- Monitor token usage after Phase 3
- Monitor response quality after Phase 2
- Roll back if issues detected

---

## Rollout Plan

1. **Development:** Implement Phase 1 and Phase 4 first (prompt changes only)
2. **Testing:** Manual testing with real requests
3. **Staging:** Deploy to staging environment, test with sample conversations
4. **Production:** Deploy with monitoring
5. **Iterate:** Implement remaining phases based on results

---

## Related Files

### Core Files
- `services/ha-ai-agent-service/src/prompts/system_prompt.py` - System prompt definition
- `services/ha-ai-agent-service/src/services/prompt_assembly_service.py` - Message assembly
- `services/ha-ai-agent-service/src/api/chat_endpoints.py` - Chat endpoint
- `services/ha-ai-agent-service/src/services/conversation_service.py` - Conversation management

### Test Files
- `services/ha-ai-agent-service/tests/test_chat_endpoints.py`
- `services/ha-ai-agent-service/tests/test_prompt_assembly_service.py`
- `services/ha-ai-agent-service/tests/integration/test_chat_flow_e2e.py`

---

## Notes

- This fix addresses a critical UX issue where users get unhelpful generic responses
- The fix is primarily prompt engineering, which is low-risk and high-impact
- Conversation history cleanup prevents future issues but may not be the root cause
- Response validation is a safety net but may not be necessary if prompt fixes work

**Next Steps:**
1. Review and approve this plan
2. Start with Phase 1 (System Prompt Enhancement)
3. Test thoroughly before moving to next phase
4. Monitor results and iterate

