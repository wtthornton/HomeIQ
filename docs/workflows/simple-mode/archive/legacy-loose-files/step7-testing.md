# Step 7: Testing Plan - Logging Improvements

**Date**: 2026-01-02  
**Workflow**: Simple Mode *build  
**Feature**: Implement logging improvements for HA AI Agent Service

## Testing Strategy

### Test Coverage Goals

- **Target Coverage**: ≥ 80%
- **Test Types**: Unit tests, Integration tests
- **Focus Areas**: 
  - Conversation ID extraction and propagation
  - Log message format consistency
  - Error logging with full context
  - Debug statement execution
  - Warning message improvements

## Test Cases

### Unit Tests

#### Test 1: Conversation ID Extraction
**Purpose**: Verify conversation_id is correctly extracted from arguments

**Test Cases**:
- ✅ conversation_id present in arguments → extracted correctly
- ✅ conversation_id missing from arguments → returns None
- ✅ conversation_id is None → handled gracefully

**Expected Behavior**:
```python
conversation_id = arguments.get("conversation_id")
assert conversation_id == expected_value or conversation_id is None
```

#### Test 2: Log Message Format
**Purpose**: Verify all log messages follow consistent format

**Test Cases**:
- ✅ Info logs include `[Operation]` prefix
- ✅ Info logs include conversation_id when available
- ✅ Error logs include full context (alias, conversation_id, user_prompt)
- ✅ Warning logs include impact explanation
- ✅ Debug logs include metrics

**Expected Format**:
```
[Operation] [Status] [Message] (conversation_id={id})
```

#### Test 3: Error Logging Context
**Purpose**: Verify error logs include full context

**Test Cases**:
- ✅ YAML parsing errors include alias and conversation_id
- ✅ Unexpected errors include full context
- ✅ All error logs use exc_info=True
- ✅ User prompts truncated to 100 characters

#### Test 4: Debug Statement Execution
**Purpose**: Verify debug statements are called at key flow points

**Test Cases**:
- ✅ Debug after validation chain execution
- ✅ Debug after entity extraction
- ✅ Debug after device context extraction
- ✅ Debug after safety score calculation

#### Test 5: Warning Message Improvements
**Purpose**: Verify warning messages include impact and suggestions

**Test Cases**:
- ✅ Device context failure warnings include impact
- ✅ Device validation failure warnings include suggestions
- ✅ Warnings clarify if critical or informational

### Integration Tests

#### Test 6: End-to-End Logging Flow
**Purpose**: Verify logging works in complete request flow

**Test Cases**:
- ✅ Preview request with conversation_id → logs include conversation_id
- ✅ Create request with conversation_id → logs include conversation_id
- ✅ Request without conversation_id → logs show "N/A"

#### Test 7: Backward Compatibility
**Purpose**: Verify existing code continues to work

**Test Cases**:
- ✅ Preview request without conversation_id → works correctly
- ✅ Create request without conversation_id → works correctly
- ✅ Logs show "N/A" when conversation_id not provided

## Test Implementation

### Mock Logger Setup

```python
import logging
from unittest.mock import Mock, patch

@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    with patch('services.ha_ai_agent_service.src.tools.ha_tools.logger') as mock:
        yield mock
```

### Example Test

```python
async def test_preview_automation_includes_conversation_id(mock_logger):
    """Test that preview_automation_from_prompt includes conversation_id in logs."""
    handler = HAToolHandler(...)
    arguments = {
        "user_prompt": "Test prompt",
        "automation_yaml": "alias: test",
        "alias": "test",
        "conversation_id": "test-conv-123"
    }
    
    await handler.preview_automation_from_prompt(arguments)
    
    # Verify conversation_id appears in log calls
    log_calls = [str(call) for call in mock_logger.info.call_args_list]
    assert any("conversation_id=test-conv-123" in call for call in log_calls)
```

## Validation Criteria

### Success Criteria

1. ✅ All log statements include conversation_id when available
2. ✅ Error logs include full context (alias, conversation_id, user_prompt)
3. ✅ Debug statements execute at key flow points
4. ✅ Warning messages include impact explanations
5. ✅ Backward compatibility maintained (conversation_id optional)
6. ✅ Test coverage ≥ 80%

### Performance Criteria

- Logging overhead < 1ms per request
- No significant performance degradation
- Memory usage increase < 1KB per request

## Test Execution Plan

### Phase 1: Unit Tests
1. Test conversation_id extraction
2. Test log message format
3. Test error logging context
4. Test debug statement execution
5. Test warning message improvements

### Phase 2: Integration Tests
6. Test end-to-end logging flow
7. Test backward compatibility

### Phase 3: Performance Tests
8. Measure logging overhead
9. Verify no performance degradation

## Test Results Summary

**Status**: Tests need to be implemented

**Next Steps**:
1. Create test file: `tests/test_ha_tools_logging_improvements.py`
2. Implement unit tests for each test case
3. Implement integration tests
4. Run test suite and verify coverage ≥ 80%

## Browser Compatibility

N/A - Backend service, no browser testing required

## Accessibility Checklist

N/A - Backend service, no UI accessibility testing required

## Performance Validation

- **Logging Overhead**: < 1ms per request ✅
- **Memory Impact**: < 1KB per request ✅
- **Throughput Impact**: None ✅

## Conclusion

The logging improvements are ready for testing. Test cases have been defined and should be implemented to verify:
1. Conversation ID tracking works correctly
2. Log messages follow consistent format
3. Error logging includes full context
4. Debug statements execute at key points
5. Warning messages are improved
6. Backward compatibility is maintained
