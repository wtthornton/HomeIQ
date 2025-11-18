# Action Execution Engine Architecture

## Overview

The Action Execution Engine executes automation actions directly via Home Assistant's REST API without creating temporary automations. This improves test performance, reduces overhead, and provides better error handling with retry logic.

## Architecture

### Technology Stack (2025 Standards)

- **Python**: 3.11+ (async/await native support)
- **Async Framework**: asyncio with asyncio.Queue for in-memory queuing
- **HTTP Client**: aiohttp 3.13.2 (existing dependency)
- **Web Framework**: FastAPI 0.121.2 (existing)
- **Retry Pattern**: Custom exponential backoff (delay * 2^attempt) matching existing ha_client pattern
- **Dependency Injection**: ServiceContainer pattern (existing)
- **Logging**: Structured logging via shared.logging_config
- **Template Engine**: Jinja2 with TemplateEngine for dynamic values
- **State Machine**: ActionExecutionStateMachine for tracking execution states
- **Models**: Pydantic v2 models for type safety

### Service Architecture

```
ai-automation-service (Port 8018)
├── ActionExecutor (new)
│   ├── asyncio.Queue (in-memory)
│   ├── Worker Tasks (background, configurable count)
│   ├── Retry Logic (exponential backoff)
│   ├── Template Engine Integration
│   └── State Machine Tracking
├── ServiceContainer (existing)
│   └── action_executor property (new)
└── HTTP → Home Assistant REST API
    └── /api/services/{domain}/{service}
```

## Components

### 1. ActionExecutor

Main execution engine that manages action queuing, worker tasks, and retry logic.

**Key Features:**
- In-memory asyncio.Queue for action queuing
- Configurable worker tasks (default: 2)
- Exponential backoff retry (max_retries=3, initial_delay=1.0s)
- Template rendering for dynamic values
- State machine tracking for execution states
- Support for: single actions, sequences, parallel actions, delays

**Location**: `services/ai-automation-service/src/services/automation/action_executor.py`

### 2. ActionParser

Parses automation YAML to extract actions for execution.

**Supports:**
- 2025 YAML format: `actions:` (plural) with `action:` field
- Nested structures: `sequence:`, `parallel:`, `repeat:`, `choose:`
- Delay parsing: `delay: '00:00:02'` or `delay: {seconds: 2}`
- Service call extraction: `action: domain.service` → domain and service_name

**Location**: `services/ai-automation-service/src/services/automation/action_parser.py`

### 3. Action Models

Pydantic models for type-safe action representation.

**Models:**
- `ActionItem`: Action item for execution queue
- `ActionExecutionResult`: Result of action execution
- `ActionExecutionSummary`: Summary of action execution batch

**Location**: `services/ai-automation-service/src/services/automation/action_models.py`

### 4. Action State Machine

State machine for tracking action execution states.

**States:**
- QUEUED → EXECUTING → SUCCESS/FAILED
- EXECUTING → RETRYING → EXECUTING → SUCCESS/FAILED
- Terminal states: SUCCESS, FAILED, CANCELLED

**Location**: `services/ai-automation-service/src/services/automation/action_state_machine.py`

### 5. Action Exceptions

Custom exceptions for action execution failures.

**Exceptions:**
- `ActionExecutionError`: Base exception
- `ServiceCallError`: HTTP service call failures
- `ActionParseError`: YAML parsing failures
- `RetryExhaustedError`: All retries failed
- `InvalidActionError`: Invalid action structure

**Location**: `services/ai-automation-service/src/services/automation/action_exceptions.py`

## Action Execution Flow

1. **Parse YAML** → Extract actions list via ActionParser
2. **Create Action Items** → Wrap in Pydantic ActionItem models with state machine
3. **Queue Actions** → Add to asyncio.Queue with correlation IDs
4. **Worker Picks Up** → Pulls from queue, logs with structured logging
5. **Execute Action**:
   - Parse service: `action: light.turn_on` → domain=`light`, service=`turn_on`
   - Render templates in service data (if template engine available)
   - Build HTTP POST: `/api/services/light/turn_on`
   - Extract target: `target.entity_id` → `entity_id` in service_data
   - Extract data: `data:` → merge into service_data
   - Make HTTP call via `ha_client._retry_request()`
6. **Handle Result**:
   - Success: Transition to SUCCESS state, continue to next action
   - Failure: Retry with exponential backoff (if enabled), transition to RETRYING state
   - Retry Exhausted: Transition to FAILED state, log error
7. **Validate States** → Compare before/after entity states

## 2025 YAML Format Support

**Input Format** (2025 standard):

```yaml
actions:
 - action: light.turn_on
   target:
     entity_id: light.office
   data:
     brightness_pct: 100
 - delay: '00:00:02'
 - action: light.turn_off
   target:
     entity_id: light.office
```

**Parsed Structure**:

```python
[
    {
        'type': 'service_call',
        'action': 'light.turn_on',
        'domain': 'light',
        'service': 'turn_on',
        'target': {'entity_id': 'light.office'},
        'data': {'brightness_pct': 100}
    },
    {'type': 'delay', 'delay': 2.0},
    {
        'type': 'service_call',
        'action': 'light.turn_off',
        'domain': 'light',
        'service': 'turn_off',
        'target': {'entity_id': 'light.office'}
    }
]
```

## HTTP Service Call Format

**Endpoint**: `POST {ha_url}/api/services/{domain}/{service}`

**Example**:

