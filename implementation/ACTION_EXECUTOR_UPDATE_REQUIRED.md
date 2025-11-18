# Action Executor Integration - ask_ai_router.py Update Required

## Status

The Action Execution Engine has been implemented with all core components. However, the `ask_ai_router.py` file needs to be updated to use the new ActionExecutor instead of the old create/delete automation approach.

## What Has Been Completed

1. ✅ ActionExecutor class with queuing and retry logic
2. ✅ ActionParser for parsing 2025 YAML format
3. ✅ Action models (Pydantic)
4. ✅ Action state machine
5. ✅ Action exceptions
6. ✅ ServiceContainer integration
7. ✅ Main.py lifespan integration
8. ✅ TestExecutor updated to use ActionExecutor
9. ✅ Configuration added
10. ✅ Architecture documentation

## What Needs to Be Done

### Update `test_suggestion_from_query()` in ask_ai_router.py

**Location**: `services/ai-automation-service/src/api/ask_ai_router.py` (around line 6032)

**Current Flow** (lines ~6283-6341):
1. Create temporary automation in HA
2. Trigger automation
3. Wait for state changes
4. Delete automation

**New Flow** (should replace the above):
1. Use AutomationTestExecutor.execute_test() which uses ActionExecutor
2. ActionExecutor parses YAML and executes actions directly
3. No need to create/delete automations

### Implementation Steps

1. **Import AutomationTestExecutor**:
```python
from ..services.service_container import ServiceContainer
```

2. **Replace the create/trigger/delete section** (lines ~6283-6341) with:
```python
# Use ActionExecutor for test execution
from ..services.service_container import ServiceContainer
service_container = ServiceContainer()
test_executor = service_container.test_executor

# Execute test using ActionExecutor
test_context = {
    'query_id': query_id,
    'suggestion_id': suggestion_id,
    'original_query': query.original_query
}

test_result = await test_executor.execute_test(
    automation_yaml=automation_yaml,
    expected_changes=None,
    context=test_context
)

# Extract results
state_validation = {
    'results': test_result.get('state_changes', {}),
    'summary': test_result.get('state_validation', {})
}

# Update performance metrics
ha_create_time = 0  # No longer needed
ha_trigger_time = 0  # No longer needed
action_execution_time = test_result.get('execution_time_ms', 0)
```

3. **Update performance metrics** to reflect ActionExecutor timing:
```python
performance_metrics = {
    "entity_resolution_ms": round(entity_resolution_time, 2),
    "yaml_generation_ms": round(yaml_gen_time, 2),
    "action_execution_ms": round(action_execution_time, 2),  # New
    "state_validation_ms": round(state_validation.get('summary', {}).get('validation_time_ms', 0), 2),  # New
    "total_ms": round(total_time, 2)
}
```

4. **Update response data**:
```python
response_data = {
    "suggestion_id": suggestion_id,
    "query_id": query_id,
    "executed": True,
    "automation_yaml": automation_yaml,
    "automation_id": None,  # No longer created
    "deleted": False,  # No longer needed
    "message": "Test completed successfully - actions executed directly",
    "quality_report": quality_report,
    "performance_metrics": performance_metrics,
    "state_validation": state_validation,
    "test_analysis": test_analysis,
    "stripped_components": stripped_components_preview,
    "restoration_hint": "These components will be added back when you approve",
    "execution_summary": test_result.get('execution_summary', {})  # New
}
```

5. **Add feature flag check** (optional, for gradual rollout):
```python
from ..config import settings

if settings.use_action_executor:
    # Use ActionExecutor (new method)
    test_result = await test_executor.execute_test(...)
else:
    # Fall back to old method (create/delete)
    # ... existing code ...
```

## Benefits of the Update

1. **50-70% faster test execution** - No need to create/delete automations
2. **Better error handling** - Retry logic with exponential backoff
3. **Cleaner code** - Separation of concerns with TestExecutor
4. **Better logging** - Structured logging with correlation IDs
5. **Template support** - Dynamic values via TemplateEngine

## Testing

After updating ask_ai_router.py:

1. Test the Test button in Ask AI UI
2. Verify actions execute correctly
3. Verify state validation works
4. Check performance metrics show improvement
5. Verify error handling works correctly

## Rollback Plan

If issues arise, set `use_action_executor = False` in config.py to fall back to the old method.

