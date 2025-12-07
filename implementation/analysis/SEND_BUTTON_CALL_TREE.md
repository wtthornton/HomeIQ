# Send Button Call Tree and Performance Tracking

**Created:** 2025-01-XX  
**Purpose:** Document the complete call flow when user clicks Send button and implement performance tracking for optimization

## Call Tree Overview

```
User Action: Click Send Button
│
├─ [FRONTEND] SendButton.tsx
│  └─ onClick → handleClick()
│     └─ onClick() prop callback
│
├─ [FRONTEND] HAAgentChat.tsx
│  └─ handleSend() [Line 149]
│     ├─ Validation: Check inputValue.trim() && !isLoading
│     ├─ Create userMessage object
│     ├─ setMessages() - Add user message to UI
│     ├─ setInputValue('') - Clear input
│     ├─ setIsLoading(true) - Set loading state
│     ├─ Create loadingMessage - Show "Thinking..." indicator
│     ├─ setMessages() - Add loading message
│     └─ sendChatMessage() [Line 175] - API call
│        │
│        └─ [FRONTEND] haAiAgentApi.ts
│           └─ sendChatMessage() [Line 190]
│              ├─ withAuthHeaders() - Add auth headers
│              └─ fetchJSON() [Line 111]
│                 ├─ fetch() - HTTP POST to /v1/chat
│                 └─ Response parsing
│                    │
│                    └─ [BACKEND] ha-ai-agent-service
│                       │
│                       └─ [API] chat_endpoints.py
│                          └─ @router.post("/chat") [Line 68]
│                             ├─ start_time = time.time() [Line 85]
│                             ├─ Rate limiting check [Line 88-94]
│                             ├─ Get/Create conversation [Line 98-117]
│                             │  └─ conversation_service.get_conversation()
│                             │     └─ conversation_service.create_conversation()
│                             │
│                             ├─ Check pending preview [Line 120-137]
│                             │  └─ conversation_service.get_pending_preview()
│                             │
│                             ├─ Assemble messages [Line 144-146]
│                             │  └─ prompt_assembly_service.assemble_messages()
│                             │     ├─ conversation_service.get_conversation()
│                             │     ├─ conversation_service.add_message() [if not skip_add_message]
│                             │     ├─ context_builder.build_complete_system_prompt() [if refresh]
│                             │     ├─ conversation.get_messages() - Get history
│                             │     ├─ Token counting and truncation
│                             │     └─ Return messages array
│                             │
│                             ├─ Get tool schemas [Line 177]
│                             │  └─ get_tool_schemas()
│                             │
│                             ├─ [LOOP] Tool calling loop [Line 192-386]
│                             │  ├─ Iteration counter (max 10)
│                             │  │
│                             │  ├─ Build messages array [Line 200-257]
│                             │  │  ├─ First iteration: base_messages from history
│                             │  │  └─ Subsequent: base + tool_calls + tool_results
│                             │  │
│                             │  ├─ OpenAI API call [Line 261-283]
│                             │  │  └─ openai_client.chat_completion()
│                             │  │     ├─ Verify messages format
│                             │  │     ├─ Prepare request params
│                             │  │     ├─ self.client.chat.completions.create()
│                             │  │     ├─ Track tokens
│                             │  │     └─ Handle errors (rate limit, token budget)
│                             │  │
│                             │  ├─ Extract assistant message [Line 286-291]
│                             │  │  └─ completion.choices[0].message
│                             │  │
│                             │  ├─ Validate response [Line 294-302]
│                             │  │  └─ is_generic_welcome_message()
│                             │  │
│                             │  ├─ Add assistant message [Line 305-308]
│                             │  │  └─ conversation_service.add_message()
│                             │  │
│                             │  ├─ Process tool calls [Line 311-376]
│                             │  │  ├─ For each tool_call:
│                             │  │  │  ├─ tool_service.execute_tool_call()
│                             │  │  │  │  ├─ Parse tool_call JSON
│                             │  │  │  │  ├─ tool_service.execute_tool()
│                             │  │  │  │  │  └─ tool_handler.{tool_name}()
│                             │  │  │  │  │     ├─ preview_automation_from_prompt
│                             │  │  │  │  │     ├─ create_automation_from_prompt
│                             │  │  │  │  │     └─ suggest_automation_enhancements
│                             │  │  │  │  │        └─ [External calls]
│                             │  │  │  │  │           ├─ ha_client.*
│                             │  │  │  │  │           ├─ data_api_client.*
│                             │  │  │  │  │           └─ ai_automation_client.*
│                             │  │  │  │  └─ Format result
│                             │  │  │  ├─ Store tool_result for next iteration
│                             │  │  │  └─ Format tool_call for response
│                             │  │  │
│                             │  │  └─ Handle pending preview [Line 331-347]
│                             │  │     ├─ set_pending_preview() [if preview tool]
│                             │  │     └─ clear_pending_preview() [if create tool]
│                             │  │
│                             │  └─ Continue loop or break [Line 377-385]
│                             │
│                             ├─ Calculate response_time_ms [Line 398]
│                             ├─ Get token counts [Line 401]
│                             │  └─ prompt_assembly_service.get_token_count()
│                             │
│                             ├─ Build ChatResponse [Line 404-415]
│                             └─ Return response [Line 428]
│
└─ [FRONTEND] HAAgentChat.tsx (continued)
   ├─ Response handling [Line 180-232]
   │  ├─ Update conversation_id [if new conversation]
   │  ├─ getConversation() [if new conversation] - Reload full conversation
   │  ├─ Remove loading message
   │  ├─ Add assistant message to UI
   │  ├─ Show tool calls indicator
   │  └─ Toast notification [if tool calls]
   │
   └─ Error handling [Line 233-262]
      ├─ Remove loading message
      ├─ Add error message to UI
      └─ Toast error notification
```

