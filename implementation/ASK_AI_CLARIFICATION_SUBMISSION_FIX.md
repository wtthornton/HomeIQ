# Ask AI Clarification Submission Fix

**Date:** November 19, 2025  
**Status:** 🔧 In Progress  
**Issue:** Clarification dialog submission fails silently and allows resubmission

## Problem Analysis

### User-Reported Issue
User submitted answers to clarification questions, but nothing happened. The dialog remained open and allowed resubmission without any feedback.

### Root Cause (from logs)

From `docker logs ai-automation-ui --tail 50`:
```
172.18.0.1 - - [19/Nov/2025:15:50:51] "POST /api/v1/ask-ai/clarify HTTP/1.1" 200 828
172.18.0.1 - - [19/Nov/2025:15:52:44] "POST /api/v1/ask-ai/clarify HTTP/1.1" 500 81
172.18.0.1 - - [19/Nov/2025:15:55:12] "POST /api/v1/ask-ai/clarify HTTP/1.1" 504 63
```

From `docker logs ai-automation-service --tail 100`:
```
❌ Unified prompt generation error: Empty content from OpenAI API
❌ Suggestion generation timed out after 60 seconds
INFO: 172.18.0.19:33732 - "POST /api/v1/ask-ai/clarify HTTP/1.1" 504 Gateway Timeout
```

### Issues Identified

#### Backend Issues

1. **Token Budget Exceeded** (85.4% usage - 25628/30000 tokens)
   - The clarification context is building duplicate answers in the prompt
   - See logs: Same question/answer pairs appearing multiple times (questions 2, 5, 6, 7 are duplicates of 1, 2, 3, 4)
   - This inflates the token count and causes OpenAI timeouts

2. **OpenAI Empty Content Error**
   - File: `services/ai-automation-service/src/llm/openai_client.py:567`
   - Error: `ValueError: Empty content from OpenAI API`
   - Likely caused by excessive token usage or API rate limiting

3. **Poor Error Handling**
   - File: `services/ai-automation-service/src/api/ask_ai_router.py`
   - The timeout error (504) doesn't provide actionable information to the frontend
   - Exception handling in `provide_clarification` endpoint doesn't catch OpenAI client errors

#### Frontend Issues

1. **No Error State Management**
   - File: `services/ai-automation-ui/src/pages/AskAI.tsx:2096-2211`
   - The `onAnswer` handler catches errors but doesn't properly reset state
   - Toast error is shown, but dialog remains open

2. **No Timeout Handling**
   - No client-side timeout for long-running clarification requests
   - User can submit multiple times while previous request is still processing

3. **Missing Loading State**
   - `isSubmitting` state is set but dialog doesn't prevent interaction during submission
   - Button text changes to "Submitting..." but no visual feedback on dialog overlay

## Fix Plan

### Phase 1: Backend Fixes (High Priority)

#### Fix 1.1: Deduplicate Clarification Answers
**File:** `services/ai-automation-service/src/api/ask_ai_router.py`
**Location:** `provide_clarification` endpoint (line 5016)

```python
# Before building clarification context, deduplicate answers by question_id
seen_question_ids = set()
deduplicated_answers = []
for answer in session.answers:
    if answer.question_id not in seen_question_ids:
        deduplicated_answers.append(answer)
        seen_question_ids.add(answer.question_id)

# Use deduplicated_answers in clarification_context
clarification_context = {
    "original_query": session.original_query,
    "questions_and_answers": [
        {
            "question": next((q.question_text for q in session.questions if q.id == answer.question_id), ""),
            "answer": answer.answer_text,
            "selected_entities": answer.selected_entities
        }
        for answer in deduplicated_answers
    ]
}
```

#### Fix 1.2: Add OpenAI Error Handling with Retry
**File:** `services/ai-automation-service/src/api/ask_ai_router.py`
**Location:** `provide_clarification` endpoint (line 5240-5330)

