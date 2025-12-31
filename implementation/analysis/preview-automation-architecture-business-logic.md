# Preview Automation - Architecture & Business Logic Analysis

**Date:** December 31, 2025  
**Analyzed By:** TappsCodingAgents (Planner, Architect, Reviewer)  
**Scope:** Architecture patterns, service integrations, business logic, data flow

## Executive Summary

The preview automation feature follows a **Preview-and-Approval Workflow** pattern with multiple service dependencies. While functional, there are opportunities to improve separation of concerns, reduce coupling, and enhance business logic validation.

## Current Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                      │
│  (ai-automation-ui - React/TypeScript)                      │
│  - AutomationPreview.tsx                                     │
│  - HAAgentChat.tsx                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/WebSocket
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              HA AI Agent Service (Port 8024)                 │
│  - HAToolHandler (Business Logic)                            │
│  - Tool Schemas (API Contracts)                              │
│  - System Prompt (Business Rules)                            │
└───────┬───────────────┬───────────────┬─────────────────────┘
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ YAML         │ │ AI           │ │ Data API     │
│ Validation   │ │ Automation   │ │ (Port 8006)  │
│ Service      │ │ Service      │ │              │
│ (Port 8037)  │ │ (Legacy)     │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│              Home Assistant (Port 8123)                      │
│  - Automation Creation API                                   │
│  - Entity Registry                                           │
└─────────────────────────────────────────────────────────────┘
```

### Service Dependencies

**Primary Dependencies:**
1. **YAML Validation Service** (Port 8037) - Primary validation (Epic 51)
2. **AI Automation Service** (Legacy) - Fallback validation
3. **Data API** (Port 8006) - Entity queries (optional)
4. **Home Assistant** (Port 8123) - Automation creation

**Dependency Chain:**
```
preview_automation_from_prompt
  ├─> _validate_yaml()
  │     ├─> YAML Validation Service (primary)
  │     ├─> AI Automation Service (fallback)
  │     └─> Basic validation (last resort)
  ├─> _extract_entities_from_yaml()
  ├─> _extract_areas_from_yaml()
  ├─> _extract_services_from_yaml()
  ├─> _describe_trigger()
  ├─> _describe_action()
  └─> _analyze_safety()
```

## Business Logic Flow

### Preview Workflow (Current)

```python
1. User Request → AI Agent (OpenAI)
   ↓
2. AI Agent generates YAML from prompt
   ↓
3. AI Agent calls preview_automation_from_prompt()
   ↓
4. HAToolHandler.preview_automation_from_prompt()
   ├─> Validate parameters (user_prompt, automation_yaml, alias)
   ├─> Validate YAML syntax (3-tier fallback)
   ├─> Parse YAML to extract details
   ├─> Extract entities, areas, services
   ├─> Generate human-readable descriptions
   ├─> Analyze safety considerations
   └─> Return preview object
   ↓
5. UI displays preview with validation results
   ↓
6. User approves/rejects/modifies
   ↓
7. If approved → create_automation_from_prompt()
   ├─> Validate YAML again
   ├─> Create automation in Home Assistant
   └─> Return automation ID
```

### Business Rules (From System Prompt)

**Mandatory Workflow:**
1. ✅ Preview MUST be generated before creation
2. ✅ User approval REQUIRED before creation
3. ✅ YAML must be valid Home Assistant 2025.10+ format
4. ✅ `initial_state: true` is REQUIRED
5. ✅ Entity resolution follows strict guidelines (area → keyword → device type)

**Validation Rules:**
- Entity matches: Verify area + keywords + device type
- Effect names: Must be EXACT (case-sensitive)
- Context completeness: All entities/areas/effects must exist
- Tool usage: Only call tools if context incomplete

**Safety Rules:**
- Security domains (lock, alarm, camera) require warnings
- Critical devices require time-based constraints
- Edge cases and failure modes must be considered

## Architectural Issues

### 1. **Tight Coupling** (Priority: HIGH)

**Issue:** `HAToolHandler` directly depends on multiple services with fallback chains.

**Current Pattern:**
```python
# Three-tier fallback in _validate_yaml()
if self.yaml_validation_client:
    # Try YAML Validation Service
    try:
        result = await self.yaml_validation_client.validate_yaml(...)
    except:
        # Fall through
