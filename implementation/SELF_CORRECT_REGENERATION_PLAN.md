# Self-Correction Regeneration via Ask AI - Implementation Plan

**Created:** December 5, 2025  
**Status:** ✅ IMPLEMENTED  
**Epic:** Self-Correction Enhancement

## Overview

Enhance the YAML Self-Correction Service to regenerate prompts through the full Ask AI pipeline when iterative refinement fails to achieve convergence.

## Current Architecture

### Existing Self-Correction Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                  Current Self-Correction Flow                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User Prompt + Generated YAML                                    │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────┐                                        │
│  │ Reverse Engineer    │  Convert YAML → Natural Language       │
│  │ (RPE)               │                                        │
│  └─────────┬───────────┘                                        │
│            │                                                     │
│            ▼                                                     │
│  ┌─────────────────────┐                                        │
│  │ Calculate Similarity│  Embedding comparison (SentenceTransf) │
│  │                     │  Target: 85%                           │
│  └─────────┬───────────┘                                        │
│            │                                                     │
│            ▼                                                     │
│    similarity >= 85%?                                            │
│     /            \                                               │
│   YES             NO                                             │
│    │               │                                             │
│    │               ▼                                             │
│    │     ┌─────────────────────┐                                │
│    │     │ Generate Feedback   │  PASR technique                │
│    │     └─────────┬───────────┘                                │
│    │               │                                             │
│    │               ▼                                             │
│    │     ┌─────────────────────┐                                │
│    │     │ Refine YAML         │  Iterate up to 5x              │
│    │     └─────────┬───────────┘                                │
│    │               │                                             │
│    │               ▼                                             │
│    │         Loop back to Reverse Engineer                       │
│    │                                                             │
│    ▼                                                             │
│  ┌─────────────────────┐                                        │
│  │ Return Final YAML   │                                        │
│  └─────────────────────┘                                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Files

| File | Purpose |
|------|---------|
| `services/ai-automation-service/src/services/yaml_self_correction.py` | Main self-correction service |
| `services/ai-automation-service/src/services/automation/yaml_generation_service.py` | YAML generation from prompts |
| `services/ai-automation-service/src/services/automation/yaml_validator.py` | Multi-stage YAML validation |
| `services/ai-automation-service/src/api/ask_ai_router.py` | Ask AI endpoint orchestration |

## Proposed Architecture

### Enhanced Self-Correction Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│               Enhanced Self-Correction Flow (with Regeneration)          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  User Prompt + Generated YAML + Context                                  │
│           │                                                              │
│           ▼                                                              │
│  ┌─────────────────────────────────────────────────────────┐            │
│  │           PHASE 1: ITERATIVE REFINEMENT                  │            │
│  │  ┌─────────────────────┐                                │            │
│  │  │ Reverse Engineer    │                                │            │
│  │  └─────────┬───────────┘                                │            │
│  │            ▼                                             │            │
│  │  ┌─────────────────────┐                                │            │
│  │  │ Calculate Similarity│                                │            │
│  │  └─────────┬───────────┘                                │            │
│  │            ▼                                             │            │
│  │    similarity >= 85%? ──YES──► Return YAML ◄────┐       │            │
│  │            │NO                                   │       │            │
│  │            ▼                                     │       │            │
│  │  ┌─────────────────────┐                        │       │            │
│  │  │ Refine YAML         │ ─────loop (5x max)─────┘       │            │
│  │  └─────────────────────┘                                │            │
│  │            │                                             │            │
│  │      Max iterations reached & similarity < threshold     │            │
│  └────────────┼─────────────────────────────────────────────┘            │
│               │                                                          │
│               ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐            │
│  │           PHASE 2: REGENERATION VIA ASK AI               │            │
│  │                                                          │            │
│  │  ┌─────────────────────┐                                │            │
│  │  │ Generate Fresh YAML │  Full Ask AI pipeline          │            │
│  │  │ from Original Prompt│  (OpenAI call with context)    │            │
│  │  └─────────┬───────────┘                                │            │
│  │            │                                             │            │
│  │            ▼                                             │            │
│  │  ┌─────────────────────┐                                │            │
│  │  │ YAML Validation     │  Multi-stage validation        │            │
│  │  │ Pipeline            │  (Syntax, Structure, Entity,   │            │
│  │  │                     │   Logic, Safety)               │            │
│  │  └─────────┬───────────┘                                │            │
│  │            │                                             │            │
│  │     validation passed?                                   │            │
│  │      /            \                                      │            │
│  │    YES             NO                                    │            │
│  │     │               │                                    │            │
│  │     │               ▼                                    │            │
│  │     │     ┌─────────────────────┐                       │            │
│  │     │     │ Attempt Auto-Fix    │                       │            │
│  │     │     │ (structure fixes)   │                       │            │
│  │     │     └─────────┬───────────┘                       │            │
│  │     │               │                                    │            │
│  │     ▼               ▼                                    │            │
│  │  ┌─────────────────────┐                                │            │
│  │  │ Calculate Final     │                                │            │
│  │  │ Similarity          │                                │            │
│  │  └─────────┬───────────┘                                │            │
│  │            │                                             │            │
│  └────────────┼─────────────────────────────────────────────┘            │
│               │                                                          │
│               ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐            │
│  │           PHASE 3: SELECTION                             │            │
│  │                                                          │            │
│  │  Compare:                                                │            │
│  │  - Original refined YAML (from Phase 1)                  │            │
│  │  - Regenerated YAML (from Phase 2)                       │            │
│  │                                                          │            │
│  │  Select based on:                                        │            │
│  │  1. Validation status (prefer valid YAML)                │            │
│  │  2. Similarity score (prefer higher)                     │            │
│  │  3. Entity coverage (prefer more entities resolved)      │            │
│  │                                                          │            │
│  └─────────────────────────────────────────────────────────┘            │
│               │                                                          │
│               ▼                                                          │
│  ┌─────────────────────┐                                                │
│  │ Return Best YAML    │                                                │
│  │ + Metrics           │                                                │
│  └─────────────────────┘                                                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Implementation Tasks

