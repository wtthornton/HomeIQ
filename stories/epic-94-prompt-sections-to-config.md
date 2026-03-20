# Epic 94: Prompt Sections to Config Files

**Priority:** P1 High
**Effort:** 3–4 days (5 stories, 18 points)
**Sprint:** 43
**Depends on:** None
**Origin:** Sapphire Review — Pattern 9 (prompt pieces as structured data) + Pattern 1 (composable prompts)

## Problem Statement

HomeIQ's system prompt is a 1,033-line Python string constant in `system_prompt.py`. It's well-structured with 9 numbered sections, versioned (v2.1.0), and has clear separation of concerns. However:

1. **Changing any prompt text requires a code change** — edit Python, rebuild Docker image, redeploy container
2. **Prompt iteration is slow** — the prompt has already been through multiple versions (v2.0 → v2.1.0), each requiring a full deploy cycle
3. **No A/B testing** — can't compare two prompt variants without code branching
4. **Tightly coupled** — runtime context injection (`prompt_assembly_service.py`) is interleaved with static prompt text loading
5. **No hot-reload** — prompt changes require container restart

The system prompt has 9 clear sections that are natural extraction points:
- Section 0: Deployment Context
- Section 1: Core Identity & Constraints
- Section 2: Mandatory Workflow
- Section 3: Error Handling & Failure Modes
- Section 3B: Memory Context
- Section 4: Context Usage & Entity Resolution
- Section 5: YAML Generation & Validation
- Section 5B: Sports-Based Automations
- Section 6: Response Format
- Section 7: Safety & Security
- Section 8: Rules & Constraints
- Section 9: YAML Patterns Reference

## Approach

1. Extract each section to a standalone text file
2. Create a prompt config that defines section ordering and inclusion
3. Load and assemble at startup (with optional hot-reload)
4. Keep `prompt_assembly_service.py` unchanged — it handles runtime context, not static prompt text
5. Maintain backward compatibility — assembled prompt must be identical to current `SYSTEM_PROMPT`

---

## Story 94.1: Extract Prompt Sections to Text Files

**Points:** 3 | **Type:** Refactor
**Goal:** Each system prompt section lives in its own text file

### Tasks

- [ ] **94.1.1** Create directory `domains/automation-core/ha-ai-agent-service/src/prompts/sections/`
- [ ] **94.1.2** Extract each section to a numbered file:
  ```
  sections/
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
  └── 09_yaml_patterns_reference.txt
  ```
- [ ] **94.1.3** Each file contains only the section content (no Python string delimiters, no section header bars — those are added during assembly)
- [ ] **94.1.4** Verify: concatenating all files with section headers produces byte-identical output to current `SYSTEM_PROMPT`

### Acceptance Criteria

- [ ] All 12 section files exist and are valid text
- [ ] `diff` between assembled output and current `SYSTEM_PROMPT` shows zero differences
- [ ] Section files are under version control

---

## Story 94.2: Create Prompt Assembly Config

**Points:** 3 | **Type:** Feature
**Goal:** YAML config defines which sections to include, their order, and optional overrides

### Tasks

- [ ] **94.2.1** Create `domains/automation-core/ha-ai-agent-service/src/prompts/prompt_config.yaml`:
  ```yaml
  # Prompt Assembly Configuration
  # Defines which sections are included and in what order.
  # Each section maps to a file in sections/ directory.
  version: "2.1.0"

  sections:
    - name: deployment_context
      file: 00_deployment_context.txt
      enabled: true
    - name: core_identity
      file: 01_core_identity.txt
      enabled: true
    - name: mandatory_workflow
      file: 02_mandatory_workflow.txt
      enabled: true
    - name: error_handling
      file: 03_error_handling.txt
      enabled: true
    - name: memory_context
      file: 03b_memory_context.txt
      enabled: true
    - name: context_entity_resolution
      file: 04_context_entity_resolution.txt
      enabled: true
    - name: yaml_generation
      file: 05_yaml_generation.txt
      enabled: true
    - name: sports_automations
      file: 05b_sports_automations.txt
      enabled: true
    - name: response_format
      file: 06_response_format.txt
      enabled: true
    - name: safety_security
      file: 07_safety_security.txt
      enabled: true
    - name: rules_constraints
      file: 08_rules_constraints.txt
      enabled: true
    - name: yaml_patterns_reference
      file: 09_yaml_patterns_reference.txt
      enabled: true

  # Section header template (inserted between sections)
  section_separator: "\n\n"
  header_template: |
    # ═══════════════════════════════════════════════════════════════════════════════
    # SECTION {index}: {title}
    # ═══════════════════════════════════════════════════════════════════════════════
  ```
