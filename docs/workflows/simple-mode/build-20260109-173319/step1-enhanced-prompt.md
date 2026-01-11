# Enhanced Prompt: Integrate PromptBuilder from shared.prompt_guidance into proactive-agent-service. Replace the hardcoded SUGGESTION_SYSTEM_PROMPT in ai_prompt_generation_service.py with PromptBuilder.build_suggestion_generation_prompt(). Update the _call_llm method to use the PromptBuilder. Ensure device_inventory and home_context are passed correctly.

[Context7: Detected 2 libraries. Documentation available for 2 libraries.]

## Metadata
- **Created**: 2026-01-09T17:33:20.329457

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
- `scripts\refresh-entities-from-ha-client.py`
- `.venv\Lib\site-packages\scipy\integrate\_tanhsinh.py`
- `scripts\refresh-context7-docs.py`
- `scripts\update-context7-versions.py`
- `scripts\cleanup-git-unified.py`
- `TappsCodingAgents\demo\demo_prompt_enhancement.py`
- `TappsCodingAgents\tapps_agents\core\init_project.py`
- `TappsCodingAgents\tapps_agents\context7\cache_prewarm.py`
- `TappsCodingAgents\examples\visual_feedback_example.py`
- `services\ai-pattern-service\.venv\Lib\site-packages\scipy\integrate\_tanhsinh.py`

### Existing Patterns
- **Common Import Patterns** (architectural): Commonly imported modules: asyncio, os, sys, traceback, math

### Cross-References
- `scripts\cleanup-git-unified.py` → `TappsCodingAgents\tapps_agents\core\init_project.py` (import)
  - imports from tapps_agents.core.worktree
- `scripts\cleanup-git-unified.py` → `TappsCodingAgents\tapps_agents\core\init_project.py` (import)
  - imports from tapps_agents.core.config
- `TappsCodingAgents\tapps_agents\core\init_project.py` → `TappsCodingAgents\tapps_agents\context7\cache_prewarm.py` (import)
  - imports from tapps_agents.context7.commands
- `TappsCodingAgents\tapps_agents\core\init_project.py` → `TappsCodingAgents\tapps_agents\context7\cache_prewarm.py` (import)
  - imports from tapps_agents.context7.security
- `TappsCodingAgents\tapps_agents\core\init_project.py` → `TappsCodingAgents\tapps_agents\context7\cache_prewarm.py` (import)
  - imports from tapps_agents.context7.security

### Context Summary
Found 10 related files in the codebase. Extracted 1 patterns and 8 cross-references. Use these as reference when implementing new features.

### Related Files
- C:\cursor\HomeIQ\scripts\refresh-entities-from-ha-client.py
- C:\cursor\HomeIQ\.venv\Lib\site-packages\scipy\integrate\_tanhsinh.py
- C:\cursor\HomeIQ\scripts\refresh-context7-docs.py
- C:\cursor\HomeIQ\scripts\update-context7-versions.py
- C:\cursor\HomeIQ\scripts\cleanup-git-unified.py
- C:\cursor\HomeIQ\TappsCodingAgents\demo\demo_prompt_enhancement.py
- C:\cursor\HomeIQ\TappsCodingAgents\tapps_agents\core\init_project.py
- C:\cursor\HomeIQ\TappsCodingAgents\tapps_agents\context7\cache_prewarm.py
- C:\cursor\HomeIQ\TappsCodingAgents\examples\visual_feedback_example.py
- C:\cursor\HomeIQ\services\ai-pattern-service\.venv\Lib\site-packages\scipy\integrate\_tanhsinh.py

### Existing Patterns
- {'type': 'architectural', 'name': 'Common Import Patterns', 'description': 'Commonly imported modules: asyncio, os, sys, traceback, math', 'examples': ['C:\\cursor\\HomeIQ\\scripts\\refresh-entities-from-ha-client.py', 'C:\\cursor\\HomeIQ\\.venv\\Lib\\site-packages\\scipy\\integrate\\_tanhsinh.py', 'C:\\cursor\\HomeIQ\\scripts\\refresh-context7-docs.py'], 'confidence': 1.0}

### Cross References
- {'source': 'C:\\cursor\\HomeIQ\\scripts\\cleanup-git-unified.py', 'target': 'C:\\cursor\\HomeIQ\\TappsCodingAgents\\tapps_agents\\core\\init_project.py', 'type': 'import', 'details': 'imports from tapps_agents.core.worktree'}
- {'source': 'C:\\cursor\\HomeIQ\\scripts\\cleanup-git-unified.py', 'target': 'C:\\cursor\\HomeIQ\\TappsCodingAgents\\tapps_agents\\core\\init_project.py', 'type': 'import', 'details': 'imports from tapps_agents.core.config'}
- {'source': 'C:\\cursor\\HomeIQ\\TappsCodingAgents\\tapps_agents\\core\\init_project.py', 'target': 'C:\\cursor\\HomeIQ\\TappsCodingAgents\\tapps_agents\\context7\\cache_prewarm.py', 'type': 'import', 'details': 'imports from tapps_agents.context7.commands'}
- {'source': 'C:\\cursor\\HomeIQ\\TappsCodingAgents\\tapps_agents\\core\\init_project.py', 'target': 'C:\\cursor\\HomeIQ\\TappsCodingAgents\\tapps_agents\\context7\\cache_prewarm.py', 'type': 'import', 'details': 'imports from tapps_agents.context7.security'}
- {'source': 'C:\\cursor\\HomeIQ\\TappsCodingAgents\\tapps_agents\\core\\init_project.py', 'target': 'C:\\cursor\\HomeIQ\\TappsCodingAgents\\tapps_agents\\context7\\cache_prewarm.py', 'type': 'import', 'details': 'imports from tapps_agents.context7.security'}
- {'source': 'C:\\cursor\\HomeIQ\\TappsCodingAgents\\examples\\visual_feedback_example.py', 'target': 'C:\\cursor\\HomeIQ\\TappsCodingAgents\\tapps_agents\\core\\init_project.py', 'type': 'import', 'details': 'imports from tapps_agents.core.browser_controller'}
- {'source': 'C:\\cursor\\HomeIQ\\TappsCodingAgents\\examples\\visual_feedback_example.py', 'target': 'C:\\cursor\\HomeIQ\\TappsCodingAgents\\tapps_agents\\core\\init_project.py', 'type': 'import', 'details': 'imports from tapps_agents.core.visual_feedback'}
- {'source': 'C:\\cursor\\HomeIQ\\TappsCodingAgents\\examples\\visual_feedback_example.py', 'target': 'C:\\cursor\\HomeIQ\\TappsCodingAgents\\tapps_agents\\core\\init_project.py', 'type': 'import', 'details': 'imports from tapps_agents.core.visual_feedback'}

## Quality Standards
### Code Quality Thresholds
- **Overall Score Threshold**: 70.0

## Implementation Strategy
## Enhanced Prompt