### Task 1: Add Regeneration Method

**File:** `services/ai-automation-service/src/services/yaml_self_correction.py`

```python
async def _regenerate_yaml_via_ask_ai(
    self,
    user_prompt: str,
    context: dict[str, Any] | None = None,
    comprehensive_enriched_data: dict[str, dict[str, Any]] | None = None,
    validated_entities: dict[str, str] | None = None
) -> tuple[str, dict[str, Any]]:
    """
    Regenerate YAML from scratch using the Ask AI YAML generation pipeline.
    
    This is called when iterative refinement fails to achieve convergence.
    Uses the same pipeline as the initial YAML generation but with fresh context.
    
    Args:
        user_prompt: Original user request
        context: Optional context (devices, areas, etc.)
        comprehensive_enriched_data: Entity enrichment data
        validated_entities: Pre-validated entity mappings
        
    Returns:
        Tuple of (regenerated_yaml, validation_result)
    """
```

**Implementation Steps:**
1. Import `generate_automation_yaml` from yaml_generation_service
2. Build suggestion dict from user_prompt and context
3. Call generate_automation_yaml with full context
4. Run YAML validation pipeline
5. Return regenerated YAML with validation results

### Task 2: Add YAML Validation Integration

**File:** `services/ai-automation-service/src/services/yaml_self_correction.py`

```python
async def _validate_regenerated_yaml(
    self,
    yaml_content: str,
    context: dict[str, Any] | None = None
) -> ValidationPipelineResult:
    """
    Run full validation pipeline on regenerated YAML.
    
    Uses AutomationYAMLValidator for comprehensive validation.
    """
```

**Validation Stages:**
1. Syntax validation (YAML parsing)
2. Structure validation (HA format compliance)
3. Entity existence validation (if HA client available)
4. Logic validation (no circular triggers)
5. Safety checks (no destructive unconfirmed actions)

### Task 3: Update Main Correction Loop

**File:** `services/ai-automation-service/src/services/yaml_self_correction.py`

**Modify `correct_yaml()` method:**

```python
async def correct_yaml(
    self,
    user_prompt: str,
    generated_yaml: str,
    context: dict | None = None,
    comprehensive_enriched_data: dict[str, dict[str, Any]] | None = None,
    validated_entities: dict[str, str] | None = None,  # NEW
    enable_regeneration: bool = True  # NEW: Control regeneration phase
) -> SelfCorrectionResponse:
    """
    Enhanced self-correction with regeneration fallback.
    
    Phase 1: Iterative refinement (existing logic)
    Phase 2: Regeneration via Ask AI (if Phase 1 fails)
    Phase 3: Selection of best result
    """
```

