# Step 4: Component Design - Logging Improvements

**Date**: 2026-01-02  
**Workflow**: Simple Mode *build  
**Feature**: Implement logging improvements for HA AI Agent Service

## Component Design Specifications

### 1. Logging Format Specification

#### Standard Log Format
```
[Operation] [Status] [Message] [Context] [Metrics]
```

**Components**:
- **Operation**: `[Preview]`, `[Create]`, `[Enhancement]`
- **Status**: `✅`, `❌`, `⚠️`, `🔍` (for debug)
- **Message**: Descriptive message
- **Context**: `(conversation_id={id}, alias={alias})`
- **Metrics**: `[entities=5, areas=1, warnings=0]`

#### Examples

**Info Log**:
```python
logger.info(
    f"[Preview] ✅ Generated for automation '{request.alias}' "
    f"(conversation_id={conversation_id}). "
    f"Entities: {len(extraction_result['entities'])}, "
    f"Areas: {len(extraction_result['areas'])}, "
    f"Safety warnings: {len(safety_warnings)}"
)
```

**Error Log**:
```python
logger.error(
    f"[Preview] ❌ YAML parsing error for automation '{request.alias}' "
    f"(conversation_id={conversation_id}): {e}. "
    f"Prompt: '{request.user_prompt[:100]}...'",
    exc_info=True
)
```

**Warning Log**:
```python
logger.warning(
    f"[Preview] ⚠️ Failed to extract device context: {e}. "
    f"Device validation will be skipped. Automation may proceed with limited validation. "
    f"Consider manual device verification. (conversation_id={conversation_id})"
)
```

**Debug Log**:
```python
logger.debug(
    f"[Preview] 🔍 Validation chain result: valid={validation_result.valid}, "
    f"errors={len(validation_result.errors or [])}, "
    f"warnings={len(validation_result.warnings or [])}, "
    f"strategy={validation_result.strategy_name if hasattr(validation_result, 'strategy_name') else 'unknown'} "
    f"(conversation_id={conversation_id})"
)
```

### 2. Method Signature Changes

#### Before
```python
async def preview_automation_from_prompt(self, arguments: dict[str, Any]) -> dict[str, Any]:
    # No conversation_id
```

#### After
```python
async def preview_automation_from_prompt(self, arguments: dict[str, Any]) -> dict[str, Any]:
    conversation_id = arguments.get("conversation_id")  # Extract conversation_id
    # ... rest of method
```

### 3. Context Extraction Pattern

#### Pattern for All Tool Methods
```python
async def tool_method(self, arguments: dict[str, Any]) -> dict[str, Any]:
    # Extract conversation_id (optional, backward compatible)
    conversation_id = arguments.get("conversation_id")
    
    # Extract other required parameters
    user_prompt = arguments.get("user_prompt")
    alias = arguments.get("alias")
    
    # Use in logging
    logger.info(f"[Operation] Message (conversation_id={conversation_id})")
```

### 4. Error Handling Pattern

#### Enhanced Error Handling
```python
try:
    # ... operation ...
except Exception as e:
    logger.error(
        f"[Operation] ❌ Error message for automation '{alias}' "
        f"(conversation_id={conversation_id}): {e}. "
        f"Prompt: '{user_prompt[:100] if user_prompt else 'N/A'}...'",
        exc_info=True
    )
    return error_response
```

### 5. Debug Statement Placement

#### Key Flow Points for Debug Statements

1. **After Validation Chain**:
```python
validation_result = await self.validation_chain.validate(request.automation_yaml)
logger.debug(
    f"[Preview] 🔍 Validation chain result: valid={validation_result.valid}, "
    f"errors={len(validation_result.errors or [])}, "
    f"warnings={len(validation_result.warnings or [])} "
    f"(conversation_id={conversation_id})"
)
```

2. **After Entity Extraction**:
```python
extraction_result = self._extract_automation_details(automation_dict)
logger.debug(
    f"[Preview] 🔍 Extracted {len(extraction_result['entities'])} entities, "
    f"{len(extraction_result['areas'])} areas, "
    f"{len(extraction_result['services'])} services "
    f"(conversation_id={conversation_id})"
)
```

3. **After Device Context Extraction**:
```python
device_context = await self._extract_device_context(automation_dict)
logger.debug(
    f"[Preview] 🔍 Device context: {len(device_context.get('device_ids', []))} devices, "
    f"{len(device_context.get('device_types', []))} types, "
    f"{len(device_context.get('area_ids', []))} areas "
    f"(conversation_id={conversation_id})"
)
```

4. **After Safety Score Calculation**:
```python
safety_score = self.business_rule_validator.calculate_safety_score(...)
logger.debug(
    f"[Preview] 🔍 Safety score calculated: {safety_score:.2f} "
    f"(conversation_id={conversation_id})"
)
```

