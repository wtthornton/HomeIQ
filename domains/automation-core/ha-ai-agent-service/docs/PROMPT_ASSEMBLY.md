# Prompt Assembly — Config-Driven System Prompt

**Epic 94 · Sprint 43**

The system prompt for ha-ai-agent-service is assembled from individual section files, controlled by a YAML config. This replaces the monolithic `SYSTEM_PROMPT` Python string constant with a file-based approach that supports prompt iteration without code changes.

## Architecture

```
src/prompts/
├── prompt_config.yaml      # Assembly config: section order, variables, headers
├── prompt_loader.py         # PromptLoader class — assembles from config
├── system_prompt.py         # Legacy constant (kept as fallback)
└── sections/
    ├── preamble.txt         # Opening line (before first section header)
    ├── 00_deployment_context.txt
    ├── 01_core_identity.txt
    ├── 02_mandatory_workflow.txt
    ├── 03_error_handling.txt
    ├── 03b_memory_context.txt
    ├── 04_context_entity_resolution.txt
    ├── 05_yaml_generation.txt
    ├── 05b_sports_automations.txt
    ├── 06_response_format.txt
    ├── 07_safety_security.txt
    ├── 08_rules_constraints.txt
    ├── 09_yaml_patterns_reference.txt
    └── 10_example_interaction.txt
```

## How It Works

1. `PromptLoader` reads `prompt_config.yaml`
2. Reads each enabled section file from `sections/`
3. Assembles: `preamble + [header + content]...` joined by `section_separator`
4. Substitutes template variables (`{ha_version}` etc.) from config defaults + env overrides
5. Returns the complete system prompt string

The `ContextBuilder.get_system_prompt()` method calls `PromptLoader.load()` — no other code changes needed.

## Iterating on Prompts

### Edit a section
1. Open the relevant `.txt` file in `src/prompts/sections/`
2. Make changes
3. Restart the container (prompt is loaded once at startup)

### Disable a section
Set `enabled: false` in `prompt_config.yaml`:
```yaml
  - name: sports_automations
    file: 05b_sports_automations.txt
    enabled: false  # Excluded from assembled prompt
```

### Reorder sections
Move entries in the `sections` list — order in config = order in prompt.

### Add a new section
1. Create `sections/11_new_section.txt`
2. Add entry to `prompt_config.yaml`:
```yaml
  - name: new_section
    file: 11_new_section.txt
    index: "11"
    title: "NEW SECTION TITLE"
    enabled: true
```

## Template Variables

Section files can use `{variable_name}` placeholders. Variables are resolved from:

| Priority | Source | Example |
|----------|--------|---------|
| 1 (highest) | `PROMPT_VAR_*` env vars | `PROMPT_VAR_HA_VERSION=2026.4` |
| 2 | `extra_vars` argument to `load()` | `loader.load(extra_vars={"ha_version": "3000"})` |
| 3 (lowest) | `variables` in `prompt_config.yaml` | `ha_version: "2025.10+/2026.x"` |

Currently defined variables:
- `{ha_version}` — Home Assistant version string (default: `2025.10+/2026.x`)
- `{ai_name}` — AI assistant name (default: `HomeIQ`)
- `{max_entities_per_area}` — Entity limit per area (default: `20`)

Unknown placeholders (e.g. `{entity_type}` in error templates) are left as-is.

## Custom Config Location

Set `PROMPT_CONFIG_PATH` env var to use a different config file:
```bash
PROMPT_CONFIG_PATH=/custom/prompt_config.yaml
```

## Fallback Behavior

If section files or config are missing/corrupt, `PromptLoader` falls back to the `SYSTEM_PROMPT` constant in `system_prompt.py`. A warning is logged:
```
⚠️ Failed to load prompt from config — falling back to SYSTEM_PROMPT constant
```

## Tests

```bash
cd domains/automation-core/ha-ai-agent-service
python -m pytest tests/test_prompt_loader.py -v
```

21 tests cover:
- Byte-identical regression (assembled == SYSTEM_PROMPT constant)
- Config validation (missing/invalid config → fallback)
- Missing section fallback
- Section ordering
- Disabled sections
- Token budget (< 32K tokens)
- Variable substitution (defaults, env overrides, extras, unknown vars)
- PromptLoader API (get_section, reload, load_raw, version)