**Logic Flow:**
```python
# Phase 1: Existing refinement loop
# ... (keep existing code)

# Check if regeneration is needed
if not convergence_achieved and final_similarity < self.regeneration_threshold:
    logger.info("🔄 Phase 2: Attempting regeneration via Ask AI...")
    
    # Phase 2: Regenerate YAML
    regenerated_yaml, validation_result = await self._regenerate_yaml_via_ask_ai(
        user_prompt=user_prompt,
        context=context,
        comprehensive_enriched_data=comprehensive_enriched_data,
        validated_entities=validated_entities
    )
    
    # Calculate similarity for regenerated YAML
    if validation_result.valid:
        regen_reverse, _ = await self._reverse_engineer_yaml(regenerated_yaml, context)
        regen_similarity = await self._calculate_similarity(user_prompt, regen_reverse)
        
        # Phase 3: Select best result
        if regen_similarity > final_similarity:
            logger.info(f"✅ Regenerated YAML is better: {regen_similarity:.2%} > {final_similarity:.2%}")
            current_yaml = regenerated_yaml
            final_similarity = regen_similarity
            # Update response to indicate regeneration was used
```

### Task 4: Add Configuration Options

**File:** `services/ai-automation-service/src/services/yaml_self_correction.py`

```python
class YAMLSelfCorrectionService:
    def __init__(
        self,
        openai_client: AsyncOpenAI,
        model: str = "gpt-4o-mini",
        similarity_model: str = "all-MiniLM-L6-v2",
        ha_client: Any | None = None,
        device_intelligence_client: Any | None = None,
        # NEW configuration options
        enable_regeneration: bool = True,
        regeneration_threshold: float = 0.70,  # Trigger regen if similarity < 70%
        max_regeneration_attempts: int = 2,
        yaml_generation_service: Any | None = None  # Optional injection
    ):
```

### Task 5: Update Response Model

**File:** `services/ai-automation-service/src/services/yaml_self_correction.py`

```python
@dataclass
class SelfCorrectionResponse:
    """Final result after all iterations"""
    final_yaml: str
    final_similarity: float
    iterations_completed: int
    max_iterations: int
    convergence_achieved: bool
    iteration_history: list[CorrectionResult]
    total_tokens_used: int
    # Existing metrics...
    
    # NEW: Regeneration metrics
    regeneration_attempted: bool = False
    regeneration_successful: bool = False
    regeneration_similarity: float | None = None
    regeneration_validation_passed: bool | None = None
    yaml_source: str = "refinement"  # "refinement" | "regeneration" | "original"
```

### Task 6: Add Dependency Injection

To avoid circular imports, inject the YAML generation capability:

```python
# In yaml_self_correction.py
from typing import Callable, Awaitable

YAMLGeneratorFunc = Callable[
    [str, dict[str, Any] | None, dict[str, str] | None],
    Awaitable[tuple[str, dict[str, Any]]]
]

class YAMLSelfCorrectionService:
    def __init__(
        self,
        # ... existing params ...
        yaml_generator: YAMLGeneratorFunc | None = None
    ):
        self.yaml_generator = yaml_generator
```

**In ask_ai_router.py (initialization):**
```python
async def _generate_yaml_for_regeneration(
    user_prompt: str,
    context: dict[str, Any] | None,
    validated_entities: dict[str, str] | None
) -> tuple[str, dict[str, Any]]:
    """Wrapper for YAML generation callable"""
    suggestion = {
        "description": user_prompt,
        "trigger_summary": "",
        "action_summary": "",
        "validated_entities": validated_entities or {}
    }
    return await generate_automation_yaml(
        suggestion=suggestion,
        validated_entities=validated_entities or {},
        enriched_entity_context="",
        openai_client=openai_client,
        ha_client=ha_client
    )

# Pass to self-correction service
_self_correction_service = YAMLSelfCorrectionService(
    openai_client.client,
    ha_client=ha_client,
    device_intelligence_client=_device_intelligence_client,
    yaml_generator=_generate_yaml_for_regeneration
)
```

