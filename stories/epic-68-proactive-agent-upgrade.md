# Epic 68: Proactive Agent Service — Autonomous Agent Upgrade

<!-- docsmcp:start:metadata -->
**Status:** Proposed
**Priority:** P1 - High
**Estimated LOE:** ~2-3 weeks (1 developer)
**Dependencies:** Epic 66 (classification for context), Memory Brain lib (homeiq-memory)

<!-- docsmcp:end:metadata -->

---

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

We are doing this so that proactive-agent-service evolves from a passive suggestion generator that delegates all execution to ha-ai-agent-service, into a lightweight autonomous agent that can observe home state, reason about proactive actions, evaluate confidence against user preference history via Memory Brain, and either act autonomously on high-confidence/low-risk actions or surface suggestions for user approval — making the smart home genuinely proactive rather than suggestion-only.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:goal -->
## Goal

Upgrade proactive-agent-service from a cron-triggered LLM prompt generator into a lightweight autonomous agent with its own observe-reason-act loop, Memory Brain integration for preference learning, confidence-based autonomous execution for low-risk actions, and feedback tracking to learn from accepted/rejected suggestions.

**Tech Stack:** homeiq, Python >=3.11

<!-- docsmcp:end:goal -->

<!-- docsmcp:start:motivation -->
## Motivation

proactive-agent-service currently generates text suggestions via LLM and throws them to ha-ai-agent-service for execution. It has no feedback loop, no preference learning, no confidence evaluation, and no ability to act on its own. The Memory Brain architecture (docs/planning/memory-brain-architecture.md) was designed for exactly this integration but is not wired in. Users must manually approve every suggestion even when the system has high confidence and the action is low-risk (e.g. turning off forgotten lights). This is the highest-ROI agent upgrade in the platform.

<!-- docsmcp:end:motivation -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] proactive-agent-service has an observe-reason-act loop that runs on configurable schedule
- [ ] Memory Brain integration: queries user preference history before generating suggestions
- [ ] Confidence scoring (0-100) on each suggestion based on: historical acceptance rate and action risk level and context match strength
- [ ] Low-risk high-confidence actions (>85 confidence and risk=low) execute autonomously via ha-device-control
- [ ] Medium/high-risk or low-confidence actions surface as suggestions for user approval
- [ ] Accepted/rejected suggestion outcomes are recorded in Memory Brain for preference learning
- [ ] User can configure autonomous execution thresholds and opt-out entirely
- [ ] All autonomous actions are logged with full audit trail and reversibility info
- [ ] Safety guardrails: never autonomously execute security-sensitive actions (locks and alarms and cameras)

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:stories -->
## Stories

### 68.1 -- Observe-Reason-Act Agent Loop

**Points:** 3

Replace the current cron-trigger → single-LLM-call → delegate pattern with an observe-reason-act loop. Observe: aggregate current home state (entities, weather, energy, time). Reason: LLM evaluates what proactive action would help with structured output (action, confidence, risk_level, reasoning). Act: route to autonomous execution or suggestion queue based on confidence/risk thresholds.

**Tasks:**
- [ ] Implement observe-reason-act agent loop
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Observe-Reason-Act Agent Loop is implemented, tests pass, and documentation is updated.

---

### 68.2 -- Memory Brain Integration — Preference Recall

**Points:** 3

Integrate homeiq-memory to query user preference history before generating suggestions. Recall: past suggestions for similar context (time of day, weather, occupancy), acceptance/rejection rates per action type, explicit user preferences ('never turn off office lights before 10pm'). Inject preference context into the LLM reasoning prompt.

**Tasks:**
- [ ] Implement memory brain integration — preference recall
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Memory Brain Integration — Preference Recall is implemented, tests pass, and documentation is updated.

---

### 68.3 -- Confidence & Risk Scoring Engine

**Points:** 3

Implement a scoring engine that evaluates each proposed action on two axes: confidence (0-100 based on historical acceptance, context match, preference alignment) and risk (low/medium/high/critical based on action type and reversibility). Define thresholds: auto-execute (confidence>85, risk=low), suggest (confidence>50 or risk=medium), suppress (confidence<30). Make thresholds configurable per user.

**Tasks:**
- [ ] Implement confidence & risk scoring engine
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Confidence & Risk Scoring Engine is implemented, tests pass, and documentation is updated.

---

### 68.4 -- Autonomous Execution Path

**Points:** 3

For actions that pass the auto-execute threshold, call ha-device-control directly instead of delegating to ha-ai-agent-service. Include: pre-execution state snapshot (for rollback), action execution via ha-device-control REST API, post-execution verification (confirm state changed), notification to user ('I turned off the kitchen lights — undo?'). Safety: never auto-execute lock/alarm/camera actions.

**Tasks:**
- [ ] Implement autonomous execution path
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Autonomous Execution Path is implemented, tests pass, and documentation is updated.

---

### 68.5 -- Feedback Loop — Outcome Recording

**Points:** 2