if self.ai_automation_client:
    # Try AI Automation Service
    try:
        result = await self.ai_automation_client.validate_yaml(...)
    except:
        # Fall through
# Basic validation (last resort)
```

**Problems:**
- Complex error handling with nested try/except
- Hard to test (multiple dependencies)
- Violates Single Responsibility Principle
- Difficult to add new validation services

**Recommendation:** Use **Strategy Pattern** or **Chain of Responsibility**

```python
class ValidationStrategy(ABC):
    @abstractmethod
    async def validate(self, yaml: str) -> ValidationResult:
        pass

class ValidationChain:
    def __init__(self, strategies: list[ValidationStrategy]):
        self.strategies = strategies
    
    async def validate(self, yaml: str) -> ValidationResult:
        for strategy in self.strategies:
            try:
                result = await strategy.validate(yaml)
                if result.valid:
                    return result
            except Exception as e:
                logger.warning(f"{strategy} failed: {e}")
                continue
        return ValidationResult(valid=False, errors=["All validation strategies failed"])
```

---

### 2. **Business Logic in Tool Handler** (Priority: HIGH)

**Issue:** Business rules are scattered across:
- System prompt (string-based rules)
- Tool handler (code-based rules)
- Validation services (service-based rules)

**Current:**
- Entity resolution rules → System prompt (lines 69-93)
- Validation rules → Tool handler + services
- Safety rules → Tool handler + system prompt

**Problem:** No single source of truth for business rules.

**Recommendation:** Extract to **Business Rules Engine**

```python
class AutomationBusinessRules:
    """Centralized business rules for automation creation."""
    
    def validate_entity_resolution(
        self, 
        user_prompt: str, 
        entities: list[str], 
        context: HomeAssistantContext
    ) -> ValidationResult:
        """Apply entity resolution rules from system prompt."""
        # Rules:
        # 1. Area filtering first
        # 2. Positional keyword matching
        # 3. Device type matching
        # 4. Validation
        pass
    
    def validate_effect_names(
        self, 
        effects: list[str], 
        entity_attributes: dict
    ) -> ValidationResult:
        """Validate effect names are exact (case-sensitive)."""
        pass
    
    def check_safety_requirements(
        self, 
        automation: dict, 
        entities: list[str]
    ) -> list[str]:
        """Check safety rules and return warnings."""
        pass
```

---

### 3. **Missing State Management** (Priority: MEDIUM)

**Issue:** No tracking of preview state or approval workflow.

**Current:**
- Preview generated → Returned to UI
- No persistence of preview state
- No tracking of approval/rejection
- No audit trail

**Recommendation:** Add **State Machine** or **Workflow Engine**

```python
class AutomationWorkflowState(Enum):
    PROMPT_RECEIVED = "prompt_received"
    PREVIEW_GENERATED = "preview_generated"
    PREVIEW_DISPLAYED = "preview_displayed"
    USER_APPROVED = "user_approved"
    USER_REJECTED = "user_rejected"
    USER_MODIFIED = "user_modified"
    AUTOMATION_CREATED = "automation_created"
    AUTOMATION_FAILED = "automation_failed"

class AutomationWorkflow:
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.state = AutomationWorkflowState.PROMPT_RECEIVED
        self.preview_data = None
        self.approval_data = None
    
    async def generate_preview(self, prompt: str, yaml: str) -> dict:
        """Generate preview and transition to PREVIEW_GENERATED."""
        # ... generate preview
        self.state = AutomationWorkflowState.PREVIEW_GENERATED
        self.preview_data = preview
        return preview
    
    async def approve(self) -> dict:
        """Approve and transition to USER_APPROVED."""
        if self.state != AutomationWorkflowState.PREVIEW_GENERATED:
            raise InvalidStateTransitionError()
        self.state = AutomationWorkflowState.USER_APPROVED
        # ... create automation
        return result
