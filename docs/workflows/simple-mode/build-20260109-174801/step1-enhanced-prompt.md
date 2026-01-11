# Enhanced Prompt: Integrate shared prompt guidance system into Proactive Agent Service. Replace the hardcoded SUGGESTION_SYSTEM_PROMPT in services/proactive-agent-service/src/services/ai_prompt_generation_service.py with PromptBuilder.build_suggestion_generation_prompt() from shared.prompt_guidance.builder. Update the _call_llm method to use the PromptBuilder instead of the hardcoded prompt constant.

[Context7: Detected 2 libraries. Documentation available for 2 libraries.]

## Metadata
- **Created**: 2026-01-09T17:48:01.599769

## Analysis
- **Intent**: unknown
- **Scope**: unknown
- **Workflow Type**: unknown
- **Complexity**: medium
- **Technologies**: playwright, puppeteer

## Requirements
## Architecture Guidance
## Codebase Context
## Codebase Context

### Related Files
- `shared\prompt_guidance\builder.py`
- `shared\prompt_guidance\templates\suggestion_generation.py`
- `shared\prompt_guidance\vocabulary.py`
- `shared\prompt_guidance\__init__.py`
- `TappsCodingAgents\demo\demo_prompt_enhancement.py`
- `shared\prompt_guidance\templates\automation_generation.py`
- `shared\prompt_guidance\templates\__init__.py`
- `shared\prompt_guidance\core_principles.py`
- `shared\prompt_guidance\templates\yaml_generation.py`
- `shared\prompt_guidance\homeiq_json_schema.py`

### Existing Patterns
- **Common Import Patterns** (architectural): Commonly imported modules: core_principles, templates

### Cross-References
- No cross-references found

### Context Summary
Found 10 related files in the codebase. Extracted 1 patterns and 0 cross-references. Use these as reference when implementing new features.

### Related Files
- C:\cursor\HomeIQ\shared\prompt_guidance\builder.py
- C:\cursor\HomeIQ\shared\prompt_guidance\templates\suggestion_generation.py
- C:\cursor\HomeIQ\shared\prompt_guidance\vocabulary.py
- C:\cursor\HomeIQ\shared\prompt_guidance\__init__.py
- C:\cursor\HomeIQ\TappsCodingAgents\demo\demo_prompt_enhancement.py
- C:\cursor\HomeIQ\shared\prompt_guidance\templates\automation_generation.py
- C:\cursor\HomeIQ\shared\prompt_guidance\templates\__init__.py
- C:\cursor\HomeIQ\shared\prompt_guidance\core_principles.py
- C:\cursor\HomeIQ\shared\prompt_guidance\templates\yaml_generation.py
- C:\cursor\HomeIQ\shared\prompt_guidance\homeiq_json_schema.py

### Existing Patterns
- {'type': 'architectural', 'name': 'Common Import Patterns', 'description': 'Commonly imported modules: core_principles, templates', 'examples': ['C:\\cursor\\HomeIQ\\shared\\prompt_guidance\\builder.py', 'C:\\cursor\\HomeIQ\\shared\\prompt_guidance\\templates\\suggestion_generation.py', 'C:\\cursor\\HomeIQ\\shared\\prompt_guidance\\vocabulary.py'], 'confidence': 0.4}

## Quality Standards
### Code Quality Thresholds
- **Overall Score Threshold**: 70.0

## Implementation Strategy
## Enhanced Prompt