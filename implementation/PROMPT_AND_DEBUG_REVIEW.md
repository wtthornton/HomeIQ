# Prompt and Debug Statement Review

**Date**: January 2025  
**Service**: `ha-ai-agent-service`  
**Files Reviewed**: 
- `services/ha-ai-agent-service/src/prompts/system_prompt.py`
- `services/ha-ai-agent-service/src/tools/ha_tools.py`
- `services/ha-ai-agent-service/src/services/prompt_assembly_service.py`

---

## Executive Summary

This review analyzes the system prompt structure and all debug/logging statements in the HA AI Agent Service. The review identifies areas for improvement in prompt clarity, logging consistency, and debug statement quality.

**Overall Assessment**: ✅ **Good** - System prompt is comprehensive and well-structured. Logging is generally good but has some inconsistencies and opportunities for improvement.

---

## System Prompt Review

### ✅ Strengths

1. **Comprehensive Coverage**: The system prompt covers all required aspects:
   - Workflow steps (preview → approval → create)
   - Tool references
   - Home Assistant context usage
   - YAML examples
   - Safety considerations

2. **Clear Structure**: Well-organized with clear sections and hierarchical structure

3. **Good Examples**: Includes practical YAML examples for common patterns

4. **Safety Focus**: Includes safety considerations and warnings

### ⚠️ Areas for Improvement

#### 1. **Prompt Length** (Medium Priority)
- **Current**: ~15,000 characters
- **Issue**: Very long prompt may hit token limits or reduce LLM focus
- **Recommendation**: 
  - Consider splitting into modular sections
  - Use dynamic context injection for examples
  - Move detailed patterns to separate reference document

#### 2. **Hardcoded Examples** (Low Priority)
- **Issue**: Contains example entity IDs (`light.office_go`, `binary_sensor.office_motion_1`)
- **Recommendation**: 
  - Add comment: "These are examples - use actual entity IDs from context"
  - Consider using placeholders: `light.{area}_{device_type}`

#### 3. **YAML Example Validation** (Low Priority)
- **Issue**: YAML examples in prompt should be validated
- **Recommendation**: Add automated test to validate all YAML examples parse correctly

#### 4. **Version References** (Low Priority)
- **Issue**: References "2025.10+" but doesn't explain version compatibility
- **Recommendation**: Add note about Home Assistant version requirements

---

## Debug Statement Review

### Logging Statement Analysis

#### Summary Statistics (ha_tools.py)
- **Total Logging Calls**: 14
- **Breakdown**:
  - `logger.debug`: 1 (7%)
  - `logger.info`: 5 (36%)
  - `logger.warning`: 2 (14%)
  - `logger.error`: 6 (43%)

#### ✅ Strengths

1. **Good Error Handling**: Most exception handlers include `exc_info=True`
2. **Contextual Information**: Most logs include relevant identifiers (alias, user_prompt)
3. **Appropriate Levels**: Good distribution of info/warning/error levels

#### ⚠️ Issues Found

### Issue 1: Inconsistent Debug Statement Usage (Medium Priority)

**Location**: `ha_tools.py:380`
```python
logger.debug(f"Using normalized YAML from validation result for preview")
```

**Problem**: 
- Only 1 debug statement in entire file (7% of logging calls)
- Debug level underutilized for detailed flow tracking
- This specific debug statement is useful but isolated

**Recommendation**:
```python
# Add more debug statements for flow tracking:
logger.debug(f"Preview request validated: alias='{request.alias}', prompt_length={len(request.user_prompt)}")
logger.debug(f"Validation chain result: valid={validation_result.valid}, errors={len(validation_result.errors)}")
logger.debug(f"Extracted {len(extraction_result['entities'])} entities, {len(extraction_result['areas'])} areas")
logger.debug(f"Device context extracted: {len(device_context.get('device_ids', []))} devices")
```

### Issue 2: Missing Context in Some Logs (Medium Priority)

**Location**: `ha_tools.py:247, 252`
```python
logger.error(f"YAML parsing error: {e}")
logger.error(f"Error creating automation: {e}", exc_info=True)
```

**Problem**: 
- Missing user_prompt or alias context in error messages
- Makes debugging harder when multiple requests are processed

**Recommendation**:
```python
logger.error(
    f"YAML parsing error for automation '{alias}': {e}. "
    f"Prompt: '{user_prompt[:100]}...'",
    exc_info=True
)
```

### Issue 3: Info Logs Missing Identifiers (Low Priority)

**Location**: `ha_tools.py:400-405`
```python
logger.info(
    f"✅ Preview generated for automation '{request.alias}'. "
    f"Entities: {len(extraction_result['entities'])}, "
    f"Areas: {len(extraction_result['areas'])}, "
    f"Safety warnings: {len(safety_warnings)}"
)
```

**Problem**: 
- Good info log, but missing conversation_id for traceability
- Can't correlate with user requests across sessions

**Recommendation**:
```python
logger.info(
    f"✅ Preview generated for automation '{request.alias}' "
    f"(conversation_id={conversation_id}). "
    f"Entities: {len(extraction_result['entities'])}, "
    f"Areas: {len(extraction_result['areas'])}, "
    f"Safety warnings: {len(safety_warnings)}"
)
```

### Issue 4: Warning Messages Could Be More Actionable (Low Priority)

**Location**: `ha_tools.py:753, 811`
```python
logger.warning(f"Failed to extract device context: {e}")
logger.warning(f"Failed to validate devices: {e}")
```

