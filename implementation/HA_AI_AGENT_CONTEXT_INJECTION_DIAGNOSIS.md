# HA AI Agent - Context Injection Diagnosis

**Issue:** Prompt and context not getting injected  
**Date:** January 2025  
**Status:** 🔍 Investigating

---

## 🔍 Problem Analysis

The user reports that the prompt and context are not getting injected. This could mean:

1. **System prompt not included** - The base system prompt isn't being added to messages
2. **Context not appended** - The Tier 1 context (entities, areas, services) isn't being appended
3. **Both missing** - Neither the prompt nor context are in the messages sent to OpenAI
4. **Context empty** - Context is being built but all sections show "(unavailable)"

---

## 🔧 Enhanced Logging Added

### Context Builder Logging
- ✅ Logs when context builder is not initialized (ERROR)
- ✅ Logs each context section as it's built (DEBUG)
- ✅ Logs when sections are unavailable (WARNING)
- ✅ Logs final context length and unavailable count (INFO/WARNING)
- ✅ Logs complete system prompt length and verification (INFO)

### Prompt Assembly Logging
- ✅ Logs when building fresh context vs using cache (INFO)
- ✅ Verifies system prompt length and content (INFO/ERROR)
- ✅ Logs if system prompt is too short or empty (ERROR)
- ✅ Verifies system message in final messages array (INFO)
- ✅ Logs message assembly summary with verification (INFO)

### OpenAI Client Logging
- ✅ Verifies messages array before sending (INFO)
- ✅ Verifies system message is first (ERROR if not)
- ✅ Logs system message content verification (INFO)
- ✅ Checks for 'CRITICAL' and 'HOME ASSISTANT CONTEXT' in system message

### Chat Endpoint Logging
- ✅ Verifies messages after assembly (INFO)
- ✅ Checks system message presence and content (ERROR if missing)
- ✅ Logs verification before sending to OpenAI

---

## 🔍 Diagnostic Steps

### Step 1: Check Service Logs

After restarting the service, look for these log patterns:

**Expected Success Pattern:**
```
[Context Building] Conversation {id}: Building fresh context...
✅ Context built successfully. Total length: {n} chars
✅ Complete system prompt built: {n} chars (base: {m}, context: {k})
[Message Assembly] Conversation {id}: ✅ Assembled {n} messages
[OpenAI API] Sending {n} messages to OpenAI. System message: {m} chars, Contains 'CRITICAL': True, Contains 'HOME ASSISTANT CONTEXT': True
```

**Failure Pattern (Context Builder Not Initialized):**
```
❌ CRITICAL: Context builder not initialized!
RuntimeError: Context builder not initialized
```

**Failure Pattern (Context Empty/Unavailable):**
```
⚠️ Context built with {n} unavailable section(s)
⚠️ Failed to get entity inventory: {error}
⚠️ Failed to get areas: {error}
```

**Failure Pattern (System Prompt Missing):**
```
❌ CRITICAL: System message missing or not first!
❌ CRITICAL: System prompt is too short ({n} chars)!
```

### Step 2: Check Context Builder Initialization

**Look for in startup logs:**
```
✅ Context builder initialized with all services
```

**If missing, check:**
- Service startup sequence
- Database initialization
- Service dependencies (HA, Data API, Device Intelligence)

### Step 3: Check Context Building

**Look for context building logs:**
```
Building Tier 1 context (entity inventory, areas, services, etc.)
✅ Entity inventory added ({n} chars)
✅ Areas added ({n} chars)
✅ Context built successfully. Total length: {n} chars
```

**If all show "(unavailable)":**
- Check Home Assistant connectivity
- Check Data API service availability
- Check Device Intelligence service availability
- Check service URLs and tokens

### Step 4: Check Message Assembly

**Look for assembly logs:**
```
[Message Assembly] Conversation {id}: ✅ Assembled {n} messages
System prompt length: {n} chars
System message role: system
Contains 'CRITICAL': True
Contains 'HOME ASSISTANT CONTEXT': True
```

