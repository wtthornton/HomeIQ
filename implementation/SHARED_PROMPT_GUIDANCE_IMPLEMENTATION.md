# Shared Prompt Guidance System - Implementation Complete

**Date:** January 8, 2026  
**Status:** ✅ Implementation Complete  
**Architecture Document:** `docs/architecture/shared-prompt-guidance-system-2025.md`

## Summary

Successfully implemented the Shared Prompt Guidance System architecture to ensure consistent LLM communication across all HomeIQ services. The system establishes that:

1. **HomeIQ creates automations** (not "Home Assistant automations")
2. **HomeIQ JSON format is the standard** automation format
3. **Home Assistant YAML is only for deployment** (not for automation creation)

## Implementation

### Created Module Structure

```
shared/prompt_guidance/
├── __init__.py                      # Module exports
├── core_principles.py               # Core identity, format standard, creation flow
├── vocabulary.py                    # Shared vocabulary and terminology
├── homeiq_json_schema.py            # HomeIQ JSON schema documentation
├── builder.py                       # Prompt builder utility
└── templates/
    ├── __init__.py
    ├── automation_generation.py     # Templates for automation generation
    ├── suggestion_generation.py     # Templates for suggestion generation
    └── yaml_generation.py           # Templates for YAML generation (deployment-only)
```

### Files Created

1. **`shared/prompt_guidance/__init__.py`**
   - Module exports: `PromptBuilder`, `CORE_IDENTITY`, `AUTOMATION_FORMAT_STANDARD`, `AUTOMATION_CREATION_FLOW`

2. **`shared/prompt_guidance/core_principles.py`**
   - `CORE_IDENTITY`: HomeIQ creates automations (not "Home Assistant automations")
   - `AUTOMATION_FORMAT_STANDARD`: HomeIQ JSON is standard, YAML is deployment-only
   - `AUTOMATION_CREATION_FLOW`: 3-step flow (Suggestion → Automation → YAML)

3. **`shared/prompt_guidance/vocabulary.py`**
   - `TERMS`: Core terminology definitions
   - `USE_TERMS`: Recommended terminology
   - `AVOID_TERMS`: Terms to avoid and alternatives

4. **`shared/prompt_guidance/homeiq_json_schema.py`**
   - `HOMEIQ_JSON_SCHEMA_DOC`: Complete schema documentation for LLM prompts

5. **`shared/prompt_guidance/templates/automation_generation.py`**
   - `AUTOMATION_GENERATION_SYSTEM_PROMPT`: Template for automation generation prompts

6. **`shared/prompt_guidance/templates/suggestion_generation.py`**
   - `SUGGESTION_GENERATION_SYSTEM_PROMPT`: Template for suggestion generation prompts

7. **`shared/prompt_guidance/templates/yaml_generation.py`**
   - `YAML_GENERATION_SYSTEM_PROMPT`: Template for YAML generation prompts (deployment-only)

8. **`shared/prompt_guidance/builder.py`**
   - `PromptBuilder` class with three static methods:
     - `build_automation_generation_prompt()`: Build automation generation prompts
     - `build_suggestion_generation_prompt()`: Build suggestion generation prompts
     - `build_yaml_generation_prompt()`: Build YAML generation prompts

### Validation

✅ **Import Test:** Module imports successfully  
✅ **Linter:** No linting errors  
✅ **Structure:** Matches architecture design document

## Next Steps (Service Integration)

### Phase 2: Integrate with Services

The following services need to be updated to use the shared prompt guidance system:

1. **Proactive Agent Service** (`services/proactive-agent-service/src/services/ai_prompt_generation_service.py`)
   - Replace `SUGGESTION_SYSTEM_PROMPT` with `PromptBuilder.build_suggestion_generation_prompt()`

2. **AI Automation Service New** (`services/ai-automation-service-new/src/clients/openai_client.py`)
   - Update `generate_homeiq_automation_json()` to use `PromptBuilder.build_automation_generation_prompt()`
   - Remove "Home Assistant automation expert" language

3. **HA AI Agent Service** (`services/ha-ai-agent-service/src/prompts/system_prompt.py`)
   - Incorporate shared principles into system prompt
   - Clarify that YAML generation is deployment-only

### Migration Example

**Before (Proactive Agent Service):**
```python
SUGGESTION_SYSTEM_PROMPT = """You are HomeIQ's Proactive Automation Intelligence...
[long hardcoded prompt]
"""
```

**After:**
```python
from shared.prompt_guidance.builder import PromptBuilder

system_prompt = PromptBuilder.build_suggestion_generation_prompt(
    device_inventory=device_inventory,
    home_context=home_context
)
```

## Benefits

1. **Consistency**: All services use shared vocabulary and principles
2. **Clarity**: Clear separation between automation creation (JSON) and deployment (YAML)
3. **Maintainability**: Single source of truth for prompt guidance
4. **Extensibility**: Easy to add new prompt templates and guidance
5. **Quality**: Better automation generation through consistent principles

## Related Documentation

- Architecture Design: `docs/architecture/shared-prompt-guidance-system-2025.md`
- HomeIQ JSON Schema: `shared/homeiq_automation/schema.py`
- YAML Transformer: `shared/homeiq_automation/yaml_transformer.py`