```

---

### 4. **Data Flow Complexity** (Priority: MEDIUM)

**Issue:** Data flows through multiple transformations without clear contracts.

**Current Flow:**
```
User Prompt (string)
  → AI Agent (generates YAML)
  → preview_automation_from_prompt (validates, extracts)
  → UI (displays preview)
  → User approves
  → create_automation_from_prompt (validates again, creates)
  → Home Assistant (stores automation)
```

**Problems:**
- YAML validated twice (preview + creation)
- Data transformations scattered
- No clear data contracts

**Recommendation:** Use **Data Transfer Objects (DTOs)**

```python
@dataclass
class AutomationPreviewRequest:
    user_prompt: str
    automation_yaml: str
    alias: str

@dataclass
class AutomationPreviewResponse:
    success: bool
    preview: AutomationPreview
    validation: ValidationResult
    entities_affected: list[str]
    areas_affected: list[str]
    services_used: list[str]
    safety_warnings: list[str]

@dataclass
class AutomationPreview:
    alias: str
    description: str
    trigger_description: str
    action_description: str
    mode: str
    initial_state: bool
```

---

### 5. **Error Handling Strategy** (Priority: MEDIUM)

**Issue:** Inconsistent error handling across service boundaries.

**Current:**
- Validation errors → Returned in response
- Service errors → Logged and fallback
- Network errors → Generic error messages

**Recommendation:** Use **Result Pattern** or **Exception Hierarchy**

```python
class AutomationError(Exception):
    """Base exception for automation errors."""
    pass

class ValidationError(AutomationError):
    """YAML validation failed."""
    pass

class EntityResolutionError(AutomationError):
    """Entity resolution failed."""
    pass

class SafetyViolationError(AutomationError):
    """Safety rule violated."""
    pass

# Usage
try:
    result = await self.preview_automation_from_prompt(args)
except ValidationError as e:
    return {"success": False, "error": f"Validation failed: {e}", "error_code": "VALIDATION_ERROR"}
except EntityResolutionError as e:
    return {"success": False, "error": f"Entity resolution failed: {e}", "error_code": "ENTITY_ERROR"}
```

---

## Business Logic Enhancements

### 1. **Entity Resolution Service** (Priority: HIGH)

**Current:** Entity resolution logic in system prompt (string-based rules).

**Enhancement:** Extract to dedicated service with testable logic.

```python
class EntityResolutionService:
    """Business logic for entity resolution."""
    
    async def resolve_entities(
        self,
        user_prompt: str,
        context: HomeAssistantContext
    ) -> EntityResolutionResult:
        """
        Resolve entities from user prompt using business rules:
        1. Area filtering first
        2. Positional keyword matching
        3. Device type matching
        4. Validation
        """
        # Extract area from prompt
        area = self._extract_area(user_prompt, context.areas)
        
        # Filter entities by area
        area_entities = self._filter_by_area(area, context.entities)
        
        # Apply positional keywords
        positional_entities = self._match_positional_keywords(
            user_prompt, area_entities
        )
        
        # Apply device type matching
        device_entities = self._match_device_type(
            user_prompt, positional_entities
        )
        
        # Validate matches
        return self._validate_matches(device_entities, user_prompt)