**If False for 'CRITICAL' or 'HOME ASSISTANT CONTEXT':**
- System prompt wasn't updated (old code running)
- Context wasn't appended
- Need to restart service

### Step 5: Check OpenAI API Call

**Look for API call logs:**
```
[OpenAI API] Sending {n} messages to OpenAI
System message: {m} chars
Contains 'CRITICAL': True
Contains 'HOME ASSISTANT CONTEXT': True
```

**If False:**
- Messages were modified before sending (unlikely)
- System message was removed (bug)
- Need to investigate message flow

---

## 🐛 Common Issues & Solutions

### Issue 1: Context Builder Not Initialized

**Symptoms:**
- `RuntimeError: Context builder not initialized`
- All context sections unavailable

**Solution:**
- Check service startup logs
- Verify `context_builder.initialize()` is called
- Check for initialization errors

### Issue 2: All Context Sections Unavailable

**Symptoms:**
- Context built but all sections show "(unavailable)"
- Context length is very short (~200 chars)

**Possible Causes:**
- Home Assistant not accessible
- Data API service down
- Device Intelligence service down
- Network connectivity issues
- Invalid tokens/credentials

**Solution:**
- Check service health endpoints
- Verify network connectivity
- Check credentials in .env
- Review service logs for connection errors

### Issue 3: System Prompt Not Updated

**Symptoms:**
- System prompt doesn't contain "CRITICAL: Request Processing Rules"
- Old system prompt being used

**Solution:**
- Restart service to load new code
- Verify code changes are deployed
- Check system prompt file was updated

### Issue 4: Context Not Appended

**Symptoms:**
- System prompt present but no "HOME ASSISTANT CONTEXT" section
- Context length matches base prompt only

**Solution:**
- Check `build_complete_system_prompt()` is being called
- Verify context is being built successfully
- Check for exceptions in context building

### Issue 5: System Message Not First

**Symptoms:**
- Error: "System message must be first message"
- Messages array has wrong order

**Solution:**
- Check message assembly logic
- Verify conversation history ordering
- Review message filtering logic

---

## 📊 Verification Commands

### Check Service Logs
```bash
# Watch for context building
docker-compose logs -f ha-ai-agent-service | Select-String "\[Context Building\]|\[Message Assembly\]|\[OpenAI API\]"

# Check for errors
docker-compose logs ha-ai-agent-service | Select-String "❌|ERROR|CRITICAL"

# Check context initialization
docker-compose logs ha-ai-agent-service | Select-String "Context builder initialized"
```

### Test Context Building Directly
```bash
# Call the complete-prompt endpoint
Invoke-WebRequest -Uri http://localhost:8030/api/v1/complete-prompt | Select-Object -ExpandProperty Content

# Should contain:
# - "CRITICAL: Request Processing Rules"
# - "HOME ASSISTANT CONTEXT:"
# - "ENTITY INVENTORY:"
# - "AREAS:"
# - etc.
```

### Check System Prompt
```bash
# Call the system-prompt endpoint
Invoke-WebRequest -Uri http://localhost:8030/api/v1/system-prompt | Select-Object -ExpandProperty Content | Select-String "CRITICAL"
```

---

## 🔧 Next Steps

1. **Restart Service** - Load new code with enhanced logging
2. **Send Test Request** - Use browser to send automation request
3. **Review Logs** - Check for the diagnostic log patterns above
4. **Identify Issue** - Use logs to determine which component is failing
5. **Fix Issue** - Address the specific problem identified

---

## 📝 Log Analysis Checklist

After sending a test request, check logs for:

- [ ] Context builder initialized (startup)
- [ ] Context building started
- [ ] Each context section fetched successfully
- [ ] Context built with reasonable length (>500 chars)
- [ ] Complete system prompt built (>2000 chars)
- [ ] System prompt contains "CRITICAL"
- [ ] System prompt contains "HOME ASSISTANT CONTEXT"
- [ ] Messages assembled with system message first
- [ ] System message verified before OpenAI API call
- [ ] No ERROR or CRITICAL messages

---

**Status:** 🔍 Enhanced logging added - Ready for diagnosis  
**Action:** Restart service and review logs to identify root cause

