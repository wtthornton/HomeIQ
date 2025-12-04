# HA AI Agent Generic Response Fix - Debugging Guide

**Created:** January 2025  
**Purpose:** Guide for debugging and monitoring the generic response fix implementation

---

## Logging Overview

Comprehensive logging has been added throughout the system to track:
- Generic message detection and filtering
- User message emphasis
- Response validation
- Tool call execution
- Message assembly flow
- Edge cases and errors

---

## Log Categories

### 1. Generic Message Filter (`[Generic Message Filter]`)

**Location:** `prompt_assembly_service.py` - Conversation history filtering

**Logs:**
- **INFO**: When generic messages are filtered from history
  ```
  [Generic Message Filter] Conversation {id}: Filtered {count} generic message(s) from history ({original} -> {filtered} messages)
  ```
- **INFO**: Individual generic message detection
  ```
  [Generic Message Filter] Conversation {id}: Filtered generic welcome message (count: {n}). Content preview: {content}...
  ```

**What to Look For:**
- High filter counts indicate old conversations with many generic responses
- If filtering happens frequently, it means the fix is working to clean up history
- Monitor if filtered count matches expected patterns

---

### 2. Message Emphasis (`[Message Emphasis]`)

**Location:** `prompt_assembly_service.py` - User request emphasis

**Logs:**
- **DEBUG**: Normal emphasis (last message is user message)
  ```
  [Message Emphasis] Conversation {id}: Emphasized user request (last message). Original length: {n}, Emphasized length: {m}
  ```
