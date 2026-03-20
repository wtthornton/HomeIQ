# Epic 93: Entity Safety Blacklisting

**Priority:** P0 Critical — Security Gap
**Status:** ✅ COMPLETE (Sprint 43, 2026-03-19)
**Effort:** 2 days (5 stories, 15 points)
**Sprint:** 43
**Depends on:** None
**Origin:** Sapphire Review — Pattern 5 (entity blacklisting)

## Problem Statement

HomeIQ exposes every Home Assistant entity to the LLM — including locks, alarm panels, garage doors, and water valves. The AI can generate automation YAML that controls these security-sensitive devices. While the system prompt (Section 7) instructs the AI to warn about critical entities, and `yaml-validation-service` Stage 5 produces safety *warnings*, neither layer actually **blocks** dangerous automations.

Current gaps:
1. **Context layer**: `enhanced_context_builder.py` sends lock/alarm entities to the LLM — the AI can reference them in generated YAML
2. **Validation layer**: `validator.py` Stage 5 scores safety and produces warnings but returns `valid: True` — dangerous YAML passes validation
3. **No configurable blacklist**: Safety-sensitive entities are hardcoded across multiple files with no central configuration
4. **No enforcement**: A user can say "unlock the front door when I leave" and the pipeline will preview, approve, and deploy it

## Approach

Defense in depth — filter at context injection AND reject at validation:
1. Configurable blacklist (central YAML config)
2. Filter blacklisted entities from LLM context (can't reference what you can't see)
3. Reject YAML containing blacklisted entities at validation (catch prompt injection / hallucination)
4. Admin override for power users who understand the risk

---

## Story 93.1: Create Entity Blacklist Configuration

**Points:** 2 | **Type:** Feature
**Goal:** Single YAML config file defines which entities/domains are blocked from AI automation

### Tasks

- [ ] **93.1.1** Create `domains/automation-core/ha-ai-agent-service/src/config/entity_blacklist.yaml`:
  ```yaml
  # Entity Safety Blacklist
  # Entities/domains listed here are filtered from AI context and rejected in validation.
  # Override with ENTITY_BLACKLIST_OVERRIDE=domain1,domain2 env var for admin access.

  blocked_domains:
    - lock              # Door locks
    - alarm_control_panel  # Security alarms

  blocked_entities:
    # Add specific entity_ids here
    # - cover.garage_door
    # - switch.main_water_valve

  blocked_services:
    - lock.lock
    - lock.unlock
    - alarm_control_panel.alarm_arm_away
    - alarm_control_panel.alarm_arm_home
    - alarm_control_panel.alarm_disarm

  # Entities that produce warnings but aren't blocked
  warn_domains:
    - cover             # Garage doors, blinds
    - siren             # Sirens
    - valve             # Water valves
  ```
- [ ] **93.1.2** Add `EntityBlacklist` class in `src/config/entity_blacklist.py` to load and query the config
- [ ] **93.1.3** Support `ENTITY_BLACKLIST_OVERRIDE` env var to allow admin override (comma-separated domains to unblock)
- [ ] **93.1.4** Add unit tests for blacklist loading, querying, and override

### Acceptance Criteria

- [ ] Blacklist config loads at service startup
- [ ] `EntityBlacklist.is_blocked(entity_id)` returns True for `lock.front_door`
- [ ] `EntityBlacklist.is_blocked(entity_id)` returns False for `light.office`
- [ ] `EntityBlacklist.is_warned(entity_id)` returns True for `cover.garage_door`
- [ ] Override env var unblocks specified domains

---

## Story 93.2: Filter Blacklisted Entities from LLM Context

**Points:** 3 | **Type:** Enhancement
**Goal:** `enhanced_context_builder.py` excludes blacklisted entities so the LLM never sees them

### Tasks

- [ ] **93.2.1** Inject `EntityBlacklist` into `EnhancedContextBuilder.__init__()` (load from config)
- [ ] **93.2.2** In `build_area_entity_context()`: skip entities whose domain is in `blocked_domains` or entity_id is in `blocked_entities`
- [ ] **93.2.3** In `build_binary_sensor_context()`: skip blocked binary sensors (unlikely but defensive)
- [ ] **93.2.4** In `build_existing_automations_context()`: do NOT filter — show existing lock/alarm automations so AI knows they exist (for duplicate detection)
- [ ] **93.2.5** Add `[FILTERED]` summary line: "Note: {N} security-sensitive entities filtered (locks, alarms). Use HomeIQ Admin to manage these devices."
- [ ] **93.2.6** Add unit tests: verify `lock.*` entities are excluded from context output, `light.*` entities are included