- [ ] **94.2.2** Support `enabled: false` to exclude sections (e.g., disable sports automations)
- [ ] **94.2.3** Support `PROMPT_CONFIG_PATH` env var for custom config location

### Acceptance Criteria

- [ ] Config loads and is validated at startup (missing file → clear error)
- [ ] Disabling a section removes it from assembled prompt
- [ ] Section order in config determines order in assembled prompt

---

## Story 94.3: Implement Prompt Loader Service

**Points:** 5 | **Type:** Feature
**Goal:** Replace `SYSTEM_PROMPT` constant with a loader that assembles from config + section files

### Tasks

- [ ] **94.3.1** Create `src/prompts/prompt_loader.py`:
  ```python
  class PromptLoader:
      """Loads and assembles system prompt from section files."""

      def __init__(self, config_path: str | None = None):
          ...

      def load(self) -> str:
          """Load config, read section files, assemble prompt."""
          ...

      def get_section(self, name: str) -> str | None:
          """Get a specific section by name (for targeted updates)."""
          ...

      @property
      def version(self) -> str:
          """Prompt version from config."""
          ...
  ```
- [ ] **94.3.2** Update `context_builder.py` line 19: change `from ..prompts.system_prompt import SYSTEM_PROMPT` to use `PromptLoader`
- [ ] **94.3.3** Keep `system_prompt.py` as a fallback — if section files are missing, fall back to the constant (graceful degradation)
- [ ] **94.3.4** Add startup log: `"✅ System prompt loaded from config (v2.1.0, 12 sections, {token_count} tokens)"`
- [ ] **94.3.5** Add unit tests: loader assembles correctly, missing section → clear error, disabled section → excluded, fallback works

### Acceptance Criteria

- [ ] Service starts and loads prompt from section files
- [ ] Assembled prompt is identical to current `SYSTEM_PROMPT` (regression test)
- [ ] If section files are missing, falls back to `SYSTEM_PROMPT` constant with warning
- [ ] Token count is logged at startup

---

## Story 94.4: Template Variable Support

**Points:** 3 | **Type:** Enhancement
**Goal:** Section files support `{variable}` placeholders resolved at load time

### Tasks

- [ ] **94.4.1** Add `variables` section to `prompt_config.yaml`:
  ```yaml
  variables:
    ha_version: "2025.10+/2026.x"
    ai_name: "HomeIQ"
    max_entities_per_area: "20"
  ```
- [ ] **94.4.2** In `PromptLoader.load()`: replace `{variable_name}` placeholders in section text with config values
- [ ] **94.4.3** Support env var override: `PROMPT_VAR_HA_VERSION=2026.4` overrides config value
- [ ] **94.4.4** Update section files to use variables where currently hardcoded (e.g., `Home Assistant 2025.10+/2026.x` → `Home Assistant {ha_version}`)
- [ ] **94.4.5** Add unit tests: variable substitution, env var override, missing variable → warning (leave placeholder as-is)

### Acceptance Criteria

- [ ] `{ha_version}` in section files resolves to config value
- [ ] Env var `PROMPT_VAR_HA_VERSION` overrides config
- [ ] Unknown variables left as-is with warning logged (no crash)

---

## Story 94.5: Validation & Regression Tests

**Points:** 4 | **Type:** Testing
**Goal:** Comprehensive tests ensure prompt assembly is correct and backward-compatible

### Tasks

- [ ] **94.5.1** Regression test: assembled prompt from loader == current `SYSTEM_PROMPT` constant (byte-for-byte)
- [ ] **94.5.2** Integration test: `PromptAssemblyService.assemble_messages()` produces identical output with loader vs constant
- [ ] **94.5.3** Config validation test: invalid YAML config → clear error message
- [ ] **94.5.4** Missing section file test: missing file → fallback to constant + warning
- [ ] **94.5.5** Section ordering test: reordered config produces reordered prompt
- [ ] **94.5.6** Disabled section test: `enabled: false` removes section from output
- [ ] **94.5.7** Token count test: assembled prompt fits within `MAX_INPUT_TOKENS` budget (32K)
- [ ] **94.5.8** Add `PROMPT_ASSEMBLY.md` documenting the config format, variables, and how to iterate on prompts

### Acceptance Criteria

- [ ] All regression tests pass
- [ ] Changing a section file and reloading produces updated prompt
- [ ] Documentation explains the prompt iteration workflow

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Prompt regression | Byte-for-byte comparison test against current constant |
| Missing section files in Docker | Dockerfile `COPY prompts/ ...` + fallback to constant |
| Config syntax errors | Validate at startup, fail fast with clear message |
| Variable injection attacks | Variables are from config/env, not user input |
| Performance (file I/O) | Load once at startup, cache assembled prompt |