- **WARNING**: Fallback scenario (last message isn't user message)
  ```
  [Message Emphasis] Conversation {id}: Last message is not a user message (role: {role}). Using fallback to find last user message.
  ```
- **INFO**: Fallback success
  ```
  [Message Emphasis] Conversation {id}: Emphasized user request using fallback (index {idx}). Total messages: {count}
  ```
- **ERROR**: No user message found (critical issue)
  ```
  [Message Emphasis] Conversation {id}: No user message found in conversation history! Total messages: {count}
  ```

**What to Look For:**
- **WARNING/ERROR logs**: Indicate edge cases that need investigation
- Normal flow should only show DEBUG logs
- If ERROR appears, there's a bug in message handling

---

### 3. Message Assembly (`[Message Assembly]`)

**Location:** `prompt_assembly_service.py` - Final message assembly

**Logs:**
- **DEBUG**: Message assembly summary
  ```
  [Message Assembly] Conversation {id}: Assembled {n} messages (1 system + {m} history). User message: {preview}...
  ```
- **INFO**: Token budget truncation
  ```
  [Token Budget] Conversation {id}: Messages truncated due to token budget ({original} -> {truncated})
  ```

**What to Look For:**
- Monitor message counts to ensure proper assembly
- Token budget truncation should be rare but logged when it happens

---

### 4. Response Validation (`[Response Validation]`)

**Location:** `chat_endpoints.py` - Response validation after OpenAI call

**Logs:**
- **WARNING**: Generic response detected (critical - indicates fix may not be working)
  ```
  [Response Validation] Conversation {id}: ⚠️ GENERIC WELCOME MESSAGE DETECTED in response!
  This indicates the prompt fixes may not be working.
  User message: {user_msg}...
  Response: {response}...
  Tool calls: {count}
  ```
- **DEBUG**: Normal response (not generic)
  ```
  [Response Validation] Conversation {id}: Response validated - not a generic welcome message.
  Response length: {n}, Tool calls: {count}
  ```

**What to Look For:**
- **WARNING logs are critical**: If you see these, the fix isn't working and needs investigation
- Should see mostly DEBUG logs with "not a generic welcome message"
- Monitor tool call counts - should be > 0 for automation requests

---

### 5. Tool Calls (`[Tool Calls]` / `[Tool Call]`)

**Location:** `chat_endpoints.py` - Tool execution

**Logs:**
- **INFO**: Tool calls summary
  ```
  [Tool Calls] Conversation {id}: Processing {n} tool call(s). Tools: [{tool_names}]
  ```
- **DEBUG**: Individual tool execution
  ```
  [Tool Call] Conversation {id}: Executing {tool_name} with args: {args}
  [Tool Call] Conversation {id}: Completed {tool_name}. Result length: {n}
  ```
- **DEBUG**: No tool calls (may indicate issue for automation requests)
  ```
  [Tool Calls] Conversation {id}: No tool calls in response. User requested: {preview}...
  ```

**What to Look For:**
- For automation requests, should see tool calls (get_entities, test_automation_yaml, create_automation)
- If no tool calls for automation requests, the model isn't following instructions
- Monitor which tools are called to understand model behavior

---

### 6. Chat Request Flow (`[Chat Request]`)

**Location:** `chat_endpoints.py` - Request handling

**Logs:**
- **INFO**: New conversation created
  ```
  [Chat Request] Created new conversation {id} for user message: {preview}...
  ```
- **DEBUG**: Existing conversation used
  ```
  [Chat Request] Using existing conversation {id}. Message count: {n}, User message: {preview}...
  ```
- **DEBUG**: Message assembly start
  ```
  [Chat Request] Conversation {id}: Assembling messages with refresh_context={bool}
  ```
- **DEBUG**: Message assembly complete
  ```
  [Chat Request] Conversation {id}: Assembled {n} messages for OpenAI API call
  ```

**What to Look For:**
- Track conversation lifecycle
- Monitor message counts in existing conversations
- Check refresh_context usage patterns

---

### 7. Chat Completion (`[Chat Complete]`)

**Location:** `chat_endpoints.py` - Request completion summary

**Logs:**
- **INFO**: Complete request summary
  ```
  [Chat Complete] Conversation {id}: Request completed.
  Tokens: {n}, Time: {ms}ms, Tool calls: {count},
  Response length: {n}, Generic response detected: {bool}
  ```

**What to Look For:**
- Monitor token usage trends
- Track response times
- Verify tool call counts match expectations
- Check "Generic response detected" flag (should be False)

---

### 8. Generic Detection (`[Generic Detection]`)

**Location:** `conversation_service.py` - Pattern matching

**Logs:**
- **DEBUG**: Pattern matched (generic detected)
  ```
  [Generic Detection] Matched pattern '{pattern}' in message (length: {n}). Content: {preview}...
  ```
- **DEBUG**: Pattern found but message too long (not flagged)
  ```
  [Generic Detection] Pattern '{pattern}' found but message too long ({n} chars). Not flagged as generic.
  ```

**What to Look For:**
- Monitor which patterns are matching
- Check if false positives occur (pattern found but message too long)
- Adjust patterns if needed based on real-world data

---

## Monitoring Checklist

### Daily Monitoring

1. **Check for WARNING logs** - Any `[Response Validation]` warnings indicate the fix isn't working
2. **Monitor tool call rates** - Should be > 80% for automation requests
3. **Review generic message filtering** - Should decrease over time as old conversations are cleaned
4. **Check ERROR logs** - Any `[Message Emphasis]` errors indicate bugs

### Weekly Analysis

1. **Generic response rate** - Should be < 5% (currently targeting < 5%)
2. **Tool call success rate** - Monitor tool execution success
3. **Response time trends** - Should remain stable
4. **Token usage patterns** - Monitor for anomalies

### Key Metrics to Track

- **Generic Response Rate**: `[Response Validation]` WARNING count / Total requests
- **Tool Call Rate**: `[Tool Calls]` with tool calls / Total automation requests
- **Filter Rate**: `[Generic Message Filter]` filtered messages / Total messages
- **Emphasis Success Rate**: `[Message Emphasis]` DEBUG / Total requests (should be ~100%)

---

## Troubleshooting Guide

### Issue: Generic responses still appearing

**Symptoms:**
- `[Response Validation]` WARNING logs appearing
- Users reporting generic welcome messages

**Debug Steps:**
1. Check `[Chat Request]` logs - verify user message is being received correctly
2. Check `[Message Assembly]` logs - verify messages are assembled correctly
3. Check `[Message Emphasis]` logs - verify user request is being emphasized
4. Check `[Tool Calls]` logs - verify tools are being called (or should be)
5. Review system prompt in logs (if enabled at DEBUG level)

**Possible Causes:**
- System prompt not being applied correctly
- Message emphasis not working
- Conversation history confusing the model
- OpenAI model not following instructions

---

### Issue: No tool calls for automation requests

**Symptoms:**
- `[Tool Calls]` shows "No tool calls in response"
- Users report automations not being created

**Debug Steps:**
1. Check `[Chat Request]` - verify user message contains automation request
2. Check `[Message Emphasis]` - verify request is emphasized
3. Check `[Response Validation]` - verify response isn't generic
4. Review tool call instructions in system prompt

**Possible Causes:**
- Model not recognizing automation requests
- Tool call instructions not clear enough
- Context missing required information

---

### Issue: Message emphasis not working

**Symptoms:**
- `[Message Emphasis]` WARNING or ERROR logs
- User requests not being processed

**Debug Steps:**
1. Check `[Message Assembly]` - verify message count
2. Check conversation history - verify user message is last
3. Check `[Generic Message Filter]` - verify filtering isn't breaking order

**Possible Causes:**
- Conversation reload issue
- Message ordering problem
- History filtering removing user messages (bug)

---

## Log Level Recommendations

### Production
- **INFO**: Generic message filtering, tool calls, chat completion
- **WARNING**: Generic response detection, message emphasis fallbacks
- **ERROR**: Critical issues (no user messages, etc.)
- **DEBUG**: Disabled (too verbose)

### Development/Staging
- **DEBUG**: All logs enabled for full visibility
- Monitor all categories for development

### Troubleshooting Mode
- Enable **DEBUG** level temporarily when investigating issues
- Focus on specific conversation IDs
- Use log filtering: `grep "\[Category\] Conversation {id}"`

---

## Example Log Analysis

### Healthy Request Flow
```
[Chat Request] Created new conversation abc123 for user message: Make the office lights blink...
[Chat Request] Conversation abc123: Assembling messages with refresh_context=False
[Message Assembly] Conversation abc123: Assembled 3 messages (1 system + 2 history). User message: Make the office lights...
[Message Emphasis] Conversation abc123: Emphasized user request (last message). Original length: 65, Emphasized length: 185
[Chat Request] Conversation abc123: Assembled 3 messages for OpenAI API call
[Tool Calls] Conversation abc123: Processing 3 tool call(s). Tools: ['get_entities', 'test_automation_yaml', 'create_automation']
[Tool Call] Conversation abc123: Executing get_entities with args: {'domain': 'light', 'area_id': 'office'}
[Tool Call] Conversation abc123: Completed get_entities. Result length: 245
[Response Validation] Conversation abc123: Response validated - not a generic welcome message. Response length: 342, Tool calls: 3
[Chat Complete] Conversation abc123: Request completed. Tokens: 1234, Time: 2345ms, Tool calls: 3, Response length: 342, Generic response detected: False
```

### Problematic Request Flow
```
[Chat Request] Created new conversation xyz789 for user message: Make the office lights blink...
[Message Assembly] Conversation xyz789: Assembled 2 messages (1 system + 1 history). User message: Make the office lights...
[Message Emphasis] Conversation xyz789: Emphasized user request (last message). Original length: 65, Emphasized length: 185
[Tool Calls] Conversation xyz789: No tool calls in response. User requested: Make the office lights...
[Response Validation] Conversation xyz789: ⚠️ GENERIC WELCOME MESSAGE DETECTED in response!
This indicates the prompt fixes may not be working.
User message: Make the office lights blink...
Response: How can I assist you with your Home Assistant automations today?...
Tool calls: 0
[Chat Complete] Conversation xyz789: Request completed. Tokens: 567, Time: 1234ms, Tool calls: 0, Response length: 89, Generic response detected: True
```

---

## Log Filtering Commands

### Find all generic response warnings
```bash
grep "\[Response Validation\].*GENERIC WELCOME MESSAGE DETECTED" logs/app.log
```

### Track a specific conversation
```bash
grep "Conversation abc123" logs/app.log
```

### Monitor tool call rates
```bash
grep "\[Tool Calls\].*Processing" logs/app.log | wc -l
```

### Find message emphasis issues
```bash
grep "\[Message Emphasis\].*WARNING\|ERROR" logs/app.log
```

### Check generic message filtering
```bash
grep "\[Generic Message Filter\].*Filtered" logs/app.log
```

---

## Next Steps

1. **Deploy with monitoring** - Enable INFO level logging in production
2. **Monitor for 24-48 hours** - Watch for WARNING and ERROR logs
3. **Analyze metrics** - Calculate generic response rate, tool call rate
4. **Adjust if needed** - Fine-tune patterns, prompts based on real data
5. **Document patterns** - Update this guide with common issues found

---

## Related Files

- `services/ha-ai-agent-service/src/prompts/system_prompt.py` - System prompt
- `services/ha-ai-agent-service/src/services/prompt_assembly_service.py` - Message assembly
- `services/ha-ai-agent-service/src/services/conversation_service.py` - Generic detection
- `services/ha-ai-agent-service/src/api/chat_endpoints.py` - Response validation
- `implementation/HA_AI_AGENT_GENERIC_RESPONSE_FIX_PLAN.md` - Original fix plan