## Performance Tracking Points

### Frontend Tracking Points

1. **User Input to Send Click**
   - Time from user typing to button click
   - Input validation time

2. **Frontend State Updates**
   - Time to add user message to UI
   - Time to show loading indicator
   - Time to update messages array

3. **API Request**
   - Time to prepare request (headers, body serialization)
   - Network latency (time to first byte)
   - Total request time (send to response received)

4. **Response Processing**
   - Time to parse JSON response
   - Time to update UI with response
   - Time to remove loading indicator

### Backend Tracking Points

1. **Request Reception**
   - Time from request received to processing start
   - Rate limiting check time

2. **Conversation Management**
   - Time to get/create conversation
   - Database query time

3. **Context Building**
   - Time to build system prompt
   - Time to fetch context (devices, areas, etc.)
   - Context cache hit/miss

4. **Message Assembly**
   - Time to assemble messages
   - Time to count tokens
   - Time to truncate history if needed

5. **OpenAI API Calls**
   - Time per API call
   - Number of iterations (tool calling loops)
   - Total tokens used
   - Rate limit handling time

6. **Tool Execution**
   - Time per tool call
   - Time per external service call (HA, data-api, etc.)
   - Tool call success/failure rate

7. **Response Building**
   - Time to build response object
   - Time to calculate metadata

## Key Metrics to Track

### Latency Metrics
- **Total Request Time**: From send click to response displayed
- **Backend Processing Time**: From request received to response sent
- **OpenAI API Time**: Time spent in OpenAI API calls
- **Tool Execution Time**: Time spent executing tools
- **Context Building Time**: Time to build system prompt with context
- **Database Query Time**: Time for conversation/message queries

### Throughput Metrics
- **Requests per Second**: Rate of incoming requests
- **Concurrent Requests**: Number of simultaneous requests
- **Tool Calls per Request**: Average number of tool calls per request

### Resource Metrics
- **Token Usage**: Total tokens per request
- **Token Breakdown**: System, history, new message tokens
- **Cache Hit Rate**: Context cache effectiveness
- **Iteration Count**: Number of OpenAI API calls per request

### Error Metrics
- **Error Rate**: Percentage of failed requests
- **Rate Limit Hits**: Number of rate limit errors
- **Token Budget Exceeded**: Number of token budget errors
- **Tool Execution Failures**: Number of failed tool calls

## Optimization Opportunities

Based on the call tree, potential optimization areas:

1. **⚠️ CRITICAL: Replace Direct HA API Calls with Local Data**
   - Currently making direct HA API calls for devices, areas, services, helpers/scenes
   - Should use data-api endpoints instead (local/cached data)
   - **Potential improvement: 15-60x faster** (300-1200ms → 20-80ms)
   - See: `implementation/analysis/CALL_TREE_DATA_SOURCE_ANALYSIS.md`

2. **Context Caching**: Already implemented, but can optimize cache refresh strategy
3. **Message History Truncation**: Optimize token counting and truncation logic
4. **Tool Call Parallelization**: Execute independent tool calls in parallel
5. **Database Query Optimization**: Batch queries, use connection pooling
6. **OpenAI API Batching**: If multiple requests, batch them
7. **Frontend State Updates**: Optimize React re-renders
8. **Network Optimization**: Compress requests/responses, use HTTP/2

## Next Steps

1. ✅ Create call tree document (this file)
2. ⏳ Implement performance tracking in frontend
3. ⏳ Implement performance tracking in backend
4. ⏳ Create performance metrics collection utility
5. ⏳ Add performance dashboard/visualization
6. ⏳ Set up performance monitoring and alerting

