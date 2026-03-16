# Story 70.2 -- Skills Guard (Security Scanner)

<!-- docsmcp:start:user-story -->

> **As a** system operator, **I want** all agent-generated skills to be security-scanned before storage, **so that** malicious or hallucinated content cannot be injected into the agent's procedural memory

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that every skill the agent creates (70.1) is scanned against 100+ threat patterns before being stored. This is the mandatory safety pair for skill learning — they ship together.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Port the security scanning engine from Hermes Agent `skills_guard.py`. Implement 100+ regex patterns covering prompt injection, HA-specific dangerous services, exfiltration, destructive commands, and invisible Unicode characters. Scanner runs synchronously before skill storage (block on fail) and asynchronously on skill recall (exclude flagged skills from context).

See [Epic 70](stories/epic-70-hermes-self-improving-agent.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/automation-core/ha-ai-agent-service/src/services/skill_learning/skills_guard.py`
- `domains/automation-core/ha-ai-agent-service/src/services/skill_learning/threat_patterns.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create `threat_patterns.py` with categorized regex patterns: INJECTION (20+), EXFILTRATION (15+), DESTRUCTIVE (10+), HA_DANGEROUS (10+), PERSISTENCE (10+), NETWORK (10+), PRIVILEGE_ESCALATION (10+), SUPPLY_CHAIN (10+), INVISIBLE_CHARS (5+)
- [ ] Add HA-specific patterns: `shell_command`, `command_line`, `python_script`, `pyscript`, `hassio`, `rest_command` service calls in YAML
- [ ] Implement `SkillsGuard.scan(content: str) → ScanResult(verdict: str, findings: list, severity: str)`
- [ ] Verdicts: "clean", "suspicious" (warn), "dangerous" (block)
- [ ] Wire into `SkillStore.create()` — block storage if verdict is "dangerous"
- [ ] Wire into `SkillRecall` — exclude "dangerous" skills, log "suspicious" skills
- [ ] Add invisible character detection (zero-width spaces, directional overrides, homoglyphs)
- [ ] Write unit tests with known-bad samples for each threat category
- [ ] Log all scan results with skill_id for audit trail

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] 100+ regex patterns across 9 threat categories
- [ ] HA-specific patterns block shell_command, command_line, python_script, pyscript, hassio, rest_command
- [ ] Dangerous skills are blocked from storage with error returned to agent
- [ ] Suspicious skills are flagged in logs but allowed (with warning)
- [ ] Invisible Unicode characters are detected and flagged
- [ ] All scan results logged with skill_id for audit
- [ ] Scanner runs in <100ms for typical skill content

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 70](stories/epic-70-hermes-self-improving-agent.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_scan_clean_skill_passes` -- Normal automation skill passes scan
2. `test_scan_prompt_injection_blocked` -- "ignore previous instructions" detected as dangerous
3. `test_scan_ha_shell_command_blocked` -- YAML with shell_command service detected as dangerous
4. `test_scan_ha_pyscript_blocked` -- YAML with pyscript service detected as dangerous
5. `test_scan_exfiltration_blocked` -- Environment variable theft pattern detected
6. `test_scan_invisible_unicode_flagged` -- Zero-width characters detected as suspicious
7. `test_scan_large_content_flagged` -- Content exceeding 256KB flagged as suspicious
8. `test_scan_performance_under_100ms` -- Scan completes in <100ms for 10KB content

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Ships together with Story 70.1 (Skill Learning)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [ ] **I**ndependent -- Must ship with 70.1
- [x] **N**egotiable -- Pattern list can be expanded incrementally
- [x] **V**aluable -- Prevents prompt injection and dangerous HA commands in skills
- [x] **E**stimable -- Clear scope: regex library + scanner + integration
- [x] **S**mall -- 3 points, well-scoped
- [x] **T**estable -- Each threat category has test samples

<!-- docsmcp:end:invest -->