```http
POST http://192.168.1.86:8123/api/services/light/turn_on
Authorization: Bearer {token}
Content-Type: application/json

{
  "entity_id": "light.office",
  "brightness_pct": 100,
  "color_name": "red"
}
```

## Error Handling & Retry Logic

### Retry Strategy

**Pattern**: Match existing `ha_client._retry_request()` pattern

- Exponential backoff: `delay = initial_delay * (2 ** attempt)`
- Max retries: 3 (configurable)
- Initial delay: 1.0 seconds (configurable)
- Retry on: HTTP 5xx errors, connection errors, timeouts
- Don't retry on: HTTP 4xx errors (client errors)

### Error Recovery

- Uses existing `ErrorRecoveryService` from ServiceContainer for user-facing errors
- Logs structured errors with context
- Returns actionable error messages

## Performance Characteristics

### Targets

- **Action Execution**: < 100ms per action (excluding network latency)
- **Queue Throughput**: > 100 actions/second
- **Test Execution**: 50-70% faster than create/delete approach
- **Memory**: < 10MB for queue (typical test: 5-10 actions)

### Comparison with Old Approach

**Old Approach (Create/Delete)**:
1. Create temporary automation in HA (~500-1000ms)
2. Trigger automation (~100-200ms)
3. Wait for execution (~500-2000ms)
4. Delete automation (~200-500ms)
**Total**: ~1300-3700ms

**New Approach (ActionExecutor)**:
1. Parse YAML (~10-50ms)
2. Execute actions directly (~100-500ms)
3. Validate states (~200-500ms)
**Total**: ~310-1050ms

**Improvement**: 50-70% faster

## Integration Points

### ServiceContainer

ActionExecutor is integrated into ServiceContainer with lazy initialization:

```python
@property
def action_executor(self) -> ActionExecutor:
    """Get or create action executor"""
    if self._action_executor is None:
        from .automation.action_executor import ActionExecutor
        from ..template_engine import TemplateEngine
        
        template_engine = TemplateEngine(ha_client=self.ha_client)
        self._action_executor = ActionExecutor(
            ha_client=self.ha_client,
            template_engine=template_engine,
            num_workers=settings.action_executor_workers,
            max_retries=settings.action_executor_max_retries,
            retry_delay=settings.action_executor_retry_delay
        )
    return self._action_executor
```

### Lifecycle Management

ActionExecutor is started on service startup and shutdown gracefully:

```python
# In main.py lifespan()
async def lifespan(app: FastAPI):
    # Startup
    service_container = ServiceContainer()
    action_executor = service_container.action_executor
    await action_executor.start()
    
    yield
    
    # Shutdown
    await action_executor.shutdown()
```

### Test Executor Integration

AutomationTestExecutor uses ActionExecutor for test execution:

```python
async def execute_test(
    self,
    automation_yaml: str,
    expected_changes: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    # Parse actions from YAML
    actions = self.action_parser.parse_actions_from_yaml(automation_yaml)
    
    # Capture entity states before execution
    before_states = await self._capture_entity_states(entity_ids)
    
    # Execute actions using ActionExecutor
    summary = await self.action_executor.execute_actions(actions, context)
    
    # Validate state changes
    state_validation = await self._validate_state_changes(...)
    
    return result
```

## Configuration

### Environment Variables

No new environment variables needed (uses existing HA_URL, HA_TOKEN)

### Service Configuration

**File**: `services/ai-automation-service/src/config.py`

```python
action_executor_workers: int = 2  # Number of worker tasks
action_executor_max_retries: int = 3  # Maximum retry attempts
action_executor_retry_delay: float = 1.0  # Initial retry delay in seconds
use_action_executor: bool = True  # Enable ActionExecutor (feature flag)
```

## Migration Strategy

### Backward Compatibility

- Feature flag: `use_action_executor` (default: True)
- Falls back to create/delete automation approach if ActionExecutor fails
- Gradual rollout: Test with feature flag, then enable by default

### Rollback Plan

- Feature flag can disable ActionExecutor
- Falls back to create/delete automation approach
- No data migration needed (in-memory only)

## Testing

### Unit Tests

**File**: `services/ai-automation-service/tests/test_action_executor.py`

**Test Cases**:
- Action queuing and execution
- Retry logic with exponential backoff
- Parallel action execution
- Sequence action execution
- Delay handling
- Error handling and retry exhaustion
- Worker shutdown and cleanup
- YAML parsing (2025 format)

### Integration Tests

**File**: `services/ai-automation-service/tests/integration/test_action_executor_integration.py`

**Test Cases**:
- End-to-end test execution via ActionExecutor
- Real HA service calls (with mocked HA if needed)
- State validation after action execution
- Performance comparison vs. old method

## Future Enhancements

1. **Persistent Queue**: Move from in-memory to Redis for durability
2. **Action Scheduling**: Support scheduled action execution
3. **Action Dependencies**: Support action dependencies and ordering
4. **Action Rollback**: Support rolling back failed action sequences
5. **Metrics & Monitoring**: Add Prometheus metrics for execution tracking
6. **Action History**: Store action execution history for debugging

## References

- Home Assistant REST API: https://developers.home-assistant.io/docs/api/rest/
- Home Assistant 2025 YAML Format: https://www.home-assistant.io/docs/automation/
- Pydantic v2: https://docs.pydantic.dev/
- asyncio Queue: https://docs.python.org/3/library/asyncio-queue.html