```python
# Wrap OpenAI call in try-catch with timeout and retry
max_retries = 2
retry_delay = 2

for attempt in range(max_retries):
    try:
        suggestions_task = asyncio.create_task(
            generate_suggestions_from_query(
                query=session.original_query,
                entities=session.ambiguities.get('entities', []),
                user_id=request.user_id,
                db_session=db,
                clarification_context=clarification_context
            )
        )
        
        # Wait with timeout
        suggestions = await asyncio.wait_for(suggestions_task, timeout=60.0)
        break  # Success, exit retry loop
        
    except asyncio.TimeoutError:
        if attempt < max_retries - 1:
            logger.warning(f"⚠️ Attempt {attempt + 1} timed out, retrying...")
            await asyncio.sleep(retry_delay)
            continue
        else:
            logger.error(f"❌ All retry attempts failed")
            raise HTTPException(
                status_code=504,
                detail={
                    "error": "timeout",
                    "message": "AI suggestion generation is taking longer than expected. This may be due to a complex request. Please try simplifying your query or try again later.",
                    "retry_after": 60
                }
            )
    except ValueError as e:
        if "Empty content from OpenAI API" in str(e):
            logger.error(f"❌ OpenAI returned empty content (likely rate limit or token overflow)")
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "api_error",
                    "message": "AI service temporarily unavailable. Please try again in a moment.",
                    "retry_after": 30
                }
            )
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error during suggestion generation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"Failed to generate suggestions: {str(e)}"
            }
        )
```

#### Fix 1.3: Reduce Token Usage in Context
**File:** `services/ai-automation-service/src/api/ask_ai_router.py`
**Location:** `generate_suggestions_from_query` (line 3058)

```python
# Add clarification context compression
if clarification_context:
    # Build enriched query with Q&A but limit token usage
    qa_summary = "\n".join([
        f"{i+1}. Q: {qa['question']}\n   A: {qa['answer']}"
        for i, qa in enumerate(clarification_context.get("questions_and_answers", [])[:5])  # Limit to 5 Q&A pairs
    ])
    
    # Truncate long answers
    max_answer_length = 200
    qa_summary_truncated = []
    for qa in clarification_context.get("questions_and_answers", [])[:5]:
        answer = qa['answer']
        if len(answer) > max_answer_length:
            answer = answer[:max_answer_length] + "..."
        qa_summary_truncated.append(f"Q: {qa['question']}\nA: {answer}")
    
    qa_summary = "\n\n".join(qa_summary_truncated)
```

### Phase 2: Frontend Fixes

#### Fix 2.1: Improve Error Handling in Dialog
**File:** `services/ai-automation-ui/src/pages/AskAI.tsx`
**Location:** Line 2096-2211

```typescript
onAnswer={async (answers) => {
  try {
    const response = await api.clarifyAnswers(clarificationDialog.sessionId, answers);
    
    // ... existing success handling ...
    
  } catch (error: any) {
    console.error('❌ Clarification error:', error);
    
    // Parse error details
    const errorMessage = error.response?.data?.detail?.message || 
                        error.response?.data?.detail || 
                        error.message || 
                        'Failed to submit clarification';
    
    const errorType = error.response?.data?.detail?.error || 'unknown';
    const retryAfter = error.response?.data?.detail?.retry_after;
    
    // Show appropriate error message
    if (errorType === 'timeout') {
      toast.error(
        `⏱️ ${errorMessage}\n\nThe request is taking longer than expected. Please try again.`,
        { duration: 8000 }
      );
    } else if (errorType === 'api_error') {
      toast.error(
        `🔌 ${errorMessage}${retryAfter ? `\n\nPlease wait ${retryAfter} seconds before retrying.` : ''}`,
        { duration: 6000 }
      );
    } else {
      toast.error(`❌ ${errorMessage}`);
    }
    
    // CRITICAL: Close dialog on error to prevent resubmission
    // Only keep open if it's a temporary error and user should retry
    if (errorType !== 'timeout' && errorType !== 'api_error') {
      setClarificationDialog(null);
    }
  } finally {
    // This is already in ClarificationDialog component
    // No additional cleanup needed here
  }
}}
```

#### Fix 2.2: Add Request Timeout Protection
**File:** `services/ai-automation-ui/src/services/api.ts`
**Location:** Line 471-478