### 6. Warning Message Pattern

#### Enhanced Warning Format
```python
logger.warning(
    f"[Operation] ⚠️ [What went wrong]. "
    f"Impact: [What's affected]. "
    f"Consider: [Remediation suggestion]. "
    f"(conversation_id={conversation_id})"
)
```

#### Examples

**Device Context Failure**:
```python
logger.warning(
    f"[Preview] ⚠️ Failed to extract device context: {e}. "
    f"Impact: Device validation will be skipped. Automation may proceed with limited validation. "
    f"Consider: Manual device verification before deployment. "
    f"(conversation_id={conversation_id})"
)
```

**Device Validation Failure**:
```python
logger.warning(
    f"[Preview] ⚠️ Failed to validate devices: {e}. "
    f"Impact: Device health scores and capability checks will be skipped. "
    f"Consider: Manual verification before deployment. "
    f"(conversation_id={conversation_id})"
)
```

### 7. Success Log Pattern

#### Enhanced Success Format
```python
logger.info(
    f"[Operation] ✅ Success message "
    f"[alias={alias}] "
    f"[entities={count}, areas={count}, warnings={count}] "
    f"(conversation_id={conversation_id})"
)
```

#### Example
```python
logger.info(
    f"[Preview] ✅ Preview generated for automation '{request.alias}' "
    f"(conversation_id={conversation_id}). "
    f"Entities: {len(extraction_result['entities'])}, "
    f"Areas: {len(extraction_result['areas'])}, "
    f"Safety warnings: {len(safety_warnings)}"
)
```

### 8. Helper Function Pattern (Optional)

#### Logging Helper Function
```python
def _log_with_context(
    self,
    level: str,
    operation: str,
    message: str,
    conversation_id: str | None = None,
    alias: str | None = None,
    metrics: dict[str, Any] | None = None,
    exc_info: bool = False
) -> None:
    """Helper function for consistent logging format."""
    context_parts = []
    if conversation_id:
        context_parts.append(f"conversation_id={conversation_id}")
    if alias:
        context_parts.append(f"alias={alias}")
    
    context_str = f"({', '.join(context_parts)})" if context_parts else ""
    
    metrics_str = ""
    if metrics:
        metrics_parts = [f"{k}={v}" for k, v in metrics.items()]
        metrics_str = f" [{', '.join(metrics_parts)}]"
    
    full_message = f"[{operation}] {message} {context_str}{metrics_str}"
    
    if level == "info":
        logger.info(full_message)
    elif level == "error":
        logger.error(full_message, exc_info=exc_info)
    elif level == "warning":
        logger.warning(full_message)
    elif level == "debug":
        logger.debug(full_message)
```

**Usage**:
```python
self._log_with_context(
    level="info",
    operation="Preview",
    message="✅ Preview generated",
    conversation_id=conversation_id,
    alias=request.alias,
    metrics={
        "entities": len(extraction_result['entities']),
        "areas": len(extraction_result['areas']),
        "warnings": len(safety_warnings)
    }
)
```

## Design Decisions

### Decision 1: Inline Logging vs Helper Function
**Chosen**: Inline logging (for now)
**Rationale**: More explicit, easier to read, no abstraction overhead
**Future**: Can refactor to helper function if pattern becomes too repetitive

### Decision 2: Conditional Context Formatting
**Chosen**: Always include conversation_id (use "N/A" if None)
**Rationale**: Consistent format, easier to parse logs
**Alternative**: Conditional inclusion (rejected - inconsistent)

### Decision 3: Truncation Length
**Chosen**: 100 characters for user prompts
**Rationale**: Balance between context and log size
**Alternative**: 50 chars (too short), 200 chars (too long)

### Decision 4: Status Emojis
**Chosen**: Use emojis (✅, ❌, ⚠️, 🔍)
**Rationale**: Visual scanning, consistent with existing codebase
**Alternative**: Text status (rejected - less scannable)

## Testing Considerations

### Unit Tests
- Test conversation_id extraction from arguments
- Test log message format
- Test backward compatibility (conversation_id=None)
- Test error logging with full context

### Integration Tests
- Test log output contains conversation_id
- Test log aggregation by conversation_id
- Test performance impact of logging

## Implementation Checklist

- [ ] Add conversation_id parameter extraction
- [ ] Update all logger.info() calls
- [ ] Update all logger.error() calls
- [ ] Update all logger.warning() calls
- [ ] Add debug statements at key flow points
- [ ] Enhance error messages with context
- [ ] Enhance warning messages with impact
- [ ] Add metrics to success logs
- [ ] Test backward compatibility
- [ ] Update tests