```

---

### 2. **Preview Caching** (Priority: MEDIUM)

**Current:** Preview regenerated on every request.

**Enhancement:** Cache previews by YAML hash to avoid redundant validation.

```python
class PreviewCache:
    """Cache preview results to avoid redundant validation."""
    
    def __init__(self, ttl: int = 3600):
        self.cache: dict[str, CachedPreview] = {}
        self.ttl = ttl
    
    async def get_or_generate(
        self,
        yaml_hash: str,
        generator: Callable[[], Awaitable[dict]]
    ) -> dict:
        """Get cached preview or generate new one."""
        if yaml_hash in self.cache:
            cached = self.cache[yaml_hash]
            if not cached.is_expired():
                return cached.preview
        
        preview = await generator()
        self.cache[yaml_hash] = CachedPreview(preview, time.time() + self.ttl)
        return preview
```

---

### 3. **Business Rule Validation** (Priority: MEDIUM)

**Current:** Business rules enforced in system prompt (not enforceable).

**Enhancement:** Enforce business rules in code.

```python
class BusinessRuleValidator:
    """Validate business rules before preview generation."""
    
    def validate_preview_request(
        self,
        request: AutomationPreviewRequest,
        context: HomeAssistantContext
    ) -> ValidationResult:
        """Validate business rules."""
        errors = []
        
        # Rule 1: Entity resolution
        entity_result = self.entity_resolver.resolve(
            request.user_prompt, context
        )
        if not entity_result.success:
            errors.append(f"Entity resolution failed: {entity_result.error}")
        
        # Rule 2: Effect names
        effects = self._extract_effects(request.automation_yaml)
        for effect in effects:
            if not self._validate_effect_name(effect, context):
                errors.append(f"Invalid effect name: {effect}")
        
        # Rule 3: Context completeness
        missing = self._check_context_completeness(request, context)
        if missing:
            errors.append(f"Missing context: {', '.join(missing)}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )
```

---

### 4. **Approval Workflow Tracking** (Priority: LOW)

**Current:** No tracking of approval/rejection rates.

**Enhancement:** Track metrics for business insights.

```python
class ApprovalMetrics:
    """Track approval/rejection metrics."""
    
    async def track_preview_generated(
        self,
        conversation_id: str,
        preview: AutomationPreview
    ):
        """Track preview generation."""
        await self.metrics_service.increment(
            "automation.preview.generated",
            tags={
                "conversation_id": conversation_id,
                "entities_count": len(preview.entities_affected),
                "has_warnings": len(preview.safety_warnings) > 0
            }
        )
    
    async def track_approval(
        self,
        conversation_id: str,
        approved: bool,
        reason: Optional[str] = None
    ):
        """Track approval/rejection."""
        await self.metrics_service.increment(
            f"automation.preview.{'approved' if approved else 'rejected'}",
            tags={
                "conversation_id": conversation_id,
                "reason": reason or "unknown"
            }
        )
```

---

## Recommended Implementation Priority

### Phase 1: Critical Architecture Improvements
1. ✅ **Extract Business Rules** - Move rules from system prompt to code
2. ✅ **Add Validation Strategy Pattern** - Replace 3-tier fallback
3. ✅ **Add DTOs** - Clear data contracts

### Phase 2: Business Logic Enhancements
4. ✅ **Entity Resolution Service** - Extract to testable service
5. ✅ **Business Rule Validator** - Enforce rules in code
6. ✅ **Error Handling Hierarchy** - Consistent error handling

### Phase 3: Operational Improvements
7. ✅ **Preview Caching** - Reduce redundant validation
8. ✅ **State Management** - Track workflow state
9. ✅ **Approval Metrics** - Business insights

---

## Testing Recommendations

After implementing enhancements:
1. **Unit Tests** - Test business rules in isolation
2. **Integration Tests** - Test service integrations
3. **Workflow Tests** - Test complete preview → approval → creation flow
4. **Performance Tests** - Test caching and validation performance

---

## Related Documentation

- [Code Quality Analysis](./preview-automation-enhancements.md) - Code-level improvements
- [System Prompt](../services/ha-ai-agent-service/src/prompts/system_prompt.py) - Business rules
- [Tool Handler](../services/ha-ai-agent-service/src/tools/ha_tools.py) - Implementation