## Testing Plan

### Unit Tests

```python
# test_yaml_self_correction_regeneration.py

@pytest.mark.asyncio
async def test_regeneration_triggered_on_low_similarity():
    """Test that regeneration is triggered when similarity is below threshold"""
    
@pytest.mark.asyncio
async def test_regeneration_not_triggered_on_high_similarity():
    """Test that regeneration is skipped when refinement succeeds"""
    
@pytest.mark.asyncio
async def test_best_yaml_selected_after_regeneration():
    """Test that the best YAML (refined vs regenerated) is selected"""
    
@pytest.mark.asyncio
async def test_validation_pipeline_runs_on_regenerated_yaml():
    """Test that full validation runs on regenerated YAML"""
    
@pytest.mark.asyncio
async def test_regeneration_disabled_via_config():
    """Test that regeneration can be disabled via enable_regeneration=False"""
```

### Integration Tests

```python
# test_ask_ai_with_regeneration.py

@pytest.mark.asyncio
async def test_full_ask_ai_flow_with_regeneration():
    """End-to-end test of Ask AI with self-correction regeneration"""
    
@pytest.mark.asyncio
async def test_regeneration_with_complex_automation():
    """Test regeneration with multi-trigger, multi-action automation"""
```

## Metrics & Observability

### New Metrics to Track

| Metric | Type | Description |
|--------|------|-------------|
| `self_correction_regeneration_attempts` | Counter | Number of regeneration attempts |
| `self_correction_regeneration_success` | Counter | Successful regenerations |
| `self_correction_regeneration_similarity_gain` | Histogram | Similarity improvement from regeneration |
| `self_correction_yaml_source` | Counter | Source of final YAML (refinement/regeneration/original) |
| `self_correction_total_tokens_regeneration` | Counter | Tokens used in regeneration phase |

### Logging

```python
# Key log points for regeneration phase
logger.info(f"🔄 Phase 2: Triggering regeneration (similarity={final_similarity:.2%} < threshold={self.regeneration_threshold:.2%})")
logger.info(f"📝 Regenerating YAML via Ask AI for prompt: {user_prompt[:60]}...")
logger.info(f"✅ Regeneration validation: {'PASSED' if validation_result.valid else 'FAILED'}")
logger.info(f"📊 Regeneration similarity: {regen_similarity:.2%} vs refined: {final_similarity:.2%}")
logger.info(f"🏆 Selected YAML source: {yaml_source} (similarity: {selected_similarity:.2%})")
```

## Rollout Plan

### Phase 1: Development (1-2 days) ✅ COMPLETE
- [x] Implement `_regenerate_yaml_via_ask_ai()` method
- [x] Implement `_validate_regenerated_yaml()` method
- [x] Update `correct_yaml()` with regeneration phase
- [x] Add configuration options
- [x] Update response model (RegenerationResult dataclass)
- [x] Update get_self_correction_service() initialization

### Phase 2: Testing (1 day)
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Manual testing with various prompts

### Phase 3: Staged Rollout (1 day)
- [ ] Deploy with `enable_regeneration=True` (enabled by default)
- [ ] Monitor metrics and logs
- [ ] Adjust thresholds if needed

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Increased token usage | Medium | Regeneration only triggered below threshold; can disable via config |
| Circular dependency issues | High | Use dependency injection pattern for yaml_generator |
| Increased latency | Medium | Regeneration adds ~2-3s; only triggered on failure cases |
| Regression in existing flow | High | Comprehensive tests; staged rollout with feature flag |

## Success Criteria

1. **Primary Goal:** Regeneration improves final similarity by 10%+ when refinement fails
2. **Validation Rate:** 95%+ of regenerated YAMLs pass validation pipeline
3. **Token Efficiency:** Regeneration adds <50% tokens vs refinement-only
4. **Latency:** Regeneration phase completes in <5 seconds

## Open Questions

1. Should regeneration use a different model (e.g., GPT-4o for complex cases)?
2. Should we cache successful regenerations for similar prompts?
3. Should regeneration be triggered based on validation failures, not just similarity?

---

**Next Steps:** Review this plan and proceed with Task 1 implementation.