Record every suggestion outcome in Memory Brain: accepted (user sent to agent), rejected (user dismissed), auto-executed (system acted), auto-executed-undone (user reversed). Use outcomes to update preference scores per action type, time slot, and context. Decay old preferences (homeiq-memory handles TTL).

**Tasks:**
- [ ] Implement feedback loop — outcome recording
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Feedback Loop — Outcome Recording is implemented, tests pass, and documentation is updated.

---

### 68.6 -- User Configuration & Safety Guardrails

**Points:** 2

Add user-facing configuration: enable/disable autonomous execution, confidence threshold slider (default 85), excluded device categories (default: locks, alarms, cameras), quiet hours (no autonomous actions). Store in PostgreSQL user_preferences table. Expose via admin-api endpoints.

**Tasks:**
- [ ] Implement user configuration & safety guardrails
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** User Configuration & Safety Guardrails is implemented, tests pass, and documentation is updated.

---

### 68.7 -- Audit Trail & Reversibility

**Points:** 2

Log every autonomous action with: timestamp, action taken, confidence score, risk level, pre-action state snapshot, reasoning summary. Expose via GET /api/proactive/audit endpoint. Add 'undo last action' capability that restores the pre-action state snapshot within a configurable window (default 15 minutes).

**Tasks:**
- [ ] Implement audit trail & reversibility
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Audit Trail & Reversibility is implemented, tests pass, and documentation is updated.

---

### 68.8 -- Integration Tests & Safety Validation

**Points:** 2

End-to-end tests: autonomous execution of low-risk action with high confidence, suggestion surfacing for medium-risk action, safety guardrail blocks lock/alarm auto-execution, preference learning improves confidence over 5 iterations, undo reverses autonomous action, quiet hours suppression. Use real Memory Brain and ha-device-control instances.

**Tasks:**
- [ ] Implement integration tests & safety validation
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Integration Tests & Safety Validation is implemented, tests pass, and documentation is updated.

---

<!-- docsmcp:end:stories -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- proactive-agent-service is at domains/energy-analytics/proactive-agent-service/ port 8046
- Currently uses gpt-4o-mini for prompt generation — keep for reasoning step
- ha-device-control at port 8040 has REST endpoints for lights/switches/climate/scenes — use for autonomous execution
- homeiq-memory lib provides Memory Brain client with save/search/consolidate
- Memory types for preferences: 'preference' (60d TTL) and 'outcome' (30d TTL)
- Safety-critical entity domains: lock alarm camera — hardcoded blocklist not configurable
- Existing CrossGroupClient in homeiq-resilience handles inter-service calls with circuit breaker

**Project Structure:** 0 packages, 0 modules, 0 public APIs

### Expert Recommendations

- **Security Expert** (68%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
- **Software Architecture Expert** (62%): *Principal software architect focused on clean architecture, domain-driven design, and evolutionary system design.*

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:non-goals -->
## Out of Scope / Future Considerations

- Multi-agent coordination between proactive-agent and ha-ai-agent-service
- Natural language conversation — proactive agent is background-only
- Replacing ha-ai-agent-service as the primary user-facing agent
- Energy optimization algorithms — that stays in energy-correlator and energy-forecasting

<!-- docsmcp:end:non-goals -->

<!-- docsmcp:start:success-metrics -->
## Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| All 9 acceptance criteria met | 0/9 | 9/9 | Checklist review |
| All 8 stories completed | 0/8 | 8/8 | Sprint board |

<!-- docsmcp:end:success-metrics -->

<!-- docsmcp:start:implementation-order -->
## Implementation Order

1. Story 68.1: Observe-Reason-Act Agent Loop
2. Story 68.2: Memory Brain Integration — Preference Recall
3. Story 68.3: Confidence & Risk Scoring Engine
4. Story 68.4: Autonomous Execution Path
5. Story 68.5: Feedback Loop — Outcome Recording
6. Story 68.6: User Configuration & Safety Guardrails
7. Story 68.7: Audit Trail & Reversibility
8. Story 68.8: Integration Tests & Safety Validation

<!-- docsmcp:end:implementation-order -->

<!-- docsmcp:start:risk-assessment -->
## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Autonomous execution of wrong action could frustrate users — mitigated by conservative default thresholds and mandatory undo window | Medium | Medium | Warning: Mitigation required - no automated recommendation available |
| Memory Brain preference learning could reinforce bad patterns — mitigated by preference decay and explicit user overrides | Medium | Medium | Warning: Mitigation required - no automated recommendation available |
| Additional LLM calls per cycle increase OpenAI costs — mitigated by using gpt-4o-mini and caching similar contexts | Medium | Medium | Warning: Mitigation required - no automated recommendation available |
| Safety guardrail bypass via misconfigured entity domains — mitigated by hardcoded blocklist for security-sensitive domains | Medium | Medium | *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*. |

**Expert-Identified Risks:**

- **Security Expert**: *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*

<!-- docsmcp:end:risk-assessment -->

<!-- docsmcp:start:files-affected -->
## Files Affected

| File | Story | Action |
|---|---|---|
| Files will be determined during story refinement | - | - |

<!-- docsmcp:end:files-affected -->
