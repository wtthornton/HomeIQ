# Step 2: User Stories - Logging Improvements

**Date**: 2026-01-02  
**Workflow**: Simple Mode *build  
**Feature**: Implement logging improvements for HA AI Agent Service

## User Stories

### Story 1: Add Conversation ID Parameter to Tool Methods
**Priority**: High  
**Complexity**: Low (2 points)  
**Description**: Add `conversation_id` as an optional parameter to `preview_automation_from_prompt` and `create_automation_from_prompt` methods.

**Acceptance Criteria**:
- [ ] `conversation_id` parameter added to both tool methods
- [ ] Parameter is optional (defaults to None)
- [ ] Parameter is extracted from arguments dictionary
- [ ] Backward compatible (existing calls still work)

**Dependencies**: None

---

### Story 2: Include Conversation ID in All Log Statements
**Priority**: High  
**Complexity**: Low (3 points)  
**Description**: Update all log statements in `ha_tools.py` to include `conversation_id` when available.

**Acceptance Criteria**:
- [ ] All `logger.info()` calls include conversation_id
- [ ] All `logger.error()` calls include conversation_id
- [ ] All `logger.warning()` calls include conversation_id
- [ ] All `logger.debug()` calls include conversation_id
- [ ] Format: `(conversation_id={conversation_id})` when available

**Dependencies**: Story 1

---

### Story 3: Enhance Error Logging with Full Context
**Priority**: High  
**Complexity**: Medium (5 points)  
**Description**: Enhance all error logging to include user_prompt, alias, and conversation_id for better debugging.

**Acceptance Criteria**:
- [ ] All error logs include user_prompt (truncated to 100 chars)
- [ ] All error logs include alias
- [ ] All error logs include conversation_id
- [ ] All exception handlers use `exc_info=True`
- [ ] Error format: `[Operation] ❌ Error message [context]`

**Dependencies**: Story 1, Story 2

---

### Story 4: Add Debug Statements for Flow Tracking
**Priority**: Medium  
**Complexity**: Low (3 points)  
**Description**: Add debug statements at key flow points to enable detailed flow analysis.

**Acceptance Criteria**:
- [ ] Debug statement after validation chain execution
- [ ] Debug statement after entity/area/service extraction
- [ ] Debug statement after device context extraction
- [ ] Debug statement after safety score calculation
- [ ] Debug statement after consistency validation
- [ ] Format: `[Preview] Debug message [metrics]`

**Dependencies**: Story 2

---

### Story 5: Improve Warning Messages with Impact Explanations
**Priority**: Medium  
**Complexity**: Low (2 points)  
**Description**: Enhance warning messages to explain impact and suggest remediation.

**Acceptance Criteria**:
- [ ] Warning messages explain what went wrong
- [ ] Warning messages explain impact (what's affected)
- [ ] Warning messages suggest remediation steps
- [ ] Warning messages clarify if critical or informational
- [ ] Format: `[Preview] ⚠️ Warning message. Impact: [impact]. Consider: [suggestion]`

**Dependencies**: Story 2

---

### Story 6: Add Performance Metrics to Success Logs
**Priority**: Medium  
**Complexity**: Low (2 points)  
**Description**: Add metrics (entity count, warning count, etc.) to success logs.

**Acceptance Criteria**:
- [ ] Success logs include entity count
- [ ] Success logs include area count
- [ ] Success logs include warning count
- [ ] Success logs include validation warnings count
- [ ] Format: `[Preview] ✅ Success [metrics]`

**Dependencies**: Story 2

---

## Story Points Summary

- **Total Story Points**: 17
- **High Priority**: 10 points (Stories 1, 2, 3)
- **Medium Priority**: 7 points (Stories 4, 5, 6)

## Priority Order

1. Story 1: Add Conversation ID Parameter (Foundation)
2. Story 2: Include Conversation ID in Logs (Foundation)
3. Story 3: Enhance Error Logging (High Value)
4. Story 4: Add Debug Statements (Medium Value)
5. Story 5: Improve Warning Messages (Medium Value)
6. Story 6: Add Performance Metrics (Nice to Have)

## Estimated Timeline

- **High Priority Stories**: 2-3 hours
- **Medium Priority Stories**: 1-2 hours
- **Total**: 3-5 hours