```typescript
async clarifyAnswers(sessionId: string, answers: Array<{
  question_id: string;
  answer_text: string;
  selected_entities?: string[];
}>): Promise<ClarificationResponse> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 90000); // 90 second timeout
  
  try {
    return await fetchJSON(`${API_BASE_URL}/v1/ask-ai/clarify`, {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        answers
      }),
      signal: controller.signal
    });
  } catch (error: any) {
    if (error.name === 'AbortError') {
      throw new Error('Request timed out after 90 seconds. Please try again with a simpler query.');
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
},
```

#### Fix 2.3: Add Loading Overlay to Dialog
**File:** `services/ai-automation-ui/src/components/ask-ai/ClarificationDialog.tsx`
**Location:** Line 331-481 (return statement)

```tsx
return (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -20 }}
    className="fixed inset-0 z-50 flex items-center justify-center p-4"
    style={{
      background: 'rgba(0, 0, 0, 0.7)',
      backdropFilter: 'blur(4px)',
      pointerEvents: isSubmitting ? 'none' : 'auto'  // Prevent clicks during submission
    }}
  >
    {/* Loading overlay */}
    {isSubmitting && (
      <div className="absolute inset-0 z-10 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-4 border-blue-500 border-t-transparent mx-auto mb-4"></div>
          <p className="text-white text-lg font-medium">Processing your answers...</p>
          <p className="text-gray-400 text-sm mt-2">This may take up to 60 seconds</p>
        </div>
      </div>
    )}
    
    <motion.div
      initial={{ scale: 0.95 }}
      animate={{ scale: 1 }}
      className="w-full max-w-2xl rounded-lg shadow-xl"
      style={{
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%)',
        border: '1px solid rgba(59, 130, 246, 0.3)',
        maxHeight: '90vh',
        overflowY: 'auto',
        opacity: isSubmitting ? 0.6 : 1,
        pointerEvents: isSubmitting ? 'none' : 'auto'
      }}
    >
      {/* ... existing dialog content ... */}
    </motion.div>
  </motion.div>
);
```

## Testing Plan

### Test Case 1: Normal Clarification Flow
1. Submit query: "Turn on office lights every 15 minutes"
2. Answer clarification questions
3. Verify suggestions are generated
4. **Expected:** Dialog closes, suggestions displayed

### Test Case 2: Timeout Scenario
1. Submit complex query with many entities
2. Answer clarification questions
3. Wait for timeout (should occur within 90 seconds)
4. **Expected:** Error toast shown, dialog stays open for retry

### Test Case 3: API Error Scenario
1. Simulate OpenAI API failure (disconnect network briefly)
2. Submit clarification answers
3. **Expected:** Error toast shown, appropriate retry message

### Test Case 4: Multiple Submission Prevention
1. Submit clarification answers
2. Attempt to click submit again before first request completes
3. **Expected:** Button disabled, loading overlay shown, second click ignored

## Success Criteria

✅ No duplicate answers in clarification context  
✅ Token usage stays below 20000 tokens (warning threshold)  
✅ OpenAI errors are caught and return meaningful messages  
✅ Frontend displays appropriate error messages  
✅ Dialog closes after successful submission  
✅ Dialog stays open for retryable errors (timeout, rate limit)  
✅ Loading overlay prevents double submission  
✅ Request timeout at 90 seconds with clear error message  

## Implementation Order

1. **Backend Fix 1.1** (deduplicate answers) - HIGHEST PRIORITY
2. **Backend Fix 1.2** (error handling) - HIGH PRIORITY
3. **Frontend Fix 2.1** (error handling) - HIGH PRIORITY
4. **Frontend Fix 2.2** (timeout) - MEDIUM PRIORITY
5. **Backend Fix 1.3** (token reduction) - MEDIUM PRIORITY
6. **Frontend Fix 2.3** (loading overlay) - LOW PRIORITY (UX enhancement)

## Files to Modify

### Backend
- `services/ai-automation-service/src/api/ask_ai_router.py` (3 changes)

### Frontend
- `services/ai-automation-ui/src/pages/AskAI.tsx` (1 change)
- `services/ai-automation-ui/src/services/api.ts` (1 change)
- `services/ai-automation-ui/src/components/ask-ai/ClarificationDialog.tsx` (1 change)

## Related Issues

- Epic 31 Architecture: ✅ (no conflicts)
- OpenAI Token Limits: ⚠️ (need to monitor)
- Rate Limiting: ⚠️ (may need retry logic)