**Problem**: 
- Warnings don't explain impact or suggest remediation
- User/developer doesn't know if this is critical or recoverable

**Recommendation**:
```python
logger.warning(
    f"Failed to extract device context: {e}. "
    f"Device validation will be skipped. Automation may proceed with limited validation."
)
logger.warning(
    f"Failed to validate devices: {e}. "
    f"Device health scores and capability checks will be skipped. "
    f"Consider manual verification before deployment."
)
```

### Issue 5: Success Logs Missing Key Metrics (Low Priority)

**Location**: `ha_tools.py:594-597`
```python
logger.info(
    f"✅ Automation created successfully: {automation_id} "
    f"for prompt: '{user_prompt[:100]}...'"
)
```

**Problem**: 
- Missing validation warnings count
- Missing timing information
- Can't track performance or quality metrics

**Recommendation**:
```python
logger.info(
    f"✅ Automation created successfully: {automation_id} "
    f"for prompt: '{user_prompt[:100]}...' "
    f"(validation_warnings: {len(validation_result.warnings)}, "
    f"entities: {len(extraction_result.get('entities', []))})"
)
```

---

## Recommendations Summary

### High Priority

1. **Add Conversation ID to All Logs** (High Impact, Low Effort)
   - Add `conversation_id` parameter to tool methods
   - Include in all log statements for traceability
   - Enables correlation across sessions

2. **Enhance Error Logging Context** (High Impact, Medium Effort)
   - Include user_prompt, alias, conversation_id in all error logs
   - Add request context to exception handlers
   - Improves debugging and support

### Medium Priority

3. **Increase Debug Statement Usage** (Medium Impact, Low Effort)
   - Add debug statements for key flow points
   - Track validation steps, extraction results, device context
   - Enables detailed flow analysis without cluttering info logs

4. **Improve Warning Messages** (Medium Impact, Low Effort)
   - Explain impact of warnings
   - Suggest remediation steps
   - Clarify if warning is critical or informational

5. **Add Performance Metrics** (Medium Impact, Medium Effort)
   - Log timing for key operations (validation, device context extraction)
   - Track success rates and common errors
   - Enables performance monitoring

### Low Priority

6. **Standardize Log Format** (Low Impact, Low Effort)
   - Use consistent format: `[Operation] [Status] [Context] [Metrics]`
   - Example: `[Preview] ✅ Generated [alias=office_lights] [entities=5, areas=1, warnings=0]`

7. **Add Structured Logging** (Low Impact, High Effort)
   - Consider structured logging (JSON) for better parsing
   - Enables log aggregation and analysis
   - Better integration with monitoring tools

8. **Prompt Optimization** (Low Impact, Medium Effort)
   - Split prompt into modular sections
   - Use dynamic context injection
   - Reduce token usage while maintaining clarity

---

## Code Examples

### Improved Logging Pattern

**Before**:
```python
logger.error(f"YAML parsing error: {e}")
```

**After**:
```python
logger.error(
    f"[Preview] ❌ YAML parsing error for automation '{request.alias}' "
    f"(conversation_id={conversation_id}): {e}. "
    f"Prompt: '{request.user_prompt[:100]}...'",
    exc_info=True
)
```

### Improved Debug Pattern

**Before**:
```python
validation_result = await self.validation_chain.validate(request.automation_yaml)
```

**After**:
```python
validation_result = await self.validation_chain.validate(request.automation_yaml)
logger.debug(
    f"[Preview] Validation chain result: valid={validation_result.valid}, "
    f"errors={len(validation_result.errors or [])}, "
    f"warnings={len(validation_result.warnings or [])}, "
    f"strategy={validation_result.strategy_name if hasattr(validation_result, 'strategy_name') else 'unknown'}"
)
```

### Improved Warning Pattern

**Before**:
```python
logger.warning(f"Failed to extract device context: {e}")
```

**After**:
```python
logger.warning(
    f"[Preview] ⚠️ Failed to extract device context: {e}. "
    f"Device validation will be skipped. Automation may proceed with limited validation. "
    f"Consider manual device verification."
)
```

---

## Testing Recommendations

1. **Add Test Coverage**:
   - Test that all logger calls include required context
   - Test that error logs include exc_info=True
   - Test that debug statements are meaningful

2. **Add Logging Tests**:
   - Mock logger and verify log calls
   - Verify log levels are appropriate
   - Verify log messages contain expected information

3. **Add Prompt Tests**:
   - Validate YAML examples parse correctly
   - Verify all required sections are present
   - Check prompt length is reasonable

---

## Implementation Plan

### Phase 1: High Priority (Week 1)
- [ ] Add conversation_id to all tool methods
- [ ] Enhance error logging with context
- [ ] Update all error logs to include exc_info=True

### Phase 2: Medium Priority (Week 2)
- [ ] Add debug statements for key flow points
- [ ] Improve warning messages with impact explanations
- [ ] Add performance metrics to success logs

### Phase 3: Low Priority (Week 3)
- [ ] Standardize log format
- [ ] Optimize system prompt (if needed)
- [ ] Add structured logging (if beneficial)

---

## Conclusion

The system prompt and logging implementation are generally good, but there are opportunities for improvement:

1. **Logging**: Add more context (conversation_id, request details) to all logs
2. **Debug Statements**: Increase usage for better flow tracking
3. **Warning Messages**: Make warnings more actionable with impact explanations
4. **Error Handling**: Ensure all errors include full context for debugging

These improvements will enhance debuggability, traceability, and support capabilities without significant code changes.