### Acceptance Criteria

- [ ] `build_area_entity_context()` output contains zero `lock.*` or `alarm_control_panel.*` entities
- [ ] `build_area_entity_context()` output contains a filtered count notice
- [ ] `cover.*` entities appear with a warning annotation (warn_domains)
- [ ] Existing automations context still shows lock/alarm automations (duplicate detection)

---

## Story 93.3: Reject Blacklisted Entities in YAML Validation

**Points:** 3 | **Type:** Enhancement
**Goal:** `yaml-validation-service` Stage 5 rejects (not just warns) YAML targeting blacklisted entities/services

### Tasks

- [ ] **93.3.1** Add blacklist config loading to `yaml-validation-service` (shared config or API call to ha-ai-agent-service)
- [ ] **93.3.2** In `_validate_safety()`: check all `entity_id` references in triggers and actions against blacklist
- [ ] **93.3.3** If a blocked entity or service is found, set `result.valid = False` and add error (not warning):
  ```
  "❌ BLOCKED: Automation targets security-sensitive entity '{entity_id}'.
   Lock and alarm automations must be created directly in Home Assistant."
  ```
- [ ] **93.3.4** Keep existing warning behavior for `warn_domains` (covers, sirens, valves)
- [ ] **93.3.5** Add `X-Safety-Override: true` header support for admin bypass (matches env var override)
- [ ] **93.3.6** Add unit tests: YAML with `lock.unlock` in actions → `valid: False`, YAML with `light.turn_on` → `valid: True`

### Acceptance Criteria

- [ ] YAML containing `lock.*` entity_ids in trigger or action → validation fails
- [ ] YAML containing `alarm_control_panel.alarm_disarm` service call → validation fails
- [ ] YAML containing `cover.garage_door` → validation passes with warning
- [ ] YAML containing only `light.*`, `switch.*`, `sensor.*` → validation passes clean
- [ ] Safety override header bypasses the block (admin use)

---

## Story 93.4: Update System Prompt Safety Section

**Points:** 2 | **Type:** Enhancement
**Goal:** System prompt Section 7 reflects the new enforcement (not just guidance)

### Tasks

- [ ] **93.4.1** Update `system_prompt.py` Section 7 to inform the LLM that lock/alarm entities are not available:
  ```
  ## Blocked Entities (NOT in your context)
  Lock, alarm, and security entities are NOT provided in your context and cannot be used in automations.
  If a user asks to automate locks or alarms, respond:
  "For security reasons, lock and alarm automations must be created directly in Home Assistant.
   I can help you with lighting, climate, sensor, and other non-security automations."
  ```
- [ ] **93.4.2** Update the Safety Classification table: Critical category changes from "Require explicit confirmation" to "Blocked — not available"
- [ ] **93.4.3** Keep warning language for covers/garage doors (warn_domains — still in context)
- [ ] **93.4.4** Add integration test: send "unlock front door when I leave" prompt → verify AI response says it can't automate locks

### Acceptance Criteria

- [ ] System prompt Section 7 clearly states locks/alarms are blocked, not just warned
- [ ] LLM response to lock/alarm request provides helpful redirect (create in HA directly)
- [ ] Cover/garage door requests still work but include safety warning

---

## Story 93.5: Documentation & Admin Guide

**Points:** 2 | **Type:** Documentation
**Goal:** Document the safety system for operators and users

### Tasks

- [ ] **93.5.1** Add `ENTITY_SAFETY.md` to `domains/automation-core/ha-ai-agent-service/docs/`:
  - What's blocked and why
  - How to customize the blacklist
  - How to use admin override (env var + header)
  - Examples of blocked vs allowed automations
- [ ] **93.5.2** Update `ha-ai-agent-service/README.md` with safety section
- [ ] **93.5.3** Add blacklist config to Docker Compose environment section (document the env var)

### Acceptance Criteria

- [ ] Admin can find and understand how to customize the blacklist
- [ ] Override mechanism is documented with security implications noted

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Users need lock automations | Admin override via env var + header |
| Blacklist out of sync between services | Shared config file, or ha-ai-agent-service exposes `/api/v1/blacklist` endpoint |
| LLM hallucinates blocked entity IDs | Validation layer catches even if context filtering misses |
| Breaking existing automations | Only blocks *creation* — existing automations are unaffected |
